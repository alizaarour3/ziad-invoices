'use strict';

(() => {
  const VERSION = '3.3.43';
  const DEFAULT_PRINT_DATA_FONT_PT = 15;
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
      // Ignore styles injected by the editor/previous print helper. They contain
      // preview-only transforms such as scale(var(--ziad-template-scale)).
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

  function transformScale(transform) {
    const value = String(transform || '').trim();
    if (!value || value === 'none') return 1;
    const scaleMatch = value.match(/scale\(\s*([0-9.]+)\s*(?:,\s*([0-9.]+)\s*)?\)/i);
    if (scaleMatch) {
      const x = Number(scaleMatch[1]);
      const y = Number(scaleMatch[2] || scaleMatch[1]);
      if (Number.isFinite(x) && Number.isFinite(y) && x > 0 && y > 0) return Math.min(x, y);
    }
    const matrixMatch = value.match(/matrix\(\s*([\-0-9.e]+)\s*,\s*([\-0-9.e]+)\s*,\s*([\-0-9.e]+)\s*,\s*([\-0-9.e]+)/i);
    if (matrixMatch) {
      const a = Number(matrixMatch[1]);
      const b = Number(matrixMatch[2]);
      const c = Number(matrixMatch[3]);
      const d = Number(matrixMatch[4]);
      const sx = Math.sqrt(a * a + b * b);
      const sy = Math.sqrt(c * c + d * d);
      const scale = Math.min(sx || 1, sy || 1);
      if (Number.isFinite(scale) && scale > 0) return scale;
    }
    return 1;
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
        [data-ziad-template-root="1"] [data-ziad-field="1"]:not(input[type="checkbox"]),
        [data-ziad-template-root="1"] .ziad-split-line {
          font-size: var(--ziad-print-data-font-size, 15pt) !important;
        }
      }
    `;
    (frameDocument.head || frameDocument.documentElement).appendChild(style);
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
    const nativeScale = paymentRequest
      ? PAYMENT_REQUEST_NATIVE_PRINT_SCALE
      : Math.max(0.01, transformScale(nativeTransform));
    const physicalFontPt = paymentRequest
      ? PAYMENT_REQUEST_PRINT_DATA_FONT_PT
      : DEFAULT_PRINT_DATA_FONT_PT;

    // The PR design canvas is 1414x2000 and its official A4 print transform is
    // 0.5613154173. Compensate before the transform so the FINAL physical text
    // printed on paper is a real 16pt instead of roughly 9pt.
    const compensatedFontPt = physicalFontPt / nativeScale;
    root.style.setProperty('--ziad-native-print-transform', nativeTransform);
    root.style.setProperty('--ziad-print-data-font-size', `${compensatedFontPt.toFixed(4)}pt`);
    root.dataset.ziadPhysicalPrintFontPt = String(physicalFontPt);
    root.dataset.ziadNativePrintScale = String(nativeScale);
    ensurePrintOverride(frameDocument);

    const guideWasVisible = frameDocument.documentElement.classList.contains('ziad-field-guide');
    frameDocument.documentElement.classList.remove('ziad-field-guide');
    const restore = () => {
      if (guideWasVisible) frameDocument.documentElement.classList.add('ziad-field-guide');
      else frameDocument.documentElement.classList.remove('ziad-field-guide');
    };
    frameWindow.addEventListener('afterprint', restore, { once: true });

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
