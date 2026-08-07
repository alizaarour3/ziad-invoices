# Ziad Invoices Professional v3.3.3 — Build Report

## Scope completed

- Calibrated every editable field against the four user-supplied alignment images.
- Added independent `line_boxes` so each purpose and written-amount line has its own exact x/y/width/height in both the browser editor and generated PDF.
- Calibrated Receipt Voucher, Payment Request, Payment Voucher, and Vehicle Maintenance fields.
- Calibrated all 12 Vehicle Maintenance table rows, the four header fields, totals, returned amount, and four signature fields.
- Exposed every grey-marked summary cell in the Vehicle Maintenance form as a real editable field.
- Preserved the direct View, Edit, Print, and permanent Delete buttons without contextual action menus.
- Preserved the hideable sidebar, responsive interface, real dashboard, attachments, users, audit, reports, backup, Render, and Supabase support.
- Official PDF and Word template files were not modified.

## Verification

- Python compilation: passed.
- JavaScript syntax check: passed.
- Automated API, PDF, UI-contract, and alignment tests: 7/7 passed.
- Exact line-box rendering contract: passed in frontend and PDF engine.
- Vehicle Maintenance creation and persistence: passed.
- Official PDF and Word SHA-256 integrity: passed.
- ZIP integrity: passed after final package verification.

## Data policy

The release contains no demo users, documents, attachments, or preview records. First launch requires creation of the real administrator account.

## Deployment boundary

The package supports local Windows operation and cloud deployment to Render with Supabase PostgreSQL and private Supabase Storage. Account credentials and secret environment variables remain the owner's responsibility.
