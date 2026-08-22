# Ziad Invoices Professional v3.3.20 — Build Report

Release scope:
- Refine global UI/button hierarchy without changing the official A4 templates.
- Add Payment Request (PR) → Payment Voucher (PV) conversion beside the Print button.
- Auto-save PR, create a saved PV, map shared fields, prevent duplicate conversions, and respect page permissions.

Validated locally:
- Python compile: PASS
- JavaScript syntax check: PASS
- Automated tests: 18/18 PASS
- PR → PV field mapping: PASS
- PR → PV duplicate prevention: PASS
- Target-page permission enforcement: PASS
- Existing print/PDF tests: PASS
- Official HTML template SHA-256 hashes: unchanged

No database migration is required. No official HTML form file was modified.
