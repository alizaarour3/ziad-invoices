# رفع تحديث 3.3.9 إلى GitHub وRender

انسخ محتويات Patch 3.3.9 فوق مشروع 3.3.8 ووافق على Replace، ثم افتح PowerShell داخل المشروع:

```powershell
git status
git add .
git commit -m "Add transfer template and page permissions v3.3.9"
git push origin main
```

انتظر Render حتى يظهر Deploy للـcommit الجديد ويصبح `Live`، ثم نفّذ `Ctrl + F5`.

التحقق السريع:
- صفحة **تحويل** ظاهرة في القائمة.
- صفحة **صلاحيات** ظاهرة للمدير.
- يمكن تفعيل/تعطيل رؤية صفحات المستندات لمستخدم غير مدير.
- لا يوجد SQL يدوي مطلوب في Supabase؛ Migration يتم تلقائياً.
