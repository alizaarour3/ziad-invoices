# Ziad Invoices Professional v3.3.19 — Build Report

Release scope:
- Force all user-entered document data to exactly 16pt in the in-app HTML editor and Chromium PDF print path.
- Keep text on ruled fields directly above each printed line instead of centered through the line or below it.
- Split multi-line ruled text areas in RV/PV into per-line editors at runtime so each line has its own baseline.
- Preserve every official HTML template byte-for-byte.

Validated locally:
- Python compile: PASS
- JavaScript syntax check: PASS
- Automated tests: 17/17 PASS
- Chromium/Playwright HTML renderer: PASS
- RV print: A4 PASS with 4-line + 3-line ruled text
- PR print: A4 PASS with line-aligned text
- PV print: A4 PASS with 3-line ruled text
- VM print: A4 PASS
- TR print: A4 PASS with line-aligned text
- Official HTML template SHA-256 hashes: unchanged from v3.3.18

No database migration is required. No official HTML form file was modified.
