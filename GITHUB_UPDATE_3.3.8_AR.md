# رفع تحديث 3.3.8 إلى GitHub وRender

انسخ محتويات Patch 3.3.8 فوق مشروع 3.3.7 ووافق على Replace، ثم نفذ:

```powershell
git status
git add .
git commit -m "Fix exact HTML template preview scaling v3.3.8"
git push origin main
```

Render سيبدأ Deploy تلقائياً إذا كان Auto Deploy مفعلاً. بعد ظهور Live استخدم Ctrl+F5 لمسح ملفات JavaScript/CSS القديمة من Cache.

لا يوجد أي SQL جديد ولا تغيير مطلوب في Supabase.
