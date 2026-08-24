'use strict';

(() => {
  const VERSION = '3.3.38';

  function printCurrentHtmlTemplate() {
    const frame = document.getElementById('template-frame');
    if (!frame || frame.dataset.ready !== '1') {
      throw new Error('قالب المستند غير جاهز للطباعة بعد');
    }

    const frameWindow = frame.contentWindow;
    const frameDocument = frame.contentDocument;
    if (!frameWindow || !frameDocument) {
      throw new Error('تعذر الوصول إلى قالب المستند');
    }

    const printablePage = frameDocument.querySelector('#voucherPage, .page, .sheet, main');
    if (!printablePage) {
      throw new Error('لم يتم العثور على صفحة المستند القابلة للطباعة');
    }

    // Keep printing entirely on the user's computer. The browser opens the
    // operating-system print UI with the local/default printer available.
    // Render is never asked to create a PDF and never launches Chromium.
    const active = frameDocument.activeElement;
    if (active && typeof active.blur === 'function') active.blur();
    frameWindow.focus();
    frameWindow.print();
  }

  document.addEventListener('click', (event) => {
    const button = event.target.closest && event.target.closest('#print-document');
    if (!button) return;

    const frame = document.getElementById('template-frame');
    if (!frame || frame.dataset.ready !== '1') return;

    // Capture before app.js so the old server-side print modal cannot run.
    event.preventDefault();
    event.stopPropagation();
    event.stopImmediatePropagation();

    try {
      printCurrentHtmlTemplate();
    } catch (error) {
      console.error(`[Ziad ${VERSION}] local browser print failed`, error);
      alert(error && error.message ? error.message : 'تعذر فتح نافذة الطباعة');
    }
  }, true);

  window.ZIAD_HTML_PRINT_VERSION = VERSION;
})();
