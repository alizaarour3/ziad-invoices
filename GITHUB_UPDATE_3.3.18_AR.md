# تحديث GitHub إلى v3.3.18

هذا التحديث يلغي قفل الحساب بعد تكرار محاولات الدخول الخاطئة ويقوي الطباعة على Render.

بعد نسخ ملفات الـ Patch فوق المشروع الحالي:

```powershell
git status
git add .
git commit -m "Disable login lockout and fix print 5xx v3.3.18"
git push origin main
```

انتظر Render حتى يصبح Live ثم نفذ Ctrl + F5. لا يحتاج التحديث إلى SQL أو تغيير Environment Variables.
