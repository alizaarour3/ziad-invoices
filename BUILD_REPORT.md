# Ziad Invoices Professional v3.3.16 — Build Report

Security hardening release for the Supabase `rls_disabled_in_public` warning.

Validated locally:
- Python compile: PASS
- JavaScript syntax check: PASS
- Automated tests: 14/14 PASS
- Official HTML template hashes: unchanged from v3.3.15
- Security regression test: verifies RLS enable + anon/authenticated privilege revocation statements for all application tables

Database security schema version: 6.
No business records are deleted or rewritten by this release.
