from __future__ import annotations

import json
from typing import Any

from . import main as core
from .services import pdf_service


BUILD_VERSION = "3.3.40"
core.APP_VERSION = BUILD_VERSION


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _payment_voucher_fields_from_request(source_number: str, source_fields: dict[str, Any]) -> dict[str, Any]:
    """User-approved Payment Request -> Payment Voucher mapping."""
    purpose_parts = [
        _text(source_fields.get("pay_to")),
        _text(source_fields.get("purpose")),
    ]
    purpose = "\n".join(part for part in purpose_parts if part)
    return {
        "date": source_fields.get("date", ""),
        "reference": source_fields.get("reference", ""),
        "payment_request": source_number,
        "pay_to": source_fields.get("department", ""),
        "purpose": purpose,
        "amount": source_fields.get("amount", ""),
        "currency": source_fields.get("currency", ""),
        "written_amount": source_fields.get("written_amount", ""),
        "receiver_name": source_fields.get("prepared_by", ""),
        "accountant": "",
        "approval": source_fields.get("approval", ""),
    }


core._payment_voucher_fields_from_request = _payment_voucher_fields_from_request
_original_existing_payment_voucher = core._existing_payment_voucher_for_request


def _existing_payment_voucher_for_request(conn: core.DBConnection, payment_request_number: str) -> core.Record | None:
    existing = _original_existing_payment_voucher(conn, payment_request_number)
    if not existing:
        return None

    source = conn.execute(
        core.DOCUMENT_SELECT + " WHERE d.document_number=? AND dt.code='PR'",
        (payment_request_number,),
    ).fetchone()
    if not source:
        return existing

    try:
        source_fields = json.loads(source["field_values_json"])
        current_fields = json.loads(existing["field_values_json"])
    except (TypeError, ValueError, json.JSONDecodeError):
        return existing

    mapped = _payment_voucher_fields_from_request(payment_request_number, source_fields)
    clean = core._safe_fields(existing, mapped, str(existing["document_number"]))
    if all(current_fields.get(key) == clean.get(key) for key in set(clean.keys())):
        return existing

    fields_json = json.dumps(clean, ensure_ascii=False, separators=(",", ":"))
    now = core.utc_iso()
    revision = int(existing["revision"]) + 1
    changed_by = int(existing["updated_by"])

    with core.transaction(conn, immediate=True):
        conn.execute(
            "UPDATE documents SET field_values_json=?, updated_at=?, revision=? WHERE id=?",
            (fields_json, now, revision, existing["id"]),
        )
        conn.execute(
            "INSERT INTO document_revisions(document_id, revision, field_values_json, changed_by, changed_at) VALUES(?,?,?,?,?)",
            (existing["id"], revision, fields_json, changed_by, now),
        )
        core.audit(
            conn,
            user_id=changed_by,
            action="document.refresh_payment_request_mapping",
            entity_type="document",
            entity_id=existing["id"],
            details={"source_document_number": payment_request_number, "mapping_version": BUILD_VERSION},
        )

    return conn.execute(core.DOCUMENT_SELECT + " WHERE d.id=?", (existing["id"],)).fetchone()


core._existing_payment_voucher_for_request = _existing_payment_voucher_for_request


# HTML documents are printed from the user's own browser to the computer's local
# printer. Server-side HTML rendering stays disabled so Render never launches a
# browser process for document printing.
_original_render_document_pdf = pdf_service.render_document_pdf


def _browser_only_html_guard(template: dict[str, Any], values: dict[str, Any], output_path):
    if template.get("template_engine") == "html" and template.get("html_template"):
        raise RuntimeError("HTML templates print from the user's local browser in Ziad Invoices 3.3.40")
    return _original_render_document_pdf(template, values, output_path)


pdf_service.render_document_pdf = _browser_only_html_guard


def _browser_printing_status() -> dict[str, Any]:
    return {
        "ready": True,
        "mode": "browser-local-printer",
        "paper": "A4",
        "preview_scale": "editor-only",
        "print_size": "native-template-A4",
        "server_chromium": False,
        "playwright": False,
        "message": "Preview scaling is editor-only; HTML documents print using each template's native A4 print sizing",
    }


core.printing_status = _browser_printing_status
pdf_service.printing_status = _browser_printing_status


@core.app.middleware("http")
async def runtime_cache_headers(request: core.Request, call_next):
    response = await call_next(request)
    path = request.url.path
    if (
        path in {
            "/",
            "/index.html",
            "/app.js",
            "/styles.css",
            "/html-browser-print-v3.3.40.js",
        }
        or path.startswith("/form-templates/")
    ):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    response.headers["X-Ziad-Build"] = BUILD_VERSION
    response.headers["X-Ziad-Print-Engine"] = "browser-local-native-a4-3.3.40"
    return response


app = core.app
