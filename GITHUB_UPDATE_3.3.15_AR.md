# تحديث GitHub إلى v3.3.15

1. فك ضغط Patch v3.3.15.
2. انسخ محتوياته فوق مشروع v3.3.14 ووافق على Replace.
3. نفذ:

```powershell
git status
git add .
git commit -m "Fix loan report popup blocker v3.3.15"
git push origin main
```

بعد أن يصبح Render `Live` نفذ `Ctrl + F5`.
