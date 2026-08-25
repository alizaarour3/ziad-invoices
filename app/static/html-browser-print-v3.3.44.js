'use strict';

(() => {
  const VERSION = '3.3.44';
  const PAYMENT_REQUEST_PRINT_DATA_FONT_PT = 16;
  const PAYMENT_REQUEST_NATIVE_PRINT_SCALE = 0.5613154173;
  const CSS_PX_PER_MM = 96 / 25.4;
  const A4_WIDTH_PX = 210 * CSS_PX_PER_MM;
  const A4_HEIGHT_PX = 297 * CSS_PX_PER_MM;

  function isPaymentRequest(frameDocument) {
    const title = String(frameDocument.title || '');
    const url = String(frameDocument.location?.pathname || '');
    return /Payment Request/i.test(title) || /payment-request\.html$/i.test(url);
  }

  function findNativePrintTransform(frameDocument, root) {
    let found = '';
    for (const sheet of Array.from(frameDocument.styleSheets || [])) {
      const ownerId = sheet.ownerNode?.id || '';
      if (ownerId === 'ziad-template-bridge-style' || ownerId === 'ziad-native-a4-print-override') continue;

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
            if (!transform || transform.includes('--ziad-template-scale') || transform.includes('--ziad-native-print-transform')) continue;
            found = transform;
          } catch (_) {}
        }
      }

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
    if (style) style.remove();
    style = frameDocument.createElement('style');
    style.id = 'ziad-native-a4-print-override';
    style.textContent = `
      @media print {
        @page { size: A4 portrait !important; margin: 0 !important; }
        html, body { margin: 0 !important; padding: 0 !important; background: #fff !important; }
        [data-ziad-template-root="1"] {
          transform: var(--ziad-native-print-transform, none) !important;
          transform-origin: top left !important;
        }
      }
    `;
    (frameDocument.head || frameDocument.documentElement).appendChild(style);
  }

  function forcePaymentRequestInlinePrintFont(frameDocument, root) {
    const compensatedPt = PAYMENT_REQUEST_PRINT_DATA_FONT_PT / PAYMENT_REQUEST_NATIVE_PRINT_SCALE;
    const elements = Array.from(root.querySelectorAll('[data-ziad-field="1"]:not(input[type="checkbox"]), .ziad-split-line'));
    const snapshots = elements.map(element => ({
      element,
      value: element.style.getPropertyValue('font-size'),
      priority: element.style.getPropertyPriority('font-size'),
    }));

    // app.js sets 16pt !important inline on these elements for the editor.
    // Stylesheet print rules cannot beat inline !important. Replace that exact
    // inline value temporarily so, after the PR's 0.5613154173 A4 transform,
    // the physical text on paper is a real 16pt.
    for (const element of elements) {
      element.style.setProperty('font-size', `${compensatedPt.toFixed(4)}pt`, 'important');
    }

    return () => {
      for (const snapshot of snapshots) {
        if (snapshot.value) snapshot.element.style.setProperty('font-size', snapshot.value, snapshot.priority || '');
        else snapshot.element.style.removeProperty('font-size');
      }
    };
  }

  function printCurrentHtmlTemplate() {
    const frame = document.getElementById('template-frame');
    if (!frame || frame.dataset.ready !== '1') throw new Error('قالب المستند غير جاهز للطباعة بعد');

    const frameWindow = frame.contentWindow;
    const frameDocument = frame.contentDocument;
    if (!frameWindow || !frameDocument) throw new Error('تعذر الوصول إلى قالب المستند');

    const root = frameDocument.querySelector('[data-ziad-template-root="1"], #voucherPage, .page, .sheet, main');
    if (!root) throw new Error('لم يتم العثور على صفحة المستند القابلة للطباعة');

    const active = frameDocument.activeElement;
    if (active && typeof active.blur === 'function') active.blur();

    const paymentRequest = isPaymentRequest(frameDocument);
    const nativeTransform = paymentRequest
      ? `scale(${PAYMENT_REQUEST_NATIVE_PRINT_SCALE})`
      : (findNativePrintTransform(frameDocument, root) || fallbackFitTransform(root));

    root.style.setProperty('--ziad-native-print-transform', nativeTransform);
    ensurePrintOverride(frameDocument);

    const restoreFont = paymentRequest
      ? forcePaymentRequestInlinePrintFont(frameDocument, root)
      : () => {};

    const guideWasVisible = frameDocument.documentElement.classList.contains('ziad-field-guide');
    frameDocument.documentElement.classList.remove('ziad-field-guide');

    let restored = false;
    const restore = () => {
      if (restored) return;
      restored = true;
      restoreFont();
      if (guideWasVisible) frameDocument.documentElement.classList.add('ziad-field-guide');
      else frameDocument.documentElement.classList.remove('ziad-field-guide');
    };

    frameWindow.addEventListener('afterprint', restore, { once: true });

    // Force layout after changing inline sizes so Chrome captures the enlarged
    // values in print preview instead of a stale editor frame.
    void root.getBoundingClientRect();
    frameWindow.focus();
    try { frameWindow.print(); }
    finally { restore(); }
  }

  document.addEventListener('click', (event) => {
    const button = event.target.closest && event.target.closest('#print-document');
    if (!button) return;
    const frame = document.getElementById('template-frame');
    if (!frame || frame.dataset.ready !== '1') return;

    event.preventDefault();
    event.stopPropagation();
    event.stopImmediatePropagation();

    try { printCurrentHtmlTemplate(); }
    catch (error) {
      console.error(`[Ziad ${VERSION}] local A4 print failed`, error);
      alert(error && error.message ? error.message : 'تعذر فتح نافذة الطباعة');
    }
  }, true);

  window.ZIAD_HTML_PRINT_VERSION = VERSION;
})();
