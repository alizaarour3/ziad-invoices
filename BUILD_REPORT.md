# Ziad Invoices Professional v3.3.18 — Build Report

Release scope:
- Disable automatic login account lockout after repeated failed attempts.
- Recover automatically from stale lock values created by older releases.
- Harden document printing on Render and remove opaque 5xx/505-style failures where possible.
- Add calibrated PDF overlay fallback for RV / PR / PV / VM when browser rendering fails.

Validated locally:
- Python compile: PASS
- JavaScript syntax check: PASS
- Automated tests: 17/17 PASS
- Printing runtime: Chromium PASS / Playwright PASS / BeautifulSoup PASS
- RV print: A4 PASS
- PR print: A4 PASS
- PV print: A4 PASS
- VM print: A4 PASS
- TR print: A4 PASS
- Failed login stress: 12 wrong attempts followed by correct login PASS
- Official HTML template hashes: unchanged from v3.3.17

No database migration is required. No official HTML form file was modified.
