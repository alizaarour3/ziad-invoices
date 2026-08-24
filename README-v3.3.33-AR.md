# Ziad Invoices v3.3.33 — تحديث موحد PR → PV والطباعة

هذا تحديث واحد يجمع التصحيحات المطلوبة على ملفات HTML الحالية التي رفعها المستخدم.

## القاعدة النهائية الثابتة

- طلب الصرف `Department / القسم` → مستند الدفع `Pay to / الدفع لـ`.
- طلب الصرف `Pay to / الدفع لـ` → مستند الدفع `Purpose / الغرض`، السطر الأول.
- `Description of Purpose` → يكمل داخل `Purpose` في الأسطر التالية.
- `Amount` → `Amount`.
- `Currency` → `Currency`.
- `Written Amount` → `Written Amount`.
- `Approval` → `Approval`.
- `Prepared by / اسم مقدم الصرف` → `Name of Receiver / اسم المستلم`.
- **Name of Requester لا يُستخدم كاسم المستلم.**

## الطباعة

كل النصوص في مستند الدفع لها ضبط Print خاص يرفعها فوق الخطوط عند PDF/الطباعة. لم يتم تغيير صورة/رسم القالب أو خطوطه.

## التثبيت

فك الضغط في أي مكان وشغّل:

`APPLY-v3.3.33-ONE-FIX.bat`

الـ installer يبحث تلقائياً عن `C:\Users\User\Desktop\ziad-invoices-v3.3.3`. إذا لم يجده يطلب مسار المشروع.

بعد النجاح أعد تشغيل النظام واضغط `Ctrl+F5` مرة واحدة.
