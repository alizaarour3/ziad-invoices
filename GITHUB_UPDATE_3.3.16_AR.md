# تحديث GitHub إلى v3.3.16

هذا الإصدار يعالج تحذير Supabase `rls_disabled_in_public` ويؤمّن جداول Ziad Invoices الموجودة داخل schema `public`.

بعد نسخ ملفات الـ Patch فوق مشروع v3.3.15:

```powershell
git status
git add .
git commit -m "Harden Supabase public schema security v3.3.16"
git push origin main
```

عند تشغيل Render بالإصدار الجديد سيحاول النظام تطبيق الحماية تلقائياً عند الاتصال بـ Supabase. ولتأمين قاعدة البيانات الحالية فوراً يمكن تشغيل `SUPABASE_SECURITY_FIX.sql` من Supabase SQL Editor.
