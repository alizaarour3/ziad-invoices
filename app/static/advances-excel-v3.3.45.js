'use strict';

(() => {
  if (window.__ziadAdvancesExcel3345) return;
  window.__ziadAdvancesExcel3345 = true;

  const XLSX_MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';

  function triggerDownload(blob, filename) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1500);
  }

  async function downloadApi(path, filename, button) {
    const old = button?.innerHTML;
    if (button) {
      button.disabled = true;
      button.innerHTML = '<span class="loader"></span> جارٍ التجهيز';
    }
    try {
      const response = await api(path);
      const blob = await response.blob();
      triggerDownload(blob, filename);
      toast('تم تجهيز ملف Excel بنجاح', 'success');
    } catch (error) {
      toast(error.message || 'تعذر تصدير ملف Excel', 'error');
    } finally {
      if (button) {
        button.disabled = false;
        button.innerHTML = old;
      }
    }
  }

  function filteredExportPath() {
    const params = new URLSearchParams();
    const q = document.getElementById('advance-search')?.value.trim();
    const status = document.getElementById('advance-status')?.value;
    const month = document.getElementById('advance-month-filter')?.value;
    if (q) params.set('q', q);
    if (status) params.set('status', status);
    if (month) params.set('month', month);
    return `/api/advance-excel/export${params.toString() ? `?${params}` : ''}`;
  }

  function showImportResult(result) {
    const imported = Number(result?.imported || 0);
    const skipped = Number(result?.skipped || 0);
    const errors = Array.isArray(result?.errors) ? result.errors : [];
    toast(`Excel: تمت إضافة ${imported}، تم تخطي ${skipped}${errors.length ? `، أخطاء ${errors.length}` : ''}`, errors.length ? '' : 'success');
    if (!errors.length || typeof showModal !== 'function') return;
    const rows = errors.slice(0, 50).map(item => `<tr><td>${escapeHtml(item.row)}</td><td>${escapeHtml(item.error)}</td></tr>`).join('');
    showModal(
      'نتيجة استيراد Excel',
      `<div class="excel-import-summary"><div><strong>${imported}</strong><span>تمت إضافتها</span></div><div><strong>${skipped}</strong><span>مكررة تم تخطيها</span></div><div class="has-errors"><strong>${errors.length}</strong><span>أخطاء</span></div></div><div class="table-wrap excel-error-table"><table><thead><tr><th>صف Excel</th><th>المشكلة</th></tr></thead><tbody>${rows}</tbody></table></div>${errors.length > 50 ? '<p class="excel-error-note">تم عرض أول 50 خطأ فقط.</p>' : ''}`,
      ['<button class="btn btn-primary" id="excel-import-close">إغلاق</button>'],
      'modal-lg'
    );
    document.getElementById('excel-import-close')?.addEventListener('click', closeModal);
  }

  async function importExcel(file, input, button) {
    if (!file) return;
    if (!/\.xlsx$/i.test(file.name)) {
      toast('اختر ملف Excel بصيغة .xlsx', 'error');
      input.value = '';
      return;
    }
    const old = button?.innerHTML;
    if (button) {
      button.disabled = true;
      button.innerHTML = '<span class="loader"></span> جارٍ الاستيراد';
    }
    try {
      const result = await api('/api/advance-excel/import', {
        method: 'POST',
        headers: {'Content-Type': XLSX_MIME},
        body: file,
      });
      showImportResult(result);
      await window.renderAdvances();
    } catch (error) {
      toast(error.message || 'تعذر استيراد ملف Excel', 'error');
    } finally {
      input.value = '';
      if (button?.isConnected) {
        button.disabled = false;
        button.innerHTML = old;
      }
    }
  }

  function enhanceAdvancesPage() {
    const header = document.querySelector('.advance-page-header');
    if (!header || header.querySelector('[data-advance-excel-actions]')) return;
    const actions = document.createElement('div');
    actions.className = 'page-actions advance-excel-actions';
    actions.dataset.advanceExcelActions = '1';
    actions.innerHTML = `
      <input id="advance-excel-file" class="advance-excel-file" type="file" accept=".xlsx,${XLSX_MIME}">
      <button type="button" class="btn btn-secondary" id="advance-excel-template">${icon('download')}<span>نموذج Excel</span></button>
      <button type="button" class="btn btn-secondary" id="advance-excel-import">${icon('upload')}<span>استيراد Excel</span></button>
      <button type="button" class="btn btn-primary" id="advance-excel-export">${icon('download')}<span>تصدير Excel</span></button>`;
    header.appendChild(actions);

    const fileInput = document.getElementById('advance-excel-file');
    const importButton = document.getElementById('advance-excel-import');
    document.getElementById('advance-excel-export')?.addEventListener('click', event => {
      downloadApi(filteredExportPath(), `advances-${new Date().toISOString().slice(0, 10)}.xlsx`, event.currentTarget);
    });
    document.getElementById('advance-excel-template')?.addEventListener('click', event => {
      downloadApi('/api/advance-excel/template', 'advances-import-template.xlsx', event.currentTarget);
    });
    importButton?.addEventListener('click', () => fileInput?.click());
    fileInput?.addEventListener('change', () => importExcel(fileInput.files?.[0], fileInput, importButton));
  }

  async function enhanceAdvanceReport(id) {
    const paper = document.getElementById('advance-report-paper');
    if (!paper || paper.dataset.premiumAdvanceReport === '1') return;
    paper.dataset.premiumAdvanceReport = '1';
    let advance;
    try {
      advance = await api(`/api/advances/${id}`);
    } catch (_) {
      return;
    }
    const amount = Number(advance.amount || 0);
    const paid = Number(advance.paid_amount || 0);
    const remaining = Number(advance.remaining_amount || 0);
    const percentage = amount > 0 ? Math.min(100, Math.max(0, (paid / amount) * 100)) : 0;
    const paymentCount = Number(advance.payment_count || advance.payments?.length || 0);

    const top = paper.querySelector('.loan-report-top');
    if (top) {
      const ref = document.createElement('div');
      ref.className = 'advance-report-ref';
      ref.innerHTML = `<span>رقم السلفة</span><strong>ADV-${String(advance.id).padStart(5, '0')}</strong>`;
      const status = top.querySelector('.loan-report-status');
      if (status) status.before(ref);
      else top.appendChild(ref);
    }

    const grid = paper.querySelector('.loan-report-grid');
    if (grid) {
      const block = document.createElement('section');
      block.className = 'advance-premium-report-summary';
      block.innerHTML = `
        <div class="advance-report-progress-head"><div><span>نسبة التسديد</span><strong>${percentage.toFixed(1)}%</strong></div><div><span>عدد عمليات التسديد</span><strong>${paymentCount}</strong></div><div><span>آخر تحديث</span><strong>${formatDate(advance.updated_at, true)}</strong></div></div>
        <div class="advance-report-progress" aria-label="نسبة التسديد"><span style="width:${percentage.toFixed(2)}%"></span></div>
        <div class="advance-report-balance-check"><span>مطابقة الحساب</span><strong>${formatMoney(amount)} = ${formatMoney(paid)} + ${formatMoney(remaining)}</strong><em>${Math.abs(amount - paid - remaining) < 0.001 ? 'متطابق' : 'راجع الحساب'}</em></div>`;
      grid.after(block);
    }

    const actions = document.querySelector('.loan-report-screen-header .page-actions');
    if (actions && !document.getElementById('advance-report-excel-btn')) {
      const button = document.createElement('button');
      button.id = 'advance-report-excel-btn';
      button.className = 'btn btn-secondary advance-report-excel-btn';
      button.innerHTML = `${icon('download')} Excel التقرير`;
      button.addEventListener('click', () => downloadApi(`/api/advance-excel/report/${id}`, `advance-${id}.xlsx`, button));
      const printButton = document.getElementById('advance-report-print-btn');
      if (printButton) actions.insertBefore(button, printButton);
      else actions.appendChild(button);
    }
  }

  const originalRenderAdvances = window.renderAdvances;
  if (typeof originalRenderAdvances === 'function') {
    window.renderAdvances = async function (...args) {
      const result = await originalRenderAdvances.apply(this, args);
      enhanceAdvancesPage();
      return result;
    };
  }

  const originalRenderAdvanceReport = window.renderAdvanceReport;
  if (typeof originalRenderAdvanceReport === 'function') {
    window.renderAdvanceReport = async function (id, ...args) {
      const result = await originalRenderAdvanceReport.call(this, id, ...args);
      await enhanceAdvanceReport(id);
      return result;
    };
  }

  function enhanceCurrentAdvanceScreen() {
    if (location.hash === '#/advances') enhanceAdvancesPage();
    const reportMatch = location.hash.match(/^#\/advances\/(\d+)\/report$/);
    if (reportMatch) enhanceAdvanceReport(Number(reportMatch[1]));
  }

  const appRoot = document.getElementById('app');
  if (appRoot) {
    let scheduled = false;
    new MutationObserver(() => {
      if (scheduled) return;
      scheduled = true;
      requestAnimationFrame(() => {
        scheduled = false;
        enhanceCurrentAdvanceScreen();
      });
    }).observe(appRoot, {childList: true, subtree: true});
  }
  window.addEventListener('hashchange', () => setTimeout(enhanceCurrentAdvanceScreen, 0));
  queueMicrotask(enhanceCurrentAdvanceScreen);
})();
