# تحديث GitHub إلى v3.3.20

فك ضغط Patch v3.3.20 وانسخ محتوياته فوق مشروع v3.3.19 ثم نفذ:

```powershell
git status
git add .
git commit -m "Polish UI and add PR to PV conversion v3.3.20"
git push origin main
```

بعد أن يصبح Render بحالة `Live` نفذ `Ctrl + F5`.

لا يحتاج هذا الإصدار إلى SQL جديد أو تغيير Environment Variables.
