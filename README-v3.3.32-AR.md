# Ziad Invoices v3.3.32 — Final HTML PR → PV mapping fix

هذا التحديث يصلح التحويل من **طلب صرف HTML** إلى **مستند دفع HTML** من المصدر مباشرة.

## القاعدة الثابتة

- طلب الصرف `Department / القسم` → مستند الدفع `Pay to / الدفع لـ`
- طلب الصرف `Pay to / الدفع لـ` → مستند الدفع `Purpose / الغرض` (السطر الأول)
- طلب الصرف `Description of purpose` → مستند الدفع `Purpose / الغرض` (الأسطر التالية)
- Amount → Amount
- Currency → Currency
- Written Amount → Written Amount
- Approval → Approval
- Name of Requester → Name of Receiver

## مهم

لا يتم تعديل أي قالب HTML أو صورة أو PDF في هذا التحديث. يتم تعديل منطق التحويل فقط.

بعد التثبيت أعد تشغيل النظام ثم اضغط Ctrl+F5 مرة واحدة.
