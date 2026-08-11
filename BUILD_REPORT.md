# Ziad Invoices Professional v3.3.14 — Build Report

## Scope

This release refreshes the **Transfer workspace** and **Dashboard UI** while preserving the existing document engine, database schema, permissions, loans, attachments, A4 rendering, and all five exact HTML templates.

## Transfer workspace

- Dedicated Transfer list UI with transfer-specific header and new-transfer action.
- Real summary metrics: total requests, saved, drafts, and total of numeric amount fields.
- Search across request number, beneficiary, transfer entity, department, purpose, amount, and creator.
- Status and department filters.
- Specialized table columns for beneficiary/purpose, transfer entity, department, amount/currency, status, creator, and direct actions.
- Transfer editor/view header now exposes date/entity/amount metadata when available.
- `request-transfer.html` SHA-256 remains `02560523c3cf78c0e4bd948e6b2961e38e10ae727deacd5c076c3783cb21ad48` (unchanged).

## Dashboard

- New operational hero with current date, current user role, today's document count, and create action.
- KPI cards are calculated from the real dashboard API response.
- Dedicated Transfer KPI when Transfer is visible to the user.
- Per-document-type cards now show saved/draft counts and saved percentage.
- Live Loans snapshot is loaded only for users who can view the Loans page.
- Added draft attention cards, latest-document table, 7-day activity, attachment and print metrics.

## Compatibility

- Database schema remains version 5.
- No new SQL or Supabase migration is required.
- Existing page permissions continue to control visible dashboard sections and document types.
- All official HTML templates remain unchanged.

## Verification

- `node --check app/static/app.js`: PASS.
- Python compile check: PASS.
- Automated test suite: **12/12 PASS**.
- Transfer template byte-integrity regression test: PASS.
