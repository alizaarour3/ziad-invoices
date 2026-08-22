# تحديث GitHub إلى v3.3.17

بعد فك ضغط Patch ونسخ محتوياته فوق مشروع v3.3.16:

```powershell
git status
git add .
git commit -m "Add advances and 16pt invoice data font v3.3.17"
git push origin main
```

بعد أن يصبح Render `Live` نفّذ `Ctrl + F5`.

لا تحتاج إلى تغيير Environment Variables. الجداول الجديدة للسلف تنشأ تلقائياً ويطبق عليها RLS عند تشغيل التطبيق.
