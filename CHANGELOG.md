# Changelog


## 3.3.4

- إصلاح محرك كتابة اللغة العربية في PDF باستخدام RAQM + HarfBuzz + FriBiDi.
- إجبار Docker/Render على بناء Pillow مع دعم RAQM والتحقق منه أثناء الـ Build.
- استخدام خطوط Noto Sans Arabic/Noto Naskh Arabic أولاً في الحقول العربية.
- إضافة language=ar واتجاه RTL الصريح لمحرك تشكيل النص.
- منع إنشاء PDF عربي مشوّه إذا كان محرك RAQM غير متاح.
- إضافة حالة محرك العربية إلى /api/health وصفحة حالة النظام.
- إضافة unicode-bidi: plaintext لحقول المحرر داخل المتصفح.
- تغيير مفتاح Cache للطباعة حتى لا يعاد استخدام PDF قديم ذي كتابة عربية غير صحيحة.
- لا تغيير على ملفات PDF/Word الرسمية أو مواقع الحقول.

## 3.3.3

- معايرة جميع حقول النماذج الأربعة وفق مناطق الكتابة التي حددها المستخدم في الصور المرجعية.
- دعم `line_boxes` بحيث يكون لكل سطر موضع وعرض وارتفاع مستقل في الشاشة وملف PDF.
- تنظيم أسطر الغرض والمبلغ كتابة سطراً بسطر دون تداخل.
- معايرة جدول صيانة السيارات والحقول العلوية والتواقيع بدقة.
- إضافة حقول قابلة للكتابة لكل الخانات المظللة في صفّي مجموع الصيانة والمبلغ المسترجع.
- لم يتم تعديل أي بايت في نماذج PDF أو Word الرسمية.

## 3.3.2

- Replaced every contextual action dropdown in document tables with direct View, Edit, Print, and Delete buttons.
- Replaced the user-table action dropdown with a direct Edit button.
- Replaced attachment dropdowns with direct View, Download, and Delete buttons.
- Exposed permanent delete directly in the document command bar for administrators.
- Fixed Vehicle Maintenance creation validation by accepting configured document types such as `VM` instead of restricting creation to three legacy codes.
- Added regression coverage for creating and saving real Vehicle Maintenance records.
- Preserved all official PDF and Word templates byte-for-byte.

## 3.3.0

- Added a fully hideable desktop sidebar and a mobile drawer with backdrop.
- Rebuilt the dashboard with real database metrics, type summaries, recent documents, and seven-day activity.
- Replaced repeated document and attachment buttons with one contextual actions menu.
- Replaced duplicate save buttons with a single Save action and an explicit saved/draft selector.
- Added exact line-by-line inputs and PDF rendering for official multiline fields.
- Refined every primary screen: document lists, editor, attachments, users, audit, reports, and system status.
- Added real list filtering and summary chips across document, user, and audit pages.
- Merged PostgreSQL/Supabase Storage support into the official-PDF-template release.
- Added Render Docker/Blueprint deployment files and SQLite-to-Supabase migration tooling.
- Added `reportlab` as an explicit runtime dependency and a Windows-specific dependency file for `pywebview`.
- Removed external web-font dependencies so the interface works offline and within the strict CSP.
- Expanded automated coverage to dashboard metrics and the line-by-line template contract.

## 3.2.0

- Added immutable official PDF templates for Receipt Voucher, Payment Request, Payment Voucher, and Vehicle Maintenance.
- Added an overlay print engine that retains every source PDF page.
- Added Vehicle Maintenance as a fourth independent section.
- Redesigned attachments with drag-and-drop and multiple selection.
- Added official PDF SHA-256 integrity and backup coverage.

## 3.0.2

- Normalized production Word forms to ISO A4 while preserving the uploaded originals.
- Rebuilt PDF output as A4 at 300 DPI.
- Improved Arabic and English text fitting.

## 3.0.1

- Added account lockout and secure password changes with session revocation.

## 2.0.0

- Added the Windows desktop launcher, reporting, backup tooling, and desktop shortcut helper.

## 1.0.0

- Initial authentication, documents, attachments, printing, users, audit, integrity, and backup foundation.
