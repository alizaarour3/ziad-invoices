# Ziad Invoices v3.3.29 — Final PR → PV contract

This release locks the user's final transfer rule. Do not reinterpret it in future updates.

| Payment Request source | Payment Voucher destination |
|---|---|
| `department` / القسم | `pay_to` |
| `pay_to` | `purpose` / الغرض — first ruled line |
| `purpose` / Description of purpose | `purpose` — remaining ruled lines |
| `amount` | `amount` |
| `currency` | `currency` |
| `written_amount` | `written_amount` |
| `approval` | `approval` |
| `prepared_by` / اسم مقدم الصرف | `receiver_name` / اسم المستلم |

## Print rule

All Payment Voucher values that sit on ruled lines must render immediately **above** the line in generated PDF output, never below it.

## Template protection

This update does not modify the Payment Request or Payment Voucher artwork/templates. It only changes data transfer behavior and value-overlay coordinates.
