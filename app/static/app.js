'use strict';

const root = document.getElementById('app');
const modalRoot = document.getElementById('modal-root');
const toastRoot = document.getElementById('toast-root');

const state = {
  token: localStorage.getItem('ziad_token') || '',
  user: null,
  types: [],
  counts: {},
  currentDocument: null,
  dirty: false,
  sidebarCollapsed: localStorage.getItem('ziad_sidebar_collapsed') === '1',
  editorViewportFit: null,
  editorViewportFitCleanup: null,
  editorZoom: 1,
  editorZoomAnchor: null,
  editorDocumentId: null,
};

const ICONS = {
  dashboard: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="3" width="7" height="7" rx="2"/><rect x="14" y="3" width="7" height="7" rx="2"/><rect x="3" y="14" width="7" height="7" rx="2"/><rect x="14" y="14" width="7" height="7" rx="2"/></svg>',
  file: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M7 3h7l5 5v13H7z"/><path d="M14 3v6h6"/></svg>',
  plus: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>',
  search: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>',
  edit: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4z"/></svg>',
  eye: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M2.5 12s3.5-6 9.5-6 9.5 6 9.5 6-3.5 6-9.5 6-9.5-6-9.5-6Z"/><circle cx="12" cy="12" r="2.7"/></svg>',
  print: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M6 9V3h12v6M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><path d="M6 14h12v7H6z"/></svg>',
  trash: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 6h18M8 6V4h8v2M19 6l-1 15H6L5 6M10 10v7M14 10v7"/></svg>',
  users: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="9" cy="8" r="4"/><path d="M2 21a7 7 0 0 1 14 0"/><path d="M16 3.5a4 4 0 0 1 0 7.5M17 14a6 6 0 0 1 5 6"/></svg>',
  permissions: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 3 4.5 6v5.5c0 4.5 3.1 7.7 7.5 9.5 4.4-1.8 7.5-5 7.5-9.5V6z"/><path d="m8.5 12 2.2 2.2 4.8-5"/></svg>',
  loan: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="6" width="18" height="13" rx="2"/><path d="M16 10h5M7 6V4h10v2M7 14h5"/></svg>',
  audit: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 4h16v16H4z"/><path d="M8 9h8M8 13h8M8 17h5"/></svg>',
  logout: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M10 17l5-5-5-5M15 12H3M15 4h5v16h-5"/></svg>',
  menu: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 7h16M4 12h16M4 17h16"/></svg>',
  close: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m6 6 12 12M18 6 6 18"/></svg>',
  upload: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 16V4M7 9l5-5 5 5"/><path d="M4 15v5h16v-5"/></svg>',
  download: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 4v12M7 11l5 5 5-5"/><path d="M4 20h16"/></svg>',
  attachment: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="m20.5 11.5-8.2 8.2a6 6 0 0 1-8.5-8.5l9-9a4 4 0 0 1 5.7 5.7l-9.1 9.1a2 2 0 1 1-2.8-2.8l8.4-8.4"/></svg>',
  save: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 4h14l2 2v14H4z"/><path d="M8 4v6h8V4M8 20v-6h8v6"/></svg>',
  chevron: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m9 18 6-6-6-6"/></svg>',
  lock: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="4" y="10" width="16" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3"/></svg>',
  settings: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2.8 2.8-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6v.2h-4V21a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1L4.2 17l.1-.1a1.7 1.7 0 0 0 .3-1.9A1.7 1.7 0 0 0 3 14H2.8v-4H3a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9L4.2 7 7 4.2l.1.1A1.7 1.7 0 0 0 9 4.6a1.7 1.7 0 0 0 1-1.6v-.2h4V3a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1L19.8 7l-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.6 1h.2v4H21a1.7 1.7 0 0 0-1.6 1Z"/></svg>',
  refresh: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M20 6v5h-5M4 18v-5h5"/><path d="M18.5 9A7 7 0 0 0 6 6.5L4 9M5.5 15A7 7 0 0 0 18 17.5l2-2.5"/></svg>',
  more: '<svg class="icon" viewBox="0 0 24 24" fill="currentColor"><circle cx="5" cy="12" r="1.7"/><circle cx="12" cy="12" r="1.7"/><circle cx="19" cy="12" r="1.7"/></svg>',
  chart: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/></svg>',
  draft: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M5 3h10l4 4v14H5z"/><path d="M14 3v5h5M8 13h8M8 17h5"/></svg>',
  check: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m5 12 4 4L19 6"/></svg>',
  transfer: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M7 7h13M17 4l3 3-3 3"/><path d="M17 17H4M7 14l-3 3 3 3"/></svg>',
  wallet: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M3 7.5A2.5 2.5 0 0 1 5.5 5H19a2 2 0 0 1 2 2v12H5a2 2 0 0 1-2-2z"/><path d="M3 8h16M16 12h5v4h-5a2 2 0 0 1 0-4Z"/></svg>',
  clock: '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>',
};

function icon(name) { return ICONS[name] || ''; }
function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>'"]/g, (char) => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[char]));
}
function formatDate(value, includeTime = false) {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return escapeHtml(value);
  return new Intl.DateTimeFormat('ar-IQ', includeTime ? {dateStyle:'medium', timeStyle:'short'} : {dateStyle:'medium'}).format(date);
}
function formatBytes(bytes) {
  const number = Number(bytes || 0);
  if (number < 1024) return `${number} B`;
  if (number < 1024 ** 2) return `${(number / 1024).toFixed(1)} KB`;
  return `${(number / (1024 ** 2)).toFixed(1)} MB`;
}
function formatMoney(value) {
  const number = Number(value || 0);
  if (!Number.isFinite(number)) return '0';
  return new Intl.NumberFormat('ar-IQ', {minimumFractionDigits:Number.isInteger(number)?0:2, maximumFractionDigits:2}).format(number);
}
function parseAmountNumber(value) {
  const arabic = '٠١٢٣٤٥٦٧٨٩';
  const persian = '۰۱۲۳۴۵۶۷۸۹';
  const normalized = String(value ?? '')
    .replace(/[٠-٩]/g, digit => arabic.indexOf(digit))
    .replace(/[۰-۹]/g, digit => persian.indexOf(digit))
    .replace(/[٬,\s]/g, '')
    .replace(/٫/g, '.')
    .replace(/[^0-9.\-]/g, '');
  const number = Number(normalized);
  return Number.isFinite(number) ? number : 0;
}
function displayDocumentAmount(value) {
  const raw = String(value ?? '').trim();
  if (!raw) return '-';
  const number = parseAmountNumber(raw);
  return number ? formatMoney(number) : escapeHtml(raw);
}
function dashboardGreeting() {
  const hour = new Date().getHours();
  if (hour < 12) return 'صباح الخير';
  if (hour < 18) return 'مساء الخير';
  return 'مساء الخير';
}
function dashboardDateLabel() {
  return new Intl.DateTimeFormat('ar-IQ', {weekday:'long', year:'numeric', month:'long', day:'numeric'}).format(new Date());
}
function roleLabel(role) { return ({admin:'مدير النظام', editor:'محرر', viewer:'مشاهد'})[role] || role; }
function canViewPage(pageKey) { return state.user?.role === 'admin' || Boolean(state.user?.page_permissions?.includes(pageKey)); }
function firstAllowedRoute() {
  if (canViewPage('dashboard')) return '/dashboard';
  const firstType = state.types[0];
  if (firstType) return `/documents/${firstType.code}`;
  if (canViewPage('loans')) return '/loans';
  return '/no-access';
}
function statusBadge(status) { return `<span class="badge badge-${status}">${status === 'draft' ? 'مسودة' : 'محفوظ'}</span>`; }
function initials(name) { return String(name || 'U').trim().split(/\s+/).slice(0,2).map(x => x[0]).join('').toUpperCase(); }

function toast(message, type = '') {
  const node = document.createElement('div');
  node.className = `toast ${type}`;
  node.textContent = message;
  toastRoot.appendChild(node);
  setTimeout(() => node.remove(), 4200);
}

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (state.token) headers.set('Authorization', `Bearer ${state.token}`);
  let body = options.body;
  if (body && !(body instanceof Blob) && !(body instanceof ArrayBuffer) && typeof body !== 'string') {
    headers.set('Content-Type', 'application/json');
    body = JSON.stringify(body);
  }
  const response = await fetch(path, {...options, headers, body});
  if (response.status === 401 && !path.includes('/auth/login')) {
    state.token = '';
    state.user = null;
    state.types = [];
    state.counts = {};
    localStorage.removeItem('ziad_token');
    renderLogin();
    throw new Error('انتهت الجلسة. سجّل الدخول من جديد.');
  }
  if (!response.ok) {
    let detail = `حدث خطأ (${response.status})`;
    try {
      const data = await response.json();
      detail = data.detail || detail;
    } catch (_) {}
    throw new Error(detail);
  }
  const contentType = response.headers.get('content-type') || '';
  if (contentType.includes('application/json')) return response.json();
  return response;
}

function navigate(path) {
  if (location.hash === `#${path}`) route();
  else location.hash = path;
}

function activePath(prefix) { return location.hash.startsWith(`#${prefix}`) ? 'active' : ''; }

function authLayout(title, description, formHtml) {
  root.innerHTML = `
    <main class="auth-shell">
      <section class="auth-panel">
        <div class="brand">
          <div class="brand-mark">ZD</div>
          <div class="brand-text"><strong>نظام المستندات والفواتير</strong><span>إدارة احترافية وآمنة</span></div>
        </div>
        <h2>${escapeHtml(title)}</h2>
        <p>${escapeHtml(description)}</p>
        ${formHtml}
      </section>
      <section class="auth-visual">
        <div class="auth-copy">
          <h1>النماذج الأصلية، داخل نظام احترافي.</h1>
          <p>اكتب مباشرة على مستندات القبض والصرف والدفع وكشوف الصيانة وطلبات التحويل، وأدر القروض والتسديدات من صفحة مستقلة مع الصلاحيات.</p>
        </div>
      </section>
    </main>`;
}

async function renderSetup() {
  authLayout('إعداد النظام لأول مرة', 'أنشئ حساب مدير النظام. لا توجد كلمة مرور افتراضية حفاظاً على الأمان.', `
    <form id="setup-form" class="form-grid">
      <div class="form-row"><label>الاسم الكامل</label><input class="control" name="full_name" required minlength="2" autocomplete="name"></div>
      <div class="form-row"><label>اسم المستخدم</label><input class="control" name="username" required minlength="3" pattern="[A-Za-z0-9_.-]+" autocomplete="username"><span class="help">حروف إنجليزية وأرقام فقط.</span></div>
      <div class="form-row"><label>كلمة المرور</label><input class="control" type="password" name="password" required minlength="10" autocomplete="new-password"><span class="help">10 أحرف على الأقل.</span></div>
      <div class="form-row"><label>تأكيد كلمة المرور</label><input class="control" type="password" name="confirm_password" required minlength="10" autocomplete="new-password"></div>
      <div id="setup-error" class="error-text"></div>
      <button class="btn btn-primary btn-lg" type="submit">إنشاء المدير وبدء النظام</button>
    </form>`);
  document.getElementById('setup-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const error = document.getElementById('setup-error');
    error.textContent = '';
    if (form.get('password') !== form.get('confirm_password')) {
      error.textContent = 'كلمتا المرور غير متطابقتين.';
      return;
    }
    const button = event.currentTarget.querySelector('button');
    button.disabled = true; button.innerHTML = '<span class="loader"></span> جارٍ الإعداد';
    try {
      await api('/api/setup/admin', {method:'POST', body:{full_name:form.get('full_name'), username:form.get('username'), password:form.get('password')}});
      toast('تم إعداد النظام بنجاح', 'success');
      renderLogin();
    } catch (err) {
      error.textContent = err.message;
      button.disabled = false; button.textContent = 'إنشاء المدير وبدء النظام';
    }
  });
}

function renderLogin() {
  authLayout('تسجيل الدخول', 'أدخل بيانات حسابك للوصول إلى المستندات.', `
    <form id="login-form" class="form-grid">
      <div class="form-row"><label>اسم المستخدم</label><input class="control" name="username" required autocomplete="username" autofocus></div>
      <div class="form-row"><label>كلمة المرور</label><input class="control" type="password" name="password" required autocomplete="current-password"></div>
      <div id="login-error" class="error-text"></div>
      <button class="btn btn-primary btn-lg" type="submit">تسجيل الدخول</button>
    </form>`);
  document.getElementById('login-form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const button = event.currentTarget.querySelector('button');
    const error = document.getElementById('login-error');
    error.textContent = '';
    button.disabled = true; button.innerHTML = '<span class="loader"></span> جارٍ الدخول';
    try {
      const data = await api('/api/auth/login', {method:'POST', body:{username:form.get('username'), password:form.get('password')}});
      state.token = data.token;
      state.user = data.user;
      state.types = [];
      state.counts = {};
      localStorage.setItem('ziad_token', data.token);
      await ensureTypes();
      navigate(firstAllowedRoute());
    } catch (err) {
      error.textContent = err.message;
      button.disabled = false; button.textContent = 'تسجيل الدخول';
    }
  });
}

function documentActionButtons(doc, {includePrint = true} = {}) {
  const edit = state.user.role !== 'viewer' ? `<button type="button" class="btn btn-secondary row-action" data-doc-action="edit" data-id="${doc.id}" data-code="${doc.type.code}" title="تعديل المستند">${icon('edit')}<span>تعديل</span></button>` : '';
  const remove = state.user.role === 'admin' ? `<button type="button" class="btn btn-danger-soft row-action" data-doc-action="delete" data-id="${doc.id}" data-code="${doc.type.code}" title="حذف المستند نهائياً">${icon('trash')}<span>حذف</span></button>` : '';
  return `<div class="row-actions" role="group" aria-label="إجراءات المستند ${escapeHtml(doc.document_number || '')}">
    <button type="button" class="btn btn-secondary row-action" data-doc-action="view" data-id="${doc.id}" data-code="${doc.type.code}" title="مشاهدة المستند">${icon('eye')}<span>مشاهدة</span></button>
    ${edit}
    ${includePrint ? `<button type="button" class="btn btn-secondary row-action" data-doc-action="print" data-id="${doc.id}" data-code="${doc.type.code}" title="طباعة المستند">${icon('print')}<span>طباعة</span></button>` : ''}
    ${remove}
  </div>`;
}

function wireDocumentActions(scope = root) {
  scope.querySelectorAll('[data-doc-action]').forEach(button => button.addEventListener('click', async () => {
    const id = Number(button.dataset.id);
    const code = button.dataset.code || state.currentDocument?.type?.code || 'RV';
    if (button.dataset.docAction === 'view') return navigate(`/documents/${id}/view`);
    if (button.dataset.docAction === 'edit') return navigate(`/documents/${id}/edit`);
    if (button.dataset.docAction === 'delete') return confirmDeleteDocument(id, code);
    if (button.dataset.docAction === 'print') {
      try { const doc = await api(`/api/documents/${id}`); openPrintModal(doc); }
      catch (err) { toast(err.message, 'error'); }
    }
  }));
}

function shell(title, content, {active = '', fullWidth = false} = {}) {
  if (state.editorViewportFitCleanup) {
    state.editorViewportFitCleanup();
    state.editorViewportFitCleanup = null;
    state.editorViewportFit = null;
  }
  const user = state.user || {};
  const adminLinks = user.role === 'admin' ? `
    <div class="nav-label">الإدارة</div>
    <a class="nav-item ${activePath('/users')}" href="#/users" title="المستخدمون">${icon('users')}<span>المستخدمون</span></a>
    <a class="nav-item ${activePath('/permissions')}" href="#/permissions" title="صلاحيات الصفحات">${icon('permissions')}<span>صلاحيات</span></a>
    <a class="nav-item ${activePath('/reports')}" href="#/reports" title="التقارير والتصدير">${icon('download')}<span>التقارير والتصدير</span></a>
    <a class="nav-item ${activePath('/audit')}" href="#/audit" title="سجل العمليات">${icon('audit')}<span>سجل العمليات</span></a>
    <a class="nav-item ${activePath('/settings')}" href="#/settings" title="الإعدادات والنسخ">${icon('settings')}<span>الإعدادات والنسخ</span></a>` : '';
  const typeLinks = state.types.map(type => `
    <a class="nav-item ${active === type.code ? 'active' : ''}" href="#/documents/${type.code}" title="${escapeHtml(type.name_ar)}">${icon('file')}<span>${escapeHtml(type.name_ar)}</span><span class="nav-badge">${state.counts[type.code] ?? ''}</span></a>
  `).join('');
  const financeLinks = canViewPage('loans') ? `
    <div class="nav-label">المالية</div>
    <a class="nav-item ${activePath('/loans')}" href="#/loans" title="قروض">${icon('loan')}<span>قروض</span></a>` : '';
  root.innerHTML = `
    <div class="app-shell ${state.sidebarCollapsed ? 'sidebar-collapsed' : ''}" id="app-shell">
      <div class="sidebar-backdrop" id="sidebar-backdrop"></div>
      <aside class="sidebar" id="sidebar">
        <div class="sidebar-head">
          <div class="brand"><div class="brand-mark">ZD</div><div class="brand-text"><strong>نظام المستندات</strong><span>الإصدار 3.3.15</span></div></div>
          <button id="sidebar-close" class="btn btn-icon btn-link sidebar-close" aria-label="إغلاق القائمة">${icon('close')}</button>
        </div>
        <nav class="sidebar-nav">
          ${canViewPage('dashboard') ? `<a class="nav-item ${activePath('/dashboard')}" href="#/dashboard" title="الداشبورد">${icon('dashboard')}<span>الداشبورد</span></a>` : ''}
          <div class="nav-label">النماذج</div>
          ${typeLinks}${financeLinks}${adminLinks}
        </nav>
        <div class="sidebar-footer">
          <div class="user-chip"><div class="avatar">${escapeHtml(initials(user.full_name))}</div><div class="user-chip-copy"><strong>${escapeHtml(user.full_name || '')}</strong><span>${escapeHtml(roleLabel(user.role))}</span></div><button id="logout-btn" class="btn btn-icon btn-link" title="تسجيل الخروج">${icon('logout')}</button></div>
        </div>
      </aside>
      <main class="main">
        <header class="topbar"><button id="sidebar-toggle" class="btn btn-icon btn-secondary" title="إظهار أو إخفاء القائمة">${icon('menu')}</button><div class="topbar-title">${escapeHtml(title)}</div><div class="topbar-spacer"></div><div class="topbar-user"><div class="avatar small">${escapeHtml(initials(user.full_name))}</div><span>${escapeHtml(user.full_name || '')}</span></div></header>
        <section class="content" style="${fullWidth ? 'max-width:none' : ''}">${content}</section>
      </main>
    </div>`;
  const appShell = document.getElementById('app-shell');
  const mobileQuery = window.matchMedia('(max-width: 900px)');
  const closeMobileSidebar = () => appShell.classList.remove('sidebar-open');
  document.getElementById('logout-btn').addEventListener('click', doLogout);
  document.getElementById('sidebar-toggle').addEventListener('click', () => {
    if (mobileQuery.matches) return appShell.classList.toggle('sidebar-open');
    state.sidebarCollapsed = !state.sidebarCollapsed;
    localStorage.setItem('ziad_sidebar_collapsed', state.sidebarCollapsed ? '1' : '0');
    appShell.classList.toggle('sidebar-collapsed', state.sidebarCollapsed);
    requestAnimationFrame(() => state.editorViewportFit?.());
    setTimeout(() => state.editorViewportFit?.(), 230);
  });
  document.getElementById('sidebar-close').addEventListener('click', closeMobileSidebar);
  document.getElementById('sidebar-backdrop').addEventListener('click', closeMobileSidebar);
  appShell.querySelectorAll('.sidebar a').forEach(link => link.addEventListener('click', () => { if (mobileQuery.matches) closeMobileSidebar(); }));
}

async function doLogout() {
  try { await api('/api/auth/logout', {method:'POST'}); } catch (_) {}
  state.token = ''; state.user = null; state.types = []; state.counts = {}; localStorage.removeItem('ziad_token');
  renderLogin();
}

function openCreateMenu() {
  const choices = state.types.map(t => `<button class="btn btn-secondary btn-lg" data-code="${t.code}">${icon('file')} ${escapeHtml(t.name_ar)}</button>`).join('');
  showModal('إنشاء مستند جديد', `<div class="form-grid">${choices}</div>`, []);
  modalRoot.querySelectorAll('[data-code]').forEach(button => button.addEventListener('click', () => {
    closeModal(); navigate(`/documents/new/${button.dataset.code}`);
  }));
}

function showModal(title, body, footerButtons = [], size = '') {
  modalRoot.innerHTML = `
    <div class="modal-backdrop" id="modal-backdrop">
      <section class="modal ${size}">
        <header class="modal-head"><h3>${escapeHtml(title)}</h3><button class="btn btn-icon btn-secondary" id="modal-close">${icon('close')}</button></header>
        <div class="modal-body">${body}</div>
        ${footerButtons.length ? `<footer class="modal-foot">${footerButtons.join('')}</footer>` : ''}
      </section>
    </div>`;
  document.getElementById('modal-close').addEventListener('click', closeModal);
  document.getElementById('modal-backdrop').addEventListener('click', (event) => { if (event.target.id === 'modal-backdrop') closeModal(); });
}
function closeModal() { modalRoot.innerHTML = ''; }

function pageLoading(title = 'جارٍ التحميل') {
  shell(title, `<div class="panel"><div class="empty"><span class="loader"></span><p>جارٍ تحميل البيانات...</p></div></div>`);
}

async function ensureTypes() {
  if (!state.types.length) state.types = await api('/api/document-types');
}

async function renderDashboard() {
  pageLoading('الداشبورد');
  const data = await api('/api/dashboard');
  const loans = canViewPage('loans') ? await api('/api/loans') : [];
  state.counts = Object.fromEntries(data.types.map(t => [t.code, t.count]));

  const weekly = data.weekly_activity || [];
  const maxActivity = Math.max(1, ...weekly.map(item => item.count));
  const activityBars = weekly.map(item => `<div class="activity-column" title="${escapeHtml(item.date)}: ${item.count}"><div class="activity-value">${item.count}</div><div class="activity-track"><span style="height:${Math.max(5, Math.round(item.count / maxActivity * 100))}%"></span></div><small>${escapeHtml(item.label)}</small></div>`).join('');

  const typeCards = data.types.map(type => {
    const saved = Number(type.saved_count || 0);
    const draft = Number(type.draft_count || 0);
    const count = Number(type.count || 0);
    const savedPercent = count ? Math.round(saved / count * 100) : 0;
    const typeIcon = type.code === 'TR' ? icon('transfer') : icon('file');
    return `<a class="type-overview-card premium" href="#/documents/${type.code}">
      <div class="type-overview-icon ${type.code === 'TR' ? 'transfer' : ''}">${typeIcon}</div>
      <div class="type-overview-copy"><strong>${escapeHtml(type.name_ar)}</strong><span>${saved} محفوظ · ${draft} مسودة</span><div class="type-overview-progress"><span style="width:${savedPercent}%"></span></div></div>
      <div class="type-overview-count"><strong>${count}</strong><small>${savedPercent}% مكتمل</small></div>${icon('chevron')}
    </a>`;
  }).join('');

  const recentRows = data.recent.length ? data.recent.map(doc => `<tr><td class="mono"><strong>${escapeHtml(doc.document_number)}</strong></td><td><span class="dashboard-type-cell">${doc.type.code === 'TR' ? icon('transfer') : icon('file')} ${escapeHtml(doc.type.name_ar)}</span></td><td>${escapeHtml(doc.fields[doc.type.config.list_primary_field] || '-')}</td><td>${statusBadge(doc.status)}</td><td>${formatDate(doc.updated_at, true)}</td><td>${documentActionButtons(doc)}</td></tr>`).join('') : `<tr><td colspan="6"><div class="empty">لا توجد مستندات حتى الآن.</div></td></tr>`;

  const activeLoans = loans.filter(item => item.status === 'active');
  const paidLoans = loans.filter(item => item.status === 'paid');
  const remainingLoans = activeLoans.reduce((sum, item) => sum + Number(item.remaining_amount || 0), 0);
  const totalLoanPayments = loans.reduce((sum, item) => sum + Number(item.payment_count || 0), 0);
  const loanSnapshot = canViewPage('loans') ? `<section class="dashboard-finance-panel">
    <div class="dashboard-finance-copy"><span class="eyebrow">المالية</span><h2>ملخص القروض</h2><p>أرقام مباشرة من صفحة القروض والتسديدات.</p></div>
    <div class="dashboard-finance-metrics"><div><span>قروض قائمة</span><strong>${activeLoans.length}</strong></div><div><span>المتبقي</span><strong>${formatMoney(remainingLoans)}</strong></div><div><span>مسددة بالكامل</span><strong>${paidLoans.length}</strong></div><div><span>عمليات تسديد</span><strong>${totalLoanPayments}</strong></div></div>
    <a class="btn btn-secondary" href="#/loans">فتح القروض ${icon('chevron')}</a>
  </section>` : '';

  const draftTypes = data.types.filter(type => Number(type.draft_count || 0) > 0);
  const draftAttention = draftTypes.length ? `<section class="dashboard-section"><div class="section-heading"><div><h2>تحتاج متابعة</h2><p>الأقسام التي تحتوي على مسودات غير مكتملة.</p></div></div><div class="dashboard-attention-grid">${draftTypes.map(type => `<a href="#/documents/${type.code}" class="attention-card"><div class="attention-icon">${icon('draft')}</div><div><strong>${escapeHtml(type.name_ar)}</strong><span>${type.draft_count} مسودة بانتظار الاستكمال</span></div>${icon('chevron')}</a>`).join('')}</div></section>` : '';

  const transferType = data.types.find(type => type.code === 'TR');
  const transferMetric = transferType ? `<article class="dashboard-kpi transfer-kpi"><div class="dashboard-kpi-top"><span>طلبات التحويل</span><div class="dashboard-kpi-icon">${icon('transfer')}</div></div><strong>${transferType.count || 0}</strong><small>${transferType.saved_count || 0} محفوظ · ${transferType.draft_count || 0} مسودة</small></article>` : '';
  const createAction = state.user.role !== 'viewer' && state.types.length ? `<button id="dashboard-create" class="btn btn-primary btn-lg">${icon('plus')} إنشاء مستند</button>` : '';

  shell('الداشبورد', `
    <section class="dashboard-hero">
      <div class="dashboard-hero-copy"><span class="dashboard-kicker">لوحة التشغيل</span><h1>${dashboardGreeting()}، ${escapeHtml(state.user.full_name)}</h1><p>كل المستندات، التحويلات، المسودات والنشاط اليومي في مكان واحد.</p><div class="dashboard-hero-meta"><span>${icon('clock')} ${escapeHtml(dashboardDateLabel())}</span><span class="badge badge-${escapeHtml(state.user.role)}">${escapeHtml(roleLabel(state.user.role))}</span></div></div>
      <div class="dashboard-hero-side"><div class="dashboard-today-card"><span>مستندات اليوم</span><strong>${data.today_documents}</strong><small>من أصل ${data.total_documents} مستند</small></div>${createAction}</div>
    </section>

    <div class="dashboard-kpi-grid">
      <article class="dashboard-kpi"><div class="dashboard-kpi-top"><span>جميع المستندات</span><div class="dashboard-kpi-icon">${icon('dashboard')}</div></div><strong>${data.total_documents}</strong><small>${data.today_documents} أُنشئت اليوم</small></article>
      <article class="dashboard-kpi success"><div class="dashboard-kpi-top"><span>المحفوظة</span><div class="dashboard-kpi-icon">${icon('save')}</div></div><strong>${data.saved_documents || 0}</strong><small>جاهزة للمشاهدة والطباعة</small></article>
      <article class="dashboard-kpi warning"><div class="dashboard-kpi-top"><span>المسودات</span><div class="dashboard-kpi-icon">${icon('draft')}</div></div><strong>${data.draft_documents || 0}</strong><small>تحتاج إلى استكمال</small></article>
      ${transferMetric || `<article class="dashboard-kpi"><div class="dashboard-kpi-top"><span>المرفقات</span><div class="dashboard-kpi-icon">${icon('attachment')}</div></div><strong>${data.total_attachments}</strong><small>${data.printed_total || 0} عملية طباعة</small></article>`}
    </div>

    ${loanSnapshot}

    <section class="dashboard-section"><div class="section-heading"><div><h2>الأقسام</h2><p>حالة كل نموذج ونسبة المستندات المحفوظة داخله.</p></div><span class="section-count">${data.types.length} أقسام</span></div><div class="type-overview-grid">${typeCards}</div></section>

    <div class="dashboard-grid dashboard-grid-premium">
      <div class="panel recent-documents-panel"><div class="panel-head"><div><h2>آخر المستندات</h2><p>آخر التعديلات في جميع الأقسام المسموح لك بها.</p></div><span class="panel-head-icon">${icon('clock')}</span></div><div class="table-wrap"><table><thead><tr><th>الرقم</th><th>النموذج</th><th>الاسم/الجهة</th><th>الحالة</th><th>آخر تعديل</th><th>الإجراءات</th></tr></thead><tbody>${recentRows}</tbody></table></div></div>
      <div class="panel activity-panel premium"><div class="panel-head"><div><h2>نشاط آخر 7 أيام</h2><p>عدد المستندات الجديدة يومياً.</p></div><div class="stat-icon">${icon('chart')}</div></div><div class="panel-body"><div class="activity-chart">${activityBars}</div><div class="activity-summary"><span>اليوم</span><strong>${data.today_documents}</strong><span>إجمالي الطباعة</span><strong>${data.printed_total || 0}</strong><span>المرفقات</span><strong>${data.total_attachments || 0}</strong></div></div></div>
    </div>
    ${draftAttention}`);
  document.getElementById('dashboard-create')?.addEventListener('click', openCreateMenu);
  wireDocumentActions(root);
}

function renderTransferList(type, documents) {
  const savedCount = documents.filter(item => item.status === 'saved').length;
  const draftCount = documents.length - savedCount;
  const numericAmounts = documents.map(item => parseAmountNumber(item.fields.amount)).filter(value => value > 0);
  const amountTotal = numericAmounts.reduce((sum, value) => sum + value, 0);
  const departments = [...new Set(documents.map(item => String(item.fields.department || '').trim()).filter(Boolean))].sort((a,b) => a.localeCompare(b, 'ar'));

  const renderRows = items => {
    const body = document.getElementById('document-rows');
    if (!body) return;
    body.innerHTML = items.length ? items.map(doc => {
      const currency = String(doc.fields.currency || '').trim();
      const entity = String(doc.fields.transfer_entity || '').trim();
      return `<tr class="transfer-row-item"><td class="mono"><strong>${escapeHtml(doc.document_number)}</strong><span class="table-subtext">${formatDate(doc.created_at)}</span></td><td>${escapeHtml(doc.fields.date || '-')}</td><td><div class="transfer-table-primary"><strong>${escapeHtml(doc.fields.pay_to || '-')}</strong><span>${escapeHtml(doc.fields.purpose || '').split('\n')[0] || 'بدون وصف'}</span></div></td><td>${entity ? `<span class="transfer-entity-pill">${icon('transfer')} ${escapeHtml(entity)}</span>` : '<span class="muted-dash">-</span>'}</td><td>${escapeHtml(doc.fields.department || '-')}</td><td><div class="transfer-money"><strong>${displayDocumentAmount(doc.fields.amount)}</strong>${currency ? `<span>${escapeHtml(currency)}</span>` : ''}</div></td><td>${statusBadge(doc.status)}</td><td>${escapeHtml(doc.created_by_name)}</td><td>${documentActionButtons(doc)}</td></tr>`;
    }).join('') : `<tr><td colspan="9"><div class="empty transfer-empty"><div class="stat-icon">${icon('transfer')}</div><strong>لا توجد طلبات تحويل</strong><p>غيّر البحث أو الفلتر، أو أنشئ طلب تحويل جديد.</p></div></td></tr>`;
    wireDocumentActions(body);
  };

  const createAction = state.user.role !== 'viewer' ? `<button class="btn btn-primary btn-lg" id="new-doc">${icon('plus')} طلب تحويل جديد</button>` : '';
  const departmentOptions = departments.map(value => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`).join('');
  shell(type.name_ar, `
    <section class="transfer-page-hero">
      <div class="transfer-page-title"><div class="transfer-page-seal">${icon('transfer')}</div><div><span class="eyebrow">إدارة التحويلات</span><h1>تحويل</h1><p>إنشاء ومتابعة طلبات التحويل مع عرض الجهة والمبلغ والحالة بشكل واضح.</p></div></div>
      <div class="transfer-page-actions">${createAction}</div>
    </section>

    <div class="transfer-summary-grid">
      <article class="transfer-summary-card"><span>كل الطلبات</span><strong>${documents.length}</strong><small>طلب تحويل</small></article>
      <article class="transfer-summary-card success"><span>محفوظ</span><strong>${savedCount}</strong><small>جاهز للطباعة</small></article>
      <article class="transfer-summary-card warning"><span>مسودة</span><strong>${draftCount}</strong><small>بانتظار الاستكمال</small></article>
      <article class="transfer-summary-card amount"><span>إجمالي المبالغ الرقمية</span><strong>${formatMoney(amountTotal)}</strong><small>${numericAmounts.length} طلب يحتوي مبلغاً رقمياً</small></article>
    </div>

    <section class="panel transfer-list-panel">
      <div class="transfer-toolbar"><div><h2>طلبات التحويل</h2><p>ابحث بالرقم، الاسم، الجهة أو القسم.</p></div><div class="transfer-filters"><div class="search-box">${icon('search')}<input id="document-search" class="control" placeholder="بحث في طلبات التحويل..."></div><select id="document-status-filter" class="control compact"><option value="">كل الحالات</option><option value="saved">محفوظ</option><option value="draft">مسودة</option></select>${departments.length ? `<select id="transfer-department-filter" class="control compact"><option value="">كل الأقسام</option>${departmentOptions}</select>` : ''}<button id="refresh-list" class="btn btn-secondary btn-icon" title="تحديث">${icon('refresh')}</button></div></div>
      <div class="table-wrap transfer-table-wrap"><table class="transfer-table"><thead><tr><th>رقم الطلب</th><th>التاريخ</th><th>الدفع إلى / الغرض</th><th>جهة التحويل</th><th>القسم</th><th>المبلغ</th><th>الحالة</th><th>المنشئ</th><th>الإجراءات</th></tr></thead><tbody id="document-rows"></tbody></table></div>
    </section>`, {active:type.code});

  const applyFilters = () => {
    const term = document.getElementById('document-search').value.trim().toLowerCase();
    const status = document.getElementById('document-status-filter').value;
    const department = document.getElementById('transfer-department-filter')?.value || '';
    renderRows(documents.filter(doc => {
      const haystack = `${doc.document_number} ${doc.fields.pay_to || ''} ${doc.fields.transfer_entity || ''} ${doc.fields.department || ''} ${doc.fields.purpose || ''} ${doc.fields.amount || ''} ${doc.created_by_name || ''}`.toLowerCase();
      return (!term || haystack.includes(term)) && (!status || doc.status === status) && (!department || doc.fields.department === department);
    }));
  };
  document.getElementById('new-doc')?.addEventListener('click', () => navigate(`/documents/new/${type.code}`));
  document.getElementById('refresh-list').addEventListener('click', () => renderDocumentList(type.code));
  document.getElementById('document-search').addEventListener('input', applyFilters);
  document.getElementById('document-status-filter').addEventListener('change', applyFilters);
  document.getElementById('transfer-department-filter')?.addEventListener('change', applyFilters);
  renderRows(documents);
}

async function renderDocumentList(code) {
  const type = state.types.find(item => item.code === code);
  if (!type) return navigate(firstAllowedRoute());
  pageLoading(type.name_ar);
  const documents = await api(`/api/documents?type_code=${encodeURIComponent(code)}&limit=500`);
  state.counts[code] = documents.length;
  if (code === 'TR') return renderTransferList(type, documents);
  const savedCount = documents.filter(item => item.status === 'saved').length;
  const draftCount = documents.length - savedCount;
  const renderRows = items => {
    const body = document.getElementById('document-rows');
    if (!body) return;
    body.innerHTML = items.length ? items.map(doc => {
      const primary = doc.fields[type.config.list_primary_field] || '-';
      const amount = doc.fields[type.config.amount_field] || '-';
      return `<tr><td class="mono"><strong>${escapeHtml(doc.document_number)}</strong></td><td>${escapeHtml(doc.fields[type.config.list_date_field || 'date'] || '-')}</td><td>${escapeHtml(primary)}</td><td>${escapeHtml(amount)}</td><td><span class="attachment-count">${icon('attachment')} ${doc.attachment_count}</span></td><td>${statusBadge(doc.status)}</td><td>${escapeHtml(doc.created_by_name)}</td><td>${formatDate(doc.updated_at, true)}</td><td>${documentActionButtons(doc)}</td></tr>`;
    }).join('') : `<tr><td colspan="9"><div class="empty"><div class="stat-icon">${icon('search')}</div><strong>لا توجد نتائج</strong><p>غيّر كلمات البحث أو حالة المستند.</p></div></td></tr>`;
    wireDocumentActions(body);
  };
  const createAction = state.user.role !== 'viewer' ? `<button class="btn btn-primary" id="new-doc">${icon('plus')} إنشاء ${escapeHtml(type.name_ar)}</button>` : '';
  shell(type.name_ar, `
    <div class="page-header"><div><span class="eyebrow">قسم المستندات</span><h1>${escapeHtml(type.name_ar)}</h1><p>مشاهدة وتعديل وطباعة وإدارة مرفقات جميع المستندات في هذا القسم.</p></div><div class="page-actions">${createAction}</div></div>
    <div class="list-summary"><div class="summary-pill"><strong>${documents.length}</strong><span>الإجمالي</span></div><div class="summary-pill"><strong>${savedCount}</strong><span>محفوظ</span></div><div class="summary-pill"><strong>${draftCount}</strong><span>مسودة</span></div></div>
    <div class="panel"><div class="panel-head document-toolbar"><div class="search-box">${icon('search')}<input id="document-search" class="control" placeholder="بحث بالرقم أو الاسم أو المبلغ..."></div><select id="document-status-filter" class="control compact"><option value="">كل الحالات</option><option value="saved">محفوظ</option><option value="draft">مسودة</option></select><button id="refresh-list" class="btn btn-secondary btn-icon" title="تحديث">${icon('refresh')}</button></div><div class="table-wrap"><table><thead><tr><th>رقم المستند</th><th>التاريخ</th><th>الاسم/الجهة</th><th>المبلغ</th><th>المرفقات</th><th>الحالة</th><th>المنشئ</th><th>آخر تعديل</th><th>الإجراءات</th></tr></thead><tbody id="document-rows"></tbody></table></div></div>`, {active:code});
  const applyFilters = () => {
    const term = document.getElementById('document-search').value.trim().toLowerCase();
    const status = document.getElementById('document-status-filter').value;
    renderRows(documents.filter(doc => (!term || `${doc.document_number} ${JSON.stringify(doc.fields)} ${doc.created_by_name}`.toLowerCase().includes(term)) && (!status || doc.status === status)));
  };
  document.getElementById('new-doc')?.addEventListener('click', () => navigate(`/documents/new/${code}`));
  document.getElementById('refresh-list').addEventListener('click', () => renderDocumentList(code));
  document.getElementById('document-search').addEventListener('input', applyFilters);
  document.getElementById('document-status-filter').addEventListener('change', applyFilters);
  renderRows(documents);
}

async function createNewDocument(code) {
  shell('إنشاء مستند', `<div class="panel"><div class="empty"><span class="loader"></span><p>جارٍ حجز رقم تلقائي وفتح النموذج...</p></div></div>`, {active:code});
  try {
    const type = state.types.find(item => item.code === code);
    const dateField = type?.config?.list_date_field || 'date';
    const initialFields = {[dateField]: new Date().toISOString().slice(0,10)};
    const doc = await api('/api/documents', {method:'POST', body:{type_code:code, status:'draft', fields:initialFields}});
    navigate(`/documents/${doc.id}/edit`);
  } catch (err) {
    toast(err.message, 'error');
    navigate(`/documents/${code}`);
  }
}

function fieldHtml(field, value, viewOnly) {
  const baseFontSize = Number(field.font_size || 17);
  const fontWeight = field.font_weight === 'normal' ? 500 : 700;
  const disabled = viewOnly || field.readonly ? 'disabled' : '';
  const lineBoxes = Array.isArray(field.line_boxes) && field.line_boxes.length
    ? field.line_boxes
    : (field.line_positions || []).map(top => ({x:field.x, y:top, w:field.w, h:field.line_height || 2.3}));
  if (lineBoxes.length) {
    const values = String(value || '').replace(/\r\n?/g, '\n').split('\n');
    return lineBoxes.map((box, index) => {
      const style = `left:${box.x}%;top:${box.y}%;width:${box.w}%;height:${box.h || field.line_height || 2.3}%;text-align:${field.align || 'right'};direction:${field.direction || 'ltr'};font-weight:${fontWeight};`;
      return `<input class="template-field template-line-field" type="text" data-field="${field.key}" data-field-line="${index}" data-field-lines="${lineBoxes.length}" data-field-type="line" data-base-font-size="${baseFontSize}" style="${style}" value="${escapeHtml(values[index] || '')}" ${disabled}>`;
    }).join('');
  }
  const style = `left:${field.x}%;top:${field.y}%;width:${field.w}%;height:${field.h}%;text-align:${field.align || 'center'};direction:${field.direction || 'ltr'};font-weight:${fontWeight};`;
  const common = `data-field="${field.key}" data-field-type="${field.type || 'text'}" data-base-font-size="${baseFontSize}" style="${style}"`;
  if (field.type === 'textarea') return `<textarea class="template-field" ${common} ${disabled}>${escapeHtml(value || '')}</textarea>`;
  if (field.type === 'checkbox') return `<label class="template-field template-checkbox" data-field-type="checkbox" data-base-font-size="${baseFontSize}" style="${style}"><input type="checkbox" data-field="${field.key}" ${value ? 'checked' : ''} ${disabled}></label>`;
  const type = field.type === 'date' ? 'date' : 'text';
  return `<input class="template-field" type="${type}" ${common} value="${escapeHtml(value || '')}" ${disabled}>`;
}

function wireLineFieldNavigation(page) {
  const lineFields = [...page.querySelectorAll('.template-line-field')];
  lineFields.forEach((input, position) => {
    input.addEventListener('keydown', event => {
      if (event.key === 'Enter' || event.key === 'ArrowDown') { event.preventDefault(); lineFields[position + 1]?.focus(); }
      else if (event.key === 'ArrowUp') { event.preventDefault(); lineFields[position - 1]?.focus(); }
      else if (event.key === 'Backspace' && !input.value && position > 0) lineFields[position - 1]?.focus();
    });
    input.addEventListener('paste', event => {
      const pasted = event.clipboardData?.getData('text') || '';
      if (!/[\r\n]/.test(pasted)) return;
      event.preventDefault();
      const parts = pasted.replace(/\r\n?/g, '\n').split('\n');
      const sameField = lineFields.filter(item => item.dataset.field === input.dataset.field);
      const start = Number(input.dataset.fieldLine || 0);
      parts.forEach((part,index) => { if (sameField[start+index]) sameField[start+index].value=part; });
      sameField[Math.min(start+parts.length,sameField.length-1)]?.focus();
      state.dirty=true;
    });
  });
}

const A4_PREVIEW_WIDTH = 794;
const A4_PREVIEW_RATIO = 210 / 297;
const EDITOR_ZOOM_MIN = 0.5;
const EDITOR_ZOOM_MAX = 2.5;
const EDITOR_ZOOM_STEP = 0.25;

function clampEditorZoom(value) {
  return Math.min(EDITOR_ZOOM_MAX, Math.max(EDITOR_ZOOM_MIN, Number(value) || 1));
}

function updateEditorZoomControls() {
  const value = clampEditorZoom(state.editorZoom);
  const label = document.getElementById('template-zoom-value');
  const zoomOut = document.getElementById('template-zoom-out');
  const zoomIn = document.getElementById('template-zoom-in');
  const fit = document.getElementById('template-zoom-fit');
  if (label) label.textContent = `${Math.round(value * 100)}%`;
  if (zoomOut) zoomOut.disabled = value <= EDITOR_ZOOM_MIN + 0.001;
  if (zoomIn) zoomIn.disabled = value >= EDITOR_ZOOM_MAX - 0.001;
  if (fit) fit.classList.toggle('active', Math.abs(value - 1) < 0.001);
}

function captureEditorZoomAnchor() {
  const stage = document.querySelector('.editor-stage.fit-a4-stage');
  if (!stage) return null;
  return {
    x: stage.scrollWidth > 0 ? (stage.scrollLeft + stage.clientWidth / 2) / stage.scrollWidth : 0.5,
    y: stage.scrollHeight > 0 ? (stage.scrollTop + stage.clientHeight / 2) / stage.scrollHeight : 0.5,
  };
}

function setEditorZoom(value) {
  state.editorZoomAnchor = captureEditorZoomAnchor();
  state.editorZoom = clampEditorZoom(value);
  updateEditorZoomControls();
  state.editorViewportFit?.();
}

function fitDocumentTemplateToViewport(page, frame, config) {
  if (!page) return;
  const stage = page.closest('.editor-stage');
  const canvas = page.closest('.template-zoom-canvas');
  if (!stage || !canvas) return;

  const stageStyle = window.getComputedStyle(stage);
  const horizontalPadding = (parseFloat(stageStyle.paddingLeft) || 0) + (parseFloat(stageStyle.paddingRight) || 0);
  const verticalPadding = (parseFloat(stageStyle.paddingTop) || 0) + (parseFloat(stageStyle.paddingBottom) || 0);
  const viewportHeight = window.visualViewport?.height || window.innerHeight || document.documentElement.clientHeight || 900;
  const stageTop = Math.max(0, stage.getBoundingClientRect().top);
  const availableWidth = Math.max(1, stage.clientWidth - horizontalPadding);
  const availableHeight = Math.max(1, viewportHeight - stageTop - verticalPadding - 14);

  // Base size always keeps the whole A4 form visible. Zoom is applied only to the editor preview.
  const fittedWidth = Math.max(1, Math.min(A4_PREVIEW_WIDTH, availableWidth, availableHeight * A4_PREVIEW_RATIO));
  const fittedHeight = fittedWidth / A4_PREVIEW_RATIO;
  const zoom = clampEditorZoom(state.editorZoom);
  const zoomedWidth = fittedWidth * zoom;
  const zoomedHeight = fittedHeight * zoom;

  page.style.width = `${fittedWidth.toFixed(2)}px`;
  page.style.height = `${fittedHeight.toFixed(2)}px`;
  page.style.aspectRatio = 'auto';
  page.style.transformOrigin = 'top left';
  page.style.transform = `scale(${zoom})`;
  page.dataset.viewportFit = '1';
  page.dataset.editorZoom = String(zoom);

  canvas.style.width = `${zoomedWidth.toFixed(2)}px`;
  canvas.style.height = `${zoomedHeight.toFixed(2)}px`;
  stage.style.height = `${Math.max(210, viewportHeight - stageTop - 14).toFixed(2)}px`;
  stage.classList.add('fit-a4-stage');
  stage.classList.toggle('zoomed-a4-stage', zoom > 1.001);

  if (frame && config) scaleHtmlTemplateFrame(frame, config);
  else applyTemplateScale(page);

  const anchor = state.editorZoomAnchor;
  if (anchor) {
    state.editorZoomAnchor = null;
    requestAnimationFrame(() => {
      const maxLeft = Math.max(0, stage.scrollWidth - stage.clientWidth);
      const maxTop = Math.max(0, stage.scrollHeight - stage.clientHeight);
      const left = anchor.x * stage.scrollWidth - stage.clientWidth / 2;
      const top = anchor.y * stage.scrollHeight - stage.clientHeight / 2;
      stage.scrollLeft = Math.min(maxLeft, Math.max(0, left));
      stage.scrollTop = Math.min(maxTop, Math.max(0, top));
    });
  }
  updateEditorZoomControls();
}

function installDocumentViewportFit(page, frame, config) {
  if (!page) return () => {};
  const stage = page.closest('.editor-stage');
  const main = document.querySelector('.main');
  let raf = 0;
  const fit = () => {
    cancelAnimationFrame(raf);
    raf = requestAnimationFrame(() => fitDocumentTemplateToViewport(page, frame, config));
  };

  const observer = window.ResizeObserver ? new ResizeObserver(fit) : null;
  if (observer) {
    if (main) observer.observe(main);
    if (stage?.parentElement) observer.observe(stage.parentElement);
  }
  window.addEventListener('resize', fit, {passive:true});
  window.visualViewport?.addEventListener('resize', fit, {passive:true});
  window.visualViewport?.addEventListener('scroll', fit, {passive:true});
  fit();

  state.editorViewportFit = fit;
  return () => {
    cancelAnimationFrame(raf);
    observer?.disconnect();
    window.removeEventListener('resize', fit);
    window.visualViewport?.removeEventListener('resize', fit);
    window.visualViewport?.removeEventListener('scroll', fit);
    if (state.editorViewportFit === fit) state.editorViewportFit = null;
  };
}

function applyTemplateScale(page) {
  if (!page) return;
  const scale = Math.max(0.35, page.clientWidth / 794);
  page.querySelectorAll('.template-field').forEach(field => {
    const base = Number(field.dataset.baseFontSize || 17);
    field.style.fontSize = `${Math.max(7, base * scale)}px`;
  });
  page.querySelectorAll('.template-checkbox input').forEach(input => {
    input.style.width = `${Math.max(10, 23 * scale)}px`;
    input.style.height = `${Math.max(10, 23 * scale)}px`;
  });
}

function htmlFieldSelectors(field) {
  if (Array.isArray(field.html_selectors) && field.html_selectors.length) return field.html_selectors;
  return field.html_selector ? [field.html_selector] : [];
}

function setHtmlElementValue(element, value, fieldType) {
  if (!element) return;
  if (fieldType === 'checkbox' || element.type === 'checkbox') { element.checked = Boolean(value); return; }
  const text = value == null ? '' : String(value);
  if (element.matches('input, textarea, select')) element.value = text;
  else element.textContent = text;
}

function getHtmlElementValue(element, fieldType) {
  if (!element) return fieldType === 'checkbox' ? false : '';
  if (fieldType === 'checkbox' || element.type === 'checkbox') return Boolean(element.checked);
  if (element.matches('input, textarea, select')) return element.value || '';
  return element.textContent || '';
}

function applyHtmlTemplateGuide(frame, visible) {
  const frameDoc = frame?.contentDocument;
  if (!frameDoc) return;
  frameDoc.documentElement.classList.toggle('ziad-field-guide', Boolean(visible));
}

function scaleHtmlTemplateFrame(frame, config) {
  const frameDoc = frame?.contentDocument;
  if (!frameDoc) return;
  const root = frameDoc.querySelector(config.html_root || '.page, .sheet, main');
  if (!root) return;

  const html = frameDoc.documentElement;
  const body = frameDoc.body;

  const hiddenSelectors = Array.isArray(config.html_hide_selectors) ? config.html_hide_selectors : [];
  hiddenSelectors.forEach(selector => {
    frameDoc.querySelectorAll(selector).forEach(element => element.style.setProperty('display', 'none', 'important'));
  });
  if (config.html_wrapper) {
    const wrapper = frameDoc.querySelector(config.html_wrapper);
    if (wrapper) {
      wrapper.style.setProperty('transform', 'none', 'important');
      wrapper.style.setProperty('transform-origin', 'top left', 'important');
      wrapper.style.setProperty('margin', '0', 'important');
      wrapper.style.setProperty('width', '210mm', 'important');
      wrapper.style.setProperty('height', '297mm', 'important');
    }
  }

  // The uploaded templates are authored with different RTL/LTR page shells.
  // In a narrow iframe, RTL block layout can place a fixed-width A4 root at a
  // negative X position, which made PV/VM look like a blank white page. Keep
  // the document shell LTR for geometry, while preserving the template root's
  // original writing direction for its Arabic content.
  if (!root.dataset.ziadOriginalDirection) {
    root.dataset.ziadOriginalDirection = frameDoc.defaultView?.getComputedStyle(root).direction || 'ltr';
  }
  html.style.direction = 'ltr';
  html.style.overflow = 'hidden';
  body.style.margin = '0';
  body.style.padding = '0';
  body.style.display = 'block';
  body.style.minHeight = '0';
  body.style.background = '#fff';
  body.style.overflow = 'hidden';
  body.style.direction = 'ltr';
  body.style.textAlign = 'left';
  body.style.justifyContent = 'flex-start';
  body.style.alignItems = 'flex-start';

  root.dataset.ziadTemplateRoot = '1';
  root.style.direction = root.dataset.ziadOriginalDirection;
  root.style.margin = '0';
  root.style.left = '0';
  root.style.right = 'auto';
  root.style.top = '0';

  let naturalWidth = Number(root.dataset.ziadNaturalWidth || 0);
  let naturalHeight = Number(root.dataset.ziadNaturalHeight || 0);
  if (!naturalWidth || !naturalHeight) {
    // offsetWidth/offsetHeight are intentionally used before getBoundingClientRect:
    // some uploaded HTML files contain their own responsive transform, and a
    // transformed bounding rect is not the true design size.
    const computed = frameDoc.defaultView?.getComputedStyle(root);
    naturalWidth = root.offsetWidth || parseFloat(computed?.width || '0') || root.getBoundingClientRect().width || 794;
    naturalHeight = root.offsetHeight || parseFloat(computed?.height || '0') || root.getBoundingClientRect().height || 1123;
    root.dataset.ziadNaturalWidth = String(naturalWidth);
    root.dataset.ziadNaturalHeight = String(naturalHeight);
  }

  const availableWidth = frame.clientWidth || 794;
  const availableHeight = frame.clientHeight || 1123;
  const scale = Math.max(0.01, Math.min(1, availableWidth / naturalWidth, availableHeight / naturalHeight));

  // The bridge stylesheet applies this with !important, so template-local
  // resize scripts cannot overwrite the editor preview scale (notably PR).
  root.style.setProperty('--ziad-template-scale', String(scale));
  root.style.transformOrigin = 'top left';
  root.style.transform = `scale(${scale})`;
  root.dataset.ziadPreviewScale = String(scale);
}

function configureHtmlTemplateFrame(frame, doc, viewOnly) {
  const frameDoc = frame.contentDocument;
  if (!frameDoc) return;

  const expectedRoot = doc.type.config.html_root || '.page, .sheet, main';
  const templateRoot = frameDoc.querySelector(expectedRoot);
  if (!templateRoot) {
    frame.dataset.ready = '0';
    const saveButton = document.getElementById('save-document');
    if (saveButton) saveButton.disabled = true;
    const host = document.getElementById('template-page');
    host?.querySelector('#template-load-error')?.remove();
    if (host) {
      const notice = document.createElement('div');
      notice.id = 'template-load-error';
      notice.className = 'template-load-error';
      notice.innerHTML = `<strong>تعذر تحميل القالب الرسمي</strong><span>ملف النموذج غير موجود على الخادم. أعد نشر ملفات <b>app/static/form-templates</b>.</span>`;
      host.appendChild(notice);
    }
    return;
  }
  document.getElementById('template-load-error')?.remove();
  let helperStyle = frameDoc.getElementById('ziad-template-bridge-style');
  if (!helperStyle) {
    helperStyle = frameDoc.createElement('style');
    helperStyle.id = 'ziad-template-bridge-style';
    helperStyle.textContent = `
      [data-ziad-field="1"]{transition:outline .12s ease,background-color .12s ease;}
      html.ziad-field-guide [data-ziad-field="1"]{outline:1px dashed rgba(14,107,79,.62)!important;outline-offset:-1px;background-color:rgba(255,255,255,.18)!important;}
      [data-ziad-viewonly="1"]{pointer-events:none!important;opacity:1!important;color:#111!important;-webkit-text-fill-color:#111!important;}
      [data-ziad-template-root="1"]{transform:scale(var(--ziad-template-scale,1))!important;transform-origin:top left!important;margin:0!important;}
    `;
    frameDoc.head.appendChild(helperStyle);
  }

  const hiddenSelectors = Array.isArray(doc.type.config.html_hide_selectors) ? doc.type.config.html_hide_selectors : [];
  hiddenSelectors.forEach(selector => {
    frameDoc.querySelectorAll(selector).forEach(element => element.style.setProperty('display', 'none', 'important'));
  });
  if (doc.type.config.html_wrapper) {
    const wrapper = frameDoc.querySelector(doc.type.config.html_wrapper);
    if (wrapper) {
      wrapper.style.setProperty('transform', 'none', 'important');
      wrapper.style.setProperty('transform-origin', 'top left', 'important');
      wrapper.style.setProperty('margin', '0', 'important');
      wrapper.style.setProperty('width', '210mm', 'important');
      wrapper.style.setProperty('height', '297mm', 'important');
    }
  }

  doc.type.config.fields.forEach(field => {
    const selectors = htmlFieldSelectors(field);
    if (!selectors.length) return;
    const rawValue = doc.fields[field.key];
    const lineValues = selectors.length > 1 ? String(rawValue || '').replace(/\r\n?/g,'\n').split('\n') : [rawValue];
    selectors.forEach((selector, index) => {
      const element = frameDoc.querySelector(selector);
      if (!element) return;
      element.dataset.ziadField = '1';
      element.dataset.ziadFieldKey = field.key;
      setHtmlElementValue(element, lineValues[index] ?? '', field.type);
      const locked = viewOnly || field.readonly || field.html_readonly;
      if (element.matches('input, textarea')) {
        if (element.type === 'checkbox') element.disabled = locked;
        else element.readOnly = locked;
      } else if (element.hasAttribute('contenteditable')) {
        element.setAttribute('contenteditable', locked ? 'false' : 'true');
      }
      element.dataset.ziadViewonly = locked ? '1' : '0';
      if (!locked) {
        element.addEventListener('input', () => { state.dirty = true; });
        element.addEventListener('change', () => { state.dirty = true; });
      }
    });
    if (!viewOnly && selectors.length > 1) {
      selectors.forEach((selector, index) => {
        const nextSelector = selectors[index + 1];
        if (!nextSelector) return;
        const element = frameDoc.querySelector(selector);
        const next = frameDoc.querySelector(nextSelector);
        if (!element || !next) return;
        element.addEventListener('keydown', event => {
          if (event.key === 'Enter' || event.key === 'ArrowDown') { event.preventDefault(); next.focus(); }
        });
      });
    }
  });

  const guide = document.getElementById('field-guide');
  applyHtmlTemplateGuide(frame, !viewOnly && (guide?.checked ?? true));
  scaleHtmlTemplateFrame(frame, doc.type.config);
  frame.dataset.ready = '1';
  const saveButton = document.getElementById('save-document');
  if (saveButton) saveButton.disabled = false;
}

function collectHtmlTemplateFields(frame, config) {
  const frameDoc = frame?.contentDocument;
  if (!frameDoc) return {};
  const result = {};
  config.fields.forEach(field => {
    const selectors = htmlFieldSelectors(field);
    if (!selectors.length) return;
    const values = selectors.map(selector => getHtmlElementValue(frameDoc.querySelector(selector), field.type));
    if (field.type === 'checkbox') result[field.key] = Boolean(values[0]);
    else if (selectors.length > 1) result[field.key] = values.map(value => String(value || '')).join('\n').replace(/\n+$/g,'');
    else result[field.key] = values[0] == null ? '' : String(values[0]);
  });
  return result;
}

async function renderDocumentEditor(id, mode) {
  pageLoading(mode === 'view' ? 'عرض المستند' : 'تعديل المستند');
  const doc = await api(`/api/documents/${id}`);
  state.currentDocument = doc;
  state.dirty = false;
  if (state.editorDocumentId !== id) {
    state.editorZoom = 1;
    state.editorZoomAnchor = null;
    state.editorDocumentId = id;
  }
  const viewOnly = mode === 'view' || state.user.role === 'viewer';
  const useHtmlTemplate = doc.type.config.template_engine === 'html' && Boolean(doc.type.config.html_template);
  const fields = useHtmlTemplate ? '' : doc.type.config.fields.map(field => fieldHtml(field, doc.fields[field.key], viewOnly)).join('');
  const templateMarkup = useHtmlTemplate
    ? `<iframe id="template-frame" class="html-template-frame" src="/form-templates/${encodeURIComponent(doc.type.config.html_template)}?v=3.3.15" title="${escapeHtml(doc.type.name_ar)}"></iframe>`
    : `<img class="template-bg" src="${doc.type.image_url}" alt="${escapeHtml(doc.type.name_ar)}">${fields}`;
  const attachments = attachmentsHtml(doc.attachments || [], viewOnly);
  const primaryAction = viewOnly ? (state.user.role !== 'viewer' ? `<button id="edit-document" class="btn btn-primary">${icon('edit')} تعديل</button>` : '') : `<select id="document-status" class="control compact status-control"><option value="saved" ${doc.status === 'saved' ? 'selected' : ''}>محفوظ</option><option value="draft" ${doc.status === 'draft' ? 'selected' : ''}>مسودة</option></select><button id="save-document" class="btn btn-primary">${icon('save')} حفظ</button>`;
  const deleteAction = state.user.role === 'admin' ? `<button type="button" class="btn btn-danger-soft" id="delete-document" title="حذف المستند نهائياً">${icon('trash')}<span>حذف نهائي</span></button>` : '';
  const isTransferDocument = doc.type.code === 'TR';
  const transferMeta = isTransferDocument ? [
    doc.fields.date ? `<span>${icon('clock')} ${escapeHtml(doc.fields.date)}</span>` : '',
    doc.fields.transfer_entity ? `<span>${icon('transfer')} ${escapeHtml(doc.fields.transfer_entity)}</span>` : '',
    doc.fields.amount ? `<span>${icon('wallet')} ${displayDocumentAmount(doc.fields.amount)} ${escapeHtml(doc.fields.currency || '')}</span>` : '',
  ].filter(Boolean).join('') : '';
  const editorHeader = isTransferDocument
    ? `<div class="page-header document-header transfer-document-header"><div class="transfer-document-heading"><div class="transfer-document-icon">${icon('transfer')}</div><div><span class="eyebrow">طلب تحويل</span><h1>${escapeHtml(doc.document_number)}</h1><p>واجهة عمل محسّنة للطلب مع بقاء نموذج التحويل الأصلي دون أي تغيير.</p>${transferMeta ? `<div class="transfer-document-meta">${transferMeta}</div>` : ''}</div></div><div class="page-actions"><a class="btn btn-secondary" href="#/documents/${doc.type.code}">${icon('chevron')} رجوع للتحويلات</a></div></div>`
    : `<div class="page-header document-header"><div><span class="eyebrow">${escapeHtml(doc.type.name_ar)}</span><h1>${escapeHtml(doc.document_number)}</h1><p>الكتابة في طبقة مستقلة، والقالب الرسمي يبقى دون تعديل.</p></div><div class="page-actions"><a class="btn btn-secondary" href="#/documents/${doc.type.code}">${icon('chevron')} رجوع للقائمة</a></div></div>`;
  shell(`${viewOnly ? 'عرض' : 'تعديل'} ${doc.type.name_ar}`, `
    ${editorHeader}
    <div class="document-commandbar"><div class="commandbar-primary">${primaryAction}<button id="print-document" class="btn btn-secondary">${icon('print')} طباعة</button></div><div class="commandbar-secondary"><div class="template-zoom-controls" aria-label="تكبير وتصغير النموذج" dir="ltr"><button type="button" class="template-zoom-button" id="template-zoom-out" title="تصغير النموذج" aria-label="تصغير النموذج">−</button><span class="template-zoom-value" id="template-zoom-value">100%</span><button type="button" class="template-zoom-button" id="template-zoom-in" title="تكبير النموذج" aria-label="تكبير النموذج">+</button><button type="button" class="template-zoom-fit active" id="template-zoom-fit" title="إظهار النموذج كاملاً داخل الشاشة">ملاءمة</button></div>${!viewOnly ? `<label class="field-guide-toggle"><input id="field-guide" type="checkbox" checked><span>إظهار حدود الكتابة</span></label>` : ''}${deleteAction}</div></div>
    <div class="editor-grid"><div class="editor-stage"><div class="template-zoom-canvas" id="template-zoom-canvas"><div id="template-page" class="template-page ${useHtmlTemplate ? 'html-template-host' : ''} ${viewOnly ? 'view-only clean' : ''}">${templateMarkup}</div></div></div><aside class="editor-side">
      <section class="panel"><div class="panel-head"><h3>معلومات المستند</h3>${statusBadge(doc.status)}</div><div class="panel-body"><div class="lock-note">${icon('lock')} القالب الرسمي محفوظ كما هو، ولا يتم تعديل أي صورة أو خط أو نقطة داخله.</div><div class="meta-list" style="margin-top:14px"><div class="meta-row"><span>أنشأه</span><strong>${escapeHtml(doc.created_by_name)}</strong></div><div class="meta-row"><span>آخر تعديل</span><strong>${escapeHtml(doc.updated_by_name)}</strong></div><div class="meta-row"><span>تاريخ الإنشاء</span><strong>${formatDate(doc.created_at, true)}</strong></div><div class="meta-row"><span>الإصدار</span><strong>${doc.revision}</strong></div><div class="meta-row"><span>مرات الطباعة</span><strong>${doc.print_count}</strong></div></div></div></section>
      <section class="panel attachments-panel"><div class="panel-head"><div><h3>المرفقات</h3><p>${doc.attachments.length} ملف مرتبط</p></div><span class="badge badge-saved">${doc.attachments.length}</span></div><div class="panel-body">${!viewOnly ? `<div class="attachment-uploader" id="attachment-dropzone"><input id="attachment-input" type="file" multiple hidden><div class="attachment-uploader-icon">${icon('upload')}</div><div class="attachment-uploader-copy"><strong>إضافة مرفقات</strong><span>اسحب الملفات إلى هذه المساحة</span><small>PDF، Word، Excel والصور · حتى 100MB</small></div><button type="button" class="btn btn-primary attachment-browse" id="attachment-browse">اختيار ملفات</button></div><div id="attachment-upload-status" class="attachment-upload-status" hidden></div>` : ''}<div class="attachment-list-head"><span>الملفات المحفوظة</span></div><div class="attachments" id="attachments-list">${attachments}</div></div></section>
    </aside></div>`, {active:doc.type.code, fullWidth:true});
  const page = document.getElementById('template-page');
  const frame = document.getElementById('template-frame');
  if (useHtmlTemplate && frame) {
    const saveButton = document.getElementById('save-document');
    if (saveButton) saveButton.disabled = true;
    const initializeFrame = () => {
      configureHtmlTemplateFrame(frame, doc, viewOnly);
      state.editorViewportFit?.();
    };
    frame.addEventListener('load', initializeFrame, {once:true});
    if (frame.contentDocument?.readyState === 'complete') initializeFrame();
  }
  state.editorViewportFitCleanup = installDocumentViewportFit(page, useHtmlTemplate ? frame : null, useHtmlTemplate ? doc.type.config : null);
  const zoomOutButton = document.getElementById('template-zoom-out');
  const zoomInButton = document.getElementById('template-zoom-in');
  const zoomFitButton = document.getElementById('template-zoom-fit');
  [zoomOutButton, zoomInButton, zoomFitButton].filter(Boolean).forEach(button => {
    button.addEventListener('mousedown', event => event.preventDefault());
  });
  zoomOutButton?.addEventListener('click', () => setEditorZoom(state.editorZoom - EDITOR_ZOOM_STEP));
  zoomInButton?.addEventListener('click', () => setEditorZoom(state.editorZoom + EDITOR_ZOOM_STEP));
  zoomFitButton?.addEventListener('click', () => setEditorZoom(1));
  updateEditorZoomControls();
  document.getElementById('field-guide')?.addEventListener('change', event => {
    if (useHtmlTemplate && frame) applyHtmlTemplateGuide(frame, event.target.checked);
    else page.classList.toggle('clean', !event.target.checked);
  });
  document.getElementById('print-document').addEventListener('click', () => openPrintModal(state.currentDocument));
  document.getElementById('edit-document')?.addEventListener('click', () => navigate(`/documents/${id}/edit`));
  document.getElementById('delete-document')?.addEventListener('click', () => confirmDeleteDocument(id, doc.type.code));
  if (!viewOnly) {
    page.querySelectorAll('[data-field]').forEach(input => input.addEventListener('input', () => { state.dirty = true; }));
    wireLineFieldNavigation(page);
    document.getElementById('save-document').addEventListener('click', () => saveDocument(id));
    const input = document.getElementById('attachment-input'); const dropzone = document.getElementById('attachment-dropzone');
    document.getElementById('attachment-browse').addEventListener('click', event => { event.stopPropagation(); input.click(); });
    dropzone.addEventListener('click', event => { if (!event.target.closest('button')) input.click(); });
    input.addEventListener('change', event => uploadFiles(id,[...event.target.files]));
    ['dragenter','dragover'].forEach(name => dropzone.addEventListener(name,event => { event.preventDefault(); dropzone.classList.add('is-dragging'); }));
    ['dragleave','drop'].forEach(name => dropzone.addEventListener(name,event => { event.preventDefault(); dropzone.classList.remove('is-dragging'); }));
    dropzone.addEventListener('drop',event => uploadFiles(id,[...event.dataTransfer.files]));
  }
  wireAttachmentButtons();
}

function collectFields() {
  const htmlFrame = document.getElementById('template-frame');
  if (htmlFrame && state.currentDocument?.type?.config?.template_engine === 'html') {
    if (htmlFrame.dataset.ready !== '1') throw new Error('القالب ما زال قيد التحميل، حاول الحفظ بعد لحظة.');
    return collectHtmlTemplateFields(htmlFrame, state.currentDocument.type.config);
  }
  const result = {};
  const lineGroups = new Map();
  document.querySelectorAll('#template-page [data-field]').forEach(input => {
    const key=input.dataset.field;
    if (input.dataset.fieldLine !== undefined) { if (!lineGroups.has(key)) lineGroups.set(key,[]); lineGroups.get(key)[Number(input.dataset.fieldLine)] = input.value; }
    else result[key]=input.type === 'checkbox' ? input.checked : input.value;
  });
  lineGroups.forEach((lines,key) => { result[key]=lines.map(line => line || '').join('\n').replace(/\n+$/g,''); });
  return result;
}

async function saveDocument(id) {
  const button=document.getElementById('save-document');
  const statusValue=document.getElementById('document-status')?.value || 'saved';
  const original=button.innerHTML;
  button.disabled=true; button.innerHTML='<span class="loader"></span> جارٍ الحفظ';
  try {
    const doc=await api(`/api/documents/${id}`,{method:'PUT',body:{status:statusValue,fields:collectFields()}});
    state.currentDocument=doc; state.dirty=false;
    toast(statusValue === 'saved' ? 'تم حفظ المستند بنجاح' : 'تم حفظ المسودة','success');
    await renderDocumentEditor(id,'edit');
  } catch(err) { toast(err.message,'error'); button.disabled=false; button.innerHTML=original; }
}

function attachmentKind(item) {
  const name = (item.original_name || '').toLowerCase();
  const mime = (item.mime_type || '').toLowerCase();
  if (mime.includes('pdf') || name.endsWith('.pdf')) return {label:'PDF', cls:'pdf'};
  if (mime.startsWith('image/') || /\.(png|jpe?g|webp|gif|bmp|tiff?)$/.test(name)) return {label:'صورة', cls:'image'};
  if (/\.(docx?|odt|rtf)$/.test(name)) return {label:'Word', cls:'word'};
  if (/\.(xlsx?|csv)$/.test(name)) return {label:'Excel', cls:'excel'};
  return {label:'ملف', cls:'file'};
}

function attachmentsHtml(items, viewOnly) {
  if (!items.length) return '<div class="attachment-empty"><div class="attachment-uploader-icon">'+icon('attachment')+'</div><strong>لا توجد مرفقات</strong><span>ستظهر الملفات المرتبطة بهذا المستند هنا.</span></div>';
  return items.map(item => { const kind=attachmentKind(item); return `<article class="attachment-item"><div class="attachment-main"><div class="attachment-type ${kind.cls}">${kind.label}</div><div class="attachment-name"><strong title="${escapeHtml(item.original_name)}">${escapeHtml(item.original_name)}</strong><span>${formatBytes(item.size_bytes)} · ${formatDate(item.created_at,true)}</span></div></div><div class="attachment-actions" role="group" aria-label="إجراءات المرفق ${escapeHtml(item.original_name)}"><button type="button" class="btn btn-secondary attachment-action" data-attachment-view="${item.id}" title="مشاهدة المرفق">${icon('eye')}<span>مشاهدة</span></button><button type="button" class="btn btn-secondary attachment-action" data-attachment-download="${item.id}" title="تنزيل المرفق">${icon('download')}<span>تنزيل</span></button>${!viewOnly ? `<button type="button" class="btn btn-danger-soft attachment-action" data-attachment-delete="${item.id}" title="حذف المرفق">${icon('trash')}<span>حذف</span></button>` : ''}</div></article>`; }).join('');
}

async function uploadFiles(documentId, files) {
  if (!files.length) return;
  const input = document.getElementById('attachment-input');
  const status = document.getElementById('attachment-upload-status');
  input.disabled = true;
  if (status) { status.hidden=false; status.innerHTML=`<span class="loader"></span><div><strong>جارٍ رفع ${files.length} ملف</strong><span id="attachment-upload-name"></span></div>`; }
  try {
    for (const file of files) {
      const nameEl=document.getElementById('attachment-upload-name'); if(nameEl) nameEl.textContent=file.name;
      await api(`/api/documents/${documentId}/attachments`, {
        method:'POST',
        headers:{'X-File-Name':encodeURIComponent(file.name), 'Content-Type':file.type || 'application/octet-stream'},
        body:file,
      });
    }
    toast('تم رفع المرفقات بنجاح', 'success');
    await renderDocumentEditor(documentId, 'edit');
  } catch (err) {
    toast(err.message, 'error');
    input.disabled = false;
    if (status) { status.hidden=true; status.innerHTML=''; }
  }
}

function wireAttachmentButtons() {
  root.querySelectorAll('[data-attachment-view]').forEach(btn => btn.addEventListener('click', () => openAttachment(Number(btn.dataset.attachmentView), false)));
  root.querySelectorAll('[data-attachment-download]').forEach(btn => btn.addEventListener('click', () => openAttachment(Number(btn.dataset.attachmentDownload), true)));
  root.querySelectorAll('[data-attachment-delete]').forEach(btn => btn.addEventListener('click', () => deleteAttachment(Number(btn.dataset.attachmentDelete))));
}

async function openAttachment(id, download) {
  const tab = download ? null : window.open('about:blank', '_blank');
  try {
    const response = await api(`/api/attachments/${id}/file${download ? '?download=1' : ''}`);
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    if (download) {
      const link = document.createElement('a'); link.href = url;
      const disposition = response.headers.get('content-disposition') || '';
      link.download = decodeURIComponent((disposition.match(/filename\*=UTF-8''([^;]+)/) || [,'attachment'])[1]);
      link.click();
    } else if (tab) tab.location = url;
    setTimeout(() => URL.revokeObjectURL(url), 120000);
  } catch (err) {
    if (tab) tab.close();
    toast(err.message, 'error');
  }
}

async function deleteAttachment(id) {
  if (!confirm('هل تريد حذف هذا المرفق؟')) return;
  try {
    await api(`/api/attachments/${id}`, {method:'DELETE'});
    toast('تم حذف المرفق', 'success');
    await renderDocumentEditor(state.currentDocument.id, 'edit');
  } catch (err) { toast(err.message, 'error'); }
}

function openPrintModal(doc) {
  const items = doc.attachments || [];
  const list = items.length ? items.map(item => `<label class="check-item"><input type="checkbox" name="print_attachment" value="${item.id}" checked><span><strong>${escapeHtml(item.original_name)}</strong><small style="display:block;color:var(--muted)">${formatBytes(item.size_bytes)}</small></span></label>`).join('') : '<div class="empty" style="padding:20px">لا توجد مرفقات لهذا المستند. ستتم طباعة النموذج فقط.</div>';
  showModal(`طباعة ${doc.document_number}`, `
    <p style="margin-top:0;color:var(--muted);line-height:1.8">حدد المرفقات التي تريد إضافتها بعد المستند. بإمكانك إلغاء تحديدها لطباعة المستند وحده.</p>
    <div class="check-list">${list}</div>`, [
      `<button id="print-cancel" class="btn btn-secondary">إلغاء</button>`,
      `<button id="print-submit" class="btn btn-primary">${icon('print')} تجهيز ملف PDF</button>`
    ], 'modal-lg');
  document.getElementById('print-cancel').addEventListener('click', closeModal);
  document.getElementById('print-submit').addEventListener('click', async () => {
    const ids = [...modalRoot.querySelectorAll('input[name="print_attachment"]:checked')].map(input => Number(input.value));
    const button = document.getElementById('print-submit');
    button.disabled = true; button.innerHTML = '<span class="loader"></span> جارٍ تجهيز الطباعة';
    const tab = window.open('about:blank', '_blank');
    try {
      const response = await api(`/api/documents/${doc.id}/print`, {method:'POST', body:{attachment_ids:ids}});
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      if (tab) tab.location = url;
      closeModal();
      toast('تم تجهيز ملف الطباعة', 'success');
      setTimeout(() => URL.revokeObjectURL(url), 300000);
    } catch (err) {
      if (tab) tab.close();
      toast(err.message, 'error');
      button.disabled = false; button.innerHTML = `${icon('print')} تجهيز ملف PDF`;
    }
  });
}

function confirmDeleteDocument(id, returnCode) {
  showModal('حذف المستند نهائياً', `
    <div class="lock-note" style="background:var(--danger-soft);border-color:#fecdca;color:var(--danger)">هذا الإجراء يحذف المستند وجميع مرفقاته نهائياً ولا يمكن التراجع عنه.</div>
    <div class="form-row" style="margin-top:16px"><label>اكتب العبارة: <strong>حذف نهائي</strong></label><input id="delete-confirmation" class="control" autocomplete="off"></div>`, [
      '<button id="delete-cancel" class="btn btn-secondary">إلغاء</button>',
      `<button id="delete-submit" class="btn btn-danger">${icon('trash')} حذف نهائي</button>`
    ]);
  document.getElementById('delete-cancel').addEventListener('click', closeModal);
  document.getElementById('delete-submit').addEventListener('click', async () => {
    const confirmation = document.getElementById('delete-confirmation').value;
    try {
      await api(`/api/documents/${id}/permanent`, {method:'DELETE', body:{confirmation}});
      closeModal(); toast('تم حذف المستند نهائياً', 'success'); navigate(`/documents/${returnCode}`);
    } catch (err) { toast(err.message, 'error'); }
  });
}


function loanStatusBadge(loan) {
  return loan.status === 'paid'
    ? '<span class="badge badge-saved">مسدد بالكامل</span>'
    : '<span class="badge badge-draft">قائم</span>';
}

function loanActionButtons(loan) {
  const canEdit = state.user.role !== 'viewer';
  const pay = canEdit && loan.status !== 'paid' ? `<button type="button" class="btn btn-primary row-action" data-loan-action="pay" data-id="${loan.id}">${icon('check')}<span>تسديد</span></button>` : '';
  const edit = canEdit ? `<button type="button" class="btn btn-secondary row-action" data-loan-action="edit" data-id="${loan.id}">${icon('edit')}<span>تعديل</span></button>` : '';
  const report = `<button type="button" class="btn btn-secondary row-action" data-loan-action="report" data-id="${loan.id}">${icon('print')}<span>تقرير</span></button>`;
  const remove = state.user.role === 'admin' ? `<button type="button" class="btn btn-danger-soft row-action" data-loan-action="delete" data-id="${loan.id}">${icon('trash')}<span>حذف نهائي</span></button>` : '';
  return `<div class="row-actions"><button type="button" class="btn btn-secondary row-action" data-loan-action="view" data-id="${loan.id}">${icon('eye')}<span>مشاهدة</span></button>${report}${pay}${edit}${remove}</div>`;
}

function wireLoanActions(loans, onChanged = renderLoans) {
  root.querySelectorAll('[data-loan-action]').forEach(button => button.addEventListener('click', async () => {
    const id = Number(button.dataset.id);
    let loan = loans?.find(item => item.id === id);
    if (!loan) {
      try { loan = await api(`/api/loans/${id}`); } catch (err) { return toast(err.message, 'error'); }
    }
    const action = button.dataset.loanAction;
    if (action === 'view') return navigate(`/loans/${id}`);
    if (action === 'report') return openLoanReport(loan);
    if (action === 'edit') return openLoanForm(loan, onChanged);
    if (action === 'pay') return openLoanPaymentModal(loan, onChanged);
    if (action === 'delete') return openLoanDeleteModal(loan, onChanged);
  }));
}


function openLoanReport(loan) {
  if (!loan?.id) return toast('تعذر تحديد القرض المطلوب', 'error');
  navigate(`/loans/${loan.id}/report`);
}

async function renderLoanReport(id) {
  pageLoading('تقرير القرض');
  const full = await api(`/api/loans/${id}`);
  const payments = full.payments || [];
  const paidAmount = Number(full.paid_amount || 0);
  const statusText = full.status === 'paid' ? 'مسدد بالكامل' : 'قائم';
  const rows = payments.map((p, index) => `<tr><td>${payments.length-index}</td><td>${formatMoney(p.amount)}</td><td>${formatMoney(p.remaining_amount_after)}</td><td>${p.months_remaining_after}</td><td>${escapeHtml(p.paid_by_name || '-')}</td><td>${formatDate(p.paid_at,true)}</td><td>${escapeHtml(p.notes || '-')}</td></tr>`).join('');
  const generatedAt = new Date().toLocaleString('ar-IQ');
  shell('تقرير القرض', `
    <div class="page-header loan-report-screen-header">
      <div><span class="eyebrow">قروض</span><h1>تقرير ${escapeHtml(full.borrower_name)}</h1><p>التقرير يفتح داخل النظام مباشرة ولا يحتاج السماح بالنوافذ المنبثقة.</p></div>
      <div class="page-actions"><a class="btn btn-secondary" href="#/loans/${full.id}">${icon('chevron')} رجوع للقرض</a><button id="loan-report-print-btn" class="btn btn-primary">${icon('print')} طباعة / حفظ PDF</button></div>
    </div>
    <article class="loan-report-paper" id="loan-report-paper">
      <header class="loan-report-top"><div><p>نظام المستندات — تقرير القروض</p><h2>${escapeHtml(full.borrower_name)}</h2><p>تقرير مالي يوضح القرض وجميع عمليات التسديد حتى تاريخ إنشاء التقرير.</p></div><span class="loan-report-status ${full.status === 'paid' ? 'paid' : ''}">${statusText}</span></header>
      <section class="loan-report-grid">
        <div class="loan-report-card"><span>مبلغ القرض</span><strong>${formatMoney(full.principal_amount)}</strong></div>
        <div class="loan-report-card"><span>إجمالي المسدد</span><strong>${formatMoney(paidAmount)}</strong></div>
        <div class="loan-report-card emphasis"><span>المبلغ المتبقي</span><strong>${formatMoney(full.remaining_amount)}</strong></div>
        <div class="loan-report-card"><span>عدد الأشهر</span><strong>${full.months_total}</strong></div>
        <div class="loan-report-card emphasis"><span>الأشهر الباقية</span><strong>${full.remaining_months}</strong></div>
        <div class="loan-report-card"><span>المبلغ المحدد (الحد الأدنى)</span><strong>${formatMoney(full.minimum_payment)}</strong></div>
      </section>
      <section class="loan-report-history"><h3>سجل التسديدات</h3><div class="table-wrap"><table><thead><tr><th>#</th><th>مبلغ التسديد</th><th>المبلغ الباقي</th><th>الأشهر الباقية</th><th>المستخدم</th><th>التاريخ</th><th>ملاحظة</th></tr></thead><tbody>${rows || `<tr><td colspan="7" class="empty">لم يتم تسجيل أي تسديد بعد.</td></tr>`}</tbody></table></div></section>
      <footer class="loan-report-meta"><span>تاريخ إنشاء القرض: <strong>${formatDate(full.created_at,true)}</strong></span><span>آخر تعديل: <strong>${formatDate(full.updated_at,true)}</strong></span><span>أنشأه: <strong>${escapeHtml(full.created_by_name || '-')}</strong></span><span>تاريخ التقرير: <strong>${escapeHtml(generatedAt)}</strong></span></footer>
    </article>`);
  document.getElementById('loan-report-print-btn')?.addEventListener('click', () => window.print());
}

async function renderLoans() {
  pageLoading('قروض');
  const loans = await api('/api/loans');
  const active = loans.filter(item => item.status === 'active');
  const paid = loans.filter(item => item.status === 'paid');
  const remainingTotal = active.reduce((sum, item) => sum + Number(item.remaining_amount || 0), 0);
  const canEdit = state.user.role !== 'viewer';
  const addPanel = canEdit ? `
    <section class="panel loan-create-panel">
      <div class="panel-head"><div><h3>إضافة قرض</h3><p>هذه صفحة بيانات مباشرة وليست فاتورة أو نموذج A4.</p></div>${icon('loan')}</div>
      <form id="loan-create-form" class="loan-inline-form">
        <div class="form-row"><label>الاسم الثلاثي</label><input class="control" name="borrower_name" required minlength="3" maxlength="160" placeholder="أدخل الاسم الثلاثي"></div>
        <div class="form-row"><label>المبلغ</label><input class="control" name="principal_amount" type="number" min="0.01" step="0.01" required placeholder="0.00"></div>
        <div class="form-row"><label>عدد الأشهر</label><input class="control" name="months_total" type="number" min="1" max="600" step="1" required placeholder="مثال: 12"></div>
        <div class="form-row"><label>المبلغ المحدد</label><input class="control" name="minimum_payment" type="number" min="0.01" step="0.01" required placeholder="الحد الأدنى لكل تسديد"><span class="help">لا يمكن تسجيل تسديد أقل من هذا المبلغ، إلا إذا كان المبلغ المتبقي النهائي أقل منه.</span></div>
        <div class="loan-inline-actions"><div id="loan-create-error" class="error-text"></div><button id="loan-create-save" class="btn btn-primary" type="submit">${icon('plus')} إضافة</button></div>
      </form>
    </section>` : '';
  shell('قروض', `
    <div class="page-header"><div><span class="eyebrow">الإدارة المالية</span><h1>قروض</h1><p>إضافة الاسم الثلاثي والمبلغ وعدد الأشهر والمبلغ المحدد، ثم متابعة التسديد والمتبقي مباشرة.</p></div></div>
    ${addPanel}
    <div class="list-summary"><div class="summary-pill"><strong>${loans.length}</strong><span>كل القروض</span></div><div class="summary-pill"><strong>${active.length}</strong><span>قرض قائم</span></div><div class="summary-pill"><strong>${paid.length}</strong><span>مسدد بالكامل</span></div><div class="summary-pill"><strong>${formatMoney(remainingTotal)}</strong><span>إجمالي المتبقي</span></div></div>
    <div class="panel"><div class="panel-head document-toolbar"><div class="filters"><div class="search-box">${icon('search')}<input id="loan-search" class="control" placeholder="بحث بالاسم الثلاثي..."></div><select id="loan-status" class="control compact"><option value="">كل الحالات</option><option value="active">قائم</option><option value="paid">مسدد بالكامل</option></select></div></div>
      <div class="table-wrap"><table><thead><tr><th>الاسم الثلاثي</th><th>المبلغ</th><th>عدد الأشهر</th><th>المبلغ المحدد</th><th>المسدد</th><th>المبلغ المتبقي</th><th>الأشهر الباقية</th><th>الحالة</th><th>الإجراءات</th></tr></thead><tbody id="loan-rows"></tbody></table></div></div>`);

  const draw = () => {
    const term = document.getElementById('loan-search').value.trim().toLowerCase();
    const status = document.getElementById('loan-status').value;
    const filtered = loans.filter(loan => (!term || loan.borrower_name.toLowerCase().includes(term)) && (!status || loan.status === status));
    const body = document.getElementById('loan-rows');
    body.innerHTML = filtered.map(loan => `<tr><td><strong>${escapeHtml(loan.borrower_name)}</strong><span class="table-subtext">${loan.payment_count} عملية تسديد</span></td><td class="mono">${formatMoney(loan.principal_amount)}</td><td>${loan.months_total}</td><td class="mono">${formatMoney(loan.minimum_payment)}</td><td class="mono">${formatMoney(loan.paid_amount)}</td><td><strong class="mono">${formatMoney(loan.remaining_amount)}</strong></td><td><span class="loan-months">${loan.remaining_months}</span></td><td>${loanStatusBadge(loan)}</td><td>${loanActionButtons(loan)}</td></tr>`).join('') || `<tr><td colspan="9"><div class="empty"><div class="stat-icon">${icon('loan')}</div><h3>لا توجد قروض</h3><p>أضف أول قرض من الحقول الموجودة أعلى الصفحة.</p></div></td></tr>`;
    wireLoanActions(filtered);
  };
  document.getElementById('loan-search').addEventListener('input', draw);
  document.getElementById('loan-status').addEventListener('change', draw);
  const createForm = document.getElementById('loan-create-form');
  createForm?.addEventListener('submit', async event => {
    event.preventDefault();
    if (!createForm.reportValidity()) return;
    const form = new FormData(createForm);
    const button = document.getElementById('loan-create-save');
    const original = button.innerHTML;
    button.disabled = true;
    button.innerHTML = '<span class="loader"></span> جارٍ الإضافة';
    document.getElementById('loan-create-error').textContent = '';
    try {
      await api('/api/loans', {method:'POST', body:{
        borrower_name:form.get('borrower_name'),
        principal_amount:Number(form.get('principal_amount')),
        months_total:Number(form.get('months_total')),
        minimum_payment:Number(form.get('minimum_payment'))
      }});
      toast('تمت إضافة القرض', 'success');
      await renderLoans();
    } catch (err) {
      document.getElementById('loan-create-error').textContent = err.message;
      button.disabled = false;
      button.innerHTML = original;
    }
  });
  draw();
}

function openLoanForm(loan = null, onSaved = renderLoans) {
  const editing = Boolean(loan);
  const body = `<form id="loan-form" class="form-grid">
    <div class="form-row"><label>الاسم الثلاثي</label><input class="control" name="borrower_name" required minlength="3" maxlength="160" value="${escapeHtml(loan?.borrower_name || '')}" placeholder="الاسم الثلاثي للمقترض"></div>
    <div class="form-row"><label>المبلغ</label><input class="control" name="principal_amount" type="number" min="0.01" step="0.01" required value="${escapeHtml(loan?.principal_amount || '')}"></div>
    <div class="form-row"><label>عدد الأشهر</label><input class="control" name="months_total" type="number" min="1" max="600" step="1" required value="${escapeHtml(loan?.months_total || '')}"><span class="help">كل عملية تسديد تحسب شهراً واحداً، والتسديد الكامل يجعل الأشهر الباقية صفراً.</span></div>
    <div class="form-row"><label>المبلغ المحدد</label><input class="control" name="minimum_payment" type="number" min="0.01" step="0.01" required value="${escapeHtml(loan?.minimum_payment || '')}"><span class="help">لن يسمح النظام بتسديد مبلغ أقل من هذا الحد، باستثناء الدفعة النهائية إذا كان المتبقي أقل منه.</span></div>
    ${editing && loan.payment_count ? `<div class="lock-note">تم تسجيل ${loan.payment_count} عملية تسديد بقيمة ${formatMoney(loan.paid_amount)}. لا يمكن تخفيض مبلغ القرض عن المبلغ المسدد أو عدد الأشهر عن عدد عمليات التسديد.</div>` : ''}
    <div id="loan-form-error" class="error-text"></div>
  </form>`;
  showModal(editing ? 'تعديل القرض' : 'إنشاء قرض جديد', body, ['<button id="loan-form-cancel" class="btn btn-secondary">إلغاء</button>', `<button id="loan-form-save" class="btn btn-primary">${icon('save')} ${editing ? 'حفظ التعديل' : 'إنشاء القرض'}</button>`]);
  document.getElementById('loan-form-cancel').addEventListener('click', closeModal);
  document.getElementById('loan-form-save').addEventListener('click', async event => {
    const formEl = document.getElementById('loan-form');
    if (!formEl.reportValidity()) return;
    const form = new FormData(formEl);
    const button = event.currentTarget; const original = button.innerHTML;
    button.disabled = true; button.innerHTML = '<span class="loader"></span> جارٍ الحفظ';
    try {
      const payload = {borrower_name:form.get('borrower_name'), principal_amount:Number(form.get('principal_amount')), months_total:Number(form.get('months_total')), minimum_payment:Number(form.get('minimum_payment'))};
      await api(editing ? `/api/loans/${loan.id}` : '/api/loans', {method:editing ? 'PUT' : 'POST', body:payload});
      closeModal(); toast(editing ? 'تم تعديل القرض' : 'تم إنشاء القرض', 'success'); await onSaved();
    } catch (err) { document.getElementById('loan-form-error').textContent = err.message; button.disabled=false; button.innerHTML=original; }
  });
}

function openLoanPaymentModal(loan, onSaved = renderLoans) {
  if (!loan || loan.status === 'paid') return toast('تم تسديد هذا القرض بالكامل', 'error');
  const body = `<form id="loan-payment-form" class="form-grid">
    <div class="loan-payment-summary"><div><span>المقترض</span><strong>${escapeHtml(loan.borrower_name)}</strong></div><div><span>المبلغ المتبقي</span><strong>${formatMoney(loan.remaining_amount)}</strong></div><div><span>الأشهر الباقية</span><strong>${loan.remaining_months}</strong></div><div><span>المبلغ المحدد</span><strong>${formatMoney(loan.minimum_payment)}</strong></div></div>
    <div class="form-row"><label>مبلغ التسديد</label><input class="control" name="amount" type="number" min="0.01" max="${escapeHtml(loan.remaining_amount)}" step="0.01" required autofocus><span class="help">يجب ألا يقل عن ${formatMoney(loan.minimum_payment)} وألا يتجاوز ${formatMoney(loan.remaining_amount)}. إذا كان المتبقي النهائي أقل من الحد الأدنى فيسمح بتسديد المتبقي كاملاً.</span></div>
    <div class="form-row"><label>ملاحظة اختيارية</label><textarea class="control" name="notes" maxlength="1000" rows="3" placeholder="مثال: تسديد شهر آب"></textarea></div>
    <div id="loan-payment-error" class="error-text"></div>
  </form>`;
  showModal('تسديد القرض', body, ['<button id="loan-payment-cancel" class="btn btn-secondary">إلغاء</button>', `<button id="loan-payment-save" class="btn btn-primary">${icon('check')} تأكيد التسديد</button>`]);
  document.getElementById('loan-payment-cancel').addEventListener('click', closeModal);
  document.getElementById('loan-payment-save').addEventListener('click', async event => {
    const formEl = document.getElementById('loan-payment-form'); if (!formEl.reportValidity()) return;
    const form = new FormData(formEl); const button=event.currentTarget; const original=button.innerHTML;
    button.disabled=true; button.innerHTML='<span class="loader"></span> جارٍ التسديد';
    try {
      const updated = await api(`/api/loans/${loan.id}/payments`, {method:'POST', body:{amount:Number(form.get('amount')), notes:form.get('notes') || ''}});
      closeModal(); toast(`تم التسديد. المتبقي ${formatMoney(updated.remaining_amount)} والأشهر الباقية ${updated.remaining_months}`, 'success'); await onSaved();
    } catch (err) { document.getElementById('loan-payment-error').textContent=err.message; button.disabled=false; button.innerHTML=original; }
  });
}

function openLoanDeleteModal(loan, onDeleted = renderLoans) {
  showModal('حذف القرض نهائياً', `<div class="danger-box"><strong>سيتم حذف القرض وسجل جميع التسديدات نهائياً.</strong><p>${escapeHtml(loan.borrower_name)} — المتبقي ${formatMoney(loan.remaining_amount)}</p></div><div class="form-row"><label>اكتب «حذف نهائي» للتأكيد</label><input id="loan-delete-confirm" class="control" autocomplete="off"></div><div id="loan-delete-error" class="error-text"></div>`, ['<button id="loan-delete-cancel" class="btn btn-secondary">إلغاء</button>', `<button id="loan-delete-go" class="btn btn-danger">${icon('trash')} حذف نهائي</button>`]);
  document.getElementById('loan-delete-cancel').addEventListener('click', closeModal);
  document.getElementById('loan-delete-go').addEventListener('click', async event => {
    const button=event.currentTarget; const original=button.innerHTML; button.disabled=true; button.innerHTML='<span class="loader"></span> جارٍ الحذف';
    try { await api(`/api/loans/${loan.id}/permanent`, {method:'DELETE', body:{confirmation:document.getElementById('loan-delete-confirm').value}}); closeModal(); toast('تم حذف القرض نهائياً','success'); await onDeleted(); }
    catch(err){ document.getElementById('loan-delete-error').textContent=err.message; button.disabled=false; button.innerHTML=original; }
  });
}

async function renderLoanDetails(id) {
  pageLoading('تفاصيل القرض');
  const loan = await api(`/api/loans/${id}`);
  const canEdit = state.user.role !== 'viewer';
  const actions = `<a class="btn btn-secondary" href="#/loans">${icon('chevron')} رجوع للقروض</a><button id="loan-detail-report" class="btn btn-secondary">${icon('print')} تقرير</button>${canEdit && loan.status !== 'paid' ? `<button id="loan-detail-pay" class="btn btn-primary">${icon('check')} تسديد</button>` : ''}${canEdit ? `<button id="loan-detail-edit" class="btn btn-secondary">${icon('edit')} تعديل</button>` : ''}${state.user.role === 'admin' ? `<button id="loan-detail-delete" class="btn btn-danger-soft">${icon('trash')} حذف نهائي</button>` : ''}`;
  const payments = loan.payments || [];
  shell('تفاصيل القرض', `
    <div class="page-header"><div><span class="eyebrow">قروض</span><h1>${escapeHtml(loan.borrower_name)}</h1><p>${loanStatusBadge(loan)}</p></div><div class="page-actions">${actions}</div></div>
    <div class="loan-detail-grid">
      <section class="panel"><div class="panel-head"><div><h3>ملخص القرض</h3><p>القيم الحالية بعد آخر عملية تسديد.</p></div>${icon('loan')}</div><div class="loan-stat-grid">
        <div class="loan-stat"><span>مبلغ القرض</span><strong>${formatMoney(loan.principal_amount)}</strong></div><div class="loan-stat"><span>المبلغ المسدد</span><strong>${formatMoney(loan.paid_amount)}</strong></div><div class="loan-stat emphasis"><span>المبلغ المتبقي</span><strong>${formatMoney(loan.remaining_amount)}</strong></div><div class="loan-stat"><span>الأشهر الأصلية</span><strong>${loan.months_total}</strong></div><div class="loan-stat emphasis"><span>الأشهر الباقية</span><strong>${loan.remaining_months}</strong></div><div class="loan-stat"><span>المبلغ المحدد</span><strong>${formatMoney(loan.minimum_payment)}</strong></div>
      </div><div class="panel-body loan-meta"><span>أنشأه: <strong>${escapeHtml(loan.created_by_name || '-')}</strong></span><span>تاريخ الإنشاء: <strong>${formatDate(loan.created_at,true)}</strong></span><span>آخر تعديل: <strong>${formatDate(loan.updated_at,true)}</strong></span></div></section>
      <section class="panel"><div class="panel-head"><div><h3>سجل التسديدات</h3><p>${payments.length} عملية محفوظة.</p></div></div><div class="table-wrap"><table><thead><tr><th>#</th><th>مبلغ التسديد</th><th>المبلغ الباقي</th><th>الأشهر الباقية</th><th>المستخدم</th><th>التاريخ</th><th>ملاحظة</th></tr></thead><tbody>${payments.map((p,index)=>`<tr><td>${payments.length-index}</td><td><strong class="mono">${formatMoney(p.amount)}</strong></td><td class="mono">${formatMoney(p.remaining_amount_after)}</td><td>${p.months_remaining_after}</td><td>${escapeHtml(p.paid_by_name)}</td><td>${formatDate(p.paid_at,true)}</td><td>${escapeHtml(p.notes || '-')}</td></tr>`).join('') || `<tr><td colspan="7"><div class="empty">لم يتم تسجيل أي تسديد بعد.</div></td></tr>`}</tbody></table></div></section>
    </div>`);
  document.getElementById('loan-detail-report')?.addEventListener('click', () => openLoanReport(loan));
  document.getElementById('loan-detail-pay')?.addEventListener('click', () => openLoanPaymentModal(loan, () => renderLoanDetails(id)));
  document.getElementById('loan-detail-edit')?.addEventListener('click', () => openLoanForm(loan, () => renderLoanDetails(id)));
  document.getElementById('loan-detail-delete')?.addEventListener('click', () => openLoanDeleteModal(loan, () => navigate('/loans')));
}

async function renderUsers() {
  pageLoading('المستخدمون');
  const users = await api('/api/users');
  const activeUsers=users.filter(user => user.is_active).length;
  const renderRows=items => {
    const body=document.getElementById('user-rows');
    body.innerHTML=items.map(user => `<tr><td><strong>${escapeHtml(user.full_name)}</strong></td><td class="mono">${escapeHtml(user.username)}</td><td><span class="badge badge-${user.role}">${escapeHtml(roleLabel(user.role))}</span></td><td>${user.is_active ? '<span class="badge badge-saved">فعال</span>' : '<span class="badge badge-draft">موقوف</span>'}</td><td>${formatDate(user.last_login_at,true)}</td><td>${formatDate(user.created_at)}</td><td><div class="row-actions"><button type="button" class="btn btn-secondary row-action" data-edit-user="${user.id}" title="تعديل المستخدم">${icon('edit')}<span>تعديل</span></button></div></td></tr>`).join('') || `<tr><td colspan="7"><div class="empty">لا توجد نتائج.</div></td></tr>`;
    body.querySelectorAll('[data-edit-user]').forEach(btn => btn.addEventListener('click',() => openEditUserModal(users.find(u => u.id === Number(btn.dataset.editUser)))));
  };
  shell('المستخدمون', `<div class="page-header"><div><span class="eyebrow">إدارة النظام</span><h1>إدارة المستخدمين</h1><p>إنشاء الحسابات وتحديد الصلاحيات وحالة الوصول.</p></div><div class="page-actions"><button id="create-user" class="btn btn-primary">${icon('plus')} مستخدم جديد</button></div></div><div class="list-summary"><div class="summary-pill"><strong>${users.length}</strong><span>كل المستخدمين</span></div><div class="summary-pill"><strong>${activeUsers}</strong><span>فعال</span></div><div class="summary-pill"><strong>${users.length-activeUsers}</strong><span>موقوف</span></div></div><div class="panel"><div class="panel-head document-toolbar"><div class="search-box">${icon('search')}<input id="user-search" class="control" placeholder="بحث بالاسم أو اسم المستخدم..."></div></div><div class="table-wrap"><table><thead><tr><th>الاسم</th><th>اسم المستخدم</th><th>الصلاحية</th><th>الحالة</th><th>آخر دخول</th><th>الإنشاء</th><th>الإجراءات</th></tr></thead><tbody id="user-rows"></tbody></table></div></div>`);
  document.getElementById('create-user').addEventListener('click',openCreateUserModal);
  document.getElementById('user-search').addEventListener('input',event => { const term=event.target.value.trim().toLowerCase(); renderRows(users.filter(user => `${user.full_name} ${user.username} ${roleLabel(user.role)}`.toLowerCase().includes(term))); });
  renderRows(users);
}

function userFormHtml(user = null) {
  return `<form id="user-form" class="form-grid">
    <div class="form-row"><label>الاسم الكامل</label><input class="control" name="full_name" required minlength="2" value="${escapeHtml(user?.full_name || '')}"></div>
    ${user ? `<div class="form-row"><label>اسم المستخدم</label><input class="control" disabled value="${escapeHtml(user.username)}"></div>` : `<div class="form-row"><label>اسم المستخدم</label><input class="control" name="username" required pattern="[A-Za-z0-9_.-]+"></div>`}
    <div class="form-row"><label>${user ? 'كلمة مرور جديدة (اختياري)' : 'كلمة المرور'}</label><input class="control" type="password" name="password" ${user ? '' : 'required'} minlength="10"></div>
    <div class="form-row"><label>الصلاحية</label><select class="control" name="role"><option value="admin" ${user?.role === 'admin' ? 'selected' : ''}>مدير النظام</option><option value="editor" ${!user || user?.role === 'editor' ? 'selected' : ''}>محرر</option><option value="viewer" ${user?.role === 'viewer' ? 'selected' : ''}>مشاهد</option></select></div>
    ${user ? `<label class="check-item"><input type="checkbox" name="is_active" ${user.is_active ? 'checked' : ''}><span>الحساب فعال</span></label>` : ''}
    <div id="user-error" class="error-text"></div>
  </form>`;
}

function openCreateUserModal() {
  showModal('إنشاء مستخدم', userFormHtml(), ['<button id="user-cancel" class="btn btn-secondary">إلغاء</button>','<button id="user-save" class="btn btn-primary">حفظ المستخدم</button>']);
  document.getElementById('user-cancel').addEventListener('click', closeModal);
  document.getElementById('user-save').addEventListener('click', async () => {
    const formEl = document.getElementById('user-form');
    if (!formEl.reportValidity()) return;
    const form = new FormData(formEl);
    try {
      await api('/api/users', {method:'POST', body:{full_name:form.get('full_name'), username:form.get('username'), password:form.get('password'), role:form.get('role')}});
      closeModal(); toast('تم إنشاء المستخدم', 'success'); renderUsers();
    } catch (err) { document.getElementById('user-error').textContent = err.message; }
  });
}

function openEditUserModal(user) {
  showModal('تعديل المستخدم', userFormHtml(user), ['<button id="user-cancel" class="btn btn-secondary">إلغاء</button>','<button id="user-save" class="btn btn-primary">حفظ التعديلات</button>']);
  document.getElementById('user-cancel').addEventListener('click', closeModal);
  document.getElementById('user-save').addEventListener('click', async () => {
    const formEl = document.getElementById('user-form');
    if (!formEl.reportValidity()) return;
    const form = new FormData(formEl);
    try {
      await api(`/api/users/${user.id}`, {method:'PUT', body:{full_name:form.get('full_name'), role:form.get('role'), is_active:form.get('is_active') === 'on', password:form.get('password') || null}});
      closeModal(); toast('تم تحديث المستخدم', 'success'); renderUsers();
    } catch (err) { document.getElementById('user-error').textContent = err.message; }
  });
}

async function renderPermissions() {
  pageLoading('صلاحيات');
  const data = await api('/api/permissions');
  const pages = data.pages || [];
  const users = data.users || [];
  const renderRows = items => {
    const body = document.getElementById('permission-user-rows');
    body.innerHTML = items.map(user => {
      const allowed = user.role === 'admin' ? pages.length : (user.page_permissions || []).length;
      const access = user.role === 'admin'
        ? '<span class="badge badge-saved">كامل تلقائياً</span>'
        : `<span class="permission-count"><strong>${allowed}</strong> / ${pages.length}</span>`;
      return `<tr><td><strong>${escapeHtml(user.full_name)}</strong><span class="table-subtext mono">${escapeHtml(user.username)}</span></td><td><span class="badge badge-${user.role}">${escapeHtml(roleLabel(user.role))}</span></td><td>${user.is_active ? '<span class="badge badge-saved">فعال</span>' : '<span class="badge badge-draft">موقوف</span>'}</td><td>${access}</td><td><div class="row-actions"><button type="button" class="btn btn-secondary row-action" data-user-permissions="${user.id}">${icon('permissions')}<span>${user.role === 'admin' ? 'عرض' : 'إدارة'}</span></button></div></td></tr>`;
    }).join('') || `<tr><td colspan="5"><div class="empty">لا يوجد مستخدمون.</div></td></tr>`;
    body.querySelectorAll('[data-user-permissions]').forEach(button => {
      const user = users.find(item => item.id === Number(button.dataset.userPermissions));
      button.addEventListener('click', () => openPermissionsModal(user, pages));
    });
  };
  shell('صلاحيات', `
    <div class="page-header"><div><span class="eyebrow">إدارة النظام</span><h1>صلاحيات الصفحات</h1><p>حدد الصفحات التي يستطيع كل مستخدم رؤيتها. نوع الحساب يحدد ما إذا كان يستطيع التعديل أو المشاهدة فقط.</p></div></div>
    <div class="permission-info-grid"><div class="lock-note">${icon('permissions')} مدير النظام يرى جميع الصفحات دائماً ولا يمكن حجب صفحات الإدارة عنه.</div><div class="lock-note">${icon('eye')} إلغاء صفحة من المستخدم يخفيها من القائمة ويمنع الوصول إلى مستنداتها من واجهة النظام وواجهات API.</div></div>
    <div class="panel"><div class="panel-head document-toolbar"><div class="search-box">${icon('search')}<input id="permission-search" class="control" placeholder="بحث باسم المستخدم..."></div></div><div class="table-wrap"><table><thead><tr><th>المستخدم</th><th>نوع الحساب</th><th>الحالة</th><th>الصفحات المتاحة</th><th>الإجراءات</th></tr></thead><tbody id="permission-user-rows"></tbody></table></div></div>`);
  document.getElementById('permission-search').addEventListener('input', event => {
    const term = event.target.value.trim().toLowerCase();
    renderRows(users.filter(user => `${user.full_name} ${user.username} ${roleLabel(user.role)}`.toLowerCase().includes(term)));
  });
  renderRows(users);
}

function openPermissionsModal(user, pages) {
  if (!user) return;
  const admin = user.role === 'admin';
  const allowed = new Set(user.page_permissions || []);
  const options = pages.map(page => `<label class="permission-page-option ${admin || allowed.has(page.key) ? 'is-enabled' : ''}"><input type="checkbox" value="${escapeHtml(page.key)}" ${admin || allowed.has(page.key) ? 'checked' : ''} ${admin ? 'disabled' : ''}><span class="permission-page-icon">${page.key === 'dashboard' ? icon('dashboard') : page.key === 'loans' ? icon('loan') : icon('file')}</span><span><strong>${escapeHtml(page.name_ar)}</strong><small>${escapeHtml(page.category)}</small></span></label>`).join('');
  const footer = admin
    ? ['<button id="permissions-close" class="btn btn-primary">إغلاق</button>']
    : ['<button id="permissions-cancel" class="btn btn-secondary">إلغاء</button>', `<button id="permissions-save" class="btn btn-primary">${icon('save')} حفظ الصلاحيات</button>`];
  showModal(`صلاحيات ${user.full_name}`, `<div class="permissions-modal"><div class="lock-note">${admin ? 'هذا الحساب مدير نظام، لذلك يمتلك وصولاً كاملاً تلقائياً.' : `حدد الصفحات التي تريد أن تظهر للمستخدم «${escapeHtml(user.full_name)}».`}</div><div class="permission-page-grid">${options}</div></div>`, footer, 'modal-lg');
  modalRoot.querySelectorAll('.permission-page-option input').forEach(input => input.addEventListener('change', () => input.closest('.permission-page-option')?.classList.toggle('is-enabled', input.checked)));
  document.getElementById('permissions-close')?.addEventListener('click', closeModal);
  document.getElementById('permissions-cancel')?.addEventListener('click', closeModal);
  document.getElementById('permissions-save')?.addEventListener('click', async event => {
    const button = event.currentTarget;
    const original = button.innerHTML;
    const pageKeys = [...modalRoot.querySelectorAll('.permission-page-option input:checked')].map(input => input.value);
    button.disabled = true; button.innerHTML = '<span class="loader"></span> جارٍ الحفظ';
    try {
      await api(`/api/permissions/users/${user.id}`, {method:'PUT', body:{page_keys:pageKeys}});
      closeModal();
      toast('تم تحديث صلاحيات الصفحات', 'success');
      await renderPermissions();
    } catch (err) {
      toast(err.message, 'error');
      button.disabled = false; button.innerHTML = original;
    }
  });
}

async function renderAudit() {
  pageLoading('سجل العمليات');
  const logs = await api('/api/audit?limit=500');
  const actionNames = {
    'auth.login':'تسجيل دخول','auth.logout':'تسجيل خروج','auth.login_failed':'محاولة دخول فاشلة','auth.password_changed':'تغيير كلمة المرور','system.setup':'إعداد النظام',
    'document.create':'إنشاء مستند','document.update':'تعديل مستند','document.delete_permanent':'حذف مستند نهائياً','document.print_export':'طباعة/تصدير',
    'attachment.upload':'رفع مرفق','attachment.delete':'حذف مرفق','attachment.update':'تعديل مرفق','loan.create':'إنشاء قرض','loan.update':'تعديل قرض','loan.payment':'تسديد قرض','loan.delete_permanent':'حذف قرض نهائياً','user.create':'إنشاء مستخدم','user.update':'تعديل مستخدم','permission.update':'تعديل صلاحيات الصفحات','system.backup':'إنشاء نسخة احتياطية'
  };
  const categoryOf = action => action.startsWith('document.') ? 'documents' : action.startsWith('attachment.') ? 'attachments' : action.startsWith('loan.') ? 'loans' : (action.startsWith('user.') || action.startsWith('permission.')) ? 'users' : action.startsWith('auth.') ? 'auth' : 'system';
  const failedLogins = logs.filter(item => item.action === 'auth.login_failed').length;
  const permanentDeletes = logs.filter(item => item.action === 'document.delete_permanent' || item.action === 'loan.delete_permanent').length;
  const renderRows = items => {
    const body = document.getElementById('audit-rows');
    body.innerHTML = items.length ? items.map(log => `<tr><td>${formatDate(log.created_at, true)}</td><td>${escapeHtml(log.user_name || '-')}</td><td><strong>${escapeHtml(actionNames[log.action] || log.action)}</strong></td><td>${escapeHtml(log.entity_type)}</td><td class="mono">${escapeHtml(log.entity_id || '-')}</td><td><code class="audit-details">${escapeHtml(JSON.stringify(log.details))}</code></td></tr>`).join('') : `<tr><td colspan="6"><div class="empty"><div class="stat-icon">${icon('search')}</div><strong>لا توجد عمليات مطابقة</strong><p>غيّر البحث أو نوع العملية.</p></div></td></tr>`;
  };
  shell('سجل العمليات', `
    <div class="page-header"><div><span class="eyebrow">الرقابة والتدقيق</span><h1>سجل العمليات</h1><p>سجل فعلي لجميع عمليات الدخول والإنشاء والتعديل والطباعة والمرفقات والحذف النهائي.</p></div></div>
    <div class="list-summary"><div class="summary-pill"><strong>${logs.length}</strong><span>عملية مسجلة</span></div><div class="summary-pill"><strong>${failedLogins}</strong><span>محاولة دخول فاشلة</span></div><div class="summary-pill"><strong>${permanentDeletes}</strong><span>حذف نهائي</span></div></div>
    <div class="panel"><div class="document-toolbar"><div class="filters"><div class="search-box">${icon('search')}<input id="audit-search" class="control" placeholder="بحث بالمستخدم أو العملية أو المعرّف..."></div><select id="audit-category" class="control compact"><option value="">كل العمليات</option><option value="documents">المستندات</option><option value="attachments">المرفقات</option><option value="loans">القروض</option><option value="users">المستخدمون</option><option value="auth">الدخول والحساب</option><option value="system">النظام</option></select></div></div><div class="table-wrap"><table><thead><tr><th>التاريخ</th><th>المستخدم</th><th>العملية</th><th>النوع</th><th>المعرّف</th><th>التفاصيل</th></tr></thead><tbody id="audit-rows"></tbody></table></div></div>`);
  const applyFilters = () => {
    const term = document.getElementById('audit-search').value.trim().toLowerCase();
    const category = document.getElementById('audit-category').value;
    renderRows(logs.filter(log => {
      const matchesCategory = !category || categoryOf(log.action) === category;
      const haystack = `${log.user_name || ''} ${actionNames[log.action] || log.action} ${log.entity_type || ''} ${log.entity_id || ''} ${JSON.stringify(log.details || {})}`.toLowerCase();
      return matchesCategory && (!term || haystack.includes(term));
    }));
  };
  document.getElementById('audit-search').addEventListener('input', applyFilters);
  document.getElementById('audit-category').addEventListener('change', applyFilters);
  renderRows(logs);
}

async function renderReports() {
  pageLoading('التقارير والتصدير');
  const dashboard = await api('/api/dashboard');
  shell('التقارير والتصدير', `
    <div class="page-header"><div><span class="eyebrow">التقارير</span><h1>تصدير سجل المستندات</h1><p>أنشئ تقريراً فعلياً من قاعدة البيانات الحالية بصيغة CSV المتوافقة مع Microsoft Excel والعربية.</p></div></div>
    <div class="list-summary"><div class="summary-pill"><strong>${dashboard.total_documents}</strong><span>كل المستندات</span></div><div class="summary-pill"><strong>${dashboard.saved_documents || 0}</strong><span>محفوظ</span></div><div class="summary-pill"><strong>${dashboard.draft_documents || 0}</strong><span>مسودة</span></div><div class="summary-pill"><strong>${dashboard.total_attachments || 0}</strong><span>مرفق</span></div></div>
    <div class="settings-layout">
      <section class="panel"><div class="panel-head"><div><h3>معايير التقرير</h3><p>حدد البيانات التي تريد تضمينها، ثم نزّل الملف مرة واحدة.</p></div><div class="stat-icon">${icon('download')}</div></div><div class="panel-body"><div class="form-grid">
        <div class="form-row"><label>نوع المستند</label><select id="report-type" class="control"><option value="">جميع الأنواع</option>${state.types.map(t=>`<option value="${t.code}">${escapeHtml(t.name_ar)}</option>`).join('')}</select></div>
        <div class="form-row"><label>الحالة</label><select id="report-status" class="control"><option value="">جميع الحالات</option><option value="saved">محفوظ</option><option value="draft">مسودة</option></select></div>
        <div class="form-row"><label>بحث اختياري</label><input id="report-q" class="control" placeholder="رقم المستند أو أي بيانات داخله"></div>
      </div><div class="form-submit"><button id="export-csv" class="btn btn-primary btn-lg">${icon('download')} تنزيل التقرير</button></div></div></section>
      <aside class="panel"><div class="panel-head"><div><h3>محتوى التقرير</h3><p>يتم جلبه مباشرة من قاعدة البيانات.</p></div></div><div class="panel-body"><ul class="feature-list"><li>${icon('check')} رقم المستند والنوع والحالة</li><li>${icon('check')} المنشئ وتواريخ الإنشاء والتعديل</li><li>${icon('check')} عدد المرفقات ومرات الطباعة</li><li>${icon('check')} جميع القيم المكتوبة في حقول النموذج</li></ul><div class="lock-note" style="margin-top:16px">لا توجد بيانات تجريبية في التقرير؛ الملف يعكس السجلات الحقيقية المحفوظة في النظام.</div></div></aside>
    </div>`);
  document.getElementById('export-csv').addEventListener('click', async (event) => {
    const button=event.currentTarget; const original=button.innerHTML; button.disabled=true; button.innerHTML='<span class="loader"></span> جارٍ تجهيز التقرير';
    try {
      const params=new URLSearchParams();
      const type=document.getElementById('report-type').value; const status=document.getElementById('report-status').value; const q=document.getElementById('report-q').value.trim();
      if(type) params.set('type_code',type); if(status) params.set('status',status); if(q) params.set('q',q);
      const response=await api('/api/reports/documents.csv?'+params.toString()); const blob=await response.blob();
      const url=URL.createObjectURL(blob); const a=document.createElement('a'); a.href=url; a.download=`ziad-documents-${Date.now()}.csv`; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url); toast('تم تصدير التقرير بنجاح','success');
    } catch(err) { toast(err.message,'error'); } finally { button.disabled=false; button.innerHTML=original; }
  });
}

async function renderSettings() {
  pageLoading('الإعدادات والنسخ الاحتياطي');
  const status = await api('/api/system/status');
  const healthyTemplates = status.templates.filter(item => item.ok === true).length;
  const templateRows = status.templates.map(item => `<tr><td>${escapeHtml(item.filename)}</td><td>${escapeHtml(item.category || '-')}</td><td class="mono">${escapeHtml((item.sha256 || '').slice(0,16))}${item.sha256 ? '…' : ''}</td><td>${item.ok === true ? '<span class="badge badge-saved">سليم</span>' : '<span class="badge badge-draft">يحتاج تحقق</span>'}</td></tr>`).join('');
  shell('الإعدادات والنسخ الاحتياطي', `
    <div class="page-header"><div><span class="eyebrow">إدارة النظام</span><h1>صحة النظام والنسخ الاحتياطي</h1><p>راقب قاعدة البيانات والقوالب الرسمية، وأنشئ نسخة احتياطية كاملة من البيانات الحقيقية.</p></div><div class="page-actions"><button id="create-backup" class="btn btn-primary">${icon('download')} إنشاء نسخة احتياطية</button></div></div>
    <div class="stats-grid">
      <article class="stat-card"><div class="stat-top"><span>الإصدار</span><div class="stat-icon">${icon('settings')}</div></div><strong>${escapeHtml(status.version)}</strong><span>الإصدار العامل حالياً</span></article>
      <article class="stat-card"><div class="stat-top"><span>المستندات</span><div class="stat-icon">${icon('file')}</div></div><strong>${status.counts.documents}</strong><span>سجل محفوظ</span></article>
      <article class="stat-card"><div class="stat-top"><span>المرفقات</span><div class="stat-icon accent">${icon('attachment')}</div></div><strong>${status.counts.attachments}</strong><span>${formatBytes(status.attachment_bytes)}</span></article>
      <article class="stat-card"><div class="stat-top"><span>قاعدة البيانات</span><div class="stat-icon ${status.database.ok ? '' : 'warning'}">${status.database.ok ? icon('check') : icon('close')}</div></div><strong>${status.database.ok ? 'سليمة' : 'خطأ'}</strong><span>${escapeHtml(status.database.message)}</span></article>
    </div>
    <div class="settings-layout wide-main"><section class="panel"><div class="panel-head"><div><h3>سلامة القوالب الرسمية</h3><p>${healthyTemplates} من ${status.templates.length} ملفاً اجتاز التحقق بواسطة SHA-256.</p></div><span class="badge ${healthyTemplates === status.templates.length ? 'badge-saved' : 'badge-draft'}">${healthyTemplates}/${status.templates.length}</span></div><div class="table-wrap"><table><thead><tr><th>القالب</th><th>النوع</th><th>SHA-256</th><th>الحالة</th></tr></thead><tbody>${templateRows}</tbody></table></div></section>
      <aside class="panel"><div class="panel-head"><div><h3>محتوى النسخة</h3><p>نسخة واحدة متكاملة للاستعادة.</p></div></div><div class="panel-body"><ul class="feature-list"><li>${icon('check')} قاعدة البيانات</li><li>${icon('check')} جميع المرفقات</li><li>${icon('check')} ملفات PDF الرسمية</li><li>${icon('check')} قوالب Word الأصلية</li><li>${icon('check')} خريطة الحقول والبصمات</li></ul><div class="lock-note" style="margin-top:16px">كلمات المرور لا تُحفظ كنص واضح؛ تبقى القيم المشفرة فقط داخل قاعدة البيانات.</div></div></aside>
    </div>`);
  document.getElementById('create-backup').addEventListener('click', async (event) => {
    const button = event.currentTarget; const original = button.innerHTML;
    button.disabled = true; button.innerHTML = '<span class="loader"></span> جارٍ تجهيز النسخة';
    try {
      const response = await api('/api/system/backup', {method:'POST'});
      const blob = await response.blob();
      const disposition = response.headers.get('content-disposition') || '';
      const match = disposition.match(/filename="?([^";]+)"?/i);
      const filename = match ? match[1] : `ziad-invoices-backup-${Date.now()}.zip`;
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a'); link.href = url; link.download = filename; document.body.appendChild(link); link.click(); link.remove(); URL.revokeObjectURL(url);
      toast('تم إنشاء النسخة الاحتياطية بنجاح', 'success');
    } catch (err) { toast(err.message, 'error'); }
    finally { button.disabled = false; button.innerHTML = original; }
  });
}

async function renderNoAccess() {
  shell('لا توجد صفحات متاحة', `<div class="panel"><div class="empty"><div class="stat-icon">${icon('lock')}</div><h3>لا توجد صفحات مفعلة لهذا الحساب</h3><p>راجع مدير النظام ليمنحك الصلاحية من صفحة «صلاحيات».</p></div></div>`);
}

async function route() {
  if (!state.user) return;
  try {
    await ensureTypes();
    const path = location.hash.replace(/^#/, '') || firstAllowedRoute();
    if (path === '/no-access') return renderNoAccess();
    if (path === '/dashboard') {
      if (canViewPage('dashboard')) return renderDashboard();
      return navigate(firstAllowedRoute());
    }
    if (path === '/loans') { if (canViewPage('loans')) return renderLoans(); return navigate(firstAllowedRoute()); }
    let loanReportMatch = path.match(/^\/loans\/(\d+)\/report$/);
    if (loanReportMatch) { if (canViewPage('loans')) return renderLoanReport(Number(loanReportMatch[1])); return navigate(firstAllowedRoute()); }
    let loanMatch = path.match(/^\/loans\/(\d+)$/);
    if (loanMatch) { if (canViewPage('loans')) return renderLoanDetails(Number(loanMatch[1])); return navigate(firstAllowedRoute()); }
    if (path === '/users' && state.user.role === 'admin') return renderUsers();
    if (path === '/permissions' && state.user.role === 'admin') return renderPermissions();
    if (path === '/reports' && state.user.role === 'admin') return renderReports();
    if (path === '/audit' && state.user.role === 'admin') return renderAudit();
    if (path === '/settings' && state.user.role === 'admin') return renderSettings();
    let match = path.match(/^\/documents\/([A-Z0-9_-]{2,8})$/i);
    if (match) {
      const code = match[1].toUpperCase();
      if (state.types.some(type => type.code === code)) return renderDocumentList(code);
      return navigate(firstAllowedRoute());
    }
    match = path.match(/^\/documents\/new\/([A-Z0-9_-]{2,8})$/i);
    if (match) {
      const code = match[1].toUpperCase();
      if (state.types.some(type => type.code === code)) return createNewDocument(code);
      return navigate(firstAllowedRoute());
    }
    match = path.match(/^\/documents\/(\d+)\/(view|edit)$/);
    if (match) return renderDocumentEditor(Number(match[1]), match[2]);
    navigate(firstAllowedRoute());
  } catch (err) {
    toast(err.message || 'حدث خطأ غير متوقع', 'error');
    shell('خطأ', `<div class="panel"><div class="empty"><h3>تعذر تحميل الصفحة</h3><p>${escapeHtml(err.message || '')}</p><button class="btn btn-primary" onclick="location.reload()">إعادة المحاولة</button></div></div>`);
  }
}

async function bootstrap() {
  try {
    const setup = await api('/api/setup/status');
    if (setup.needs_setup) return renderSetup();
    if (!state.token) return renderLogin();
    try {
      state.user = await api('/api/auth/me');
      await ensureTypes();
      if (!location.hash) location.hash = firstAllowedRoute();
      else route();
    } catch (_) {
      state.token = ''; state.user = null; state.types = []; state.counts = {}; localStorage.removeItem('ziad_token'); renderLogin();
    }
  } catch (err) {
    root.innerHTML = `<main class="auth-shell" style="grid-template-columns:1fr"><section class="auth-panel"><h2>تعذر تشغيل النظام</h2><p>${escapeHtml(err.message)}</p><button class="btn btn-primary" onclick="location.reload()">إعادة المحاولة</button></section></main>`;
  }
}

window.addEventListener('hashchange', route);
window.addEventListener('beforeunload', (event) => {
  if (state.dirty) { event.preventDefault(); event.returnValue = ''; }
});
bootstrap();
