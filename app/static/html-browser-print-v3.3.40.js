'use strict';

(() => {
  const VERSION = '3.3.40';
  const CSS_PX_PER_MM = 96 / 25.4;
  const A4_WIDTH_PX = 210 * CSS_PX_PER_MM;
  const A4_HEIGHT_PX = 297 * CSS_PX_PER_MM;

  function findNativePrintTransform(frameDocument, root) {
    let found = '';

    function walk(rules, insidePrint) {
      if (!rules) return;
      for (const rule of Array.from(rules)) {
        try {
          if (rule.type === CSSRule.MEDIA_RULE) {
            const isPrint = insidePrint || String(rule.media?.mediaText || '').toLowerCase().includes('print');
            walk(rule.cssRules, isPrint);
            continue;
          }
          if (!insidePrint || rule.type !== CSSRule.STYLE_RULE || !rule.selectorText) continue;
          if (!root.matches(rule.selectorText)) continue;
          const transform = rule.style.getPropertyValue('transform').trim();
          if (transform) found = transform;
        } catch (_) {
          // Ignore unsupported selectors/rules; all template styles are same-origin.
        }
      }
    }

    for (const sheet of Array.from(frameDocument.styleSheets || [])) {
      try { walk(sheet.cssRules, false); } catch (_) {}
    }
    return found;
  }

  function fallbackFitTransform(root) {
    const width = Math.max(1, root.offsetWidth || root.scrollWidth || A4_WIDTH_PX);
    const height = Math.max(1, root.offsetHeight || root.scrollHeight || A4_HEIGHT_PX);
    const scale = Math.min(1, A4_WIDTH_PX / width, A4_HEIGHT_PX / height);
    return scale < 0.999 ? `scale(${scale})` : 'none';
  }

  function ensurePrintOverride(frameDocument) {
    let style = frameDocument.getElementById('ziad-native-a4-print-override');
    if (style) return style;

    style = frameDocument.createElement('style');
    style.id = 'ziad-native-a4-print-override';
    style.textContent = `
      @media print {
        @page { size: A4 portrait !important; margin: 0 !important; }
        html, body {
          margin: 0 !important;
          padding: 0 !important;
          background: #fff !important;
        }
        [data-ziad-template-root="1"] {
          /* Preview scale belongs only to the editor. Printing uses the
             template's own A4 transform, or an automatic A4 fit fallback. */
          transform: var(--ziad-native-print-transform, none) !important;
          transform-origin: top left !important;
        }
      }
    `;
    (frameDocument.head || frameDocument.documentElement).appendChild(style);
    return style;
  }

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

    const root = frameDocument.querySelector(
      '[data-ziad-template-root="1"], #voucherPage, .page, .sheet, main'
    );
    if (!root) throw new Error('لم يتم العثور على صفحة المستند القابلة للطباعة');

    const active = frameDocument.activeElement;
    if (active && typeof active.blur === 'function') active.blur();

    // Important: app.js may scale this root to fit the editor viewport. Do not
    // remove or copy that preview scale into print. Read the template's own
    // @media print transform instead. Payment Request, for example, defines
    // scale(0.5613154173), which converts its 1414x2000 design canvas to A4.
    const nativeTransform = findNativePrintTransform(frameDocument, root) || fallbackFitTransform(root);
    root.style.setProperty('--ziad-native-print-transform', nativeTransform);
    ensurePrintOverride(frameDocument);

    const guideWasVisible = frameDocument.documentElement.classList.contains('ziad-field-guide');
    frameDocument.documentElement.classList.remove('ziad-field-guide');

    const restore = () => {
      if (guideWasVisible) frameDocument.documentElement.classList.add('ziad-field-guide');
      else frameDocument.documentElement.classList.remove('ziad-field-guide');
    };
    frameWindow.addEventListener('afterprint', restore, { once: true });

    frameWindow.focus();
    try {
      frameWindow.print();
    } finally {
      restore();
    }
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
      printCurrentHtmlTemplate();
    } catch (error) {
      console.error(`[Ziad ${VERSION}] native A4 local print failed`, error);
      alert(error && error.message ? error.message : 'تعذر فتح نافذة الطباعة');
    }
  }, true);

  window.ZIAD_HTML_PRINT_VERSION = VERSION;
})();
