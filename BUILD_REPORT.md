# Ziad Invoices Professional v3.3.9 — Build Report

## Scope

v3.3.9 adds a fifth active document type, `TR` (تحويل), and an admin-only page-permission manager while preserving the v3.3.8 exact-HTML preview, v3.3.7 zoom, and v3.3.6 full-A4-fit behavior.

## Transfer document

- New document type: `TR` / تحويل.
- Independent sequence: `TR-000001`, `TR-000002`, ...
- Exact uploaded HTML stored at `app/static/form-templates/request-transfer.html`.
- Source SHA-256: `02560523c3cf78c0e4bd948e6b2961e38e10ae727deacd5c076c3783cb21ad48`.
- The template source is preserved byte-for-byte.
- Runtime bridge hides the template-local toolbar and neutralizes its local screen transform only inside the app editor.
- Print stays A4 and uses the same HTML template through Chromium/Playwright.
- The uploaded template has no document-number field, so the generated TR number remains in the application header/database rather than being placed in an invented position.

## Page permissions

- New admin page: صلاحيات.
- Managed business pages: dashboard + every active document type.
- New database table: `user_page_permissions`.
- Database schema version: 4.
- Existing users receive all current business pages by default at migration time.
- Admin accounts always have full page visibility.
- Non-admin users can be limited to any subset of business pages.
- Enforcement exists in both navigation/UI and document/attachment/report APIs.

## Verification

- Transfer source `cmp` against the uploaded file: PASS.
- `node --check app/static/app.js`: PASS.
- Python compile checks: PASS.
- Automated test suite: 9/9 PASS.
- TR HTML-to-PDF regression: PASS.
- Permission API/UI behavior covered by tests.
