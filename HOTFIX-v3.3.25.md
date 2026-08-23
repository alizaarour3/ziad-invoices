# Ziad Invoices Professional v3.3.25 — Premium System UI

This update applies the uploaded `DESIGN.md` direction to the **system interface only**.

## Changed
- Dark technical-premium application shell.
- Professional Blue (`#2563EB`) for primary actions and active states.
- Refined sidebar, topbar, dashboard cards, document lists, tables, inputs, buttons, badges, modals, attachments, settings and admin screens.
- Friendlier spacing and clearer hierarchy while remaining compact enough for financial/admin work.
- Full-size login screen with 68px controls on desktop.
- App-level zoom is explicitly 100%; no CSS `scale()` is used to shrink the application.
- Responsive layouts reflow instead of zooming out.

## NOT changed
- Voucher templates.
- Request templates.
- `app/static/templates/`.
- `app/static/form-templates/`.
- Root `templates/`.
- `.template-page`, `.template-bg`, `.template-field`, `.template-line-field`, `.template-checkbox` styles.
- `app/static/app.js` business logic.
- Database/API/auth/PDF code.

The installer fingerprints protected template files before and after installation and aborts if a protected file changes.
