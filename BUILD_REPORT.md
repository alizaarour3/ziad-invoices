# Ziad Invoices Professional v3.3.17 — Build Report

Release scope:
- Invoice data font minimum: 16pt in editor + printed HTML/PDF output.
- New financial page: Advances / سلف with repayment history and permissions.
- Automatic database schema migration to version 7.
- Supabase RLS hardening extended to the new financial tables.

Validated locally:
- Python compile: PASS
- JavaScript syntax check: PASS
- Automated tests: 16/16 PASS
- Official HTML template hashes: unchanged from v3.3.16
- Advances lifecycle/permissions: PASS
- 16pt editor + print font contract: PASS
- Supabase RLS table coverage: PASS

No official HTML invoice template file is modified by this release.
