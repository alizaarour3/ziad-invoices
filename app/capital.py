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

from fastapi import Depends
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


def compute_capital(conn: Any, config: dict[str, Any]) -> dict[str, Any]:
    start = str(config["start_date"])
    opening = {cur: Decimal(str(config.get("opening", {}).get(cur, "0"))) for cur in CURRENCIES}
    totals = {
        cur: {"receipts": Decimal(0), "payments": Decimal(0), "advances": Decimal(0), "advance_repayments": Decimal(0)}
        for cur in CURRENCIES
    }
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
            "currency": currency,
        }
        if amount is None:
            needs_review.append({**base, "raw_amount": str(raw_amount or "")})
            continue
        totals[currency]["receipts" if is_receipt else "payments"] += amount
        movements.append({**base, "amount": _money(amount), "direction": 1 if is_receipt else -1})

    for row in conn.execute("SELECT id, person_name, amount_minor, created_at FROM advances").fetchall():
        when = str(row["created_at"])[:10]
        if when < start:
            continue
        amount = Decimal(int(row["amount_minor"])) / 100
        totals["IQD"]["advances"] += amount
        movements.append({
            "kind": "advance", "date": when, "advance_id": int(row["id"]), "reference": f"سلفة #{row['id']}",
            "party": row["person_name"], "currency": "IQD", "amount": _money(amount), "direction": -1,
        })

    for row in conn.execute(
        "SELECT p.id, p.advance_id, p.amount_minor, p.paid_at, a.person_name "
        "FROM advance_payments p JOIN advances a ON a.id=p.advance_id"
    ).fetchall():
        when = str(row["paid_at"])[:10]
        if when < start:
            continue
        amount = Decimal(int(row["amount_minor"])) / 100
        totals["IQD"]["advance_repayments"] += amount
        movements.append({
            "kind": "advance_repayment", "date": when, "advance_id": int(row["advance_id"]),
            "reference": f"تسديد سلفة #{row['advance_id']}", "party": row["person_name"],
            "currency": "IQD", "amount": _money(amount), "direction": 1,
        })

    movements.sort(key=lambda item: (item["date"], item["reference"]), reverse=True)
    needs_review.sort(key=lambda item: item["date"], reverse=True)
    funds = {}
    for cur in CURRENCIES:
        t = totals[cur]
        balance = opening[cur] + t["receipts"] - t["payments"] - t["advances"] + t["advance_repayments"]
        funds[cur] = {"opening": _money(opening[cur]), **{k: _money(v) for k, v in t.items()}, "balance": _money(balance)}
    return {
        "configured": True,
        "start_date": start,
        "notes": config.get("notes", ""),
        "updated_at": config.get("updated_at"),
        "updated_by_name": config.get("updated_by_name"),
        "funds": funds,
        "movements": movements[:RECENT_LIMIT],
        "movement_count": len(movements),
        "needs_review": needs_review,
    }


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

    keep_static_mount_last(core.app)
