# v3.3.10 - HTML Template 404 Fix

- Fixed `{"detail":"Not Found"}` appearing inside the document editor.
- Ensured all five exact HTML templates are shipped under `app/static/form-templates/`.
- Added a missing-template guard that keeps Save disabled if the template cannot load.
- Added cache-busting for HTML template iframe requests.
- Added static-route regression coverage for every HTML template.

# سجل التغييرات

## 3.3.9

- إضافة صفحة مستند جديدة باسم **تحويل** بالرمز `TR` مع ترقيم مستقل `TR-000001` وما بعده.
- اعتماد ملف `request-transfer.html` المرفوع كما هو byte-for-byte وربط حقوله الفعلية بقاعدة البيانات.
- دعم حقول التحويل: التاريخ، القسم، المستفيد، الغرض بسطرين، جهة التحويل، المبلغ، العملة، المبلغ كتابة بسطرين، الإعداد، الحسابات، والموافقة.
- دعم نفس Auto Fit وZoom 50%–250% للقالب الجديد، مع إخفاء Toolbar الداخلي أثناء عرضه داخل النظام دون تعديل الملف الأصلي.
- إضافة صفحة إدارية **صلاحيات** لإدارة رؤية الصفحات لكل مستخدم.
- فصل صلاحية رؤية الصفحة عن دور المستخدم؛ الدور يحدد العمليات والصفحات تحدد ما يستطيع رؤيته.
- تطبيق صلاحيات الصفحات على الواجهة وعلى API حتى لا يمكن الوصول المباشر إلى مستندات صفحة محجوبة.
- إضافة جدول قاعدة البيانات `user_page_permissions` ورفع Schema إلى الإصدار 4 مع Migration تلقائي.
- منح المستخدمين الحاليين الصفحات الحالية افتراضياً عند الترقية لتجنب إغلاق وصولهم، ثم يمكن للمدير سحب الصلاحيات.
- المدير يمتلك الوصول الكامل تلقائياً ولا يمكن تقييد صفحاته من شاشة الصلاحيات.
- إضافة صلاحيات الصفحات إلى النسخ الاحتياطي PostgreSQL JSON.
- توسيع الاختبارات لتغطية TR وإدارة الصلاحيات والمنع من API.
- الاختبارات الآلية: 9/9 ناجحة.

## 3.3.8

- Fixed Payment Request preview being rendered at the wrong internal scale.
- Fixed Payment Voucher and Vehicle Maintenance previews appearing as blank white pages in RTL iframe layout.
- Fixed multi-line HTML field navigation throwing an invalid empty selector error.
- Preview bridge now normalizes iframe geometry without changing the original template files.
- Zoom controls remain editor-only; print output stays A4 at the original template dimensions.

## 3.3.7
- إضافة أزرار تكبير وتصغير مباشرة داخل شريط المستند أثناء الإنشاء والتعديل والمشاهدة.
- مستوى التكبير من 50% إلى 250% بخطوات 25%، مع زر «ملاءمة» للرجوع فوراً إلى عرض A4 الكامل.
- التكبير يؤثر على معاينة القالب فقط ولا يغيّر ملف HTML الرسمي أو مقاس A4 أو الطباعة.
- عند التكبير تصبح منطقة القالب قابلة للتمرير أفقياً وعمودياً لتسهيل الكتابة في الحقول الصغيرة.
- يحافظ النظام على موضع المشاهدة قدر الإمكان أثناء التكبير والتصغير.
- يبدأ كل مستند جديد على وضع «ملاءمة» كما في 3.3.6، ويبقى مستوى التكبير عند الحفظ داخل نفس المستند.

## 3.3.6
- جعل نموذج A4 يظهر كاملاً داخل شاشة الإنشاء والتعديل والمشاهدة بدون تكبير.
- Auto Fit يعتمد على عرض المساحة المتاحة وارتفاع نافذة المتصفح مع الحفاظ على نسبة A4.
- يمنع تكبير النموذج فوق حجمه الطبيعي؛ يتم التصغير فقط عند الحاجة.
- إعادة الضبط تلقائياً عند تغيير حجم النافذة أو إخفاء/إظهار القائمة الجانبية.
- الطباعة تبقى A4 بالحجم الأصلي 100% ولا تتأثر بحجم المعاينة.
- لا يوجد أي تعديل على ملفات HTML الرسمية الأربعة أو مواقع حقولها.

# Changelog

## 3.3.5

- استبدال واجهات النماذج الأربعة بالقوالب HTML التي وفرها المستخدم، دون تعديل أي بايت في ملفات HTML الأصلية داخل `app/static/form-templates`.
- اعتماد نفس HTML في شاشة التحرير والطباعة، بدلاً من إعادة بناء النموذج كصورة مع طبقة حقول منفصلة.
- ربط جميع حقول RV / PR / PV / VM مباشرة بعناصرها الأصلية داخل القوالب الجديدة.
- حفظ الحقول متعددة الأسطر كسطور مستقلة في طلب الصرف مع الانتقال المنظم بينها.
- الطباعة تتم بواسطة Chromium/Playwright ثم تثبت على A4 300 DPI، ما يحافظ على العربية والاتجاه RTL والمواقع البصرية للقالب.
- Chromium يعمل فقط عند تجهيز ملف الطباعة، والملف الناتج يبقى ضمن Cache الإصدار الحالي لتفادي إعادة الرندر غير الضرورية.
- إضافة SHA-256 مستقل للقوالب HTML باسم `HTML_TEMPLATE_HASHES.sha256` وضمها للنسخ الاحتياطي وفحص سلامة النظام.
- إضافة Chromium وPlaywright إلى صورة Render production.
- الاختبارات الآلية: 9/9 ناجحة.


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
