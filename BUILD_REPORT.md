# Ziad Invoices Professional v3.3.4 — Build Report

## Arabic/RTL production fix

- Correct Arabic contextual shaping and right-to-left/BiDi ordering in generated PDFs.
- Pillow now loads RAQM as the layout engine when available and passes `direction=rtl` plus `language=ar` for Arabic fields.
- Linux/Render prefers a cross-script Arabic-capable font (DejaVu Sans), with Arial/Segoe UI on Windows and Noto Arabic fallbacks.
- The production Docker image installs RAQM, HarfBuzz and FriBiDi development libraries and forces Pillow 12.2.0 to build from source against them.
- Docker build performs a hard RAQM/Harfbuzz/FriBiDi verification before deployment.
- If a non-RAQM runtime attempts to print real Arabic text, PDF generation stops with a clear error instead of producing reversed/unjoined Arabic.
- Browser editor fields use `unicode-bidi: plaintext` and explicit field directions for cleaner mixed Arabic/number text.
- Print cache generation key was bumped so previously generated broken Arabic PDFs are not reused.
- `/api/health` and system status now report Arabic rendering capabilities.

## Preserved behavior

- Exact field positions from v3.3.3 remain unchanged.
- Official PDF templates remain byte-for-byte unchanged.
- Official Word templates remain byte-for-byte unchanged.
- Automatic numbering, attachments, view/edit/print/permanent-delete, users, audit, dashboard, Render and Supabase support remain intact.
- No demo users, documents, attachments or customer data are included.

## Verification performed

- Python compilation: passed.
- JavaScript syntax check: passed.
- Automated API/PDF/UI/alignment/Arabic tests: 8/8 passed.
- Arabic render preview using `محمد علي حسن` and mixed Arabic/Latin/digits: passed visually.
- Runtime shaping features in the test environment: RAQM=True, HarfBuzz=True, FriBiDi=True.
- Original Word template SHA-256 checks: passed.
- A4 Word template SHA-256 checks: passed.
- Official PDF template SHA-256 checks: passed.

## Render verification after deploy

Open `/api/health` and confirm:

```json
{
  "ok": true,
  "version": "3.3.4",
  "arabic_rendering": {
    "raqm": true,
    "harfbuzz": true,
    "fribidi": true
  }
}
```

If any of the three shaping values is false, do not use the deployment for production printing.
