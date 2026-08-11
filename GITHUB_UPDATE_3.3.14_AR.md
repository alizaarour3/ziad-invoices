# تحديث GitHub إلى v3.3.14

الإصدار يحسن واجهة **تحويل** و**الداشبورد** فقط، ولا يحتاج أي تغيير في Supabase أو Environment Variables.

## الخطوات

1. فك ضغط Patch v3.3.14.
2. انسخ محتوياته مباشرة فوق مجلد المشروع الحالي ووافق على Replace.
3. نفذ:

```powershell
git status
git add .
git commit -m "Improve transfer workspace and dashboard v3.3.14"
git push origin main
```

4. انتظر Render حتى يظهر `Live`.
5. افتح النظام واضغط `Ctrl + F5`.
6. اختبر الداشبورد وصفحة تحويل ثم افتح طلب تحويل وتأكد من أن القالب نفسه لم يتغير.
