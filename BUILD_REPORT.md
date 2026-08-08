# Ziad Invoices Professional v3.3.8 — Build Report

## Scope

v3.3.8 fixes the exact HTML template preview bridge used by the document editor. It keeps the v3.3.7 zoom controls and v3.3.6 full-A4 fit behavior.

## Fixed

- Payment Request (`PR`) no longer opens as an oversized/cropped template.
- Payment Voucher (`PV`) no longer appears as a blank white A4 page.
- Vehicle Maintenance (`VM`) no longer appears as a blank white A4 page.
- Multi-line field navigation no longer calls `querySelector('')` on the last line.
- RTL iframe geometry is normalized to LTR only for page placement, while the original template root writing direction is preserved for Arabic content.
- The inner HTML template now scales using its true `offsetWidth`/`offsetHeight`, not a transformed bounding rectangle.
- Both width and height are used when fitting the inner template into the editor iframe.
- Template-local transforms cannot overwrite the editor preview scale.

## Preserved

- The four uploaded HTML template files are byte-for-byte unchanged.
- Zoom remains 50%–250% and editor-only.
- Print output remains A4 at original template dimensions.
- No database schema or Supabase change is required.

## Verification completed

- `node --check app/static/app.js` — PASS.
- Automated Python test suite — 9/9 PASS.
- Browser regression rendering of PR/PV/VM/RV in a narrow iframe — all four roots visible and fitted to the page bounds.
- HTML template SHA-256 values match the v3.3.7 originals.
