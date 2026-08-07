# نشر Ziad Invoices Professional 3.3.3 على Render وSupabase

يستخدم النشر السحابي:

- Render Web Service باستخدام Docker.
- Supabase PostgreSQL لقاعدة البيانات.
- Supabase Storage في Bucket خاص للمرفقات.

## 1. تجهيز Supabase

1. أنشئ مشروع Supabase.
2. من نافذة **Connect** انسخ رابط **Session pooler** وضعه في `DATABASE_URL`.
   - Session pooler مناسب لخدمة Backend دائمة عندما يكون الاتصال عبر IPv4.
   - استخدم `sslmode=require`.
3. من إعدادات API انسخ:
   - Project URL إلى `SUPABASE_URL`.
   - Server-side secret أو مفتاح `service_role` القديم إلى `SUPABASE_SERVICE_ROLE_KEY`.
4. لا تضع المفتاح السري داخل GitHub أو JavaScript أو أي ملف عام.

النظام ينشئ الجداول والفهارس عند أول تشغيل. كما يحاول إنشاء Bucket خاص بالاسم الموجود في `SUPABASE_STORAGE_BUCKET`، والقيمة الافتراضية `ziad-invoices`.

## 2. رفع المشروع إلى GitHub

ارفع ملفات المشروع إلى مستودع خاص، ولا ترفع `.env` أو بيانات العملاء:

```powershell
git init
git add .
git commit -m "Ziad Invoices 3.3.3"
git branch -M main
git remote add origin YOUR_PRIVATE_REPOSITORY
git push -u origin main
```

## 3. النشر بواسطة Render Blueprint

1. من Render اختر **New > Blueprint**.
2. اربط المستودع الخاص.
3. سيقرأ Render ملف `render.yaml` ويستخدم `Dockerfile`.
4. أدخل الأسرار المطلوبة عند الطلب:
   - `DATABASE_URL`
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_ROLE_KEY`
5. ابدأ النشر.

الخدمة مجهزة للاستماع على `0.0.0.0` والمنفذ الموجود في متغير `PORT`، ومسار الفحص هو `/api/health`.

## 4. المتغيرات

| المتغير | القيمة أو الغرض |
|---|---|
| `DATABASE_URL` | رابط PostgreSQL Session pooler |
| `SUPABASE_URL` | رابط مشروع Supabase |
| `SUPABASE_SERVICE_ROLE_KEY` | سر الخادم للوصول إلى Storage |
| `SUPABASE_STORAGE_BUCKET` | اسم Bucket الخاص |
| `ZIAD_STORAGE_BACKEND` | `supabase` |
| `ZIAD_SESSION_HOURS` | مدة الجلسة |
| `ZIAD_MAX_ATTACHMENT_BYTES` | أقصى حجم للمرفق |

## 5. أول تشغيل

1. افتح رابط الخدمة بعد نجاح Health Check.
2. أنشئ حساب المدير الحقيقي.
3. أنشئ مستنداً واحفظه.
4. ارفع مرفقاً وتأكد من ظهوره داخل المستند.
5. اطبع النموذج وحده ثم مع المرفق.
6. افتح صفحة الإعدادات وتأكد من قاعدة البيانات والقوالب.

لا تضف بيانات تجريبية إلى بيئة الإنتاج. استخدم مستنداً حقيقياً مصرحاً به أو نفذ اختبار القبول في مشروع Supabase منفصل.

## 6. نقل بيانات SQLite القديمة

قبل استخدام النسخة السحابية فعلياً، يمكن تشغيل:

```text
scripts/migrate_sqlite_to_supabase.py
```

خذ نسخة احتياطية أولاً، وضع متغيرات Supabase في البيئة، ثم نفّذ السكربت على نسخة من قاعدة SQLite. لا تشغله مرتين على نفس البيانات دون مراجعة النتائج.

## 7. التحقق

بعد النشر افتح:

```text
https://YOUR-SERVICE.onrender.com/api/health
```

يجب أن يعيد الإصدار `3.3.3` وحالة سليمة. راجع Logs في Render عند أي فشل في قاعدة البيانات أو Storage.

## 8. الحماية

- اجعل مستودع GitHub خاصاً.
- لا تكشف مفتاح Supabase السري للمتصفح.
- استخدم كلمة مرور قوية لقاعدة البيانات والمدير.
- فعّل النسخ الاحتياطية المناسبة في Supabase، ونزّل نسخة من داخل النظام دورياً.
- اختبر الاستعادة قبل الاعتماد التجاري.
