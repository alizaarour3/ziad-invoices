# تحديث GitHub إلى v3.3.11 — صفحة قروض

1. انسخ محتويات Patch فوق مشروعك الحالي v3.3.10 ووافق على Replace.
2. نفذ:

```powershell
git status
git add .
git commit -m "Add loans and repayment management v3.3.11"
git push origin main
```

3. انتظر Render حتى يصبح `Live`.
4. نفذ `Ctrl + F5` في المتصفح.
5. ستظهر صفحة **قروض** ويمكن إدارتها من صفحة **صلاحيات**.

لا تحتاج إلى SQL يدوي في Supabase؛ التطبيق ينشئ الجداول الجديدة تلقائياً عند التشغيل.
