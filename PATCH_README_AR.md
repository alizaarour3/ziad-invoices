# Patch v3.3.15 — إصلاح فتح تقرير القروض

هذا الـPatch مخصص للترقية من **v3.3.14 إلى v3.3.15**.

## الإصلاح

تقرير القرض لم يعد يعتمد على `window.open`، لذلك لن تظهر رسالة طلب السماح بفتح نافذة التقرير. التقرير يفتح كصفحة داخل النظام، والطباعة تعمل من زر **طباعة / حفظ PDF**.

لا توجد أي ترقية SQL ولا تغيير في Supabase.

بعد نسخ الملفات فوق مشروعك:

```powershell
git status
git add .
git commit -m "Fix loan report popup blocker v3.3.15"
git push origin main
```
