# رفع تحديث 3.3.4 إلى GitHub

هذا الإصدار يصلح كتابة العربية في PDF ولا يغير قوالب PDF/Word أو مواقع الحقول.

## الطريقة الأسهل

1. فك ضغط الحزمة الجديدة.
2. داخل مستودعك المحلي الحالي `ziad-invoices` انسخ محتويات مجلد `ziad-invoices-v3.3.4` فوق الملفات الحالية.
3. **لا تنسخ أو ترفع** `.env` أو قاعدة البيانات المحلية أو مرفقات العملاء.
4. افتح PowerShell داخل مجلد المستودع ونفذ:

```powershell
git status
git add .
git commit -m "Fix Arabic RTL PDF rendering v3.3.4"
git push origin main
```

## الملفات المهمة في هذا التحديث

- `Dockerfile`
- `app/services/pdf_service.py`
- `app/main.py`
- `app/services/backup_service.py`
- `app/static/app.js`
- `app/static/styles.css`
- `app/static/index.html`
- `tests/test_system.py`

## بعد GitHub

Render سيبدأ Deploy تلقائياً إذا كان Auto-Deploy مفعلاً. في Build Logs يجب أن ترى:

```text
RAQM: True Harfbuzz: True FriBiDi: True
```

وبعد أن تصبح الخدمة Live افتح:

```text
https://YOUR-SERVICE.onrender.com/api/health
```

وتأكد أن `raqm`, `harfbuzz`, `fribidi` كلها `true`.

ثم أنشئ PDF جديداً من مستند عربي؛ لا تعتمد على PDF قديم مخزن سابقاً.
