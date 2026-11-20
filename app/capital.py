"""Capital / cash fund page (رأس المال).

The administrator sets an opening balance per currency (IQD and USD) and a start
date. The current balance is always *computed* from the saved data, never stored
as a running number, so editing or deleting a voucher corrects the balance
automatically:

    balance = opening
              + saved Receipt Vouchers (RV)
              - saved Payment Vouchers (PV)
              - advances given            (IQD)
              + advance repayments        (IQD)

Only movements dated on/after the start date count. Drafts never count.
Vouchers whose amount cannot be read safely are listed for review and excluded
instead of being guessed.
"""
# No `from __future__ import annotations`: FastAPI must resolve the
# `core.CurrentUser` dependency annotations inside register_capital_routes().
import json
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Annotated, Any

from urllib.parse import quote

from fastapi import Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field

SETTINGS_KEY = "capital_fund"
PAGE_KEY = "capital"
CURRENCIES = ("IQD", "USD")
RECENT_LIMIT = 300

_USD_MARKERS = re.compile(r"usd|\$|دولار", re.IGNORECASE)
_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_CURRENCY_WORDS = re.compile(r"usd|iqd|idq|uqd|\$|دولار|دينار|عراقي|د\.ع", re.IGNORECASE)
_GROUPED = re.compile(r"^\d{1,3}(,\d{3})+(\.\d+)?$")
# Dots used as thousands separators: "19.000", "1.350.000" (common for dinars).
_DOT_GROUPED = re.compile(r"^\d{1,3}(\.\d{3})+$")
# A dot followed by exactly three digits that is not a valid dot-grouping, e.g.
# "1100.000": could be 1,100 or 1,100,000, so it must be reviewed by a person.
_AMBIGUOUS_THREE_DECIMALS = re.compile(r"^\d+\.\d{3}$")
_PLAIN = re.compile(r"^\d+(\.\d+)?$")


class CapitalUpdateRequest(BaseModel):
    start_date: date
    opening_iqd: Decimal = Field(default=Decimal("0"), ge=0, le=Decimal("1e15"))
    opening_usd: Decimal = Field(default=Decimal("0"), ge=0, le=Decimal("1e15"))
    notes: str = Field(default="", max_length=1000)


def detect_currency(currency_text: Any, amount_text: Any) -> str:
    """IQD unless the currency or the amount itself says dollars."""
    combined = f"{currency_text or ''} {amount_text or ''}"
    return "USD" if _USD_MARKERS.search(combined) else "IQD"


def parse_amount(value: Any, currency: str = "IQD") -> Decimal | None:
    """Read amounts such as '50,000,000', '50،000،000', '4,500$', '8500'.

    For dinars, '19.000' / '1.350.000' use dots as thousands separators (there
    are no fils in practice). For dollars that form is ambiguous ('12.500' may
    be 12.5). Returns None for anything ambiguous (e.g. '378,2', '1100.000' or
    free text) so it is reported for review rather than silently miscounted.
    """
    if value is None:
        return None
    text = str(value).translate(_ARABIC_DIGITS).replace("،", ",").replace("٬", ",").replace("٫", ".")
    text = _CURRENCY_WORDS.sub("", text).strip().replace(" ", "")
    if not text:
        return None
    if _GROUPED.match(text):
        text = text.replace(",", "")
    elif _DOT_GROUPED.match(text):
        if currency != "IQD":
            return None
        text = text.replace(".", "")
    elif _AMBIGUOUS_THREE_DECIMALS.match(text) or not _PLAIN.match(text):
        return None
    try:
        amount = Decimal(text)
    except InvalidOperation:
        return None
    return amount if amount > 0 else None


def parse_doc_date(value: Any, fallback_iso: str) -> str:
    """Return YYYY-MM-DD from the voucher date field, else the creation date."""
    text = str(value or "").strip().translate(_ARABIC_DIGITS)
    match = re.match(r"^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$", text)
    if match:
        y, m, d = (int(part) for part in match.groups())
    else:
        match = re.match(r"^(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})$", text)
        if match:
            d, m, y = (int(part) for part in match.groups())
        else:
            return str(fallback_iso or "")[:10]
    try:
        return date(y, m, d).isoformat()
    except ValueError:
        return str(fallback_iso or "")[:10]


def _money(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.01")), "f")


def load_config(conn: Any) -> dict[str, Any] | None:
    row = conn.execute("SELECT value_json, updated_at FROM settings WHERE key=?", (SETTINGS_KEY,)).fetchone()
    if not row:
        return None
    try:
        config = json.loads(row["value_json"])
    except (TypeError, ValueError):
        return None
    config["updated_at"] = row["updated_at"]
    return config


KIND_FIELD = {
    "receipt": "receipts",
    "payment": "payments",
    "advance": "advances",
    "advance_repayment": "advance_repayments",
}
KIND_LABELS = {
    "receipt": "مستند قبض",
    "payment": "مستند دفع",
    "advance": "سلفة",
    "advance_repayment": "تسديد سلفة",
}
CURRENCY_LABELS = {"IQD": "دينار عراقي", "USD": "دولار أمريكي"}


def _empty_totals() -> dict[str, Decimal]:
    return {field: Decimal(0) for field in KIND_FIELD.values()}


def _net(totals: dict[str, Decimal]) -> Decimal:
    return totals["receipts"] - totals["payments"] - totals["advances"] + totals["advance_repayments"]


def collect_movements(conn: Any, start: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Every cash movement dated on/after `start`, oldest first.

    Each movement carries `value` (Decimal, unsigned) plus display fields.
    Vouchers whose amount cannot be read are returned separately for review.
    """
    movements: list[dict[str, Any]] = []
    needs_review: list[dict[str, Any]] = []

    rows = conn.execute(
        """
        SELECT d.id, d.document_number, d.field_values_json, d.created_at, dt.code
        FROM documents d JOIN document_types dt ON dt.id=d.document_type_id
        WHERE d.status='saved' AND dt.code IN ('RV','PV')
        """
    ).fetchall()
    for row in rows:
        try:
            fields = json.loads(row["field_values_json"]) or {}
        except (TypeError, ValueError):
            fields = {}
        if not isinstance(fields, dict):
            fields = {}
        when = parse_doc_date(fields.get("date"), row["created_at"])
        if when < start:
            continue
        is_receipt = row["code"] == "RV"
        party = fields.get("received_from") if is_receipt else fields.get("pay_to")
        raw_amount = fields.get("amount")
        currency = detect_currency(fields.get("currency"), raw_amount)
        amount = parse_amount(raw_amount, currency)
        base = {
            "kind": "receipt" if is_receipt else "payment",
            "date": when,
            "document_id": int(row["id"]),
            "reference": row["document_number"],
            "party": str(party or "").strip(),
            "description": str((fields.get("about") if is_receipt else fields.get("purpose")) or "").strip(),
            "currency": currency,
        }
        if amount is None:
            needs_review.append({**base, "raw_amount": str(raw_amount or "")})
            continue
        movements.append({**base, "value": amount, "direction": 1 if is_receipt else -1})

    for row in conn.execute("SELECT id, person_name, amount_minor, notes, created_at FROM advances").fetchall():
        when = str(row["created_at"])[:10]
        if when < start:
            continue
        movements.append({
            "kind": "advance", "date": when, "advance_id": int(row["id"]), "reference": f"سلفة #{row['id']}",
            "party": row["person_name"], "description": str(row["notes"] or "").strip(), "currency": "IQD",
            "value": Decimal(int(row["amount_minor"])) / 100, "direction": -1,
        })

    for row in conn.execute(
        "SELECT p.id, p.advance_id, p.amount_minor, p.notes, p.paid_at, a.person_name "
        "FROM advance_payments p JOIN advances a ON a.id=p.advance_id"
    ).fetchall():
        when = str(row["paid_at"])[:10]
        if when < start:
            continue
        movements.append({
            "kind": "advance_repayment", "date": when, "advance_id": int(row["advance_id"]),
            "reference": f"تسديد سلفة #{row['advance_id']}", "party": row["person_name"],
            "description": str(row["notes"] or "").strip(), "currency": "IQD",
            "value": Decimal(int(row["amount_minor"])) / 100, "direction": 1,
        })

    movements.sort(key=lambda item: (item["date"], item["reference"]))
    needs_review.sort(key=lambda item: (item["date"], item["reference"]))
    return movements, needs_review


def _public_movement(item: dict[str, Any], **extra: Any) -> dict[str, Any]:
    out = {key: value for key, value in item.items() if key != "value"}
    out["amount"] = _money(item["value"])
    out.update(extra)
    return out


def _opening_balances(config: dict[str, Any]) -> dict[str, Decimal]:
    return {cur: Decimal(str(config.get("opening", {}).get(cur, "0"))) for cur in CURRENCIES}


def compute_capital(conn: Any, config: dict[str, Any]) -> dict[str, Any]:
    start = str(config["start_date"])
    opening = _opening_balances(config)
    movements, needs_review = collect_movements(conn, start)
    totals = {cur: _empty_totals() for cur in CURRENCIES}
    for item in movements:
        totals[item["currency"]][KIND_FIELD[item["kind"]]] += item["value"]

    funds = {}
    for cur in CURRENCIES:
        t = totals[cur]
        funds[cur] = {"opening": _money(opening[cur]), **{k: _money(v) for k, v in t.items()},
                      "balance": _money(opening[cur] + _net(t))}
    newest_first = list(reversed(movements))
    return {
        "configured": True,
        "start_date": start,
        "notes": config.get("notes", ""),
        "updated_at": config.get("updated_at"),
        "updated_by_name": config.get("updated_by_name"),
        "funds": funds,
        "movements": [_public_movement(item) for item in newest_first[:RECENT_LIMIT]],
        "movement_count": len(movements),
        "needs_review": list(reversed(needs_review)),
    }


def build_report(conn: Any, config: dict[str, Any], date_from: str, date_to: str) -> dict[str, Any]:
    """Cash report for [date_from, date_to]: balance at the start of the first
    day, that period's movements with a running balance, and closing balance."""
    start = str(config["start_date"])
    opening = _opening_balances(config)
    movements, needs_review = collect_movements(conn, start)

    period_opening = dict(opening)
    period_totals = {cur: _empty_totals() for cur in CURRENCIES}
    running = {}
    rows: list[dict[str, Any]] = []
    for item in movements:
        cur = item["currency"]
        if item["date"] < date_from:
            period_opening[cur] += item["value"] * item["direction"]
            continue
        if item["date"] > date_to:
            continue
        if cur not in running:
            running[cur] = period_opening[cur]
        running[cur] += item["value"] * item["direction"]
        period_totals[cur][KIND_FIELD[item["kind"]]] += item["value"]
        rows.append(_public_movement(item, balance_after=_money(running[cur])))

    funds = {}
    for cur in CURRENCIES:
        t = period_totals[cur]
        funds[cur] = {
            "opening": _money(period_opening[cur]),
            **{k: _money(v) for k, v in t.items()},
            "net": _money(_net(t)),
            "closing": _money(period_opening[cur] + _net(t)),
        }
    return {
        "date_from": date_from,
        "date_to": date_to,
        "start_date": start,
        "funds": funds,
        "movements": rows,
        "needs_review": [item for item in needs_review if date_from <= item["date"] <= date_to],
    }


def report_workbook(report: dict[str, Any], prepared_by: str) -> bytes:
    """Excel version of build_report(): a summary sheet and a movements sheet."""
    import io
    from datetime import datetime

    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    green = "0E6B4F"
    header_fill = PatternFill("solid", fgColor=green)
    header_font = Font(color="FFFFFF", bold=True, size=11)
    thin = Side(style="thin", color="CFC7B2")
    money_format = "#,##0.00"

    def style_header(ws, row_number):
        for cell in ws[row_number]:
            if cell.value is None:
                continue
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = Border(bottom=thin)
        ws.row_dimensions[row_number].height = 24

    period = report["date_from"] if report["date_from"] == report["date_to"] else f"{report['date_from']} → {report['date_to']}"
    wb = Workbook()
    ws = wb.active
    ws.title = "ملخص"
    ws.sheet_view.rightToLeft = True
    ws["A1"] = "تقرير رأس المال — الصندوق"
    ws["A1"].font = Font(size=18, bold=True, color=green)
    ws.merge_cells("A1:C1")
    meta = [
        ("الفترة", period),
        ("بداية احتساب الصندوق", report["start_date"]),
        ("أعدّه", prepared_by),
        ("تاريخ التصدير", datetime.now().strftime("%Y-%m-%d %H:%M")),
    ]
    for offset, (label, value) in enumerate(meta):
        ws.cell(3 + offset, 1, label).font = Font(bold=True)
        ws.cell(3 + offset, 2, value)

    header_row = 3 + len(meta) + 1
    ws.cell(header_row, 1, "البند")
    for col, cur in enumerate(CURRENCIES, start=2):
        ws.cell(header_row, col, f"{CURRENCY_LABELS[cur]} ({cur})")
    style_header(ws, header_row)
    lines = [
        ("الرصيد في بداية الفترة", "opening"),
        ("+ مستندات القبض", "receipts"),
        ("− مستندات الدفع", "payments"),
        ("− السلف", "advances"),
        ("+ تسديد السلف", "advance_repayments"),
        ("صافي الحركة", "net"),
        ("الرصيد في نهاية الفترة", "closing"),
    ]
    for offset, (label, key) in enumerate(lines, start=1):
        row = header_row + offset
        ws.cell(row, 1, label)
        for col, cur in enumerate(CURRENCIES, start=2):
            cell = ws.cell(row, col, float(Decimal(report["funds"][cur][key])))
            cell.number_format = money_format
        if key in ("opening", "closing"):
            for col in range(1, len(CURRENCIES) + 2):
                ws.cell(row, col).font = Font(bold=True, color=green if key == "closing" else "000000")
    ws.column_dimensions["A"].width = 28
    for col in range(2, len(CURRENCIES) + 2):
        ws.column_dimensions[get_column_letter(col)].width = 24

    if report["needs_review"]:
        row = header_row + len(lines) + 2
        ws.cell(row, 1, f"تنبيه: {len(report['needs_review'])} مستند في هذه الفترة لم يُحسب لأن مبلغه غير مقروء — راجع ورقة «تحتاج مراجعة».").font = Font(bold=True, color="AD2B21")

    ws2 = wb.create_sheet("الحركات")
    ws2.sheet_view.rightToLeft = True
    headers = ["التاريخ", "النوع", "الرقم", "الجهة / الاسم", "البيان", "العملة", "وارد (+)", "صادر (−)", "الرصيد بعد الحركة"]
    ws2.append(headers)
    style_header(ws2, 1)
    for item in report["movements"]:
        value = float(Decimal(item["amount"]))
        ws2.append([
            item["date"], KIND_LABELS[item["kind"]], item["reference"], item["party"], item.get("description", ""),
            item["currency"], value if item["direction"] > 0 else None, value if item["direction"] < 0 else None,
            float(Decimal(item["balance_after"])),
        ])
    for row in ws2.iter_rows(min_row=2, min_col=7, max_col=9):
        for cell in row:
            cell.number_format = money_format
    widths = [12, 14, 16, 26, 36, 8, 16, 16, 18]
    for col, width in enumerate(widths, start=1):
        ws2.column_dimensions[get_column_letter(col)].width = width
    ws2.freeze_panes = "A2"

    if report["needs_review"]:
        ws3 = wb.create_sheet("تحتاج مراجعة")
        ws3.sheet_view.rightToLeft = True
        ws3.append(["التاريخ", "النوع", "الرقم", "الجهة / الاسم", "العملة", "المبلغ المكتوب"])
        style_header(ws3, 1)
        for item in report["needs_review"]:
            ws3.append([item["date"], KIND_LABELS[item["kind"]], item["reference"], item["party"], item["currency"], item["raw_amount"] or "(فارغ)"])
        for col, width in enumerate([12, 14, 16, 26, 8, 30], start=1):
            ws3.column_dimensions[get_column_letter(col)].width = width

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def keep_static_mount_last(app: Any) -> None:
    """StaticFiles is mounted at "/" in app.main and swallows every route added
    after it (they answer 404). Move that catch-all mount back to the end."""
    routes = app.router.routes
    static_mounts = [route for route in routes if getattr(route, "name", None) == "static"]
    for mount in static_mounts:
        routes.remove(mount)
        routes.append(mount)


def register_capital_routes(core: Any) -> None:
    if getattr(core.app.state, "capital_routes_registered", False):
        # Already registered by app.main; other routes (e.g. advance Excel) may
        # have been added since, so re-apply the ordering fix.
        keep_static_mount_last(core.app)
        return
    core.app.state.capital_routes_registered = True

    @core.app.get("/api/capital")
    def get_capital(user: Annotated[core.CurrentUser, Depends(core.require("documents.read"))]):
        conn = core.connect()
        try:
            core._require_page_access(conn, user, PAGE_KEY)
            config = load_config(conn)
            result = {"configured": False} if not config else compute_capital(conn, config)
            result["can_manage"] = user.role == "admin"
            return result
        finally:
            conn.close()

    @core.app.put("/api/capital")
    def update_capital(
        payload: CapitalUpdateRequest,
        user: Annotated[core.CurrentUser, Depends(core.require("system.manage"))],
    ):
        conn = core.connect()
        try:
            previous = load_config(conn)
            config = {
                "start_date": payload.start_date.isoformat(),
                "opening": {"IQD": _money(payload.opening_iqd), "USD": _money(payload.opening_usd)},
                "notes": payload.notes.strip(),
                "updated_by": user.id,
                "updated_by_name": user.full_name,
            }
            now = core.utc_iso()
            with core.transaction(conn, immediate=True):
                conn.execute(
                    "INSERT INTO settings(key, value_json, updated_at) VALUES(?,?,?) "
                    "ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, updated_at=excluded.updated_at",
                    (SETTINGS_KEY, json.dumps(config, ensure_ascii=False), now),
                )
                core.audit(
                    conn,
                    user_id=user.id,
                    action="capital.update",
                    entity_type="capital",
                    entity_id=SETTINGS_KEY,
                    details={
                        "start_date": config["start_date"],
                        "opening": config["opening"],
                        "previous": None if not previous else {
                            "start_date": previous.get("start_date"), "opening": previous.get("opening"),
                        },
                    },
                )
            result = compute_capital(conn, {**config, "updated_at": now})
            result["can_manage"] = True
            return result
        finally:
            conn.close()

    def _report_for(conn: Any, user: Any, date_from: date | None, date_to: date | None) -> dict[str, Any]:
        core._require_page_access(conn, user, PAGE_KEY)
        config = load_config(conn)
        if not config:
            raise HTTPException(status_code=404, detail="لم يُحدَّد صندوق الشركة بعد")
        day_from = (date_from or date_to or date.today()).isoformat()
        day_to = (date_to or date_from or date.today()).isoformat()
        if day_to < day_from:
            raise HTTPException(status_code=422, detail="تاريخ النهاية يجب أن يكون بعد تاريخ البداية")
        if day_from < str(config["start_date"]):
            raise HTTPException(
                status_code=422,
                detail=f"لا يمكن إصدار تقرير قبل تاريخ بداية الصندوق ({config['start_date']})",
            )
        return build_report(conn, config, day_from, day_to)

    @core.app.get("/api/capital/report")
    def capital_report(
        user: Annotated[core.CurrentUser, Depends(core.require("documents.read"))],
        date_from: date | None = Query(default=None),
        date_to: date | None = Query(default=None),
    ):
        conn = core.connect()
        try:
            return _report_for(conn, user, date_from, date_to)
        finally:
            conn.close()

    @core.app.get("/api/capital/report.xlsx")
    def capital_report_excel(
        user: Annotated[core.CurrentUser, Depends(core.require("documents.read"))],
        date_from: date | None = Query(default=None),
        date_to: date | None = Query(default=None),
    ):
        conn = core.connect()
        try:
            report = _report_for(conn, user, date_from, date_to)
        finally:
            conn.close()
        payload = report_workbook(report, user.full_name)
        suffix = report["date_from"] if report["date_from"] == report["date_to"] else f"{report['date_from']}_{report['date_to']}"
        filename = f"capital-report-{suffix}.xlsx"
        return Response(
            content=payload,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
                "Content-Length": str(len(payload)),
                "Cache-Control": "no-store",
            },
        )

    keep_static_mount_last(core.app)
