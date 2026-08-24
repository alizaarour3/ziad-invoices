'use strict';

(() => {
  const VERSION = '3.3.37';

  function documentIdFromPath() {
    const match = window.location.pathname.match(/^\/documents\/(\d+)(?:\/|$)/);
    return match ? Number(match[1]) : null;
  }

  function recordPrint(documentId) {
    if (!documentId) return;
    const token = localStorage.getItem('ziad_token') || '';
    if (!token) return;
    fetch(`/api/documents/${documentId}/record-html-print`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      keepalive: true,
    }).catch(() => {});
  }

  function printHtmlFrame(frame) {
    const frameWindow = frame && frame.contentWindow;
    const frameDocument = frame && frame.contentDocument;
    if (!frameWindow || !frameDocument) throw new Error('تعذر الوصول إلى قالب الطباعة');

    const page = frameDocument.querySelector('#voucherPage, .page, .sheet, main');
    if (!page) throw new Error('قالب HTML غير جاهز للطباعة');

    // The exact same HTML visible in the editor is printed by the user's browser.
    // No server-side Chromium, screenshot, image fallback, or legacy PDF is used.
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
      recordPrint(documentIdFromPath());
      printHtmlFrame(frame);
    } catch (error) {
      console.error(`[Ziad ${VERSION}] browser HTML print failed`, error);
      alert(error && error.message ? error.message : 'تعذر فتح نافذة الطباعة');
    }
  }, true);

  window.ZIAD_HTML_PRINT_VERSION = VERSION;
})();
