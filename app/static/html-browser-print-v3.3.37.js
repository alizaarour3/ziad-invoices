'use strict';

(() => {
  const VERSION = '3.3.37';

  function printHtmlFrame(frame) {
    const frameWindow = frame && frame.contentWindow;
    const frameDocument = frame && frame.contentDocument;
    if (!frameWindow || !frameDocument) throw new Error('تعذر الوصول إلى قالب الطباعة');

    const page = frameDocument.querySelector('#voucherPage, .page, .sheet, main');
    if (!page) throw new Error('قالب HTML غير جاهز للطباعة');

    // Print the exact HTML already loaded in the editor. This deliberately avoids
    // the server /api/.../print endpoint, server-side Chromium, screenshots, the
    // legacy image/PDF fallback, and the Render memory spike that caused exit 137.
    frameWindow.focus();
    frameWindow.print();
  }

  document.addEventListener('click', (event) => {
    const button = event.target.closest && event.target.closest('#print-document');
    if (!button) return;

    const frame = document.getElementById('template-frame');
    if (!frame || frame.dataset.ready !== '1') return;

    event.preventDefault();
    event.stopPropagation();
    event.stopImmediatePropagation();

    try {
      printHtmlFrame(frame);
    } catch (error) {
      console.error(`[Ziad ${VERSION}] browser HTML print failed`, error);
      alert(error && error.message ? error.message : 'تعذر فتح نافذة الطباعة');
    }
  }, true);

  window.ZIAD_HTML_PRINT_VERSION = VERSION;
})();
