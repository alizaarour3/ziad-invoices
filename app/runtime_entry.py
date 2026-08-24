from __future__ import annotations

import json
from typing import Any

from . import main as core
from .services import pdf_service


BUILD_VERSION = "3.3.34"


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _payment_voucher_fields_from_request(source_number: str, source_fields: dict[str, Any]) -> dict[str, Any]:
    """User-approved Payment Request -> Payment Voucher mapping.

    PR department -> PV pay_to
    PR pay_to -> first line of PV purpose
    PR purpose/description -> following PV purpose lines
    PR prepared_by -> PV receiver_name
    """
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


# The conversion endpoint resolves this global at request time, so replacing the
# helper here fixes the real backend path used by desktop and Render.
core._payment_voucher_fields_from_request = _payment_voucher_fields_from_request


_original_existing_payment_voucher = core._existing_payment_voucher_for_request


def _existing_payment_voucher_for_request(conn: core.DBConnection, payment_request_number: str) -> core.Record | None:
    """Refresh an already-converted PV so old incorrect mappings are repaired too."""
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

    # Do not create a revision if the linked voucher already contains the exact
    # approved mapping.
    comparable_keys = set(clean.keys())
    if all(current_fields.get(key) == clean.get(key) for key in comparable_keys):
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
            details={
                "source_document_number": payment_request_number,
                "mapping_version": BUILD_VERSION,
            },
        )

    return conn.execute(core.DOCUMENT_SELECT + " WHERE d.id=?", (existing["id"],)).fetchone()


core._existing_payment_voucher_for_request = _existing_payment_voucher_for_request


# pdf_service renders HTML using screen media and injects its own 16pt print
# helper. Add a high-specificity style to the in-memory Payment Voucher only so
# every entered value sits clearly above its printed line without changing the
# official HTML/template artwork stored on disk.
_OriginalBeautifulSoup = pdf_service.BeautifulSoup


def _print_adjusted_soup(markup: str, *args: Any, **kwargs: Any):
    soup = _OriginalBeautifulSoup(markup, *args, **kwargs)
    title_text = soup.title.get_text(strip=True) if soup.title else ""
    if "Payment Voucher" not in title_text:
        return soup

    style = soup.new_tag("style")
    style["data-ziad-runtime-print-fix"] = BUILD_VERSION
    style.string = """
      #voucherPage .field[data-ziad-print-field=\"1\"]:not(input[type=\"checkbox\"]) {
        transform: translateY(-0.90mm) !important;
      }
      #voucherPage #payto[data-ziad-print-field=\"1\"] {
        transform: translateY(-1.70mm) !important;
        padding-bottom: 1.15mm !important;
      }
      #voucherPage .purpose[data-ziad-print-field=\"1\"],
      #voucherPage .written[data-ziad-print-field=\"1\"] {
        transform: translateY(-1.90mm) !important;
      }
      #voucherPage .signature[data-ziad-print-field=\"1\"] {
        transform: translateY(-1.45mm) !important;
        padding-bottom: 1.05mm !important;
      }
      #voucherPage .ziad-print-split-lines {
        transform: translateY(-1.90mm) !important;
      }
      #voucherPage [data-ziad-print-line=\"1\"] {
        padding-bottom: 1.05mm !important;
      }
    """
    if soup.head:
        soup.head.append(style)
    else:
        soup.insert(0, style)
    return soup


pdf_service.BeautifulSoup = _print_adjusted_soup


# Static assets and HTML form templates changed several times while the URLs
# still carried v=3.3.20. Do not allow Render/browser caches to keep old UI or
# old templates after a deploy.
@core.app.middleware("http")
async def runtime_cache_headers(request: core.Request, call_next):
    response = await call_next(request)
    path = request.url.path
    if (
        path in {"/", "/index.html", "/app.js", "/styles.css", "/runtime-v3.3.34.js"}
        or path.startswith("/form-templates/")
    ):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    response.headers["X-Ziad-Build"] = BUILD_VERSION
    return response


app = core.app
