'use strict';

(() => {
  const VERSION = '3.3.39';

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

    const printablePage = frameDocument.querySelector(
      '[data-ziad-template-root="1"], #voucherPage, .page, .sheet, main'
    );
    if (!printablePage) {
      throw new Error('لم يتم العثور على صفحة المستند القابلة للطباعة');
    }

    const active = frameDocument.activeElement;
    if (active && typeof active.blur === 'function') active.blur();

    // app.js scales the A4 document down only so it fits inside the editor.
    // That preview transform must NEVER reach the physical print job. Save the
    // exact preview state, force true 1:1 A4 size for printing, then restore it.
    const previousStyle = printablePage.getAttribute('style');
    const previousPreviewScale = printablePage.dataset.ziadPreviewScale;
    const guideWasVisible = frameDocument.documentElement.classList.contains('ziad-field-guide');

    let printOverride = frameDocument.getElementById('ziad-local-print-100pct');
    if (!printOverride) {
      printOverride = frameDocument.createElement('style');
      printOverride.id = 'ziad-local-print-100pct';
      printOverride.textContent = `
        @media print {
          @page { size: A4 portrait !important; margin: 0 !important; }
          html, body {
            margin: 0 !important;
            padding: 0 !important;
            width: 210mm !important;
            min-width: 210mm !important;
            height: 297mm !important;
            min-height: 297mm !important;
            overflow: visible !important;
            background: #fff !important;
          }
          body { display: block !important; }
          [data-ziad-template-root="1"], #voucherPage, .page, .sheet {
            transform: none !important;
            transform-origin: top left !important;
            margin: 0 !important;
          }
        }
      `;
      (frameDocument.head || frameDocument.documentElement).appendChild(printOverride);
    }

    printablePage.style.setProperty('--ziad-template-scale', '1');
    printablePage.style.setProperty('transform', 'none', 'important');
    printablePage.style.setProperty('transform-origin', 'top left', 'important');
    printablePage.dataset.ziadPreviewScale = '1';
    frameDocument.documentElement.classList.remove('ziad-field-guide');

    const restorePreview = () => {
      if (previousStyle === null) printablePage.removeAttribute('style');
      else printablePage.setAttribute('style', previousStyle);

      if (previousPreviewScale === undefined) delete printablePage.dataset.ziadPreviewScale;
      else printablePage.dataset.ziadPreviewScale = previousPreviewScale;

      if (guideWasVisible) frameDocument.documentElement.classList.add('ziad-field-guide');
      else frameDocument.documentElement.classList.remove('ziad-field-guide');
    };

    frameWindow.addEventListener('afterprint', restorePreview, { once: true });

    // Force style/layout calculation before Chrome builds the print preview.
    void printablePage.getBoundingClientRect();
    frameWindow.focus();
    try {
      frameWindow.print();
    } finally {
      // Chromium blocks while the print dialog is open. Restoring here is safe
      // and also protects browsers that do not fire afterprint reliably.
      restorePreview();
    }
  }

  document.addEventListener('click', (event) => {
    const button = event.target.closest && event.target.closest('#print-document');
    if (!button) return;

    const frame = document.getElementById('template-frame');
    if (!frame || frame.dataset.ready !== '1') return;

    // Capture before app.js so the old server-side PDF modal cannot run.
    event.preventDefault();
    event.stopPropagation();
    event.stopImmediatePropagation();

    try {
      printCurrentHtmlTemplate();
    } catch (error) {
      console.error(`[Ziad ${VERSION}] local A4 print failed`, error);
      alert(error && error.message ? error.message : 'تعذر فتح نافذة الطباعة');
    }
  }, true);

  window.ZIAD_HTML_PRINT_VERSION = VERSION;
})();
