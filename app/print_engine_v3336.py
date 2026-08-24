from __future__ import annotations

from pathlib import Path
from typing import Any

from pypdf import PdfReader

from .services import pdf_service


PRINT_ENGINE_VERSION = "3.3.36"


def _split_selector_values(raw: Any, count: int) -> list[Any]:
    if count <= 1:
        return [raw]
    parts = str(raw or "").replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if len(parts) > count:
        parts = parts[: count - 1] + [" ".join(part.strip() for part in parts[count - 1 :] if part.strip())]
    return (parts + [""] * count)[:count]


def _render_html_template_pdf_direct(template: dict[str, Any], values: dict[str, Any], output_path: Path) -> Path:
    """Render the official HTML document directly to a one-page A4 PDF.

    This path deliberately does not use the legacy image/PDF overlay renderer.
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

    # runtime_entry wraps BeautifulSoup for the Payment Voucher print-position
    # adjustments. We intentionally use that wrapped constructor here.
    soup = pdf_service.BeautifulSoup(source_path.read_text(encoding="utf-8"), "html.parser")

    # User-entered template scripts are only needed in the browser editor. The
    # server print copy is deterministic and receives values from saved fields.
    for script in soup.find_all("script"):
        script.decompose()

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
            if field.get("direction") in {"rtl", "ltr"}:
                element["dir"] = field["direction"]

    helper_style = soup.new_tag("style")
    helper_style["data-ziad-direct-pdf"] = PRINT_ENGINE_VERSION
    helper_style.string = """
      @page { size: A4 portrait !important; margin: 0 !important; }
      html, body {
        margin: 0 !important;
        padding: 0 !important;
        width: 210mm !important;
        min-width: 210mm !important;
      }
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
                    "--font-render-hinting=none",
                ],
            )
            try:
                context = browser.new_context(locale="ar-IQ")
                page = context.new_page()
                page.set_default_timeout(45000)
                page.set_content(str(soup), wait_until="load", timeout=45000)
                page.emulate_media(media="print")
                page.evaluate(
                    """async () => {
                        if (document.fonts && document.fonts.ready) await document.fonts.ready;
                        document.querySelectorAll('input, textarea, [contenteditable]').forEach((el) => el.blur());
                    }"""
                )

                # IMPORTANT: Playwright page.pdf() does not accept a timeout
                # keyword. v3.3.35 passed one, causing an immediate TypeError and
                # silently triggering the old legacy PDF/image fallback.
                page.pdf(
                    path=str(output_path),
                    format="A4",
                    print_background=True,
                    prefer_css_page_size=True,
                    display_header_footer=False,
                    margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
                )
                context.close()
            finally:
                browser.close()

        pdf_service._validate_a4_pdf(output_path)
        reader = PdfReader(str(output_path))
        if len(reader.pages) != 1:
            raise RuntimeError(f"HTML template rendered {len(reader.pages)} pages instead of one A4 page")
        return output_path
    except Exception as exc:
        pdf_service.logger.exception("Direct HTML PDF renderer failed for %s", template_name)
        output_path.unlink(missing_ok=True)
        raise RuntimeError(
            f"Direct HTML PDF renderer failed for {template_name}: {type(exc).__name__}: {exc}"
        ) from exc


_original_render_document_pdf = pdf_service.render_document_pdf


def _render_document_pdf_no_html_fallback(template: dict[str, Any], values: dict[str, Any], output_path: Path) -> Path:
    if template.get("template_engine") == "html" and template.get("html_template"):
        # Never print an old image/PDF when an HTML template is configured.
        # A renderer error must remain visible so the wrong official document is
        # never produced silently.
        return _render_html_template_pdf_direct(template, values, output_path)
    return _original_render_document_pdf(template, values, output_path)


def install() -> None:
    pdf_service._render_html_template_pdf = _render_html_template_pdf_direct
    pdf_service.render_document_pdf = _render_document_pdf_no_html_fallback
