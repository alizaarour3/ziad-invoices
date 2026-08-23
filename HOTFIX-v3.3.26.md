# Ziad Invoices v3.3.26 — Premium UI Only

This update uses the supplied `DESIGN.md` visual system and changes **application UI only**.

## Fixed

- Completes the Technical-Premium dark UI across legacy/raw inputs that did not use the `.control` class.
- Fixes the repayment field area shown in the screenshot (`المبلغ المحدد` / minimum payment) so it no longer appears as an old white control.
- Unified labels, helper text, selects, numeric inputs, cards, tables and modal controls.
- Keeps RTL logical spacing and readable financial values.
- Keeps the application at **100% real size**. No `zoom-out`, `transform: scale(...)`, or responsive scale-down is introduced.

## Template protection

The installer only:

1. copies `app/static/premium-system-v3.3.26.css`, and
2. adds its stylesheet link to `app/static/index.html`.

Before and after installation it hashes protected template files. If a voucher/request template changes, installation fails and rolls back `index.html`.

Protected areas include `templates/`, `app/static/templates/`, `app/static/form-templates/`, and standalone static document HTML pages.

**No voucher/request layout, field position, font, line, print/PDF layout, or data mapping is modified by this patch.**
