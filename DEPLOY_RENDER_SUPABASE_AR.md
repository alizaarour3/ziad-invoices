# نشر Ziad Invoices Professional 3.3.9 على Render وSupabase

يستخدم النشر السحابي Render Web Service باستخدام Docker، وSupabase PostgreSQL لقاعدة البيانات، وSupabase Storage للمرفقات.

## متغيرات البيئة

| المتغير | الغرض |
|---|---|
| `DATABASE_URL` | PostgreSQL Session Pooler |
| `SUPABASE_URL` | رابط مشروع Supabase |
| `SUPABASE_SERVICE_ROLE_KEY` | سر الخادم للوصول إلى Storage |
| `SUPABASE_STORAGE_BUCKET` | اسم Bucket |
| `ZIAD_STORAGE_BACKEND` | `supabase` |
| `ZIAD_SESSION_HOURS` | مدة الجلسة |
| `ZIAD_MAX_ATTACHMENT_BYTES` | أقصى حجم للمرفق |

## قاعدة البيانات في 3.3.9

لا تشغّل SQL يدوياً لهذا التحديث. عند بدء التطبيق:
1. ينشئ/يتحقق من الجداول الأساسية.
2. يرفع Schema إلى الإصدار 4.
3. ينشئ جدول `user_page_permissions`.
4. يضيف مفاتيح صفحات الأعمال الحالية للمستخدمين الموجودين بقيمة مفعلة افتراضياً.
5. يضيف نوع المستند `TR` إلى `document_types` ويجهز عداده المستقل.

بعد ذلك يمكن للمدير تعطيل الصفحات للمستخدمين من صفحة **صلاحيات**.

## رفع GitHub

```powershell
git status
git add .
git commit -m "Add transfer template and page permissions v3.3.9"
git push origin main
```

إذا كان Auto Deploy مفعلاً سيبدأ Render النشر تلقائياً.

## التحقق بعد Render

افتح:

```text
https://YOUR-SERVICE.onrender.com/api/health
```

يجب أن يعيد الإصدار `3.3.9`.

ثم اختبر تسجيل الدخول كمدير، ظهور **تحويل**، إنشاء مستند TR، فتح **صلاحيات**، تعطيل صفحة لمستخدم غير مدير، والتأكد أن الوصول المباشر إليها مرفوض.

## الحماية

- اجعل مستودع GitHub خاصاً.
- لا تضع أسرار Supabase في GitHub.
- خذ نسخة احتياطية قبل تحديث Production.
- مدير النظام لا يمكن حجب الصفحات عنه من شاشة الصلاحيات.
- لا تضف بيانات Demo إلى قاعدة الإنتاج.

## متطلبات الطباعة

Dockerfile يثبت Chromium ويستخدم التطبيق Playwright لطباعة القوالب HTML إلى A4. استخدم Docker runtime على Render.
