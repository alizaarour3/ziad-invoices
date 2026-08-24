/* Ziad Invoices v3.3.33 - HTML templates + locked Payment Request -> Payment Voucher transfer */
(() => {
  'use strict';

  const VERSION = '3.3.33';
  const HOST_CLASS = 'ziad-html-template-host';
  const FRAME_CLASS = 'ziad-html-template-frame';

  const templateDefs = {
    PV: {
      url: '/static/form-templates/payment-voucher.html',
      map: {
        document_number: ['#rv'], date: ['#date'], reference: ['#ref'], payment_request: ['#request'],
        pay_to: ['#payto'], purpose: ['#purpose'], amount: ['#amount'], currency: ['#currency'],
        written_amount: ['#written'], receiver_name: ['#receiver'], accountant: ['#accountant'], approval: ['#approval']
      }
    },
    PR: {
      url: '/static/form-templates/payment-request.html',
      map: {
        document_number: ['[data-save="pr_number"]'], date: ['[data-save="date"]'], reference: ['[data-save="reference"]'],
        requester_name: ['[data-save="requester"]'], requester: ['[data-save="requester"]'],
        department: ['[data-save="department"]'], pay_to: ['[data-save="pay_to"]'],
        purpose: ['[data-save="purpose_1"]','[data-save="purpose_2"]'],
        payment_cash: ['[data-save="cash"]'], cash: ['[data-save="cash"]'],
        payment_bank: ['[data-save="bank"]'], bank: ['[data-save="bank"]'],
        payment_transfer: ['[data-save="transfer"]'], transfer: ['[data-save="transfer"]'],
        amount: ['[data-save="amount"]'], currency: ['[data-save="currency"]'],
        written_amount: ['[data-save="written_amount_1"]','[data-save="written_amount_2"]'],
        prepared_by: ['[data-save="prepared_signature"]'], verified_by: ['[data-save="manager_signature"]'],
        approval: ['[data-save="approval_signature"]']
      }
    },
    TRANSFER: {
      url: '/static/form-templates/request-transfer.html',
      map: {
        date: ['[data-field="date"]'], department: ['[data-field="department"]'], pay_to: ['[data-field="payto"]'],
        purpose: ['[data-field="purpose1"]','[data-field="purpose2"]'], transfer: ['[data-field="transfer"]'],
        amount: ['[data-field="amount"]'], currency: ['[data-field="currency"]'],
        written_amount: ['[data-field="written1"]','[data-field="written2"]'],
        prepared_by: ['[data-field="prepared"]'], accountant: ['[data-field="accounts"]'], approval: ['[data-field="approval"]']
      }
    },
    CAR_MAINTENANCE: {
      url: '/static/form-templates/car-maintenance.html',
      map: {
        vehicle: ['[aria-label="السيارة"]'], car: ['[aria-label="السيارة"]'],
        vehicle_number: ['[aria-label="رقم السيارة"]'], car_number: ['[aria-label="رقم السيارة"]'],
        date: ['[aria-label="تاريخ الصيانة"]'], maintenance_date: ['[aria-label="تاريخ الصيانة"]'],
        received_amount: ['[aria-label="المبلغ المستلم لغرض الصيانة"]'], maintenance_amount: ['[aria-label="المبلغ المستلم لغرض الصيانة"]'],
        driver: ['[aria-label="السائق"]'], executive_manager: ['[aria-label="المدير التنفيذي"]'],
        line_manager: ['[aria-label="المدير المباشر"]'], accounts_manager: ['[aria-label="مدير الحسابات"]']
      }
    }
  };

  function allMirrors(page) {
    return [...page.querySelectorAll('[data-field]')].filter(el => !el.closest('iframe'));
  }

  function mirrorKeys(page) {
    return new Set(allMirrors(page).map(el => el.dataset.field).filter(Boolean));
  }

  function pageText(page) {
    return (page.closest('.app-content,main,.shell-content,.content')?.innerText || document.body.innerText || '').replace(/\s+/g,' ');
  }

  function detectType(page) {
    const img = page.querySelector('.template-bg');
    const src = (img?.getAttribute('src') || '').toLowerCase();
    const keys = mirrorKeys(page);
    const text = pageText(page);

    if (/payment[-_ ]?voucher|voucher|pv\b/.test(src) || keys.has('receiver_name') || keys.has('payment_request') || /مستند دفع|سند دفع|Payment Voucher/i.test(text)) return 'PV';
    if (/payment[-_ ]?request|request|pr\b/.test(src) || (keys.has('department') && keys.has('pay_to') && (keys.has('requester_name') || keys.has('payment_cash'))) || /طلب صرف|Payment Request/i.test(text)) return 'PR';
    if (/transfer|تحويل/.test(src) || /طلب تحويل/.test(text)) return 'TRANSFER';
    if (/maintenance|car|vehicle|صيانة/.test(src) || /كشف صيانة السيارات/.test(text)) return 'CAR_MAINTENANCE';
    return null;
  }

  function getMirrorGroup(page, key) {
    return allMirrors(page).filter(el => el.dataset.field === key).sort((a,b) => Number(a.dataset.fieldLine || 0) - Number(b.dataset.fieldLine || 0));
  }

  function readMirror(page, key) {
    const group = getMirrorGroup(page, key);
    if (!group.length) return undefined;
    if (group.length > 1 || group.some(el => el.dataset.fieldLine !== undefined)) {
      return group.map(el => String(el.value || '')).join('\n').replace(/\n+$/g,'');
    }
    const el = group[0];
    return el.type === 'checkbox' ? !!el.checked : String(el.value ?? '');
  }

  function writeMirror(page, key, value) {
    const group = getMirrorGroup(page, key);
    if (!group.length) return;
    if (group.length > 1 || group.some(el => el.dataset.fieldLine !== undefined)) {
      const parts = String(value ?? '').replace(/\r\n?/g,'\n').split('\n');
      group.forEach((el,i) => {
        const next = parts[i] || '';
        if (el.value !== next) {
          el.value = next;
          el.dispatchEvent(new Event('input',{bubbles:true}));
          el.dispatchEvent(new Event('change',{bubbles:true}));
        }
      });
      return;
    }
    const el = group[0];
    if (el.type === 'checkbox') {
      const next = !!value;
      if (el.checked !== next) {
        el.checked = next;
        el.dispatchEvent(new Event('input',{bubbles:true}));
        el.dispatchEvent(new Event('change',{bubbles:true}));
      }
    } else {
      const next = String(value ?? '');
      if (el.value !== next) {
        el.value = next;
        el.dispatchEvent(new Event('input',{bubbles:true}));
        el.dispatchEvent(new Event('change',{bubbles:true}));
      }
    }
  }

  function childValue(el) {
    if (!el) return '';
    if (el.type === 'checkbox' || el.type === 'radio') return !!el.checked;
    if (el.isContentEditable) return (el.textContent || '').replace(/\r/g,'').trim();
    return String(el.value ?? '');
  }

  function setChildValue(el, value) {
    if (!el) return;
    if (el.type === 'checkbox' || el.type === 'radio') {
      el.checked = !!value;
      return;
    }
    const next = String(value ?? '');
    if (el.isContentEditable) el.textContent = next;
    else el.value = next;
    try { el.dispatchEvent(new Event('input',{bubbles:true})); } catch (_) {}
  }

  function splitLines(value, count) {
    const parts = String(value ?? '').replace(/\r\n?/g,'\n').split('\n');
    if (parts.length > count) parts.splice(count - 1, parts.length - count + 1, parts.slice(count - 1).join(' '));
    while (parts.length < count) parts.push('');
    return parts.slice(0,count);
  }

  function findChild(doc, selectors) {
    return selectors.map(sel => doc.querySelector(sel)).filter(Boolean);
  }

  function canonicalKeys(page, def) {
    const present = mirrorKeys(page);
    return Object.keys(def.map).filter(key => present.has(key));
  }

  // FINAL user-approved PR -> PV contract for the real HTML templates.
  // This intentionally reads/writes the HTML fields themselves, not a screenshot/background.
  const PR_TO_PV_STORAGE = 'ziad-pr-pv-html-final-v3.3.33';
  const PR_TO_PV_MAX_AGE = 10 * 60 * 1000;

  function readSavedElement(doc, selector) {
    const el = doc?.querySelector(selector);
    return childValue(el).trim();
  }

  function readSavedLines(doc, selectors) {
    return selectors
      .map(selector => readSavedElement(doc, selector))
      .filter(Boolean)
      .join('\n')
      .trim();
  }

  function collectPaymentRequestHtml(doc) {
    if (!doc) return null;
    const values = {
      // LOCKED RULE: Department/القسم -> PV Pay to/الدفع لـ
      department: readSavedElement(doc, '[data-save="department"]'),
      // LOCKED RULE: PR Pay to/الدفع لـ -> PV Purpose/الغرض (first line)
      pay_to: readSavedElement(doc, '[data-save="pay_to"]'),
      // Description of purpose continues inside PV Purpose after PR Pay to.
      purpose: readSavedLines(doc, ['[data-save="purpose"]','[data-save="purpose_1"]','[data-save="purpose_2"]']),
      amount: readSavedElement(doc, '[data-save="amount"]'),
      currency: readSavedElement(doc, '[data-save="currency"]'),
      written_amount: readSavedLines(doc, ['[data-save="written_amount"]','[data-save="written_amount_1"]','[data-save="written_amount_2"]']),
      approval: readSavedElement(doc, '[data-save="approval_signature"]'),
      // Name of Requester stays separate. User-approved receiver source is Prepared by only.
      requester_name: readSavedElement(doc, '[data-save="requester"]'),
      prepared_by: readSavedElement(doc, '[data-save="prepared_signature"]')
    };
    if (!Object.values(values).some(Boolean)) return null;
    return { version: VERSION, captured_at: Date.now(), values };
  }

  function savePaymentRequestSnapshot(doc) {
    const payload = collectPaymentRequestHtml(doc);
    if (!payload) return null;
    const raw = JSON.stringify(payload);
    try { sessionStorage.setItem(PR_TO_PV_STORAGE, raw); } catch (_) {}
    try { localStorage.setItem(PR_TO_PV_STORAGE, raw); } catch (_) {}
    return payload;
  }

  function loadPaymentRequestSnapshot() {
    let raw = null;
    try { raw = sessionStorage.getItem(PR_TO_PV_STORAGE); } catch (_) {}
    if (!raw) { try { raw = localStorage.getItem(PR_TO_PV_STORAGE); } catch (_) {} }
    if (!raw) return null;
    try {
      const payload = JSON.parse(raw);
      if (!payload?.values || !payload.captured_at) return null;
      if (Date.now() - Number(payload.captured_at) > PR_TO_PV_MAX_AGE) return null;
      return payload;
    } catch (_) { return null; }
  }

  function composeVoucherPurpose(values) {
    const payTo = String(values?.pay_to || '').trim();
    const description = String(values?.purpose || '').replace(/\r\n?/g,'\n').trim();
    if (payTo && description && payTo !== description) return `${payTo}\n${description}`;
    return payTo || description;
  }

  function setVoucherHtmlField(doc, selector, value) {
    if (!doc || value === undefined || value === null || String(value).trim() === '') return false;
    const el = doc.querySelector(selector);
    if (!el) return false;
    const before = childValue(el);
    setChildValue(el, value);
    try { el.dispatchEvent(new Event('change',{bubbles:true})); } catch (_) {}
    return before !== String(value);
  }

  function applyPaymentRequestToVoucherHtml(frame) {
    if (!frame || frame.dataset.ziadTemplateType !== 'PV') return false;
    const doc = frame.contentDocument;
    const payload = loadPaymentRequestSnapshot();
    if (!doc || !payload?.values) return false;
    const src = payload.values;
    let changed = false;

    // === FINAL LOCKED MAPPING ===
    // PR Department / القسم       -> PV Pay to / الدفع لـ
    changed = setVoucherHtmlField(doc, '#payto', src.department) || changed;

    // PR Pay to / الدفع لـ        -> PV Purpose / الغرض (first line)
    // PR Description of purpose   -> PV Purpose / الغرض (following line(s))
    changed = setVoucherHtmlField(doc, '#purpose', composeVoucherPurpose(src)) || changed;

    // Remaining previously approved mappings.
    changed = setVoucherHtmlField(doc, '#amount', src.amount) || changed;
    changed = setVoucherHtmlField(doc, '#currency', src.currency) || changed;
    changed = setVoucherHtmlField(doc, '#written', src.written_amount) || changed;
    changed = setVoucherHtmlField(doc, '#approval', src.approval) || changed;
    changed = setVoucherHtmlField(doc, '#receiver', src.prepared_by) || changed;

    if (changed) {
      frame.dataset.ziadPrPvMapping = 'final-v3.3.33-applied';
      doc.documentElement.dataset.ziadPrPvMapping = 'final-v3.3.33-applied';
    }
    return changed;
  }

  function bindPaymentRequestCapture(frame) {
    const doc = frame?.contentDocument;
    if (!doc || doc.documentElement.dataset.ziadPrPvCapture === VERSION) return;
    doc.documentElement.dataset.ziadPrPvCapture = VERSION;
    const save = () => savePaymentRequestSnapshot(doc);
    doc.addEventListener('input', save, true);
    doc.addEventListener('change', save, true);
    doc.addEventListener('blur', save, true);
    // Capture after the normal HTML-runtime mirror binding has populated the template.
    setTimeout(save, 0);
    setTimeout(save, 120);
  }

  function scheduleVoucherApply(frame) {
    // Run after the ordinary HTML-template binding so the final user-approved mapping wins.
    [0, 60, 180, 450, 900, 1500, 3000].forEach(delay => setTimeout(() => applyPaymentRequestToVoucherHtml(frame), delay));
  }

  function captureOpenPaymentRequest() {
    const frame = document.querySelector(`iframe.${FRAME_CLASS}[data-ziad-template-type="PR"]`);
    if (frame?.contentDocument) savePaymentRequestSnapshot(frame.contentDocument);
  }

  function lockChild(doc, locked) {
    if (!locked) return;
    doc.querySelectorAll('input,textarea,select,button').forEach(el => { if (!el.closest('.toolbar')) el.disabled = true; });
    doc.querySelectorAll('[contenteditable="true"]').forEach(el => el.setAttribute('contenteditable','false'));
    doc.querySelector('.toolbar')?.remove();
  }

  function bindFrame(page, frame, type) {
    const def = templateDefs[type];
    const doc = frame.contentDocument;
    if (!doc) return;
    doc.documentElement.dataset.ziadTemplateRuntime = VERSION;

    const keys = canonicalKeys(page, def);
    keys.forEach(key => {
      const childEls = findChild(doc, def.map[key]);
      if (!childEls.length) return;
      const value = readMirror(page,key);
      if (childEls.length === 1) setChildValue(childEls[0], value);
      else splitLines(value, childEls.length).forEach((part,i) => setChildValue(childEls[i], part));

      const sync = () => {
        let next;
        if (childEls.length === 1) next = childValue(childEls[0]);
        else next = childEls.map(childValue).join('\n').replace(/\n+$/g,'');
        writeMirror(page,key,next);
      };
      childEls.forEach(el => {
        el.addEventListener('input',sync);
        el.addEventListener('change',sync);
        el.addEventListener('blur',sync);
      });
    });

    const locked = allMirrors(page).length > 0 && allMirrors(page).every(el => el.disabled || el.readOnly);
    lockChild(doc, locked);

    // Payment Request document number is generated by the system and may not be an editable config field.
    if (type === 'PR') {
      const headerNo = document.querySelector('.document-header h1')?.textContent?.trim();
      if (headerNo) setChildValue(doc.querySelector('[data-save="pr_number"]'), headerNo);
    }
    if (type === 'PV') {
      const headerNo = document.querySelector('.document-header h1')?.textContent?.trim();
      if (headerNo && !readMirror(page,'document_number')) setChildValue(doc.querySelector('#rv'), headerNo);
    }

    // v3.3.33: bind the transfer contract to the real HTML template fields.
    if (type === 'PR') bindPaymentRequestCapture(frame);
    if (type === 'PV') scheduleVoucherApply(frame);
  }

  function activate(page) {
    if (!page || page.dataset.ziadHtmlTemplate === VERSION) return;
    const type = detectType(page);
    if (!type || !templateDefs[type]) return;

    page.dataset.ziadHtmlTemplate = VERSION;
    page.dataset.ziadHtmlTemplateType = type;
    page.classList.add(HOST_CLASS);

    const frame = document.createElement('iframe');
    frame.className = FRAME_CLASS;
    frame.title = `Ziad ${type} HTML template`;
    frame.src = `${templateDefs[type].url}?v=${VERSION}`;
    frame.setAttribute('data-ziad-template-type',type);
    frame.addEventListener('load',() => bindFrame(page,frame,type),{once:true});
    page.appendChild(frame);
  }

  function scan() {
    document.querySelectorAll('#template-page.template-page').forEach(activate);
  }

  const observer = new MutationObserver(() => requestAnimationFrame(scan));
  observer.observe(document.documentElement,{childList:true,subtree:true});
  document.addEventListener('DOMContentLoaded',scan);
  window.addEventListener('hashchange',() => setTimeout(scan,0));
  scan();

  // Print the exact user-supplied HTML template. Capture phase prevents the legacy image/PDF route.
  document.addEventListener('click',event => {
    // Always capture the latest Payment Request values before any conversion/navigation action.
    // Capturing on all clicks is harmless and avoids depending on the exact button wording.
    captureOpenPaymentRequest();

    const button = event.target.closest('#print-document');
    if (!button) return;
    const page = document.querySelector('#template-page.ziad-html-template-host');
    const frame = page?.querySelector(`iframe.${FRAME_CLASS}`);
    if (!frame?.contentWindow) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    try {
      frame.contentWindow.focus();
      frame.contentWindow.print();
    } catch (err) {
      console.error('HTML template print failed',err);
    }
  },true);
})();
