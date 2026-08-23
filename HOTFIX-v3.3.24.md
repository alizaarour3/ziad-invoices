# Ziad Invoices v3.3.24 - Exact PR -> Payment Voucher Mapping

This update keeps the v3.3.23 Payment Voucher line-alignment and footer-removal fixes, and makes the conversion from **Payment Request / طلب صرف** to **Payment Voucher / مستند دفع** follow exactly the six requested mappings.

## Exact transfer mapping

1. Payment Request `Pay to` -> Payment Voucher `Pay to`
2. Payment Request `Description of purpose` -> Payment Voucher `Purpose`
3. Payment Request `Amount` -> Payment Voucher `Amount`
4. Payment Request `Currency / Currancy` -> Payment Voucher `Currency / Currancy`
5. Payment Request `Written amount` -> Payment Voucher `Written amount`
6. Payment Request `Approval` -> Payment Voucher `Approval`

## Nothing else is copied by this runtime conversion

The v3.3.24 transfer layer does **not** copy the PR number, date, reference, requester name, department, Cash/Bank/Transfer choice, prepared-by, or verified-by fields.

For the six fields above, the Payment Request value is treated as the source of truth during conversion, so a stale/default value already present in the Payment Voucher will be replaced by the value from the Payment Request.

## Existing v3.3.23 fixes retained

- Payment Voucher typed values remain raised so they sit directly above the ruled lines.
- The requested printing/design footer sentence remains removed/masked.
- The patch continues to work with aliases such as `description_of_purpose` -> `purpose` and `currancy` -> `currency`.

## Install

1. Close Ziad Invoices.
2. Extract this patch into the project root (the folder that contains `app`).
3. Run `APPLY-EXACT-PR-TO-PV-MAPPING-FIX.bat`.
4. Restart the application.
5. Create a Payment Request with all six mapped fields filled, convert it to a Payment Voucher, and verify the same six values appear in their matching positions.
