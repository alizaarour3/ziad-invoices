from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont, ImageOps, features
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

from ..settings import ATTACHMENTS_DIR, GENERATED_DIR, STATIC_DIR, TEMPLATES_DIR

# Exact ISO A4 canvas at 300 DPI.
A4_DPI = 300
A4_SIZE = (2480, 3508)
BASE_EDITOR_WIDTH = 794
HTML_DATA_MIN_FONT_PT = 16
HTML_DATA_MIN_FONT_PX = HTML_DATA_MIN_FONT_PT * 96 / 72

logger = logging.getLogger(__name__)


ARABIC_RANGES = (
    (0x0600, 0x06FF),
    (0x0750, 0x077F),
    (0x08A0, 0x08FF),
    (0xFB50, 0xFDFF),
    (0xFE70, 0xFEFF),
)


def _has_arabic(text: str) -> bool:
    return any(start <= ord(char) <= end for char in text for start, end in ARABIC_RANGES)


def arabic_rendering_status() -> dict[str, Any]:
    """Expose the state of the shaping engine used for Arabic/RTL output.

    RAQM is required for correct Arabic contextual shaping and BiDi ordering in
    Pillow. The production Docker image installs and verifies it at build time.
    """
    return {
        "raqm": bool(features.check("raqm")),
        "harfbuzz": bool(features.check("harfbuzz")),
        "fribidi": bool(features.check("fribidi")),
    }


def _field_text(value: Any, field_type: str) -> str:
    if field_type == "checkbox":
        return "✓" if value in (True, 1, "1", "true", "on", "yes") else ""
    if value is None:
        return ""
    return str(value).strip()


def _find_font(
    size: int,
    *,
    bold: bool = True,
    direction: str = "ltr",
) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    # Prefer fonts designed for Arabic when drawing RTL fields. This keeps
    # Arabic glyph proportions stable on Linux/Render while preserving the
    # Windows Arial/Segoe fallbacks used by the desktop build.
    arabic_regular = [
        # These fonts contain Arabic + Latin + digits/symbols in one file,
        # which is important for mixed strings such as Arabic text with 350,000.
        Path(r"C:\\Windows\\Fonts\\arial.ttf"),
        Path(r"C:\\Windows\\Fonts\\segoeui.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/noto/NotoSansArabic-Regular.ttf"),
        Path("/usr/share/fonts/truetype/noto/NotoNaskhArabic-Regular.ttf"),
    ]
    arabic_bold = [
        Path(r"C:\\Windows\\Fonts\\arialbd.ttf"),
        Path(r"C:\\Windows\\Fonts\\segoeuib.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf"),
        Path("/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf"),
    ]
    regular = [
        Path(r"C:\\Windows\\Fonts\\arial.ttf"),
        Path(r"C:\\Windows\\Fonts\\segoeui.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf"),
    ]
    bold_fonts = [
        Path(r"C:\\Windows\\Fonts\\arialbd.ttf"),
        Path(r"C:\\Windows\\Fonts\\segoeuib.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf"),
    ]
    if direction == "rtl":
        candidates = (arabic_bold if bold else arabic_regular) + arabic_regular + regular
    else:
        candidates = (bold_fonts if bold else regular) + regular

    layout_engine = ImageFont.Layout.RAQM if features.check("raqm") else ImageFont.Layout.BASIC
    for candidate in candidates:
        if candidate.exists():
            return ImageFont.truetype(
                str(candidate),
                size=max(1, size),
                layout_engine=layout_engine,
            )
    return ImageFont.load_default()


def _direction_kwargs(direction: str) -> dict[str, str]:
    if direction not in {"rtl", "ltr"}:
        return {}
    if not features.check("raqm"):
        return {}
    if direction == "rtl":
        return {"direction": "rtl", "language": "ar"}
    return {"direction": "ltr"}


def _text_bbox(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, direction: str) -> tuple[int, int, int, int]:
    kwargs = {"font": font, "spacing": 4, **_direction_kwargs(direction)}
    try:
        return draw.textbbox((0, 0), text, **kwargs)
    except (TypeError, ValueError):
        kwargs.pop("direction", None)
        return draw.textbbox((0, 0), text, **kwargs)


def _wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.ImageFont,
    max_width: int,
    direction: str,
    *,
    multiline: bool,
) -> list[str]:
    if not text:
        return [""]
    explicit_lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if not multiline:
        return [" ".join(explicit_lines).strip()]

    lines: list[str] = []
    for explicit in explicit_lines:
        words = explicit.split()
        if not words:
            lines.append("")
            continue
        current = ""
        for word in words:
            trial = f"{current} {word}".strip()
            bbox = _text_bbox(draw, trial, font, direction)
            width = bbox[2] - bbox[0]
            if current and width > max_width:
                lines.append(current)
                current = word
            else:
                current = trial
        lines.append(current)
    return lines or [""]


def _fit_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    *,
    initial_size: int,
    min_size: int,
    max_width: int,
    max_height: int,
    direction: str,
    multiline: bool,
    bold: bool,
) -> tuple[ImageFont.ImageFont, list[str], int]:
    size = max(min_size, initial_size)
    while size >= min_size:
        font = _find_font(size, bold=bold, direction=direction)
        lines = _wrap_text(draw, text, font, max_width, direction, multiline=multiline)
        line_height = max(size + max(4, round(size * 0.2)), 12)
        widths = [(_text_bbox(draw, line, font, direction)[2] - _text_bbox(draw, line, font, direction)[0]) for line in lines]
        total_height = len(lines) * line_height
        if (not widths or max(widths) <= max_width) and total_height <= max_height:
            return font, lines, line_height
        size -= 1
    font = _find_font(min_size, bold=bold, direction=direction)
    lines = _wrap_text(draw, text, font, max_width, direction, multiline=multiline)
    return font, lines, max(min_size + 4, 12)


def _draw_text_box(
    draw: ImageDraw.ImageDraw,
    value: str,
    box: tuple[int, int, int, int],
    *,
    font_size: int,
    min_font_size: int,
    align: str,
    direction: str,
    multiline: bool,
    bold: bool = True,
) -> None:
    x, y, w, h = box
    if direction == "rtl" and _has_arabic(value or "") and not features.check("raqm"):
        raise RuntimeError(
            "Arabic/RTL rendering is unavailable because Pillow RAQM support is missing. "
            "Use the production Docker image or install a Pillow build with RAQM/Harfbuzz/FriBiDi."
        )
    padding_x = max(8, round(w * 0.012))
    padding_y = max(4, round(h * 0.05))
    max_width = max(1, w - 2 * padding_x)
    max_height = max(1, h - 2 * padding_y)
    font, lines, line_height = _fit_text(
        draw,
        value or "",
        initial_size=font_size,
        min_size=min_font_size,
        max_width=max_width,
        max_height=max_height,
        direction=direction,
        multiline=multiline,
        bold=bold,
    )
    total_height = min(len(lines) * line_height, max_height)
    cursor_y = y + padding_y + max(0, (max_height - total_height) // 2)
    draw_kwargs: dict[str, Any] = {
        "font": font,
        "fill": "#111111",
        "spacing": 4,
        **_direction_kwargs(direction),
    }
    for line in lines:
        if cursor_y + line_height > y + h - padding_y + 1:
            break
        if align == "center":
            anchor_x, anchor = x + w / 2, "mm"
        elif align == "right":
            anchor_x, anchor = x + w - padding_x, "rm"
        else:
            anchor_x, anchor = x + padding_x, "lm"
        anchor_y = cursor_y + line_height / 2
        anchored_kwargs = {**draw_kwargs, "anchor": anchor}
        try:
            draw.text((anchor_x, anchor_y), line, **anchored_kwargs)
        except (TypeError, ValueError):
            # Older Pillow builds may reject direction or advanced anchors.
            anchored_kwargs.pop("direction", None)
            try:
                draw.text((anchor_x, anchor_y), line, **anchored_kwargs)
            except (TypeError, ValueError):
                anchored_kwargs.pop("anchor", None)
                bbox = _text_bbox(draw, line, font, direction)
                line_width = bbox[2] - bbox[0]
                glyph_height = bbox[3] - bbox[1]
                if align == "center":
                    desired_left = x + max(0, (w - line_width) // 2)
                elif align == "right":
                    desired_left = x + max(padding_x, w - line_width - padding_x)
                else:
                    desired_left = x + padding_x
                draw_x = desired_left - bbox[0]
                draw_y = cursor_y + max(0, (line_height - glyph_height) // 2) - bbox[1]
                draw.text((draw_x, draw_y), line, **anchored_kwargs)
        cursor_y += line_height



def _split_configured_lines(value: str, count: int) -> list[str]:
    normalized = (value or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")
    if len(lines) > count:
        lines = lines[: count - 1] + [" ".join(part.strip() for part in lines[count - 1 :] if part.strip())]
    return (lines + [""] * count)[:count]


def _draw_configured_field(
    draw: ImageDraw.ImageDraw,
    *,
    field: dict[str, Any],
    value: str,
    canvas_width: int,
    canvas_height: int,
) -> None:
    css_size = int(field.get("font_size", 17))
    min_css = int(field.get("min_font_size", max(9, css_size - 6)))
    common = {
        "font_size": max(18, round(css_size * canvas_width / BASE_EDITOR_WIDTH)),
        "min_font_size": max(14, round(min_css * canvas_width / BASE_EDITOR_WIDTH)),
        "align": field.get("align", "center"),
        "direction": field.get("direction") or "ltr",
        "bold": field.get("font_weight", "bold") != "normal",
    }
    line_boxes = field.get("line_boxes") or []
    if line_boxes:
        for line, line_box in zip(_split_configured_lines(value, len(line_boxes)), line_boxes):
            box = (
                round(canvas_width * float(line_box["x"]) / 100),
                round(canvas_height * float(line_box["y"]) / 100),
                round(canvas_width * float(line_box["w"]) / 100),
                round(canvas_height * float(line_box.get("h", field.get("line_height", 2.4))) / 100),
            )
            _draw_text_box(draw, line, box, multiline=False, **common)
        return
    line_positions = field.get("line_positions") or []
    if line_positions:
        line_height = float(field.get("line_height", field.get("h", 2.4)))
        for line, top in zip(_split_configured_lines(value, len(line_positions)), line_positions):
            box = (
                round(canvas_width * float(field["x"]) / 100),
                round(canvas_height * float(top) / 100),
                round(canvas_width * float(field["w"]) / 100),
                round(canvas_height * line_height / 100),
            )
            _draw_text_box(draw, line, box, multiline=False, **common)
        return
    box = (
        round(canvas_width * float(field["x"]) / 100),
        round(canvas_height * float(field["y"]) / 100),
        round(canvas_width * float(field["w"]) / 100),
        round(canvas_height * float(field["h"]) / 100),
    )
    _draw_text_box(draw, value, box, multiline=field.get("type") == "textarea", **common)


def _find_chromium() -> str | None:
    configured = os.environ.get("CHROMIUM_BIN", "").strip()
    candidates = [
        configured,
        shutil.which("chromium") or "",
        shutil.which("chromium-browser") or "",
        shutil.which("google-chrome") or "",
        shutil.which("google-chrome-stable") or "",
        shutil.which("chrome") or "",
        shutil.which("msedge") or "",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    ]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate)
        if path.exists():
            return str(path)
    return None


def printing_status() -> dict[str, Any]:
    """Return non-secret runtime diagnostics for the document print engine."""
    chromium = _find_chromium()
    try:
        from playwright.sync_api import sync_playwright as _sync_playwright  # noqa: F401
        playwright_ok = True
    except Exception:
        playwright_ok = False
    try:
        import bs4 as _bs4  # noqa: F401
        beautifulsoup_ok = True
    except Exception:
        beautifulsoup_ok = False
    return {
        "ready": bool(chromium and playwright_ok and beautifulsoup_ok),
        "chromium": bool(chromium),
        "playwright": playwright_ok,
        "beautifulsoup": beautifulsoup_ok,
    }


def _validate_a4_pdf(path: Path) -> None:
    if not path.exists() or path.stat().st_size < 1000:
        raise RuntimeError("Generated print PDF is empty")
    reader = PdfReader(str(path))
    if not reader.pages:
        raise RuntimeError("Generated print PDF has no pages")
    first = reader.pages[0]
    width_mm = float(first.mediabox.width) * 25.4 / 72
    height_mm = float(first.mediabox.height) * 25.4 / 72
    if abs(width_mm - 210.0) > 1.0 or abs(height_mm - 297.0) > 1.0:
        raise RuntimeError(f"Generated page is not A4: {width_mm:.2f}x{height_mm:.2f} mm")


def _html_selectors(field: dict[str, Any]) -> list[str]:
    selectors = field.get("html_selectors")
    if isinstance(selectors, list) and selectors:
        return [str(item) for item in selectors if item]
    selector = field.get("html_selector")
    return [str(selector)] if selector else []


def _set_html_value(element: Any, value: Any, field_type: str) -> None:
    if field_type == "checkbox" or element.name == "input" and element.get("type", "").lower() == "checkbox":
        truthy = value in (True, 1, "1", "true", "on", "yes")
        if truthy:
            element["checked"] = "checked"
        elif element.has_attr("checked"):
            del element["checked"]
        return
    text = "" if value is None else str(value)
    if element.name == "textarea":
        element.clear()
        element.append(text)
    elif element.name in {"input", "select"}:
        element["value"] = text
    else:
        element.clear()
        element.append(text)


def _render_html_template_pdf(template: dict[str, Any], values: dict[str, Any], output_path: Path) -> Path:
    template_name = str(template.get("html_template") or "").strip()
    if not template_name:
        raise RuntimeError("HTML template filename is missing")
    source_path = (STATIC_DIR / "form-templates" / template_name).resolve()
    if not source_path.exists():
        raise RuntimeError(f"HTML template not found: {template_name}")

    chromium = _find_chromium()
    if not chromium:
        raise RuntimeError(
            "Chromium/Chrome/Edge is required to print the exact HTML invoice templates. "
            "Install Chromium on the server or use the production Docker image."
        )

    soup = BeautifulSoup(source_path.read_text(encoding="utf-8"), "html.parser")
    # The official HTML file is never rewritten. The print engine only changes
    # this in-memory copy so saved application values can be rendered safely.
    for script in soup.find_all("script"):
        script.decompose()

    for field in template.get("fields", []):
        selectors = _html_selectors(field)
        if not selectors:
            continue
        raw = values.get(field.get("key"), "")
        if len(selectors) > 1:
            parts = str(raw or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
            parts = (parts + [""] * len(selectors))[: len(selectors)]
        else:
            parts = [raw]
        for selector, value in zip(selectors, parts):
            element = soup.select_one(selector)
            if element is None:
                raise RuntimeError(f"Template field selector not found: {template_name} :: {selector}")
            _set_html_value(element, value, str(field.get("type") or "text"))
            element["data-ziad-print-field"] = "1"
            if field.get("direction") in {"rtl", "ltr"}:
                element["dir"] = field["direction"]

    helper_style = soup.new_tag("style")
    helper_style.string = """
      [data-ziad-print-field="1"] {
        outline:none !important; box-shadow:none !important;
        caret-color:transparent !important;
      }
    """
    if soup.head:
        soup.head.append(helper_style)
    else:
        soup.insert(0, helper_style)

    root_selector = str(template.get("html_root") or ".page, .sheet, main")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp_png = output_path.with_suffix(".browser.png")
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                executable_path=chromium,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
            )
            try:
                context = browser.new_context(
                    viewport={"width": 1600, "height": 2200},
                    device_scale_factor=2,
                    locale="ar-IQ",
                )
                page = context.new_page()
                page.set_content(str(soup), wait_until="load", timeout=45000)
                page.evaluate(
                    """(minimumPx) => {
                        document.querySelectorAll('[data-ziad-print-field="1"]').forEach((element) => {
                            const current = parseFloat(getComputedStyle(element).fontSize || '0');
                            if (Number.isFinite(current) && current < minimumPx) {
                                element.style.setProperty('font-size', '16pt', 'important');
                            }
                        });
                    }""",
                    HTML_DATA_MIN_FONT_PX,
                )
                root = page.locator(root_selector).first
                if root.count() != 1:
                    raise RuntimeError(f"HTML template root not found: {template_name} :: {root_selector}")
                root.screenshot(path=str(temp_png), animations="disabled", timeout=45000)
                context.close()
            finally:
                browser.close()

        with Image.open(temp_png) as rendered:
            a4 = rendered.convert("RGB").resize(A4_SIZE, Image.Resampling.LANCZOS)
            a4.save(output_path, "PDF", resolution=float(A4_DPI), quality=95)
        _validate_a4_pdf(output_path)
        return output_path
    except Exception as exc:
        logger.exception("Exact HTML print renderer failed for %s", template_name)
        raise RuntimeError(f"Exact HTML print renderer failed for {template_name}: {type(exc).__name__}: {exc}") from exc
    finally:
        temp_png.unlink(missing_ok=True)

def render_document_pdf(template: dict, values: dict[str, Any], output_path: Path) -> Path:
    if template.get("template_engine") == "html" and template.get("html_template"):
        try:
            return _render_html_template_pdf(template, values, output_path)
        except Exception:
            # Four original document types still carry their calibrated PDF field
            # geometry. If the browser renderer fails on Render, use that proven
            # PDF overlay path instead of returning a generic 5xx print error.
            fields = template.get("fields", [])
            legacy_ready = bool(template.get("pdf")) and all(
                (all(key in field for key in ("x", "y", "w", "h")) or field.get("line_boxes"))
                for field in fields
            )
            if not legacy_ready:
                raise
            logger.warning(
                "Falling back to calibrated PDF overlay for %s after HTML renderer failure",
                template.get("html_template"),
            )

    """Place entered values on a separate overlay and merge it with the untouched source PDF.

    The uploaded PDF bytes are never rewritten. Every original page is retained, including
    additional pages. Only page 1 receives the data overlay.
    """
    source_pdf_name = template.get("pdf")
    if not source_pdf_name:
        # Compatibility fallback for older installations.
        image_path = (STATIC_DIR / "templates" / template["image"]).resolve()
        with Image.open(image_path) as source:
            page = source.convert("RGB").resize(A4_SIZE, Image.Resampling.LANCZOS)
            draw = ImageDraw.Draw(page)
            width, height = page.size
            for field in template["fields"]:
                value = _field_text(values.get(field["key"], ""), field.get("type", "text"))
                _draw_configured_field(draw, field=field, value=value, canvas_width=width, canvas_height=height)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            page.save(output_path,"PDF",resolution=float(A4_DPI),quality=95)
        return output_path

    source_path = (TEMPLATES_DIR / "pdfs" / source_pdf_name).resolve()
    reader = PdfReader(str(source_path))
    first = reader.pages[0]
    page_w = float(first.mediabox.width)
    page_h = float(first.mediabox.height)
    pixel_w = max(1200, round(page_w / 72 * A4_DPI))
    pixel_h = max(1200, round(page_h / 72 * A4_DPI))
    overlay_img = Image.new("RGBA", (pixel_w, pixel_h), (255,255,255,0))
    draw = ImageDraw.Draw(overlay_img)
    for field in template["fields"]:
        value = _field_text(values.get(field["key"], ""), field.get("type", "text"))
        _draw_configured_field(draw, field=field, value=value, canvas_width=pixel_w, canvas_height=pixel_h)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    overlay_png=output_path.with_suffix('.overlay.png')
    overlay_pdf=output_path.with_suffix('.overlay.pdf')
    overlay_img.save(overlay_png, "PNG")
    c=canvas.Canvas(str(overlay_pdf), pagesize=(page_w,page_h), pageCompression=1)
    c.drawImage(ImageReader(str(overlay_png)),0,0,width=page_w,height=page_h,mask='auto')
    c.showPage(); c.save()
    overlay_reader=PdfReader(str(overlay_pdf))
    writer=PdfWriter()
    first.merge_page(overlay_reader.pages[0])
    writer.add_page(first)
    for original_page in reader.pages[1:]:
        writer.add_page(original_page)
    with output_path.open('wb') as handle:
        writer.write(handle)
    overlay_png.unlink(missing_ok=True); overlay_pdf.unlink(missing_ok=True)
    return output_path


def _image_to_pdf(image_path: Path, output_path: Path) -> Path:
    # Exact A4 at 300 DPI. Images are contained without distortion.
    with Image.open(image_path) as source:
        image = source.convert("RGB")
        margin = 150
        contained = ImageOps.contain(image, (A4_SIZE[0] - 2 * margin, A4_SIZE[1] - 2 * margin), Image.Resampling.LANCZOS)
        page = Image.new("RGB", A4_SIZE, "white")
        x = (A4_SIZE[0] - contained.width) // 2
        y = (A4_SIZE[1] - contained.height) // 2
        page.paste(contained, (x, y))
        page.save(output_path, "PDF", resolution=float(A4_DPI), quality=95)
    return output_path


def _notice_pdf(filename: str, message: str, output_path: Path) -> Path:
    page = Image.new("RGB", A4_SIZE, "white")
    draw = ImageDraw.Draw(page)
    title_font = _find_font(68)
    body_font = _find_font(44, bold=False)
    draw.rounded_rectangle((200, 540, A4_SIZE[0] - 200, 1800), radius=48, outline="#d8dee9", width=6)
    draw.text((320, 680), "Attachment could not be merged automatically", font=title_font, fill="#172033")
    draw.text((320, 880), filename[:80], font=body_font, fill="#172033")
    draw.multiline_text((320, 1080), message, font=body_font, fill="#172033", spacing=24)
    page.save(output_path, "PDF", resolution=float(A4_DPI), quality=95)
    return output_path


def _docx_to_pdf(docx_path: Path, output_dir: Path) -> Path | None:
    libreoffice = shutil.which("libreoffice") or shutil.which("soffice")
    if not libreoffice:
        return None
    output_dir.mkdir(parents=True, exist_ok=True)
    profile = output_dir / "lo-profile"
    profile.mkdir(parents=True, exist_ok=True)
    command = [
        libreoffice,
        f"-env:UserInstallation={profile.as_uri()}",
        "--headless",
        "--convert-to",
        "pdf",
        "--outdir",
        str(output_dir),
        str(docx_path),
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60, check=False)
    candidate = output_dir / f"{docx_path.stem}.pdf"
    if result.returncode == 0 and candidate.exists():
        return candidate
    return None


def _attachment_pdf(attachment: dict, work_dir: Path) -> Path:
    source = Path(attachment.get("local_path") or (ATTACHMENTS_DIR / attachment["stored_name"]))
    name = attachment["original_name"]
    mime = (attachment.get("mime_type") or "").lower()
    suffix = source.suffix.lower()
    digest = hashlib.sha256(f"{attachment['id']}:{attachment['sha256']}".encode()).hexdigest()[:12]
    output = work_dir / f"attachment-{digest}.pdf"

    try:
        if mime == "application/pdf" or suffix == ".pdf":
            PdfReader(str(source))
            shutil.copy2(source, output)
            return output
        if mime.startswith("image/") or suffix in {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}:
            return _image_to_pdf(source, output)
        if suffix in {".docx", ".doc", ".odt", ".rtf"}:
            converted = _docx_to_pdf(source, work_dir / f"convert-{digest}")
            if converted:
                shutil.copy2(converted, output)
                return output
            return _notice_pdf(name, "يتطلب هذا الملف وجود LibreOffice على جهاز التشغيل لكي تتم طباعته مع المستند.", output)
        return _notice_pdf(name, "نوع هذا الملف غير قابل للطباعة التلقائية. يبقى المرفق محفوظاً ويمكن تنزيله بشكل منفصل.", output)
    except Exception as exc:
        return _notice_pdf(name, f"تعذر تجهيز المرفق للطباعة: {type(exc).__name__}", output)


def build_print_bundle(
    *,
    document_id: int,
    revision: int,
    template: dict,
    values: dict[str, Any],
    attachments: list[dict],
) -> Path:
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    attachment_key = ",".join(f"{item['id']}:{item['sha256']}" for item in attachments)
    cache_key = hashlib.sha256(
        json.dumps(
            {"document": document_id, "revision": revision, "attachments": attachment_key, "paper": "A4-html-exact-browser-v1"},
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()[:20]
    final_path = GENERATED_DIR / f"document-{document_id}-{cache_key}.pdf"
    if final_path.exists():
        return final_path

    work_dir = Path(tempfile.mkdtemp(prefix=f"print-{document_id}-", dir=GENERATED_DIR))
    try:
        main_pdf = render_document_pdf(template, values, work_dir / "document.pdf")
        writer = PdfWriter()
        for page in PdfReader(str(main_pdf)).pages:
            writer.add_page(page)
        for attachment in attachments:
            attachment_pdf = _attachment_pdf(attachment, work_dir)
            for page in PdfReader(str(attachment_pdf)).pages:
                writer.add_page(page)
        temp_final = work_dir / "bundle.pdf"
        with temp_final.open("wb") as handle:
            writer.write(handle)
        shutil.move(str(temp_final), str(final_path))
        return final_path
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
