from __future__ import annotations

from pathlib import Path
from typing import Any

from .services import pdf_service


PRINT_ENGINE_VERSION = "3.3.35"


def _split_selector_values(raw: Any, count: int) -> list[Any]:
    if count <= 1:
        return [raw]
    parts = str(raw or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if len(parts) > count:
        parts = parts[: count - 1] + [" ".join(part.strip() for part in parts[count - 1 :] if part.strip())]
    return (parts + [""] * count)[:count]


def _render_html_template_pdf_direct(template: dict[str, Any], values: dict[str, Any], output_path: Path) -> Path:
    """Render the official HTML template directly to A4 PDF with Chromium.

    The previous renderer captured a very large high-DPI screenshot and then converted
    that bitmap to PDF. On constrained cloud instances that path can exhaust browser
    memory and surface as HTTP 503. This renderer asks Chromium for an A4 PDF directly,
    preserving the exact HTML/CSS while using much less memory.
    """
    template_name = str(template.get("html_template") or "").strip()
    if not template_name:
        raise RuntimeError("HTML template filename is missing")

    source_path = (pdf_service.STATIC_DIR / "form-templates" / template_name).resolve()
    if not source_path.exists():
        raise RuntimeError(f"HTML template not found: {template_name}")

    chromium = pdf_service._find_chromium()
    if not chromium:
        raise RuntimeError("Chromium/Chrome/Edge is required for exact HTML PDF rendering")

    # pdf_service.BeautifulSoup may be wrapped by runtime_entry to inject the
    # Payment Voucher line-position fix. Use that wrapper intentionally.
    soup = pdf_service.BeautifulSoup(source_path.read_text(encoding="utf-8"), "html.parser")
    for script in soup.find_all("script"):
        script.decompose()

    selectors_for_lines: list[str] = []
    for field in template.get("fields", []):
        selectors = pdf_service._html_selectors(field)
        if not selectors:
            continue
        raw = values.get(field.get("key"), "")
        parts = _split_selector_values(raw, len(selectors))
        for selector, value in zip(selectors, parts):
            element = soup.select_one(selector)
            if element is None:
                raise RuntimeError(f"Template field selector not found: {template_name} :: {selector}")
            pdf_service._set_html_value(element, value, str(field.get("type") or "text"))
            element["data-ziad-print-field"] = "1"
            if field.get("html_line"):
                element["data-ziad-print-line"] = "1"
                selectors_for_lines.append(selector)
            if field.get("direction") in {"rtl", "ltr"}:
                element["dir"] = field["direction"]

    helper_style = soup.new_tag("style")
    helper_style["data-ziad-direct-pdf"] = PRINT_ENGINE_VERSION
    helper_style.string = """
      @page { size: A4 portrait !important; margin: 0 !important; }
      html, body { margin: 0 !important; padding: 0 !important; }
      [data-ziad-print-field="1"] {
        outline: none !important;
        box-shadow: none !important;
        caret-color: transparent !important;
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
      }
      [data-ziad-print-line="1"] {
        box-sizing: border-box !important;
      }
    """
    if soup.head:
        soup.head.append(helper_style)
    else:
        soup.insert(0, helper_style)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(
                headless=True,
                executable_path=chromium,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-software-rasterizer",
                    "--font-render-hinting=none",
                ],
            )
            try:
                context = browser.new_context(locale="ar-IQ")
                page = context.new_page()
                page.set_content(str(soup), wait_until="load", timeout=45000)
                page.emulate_media(media="print")
                page.evaluate(
                    """async () => {
                        if (document.fonts && document.fonts.ready) await document.fonts.ready;
                        document.querySelectorAll('input, textarea, [contenteditable]').forEach((el) => el.blur());
                    }"""
                )
                page.pdf(
                    path=str(output_path),
                    format="A4",
                    print_background=True,
                    prefer_css_page_size=True,
                    display_header_footer=False,
                    margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
                    timeout=45000,
                )
                context.close()
            finally:
                browser.close()

        pdf_service._validate_a4_pdf(output_path)
        return output_path
    except Exception as exc:
        pdf_service.logger.exception("Direct HTML PDF renderer failed for %s", template_name)
        output_path.unlink(missing_ok=True)
        raise RuntimeError(
            f"Direct HTML PDF renderer failed for {template_name}: {type(exc).__name__}: {exc}"
        ) from exc


def install() -> None:
    pdf_service._render_html_template_pdf = _render_html_template_pdf_direct
