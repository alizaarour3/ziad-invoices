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
function roleLabel(role) { return ({admin:'مدير النظام', editor:'محرر', viewer:'مشاهد'})[role] || role; }
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
          <p>اكتب مباشرة على مستندات القبض وطلبات الصرف ومستندات الدفع، ثم احفظها وعدّلها واطبعها مع مرفقاتها دون تغيير أي تفصيل في القالب الأصلي.</p>
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
      localStorage.setItem('ziad_token', data.token);
      navigate('/dashboard');
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
  const user = state.user || {};
  const adminLinks = user.role === 'admin' ? `
    <div class="nav-label">الإدارة</div>
    <a class="nav-item ${activePath('/users')}" href="#/users" title="المستخدمون">${icon('users')}<span>المستخدمون</span></a>
    <a class="nav-item ${activePath('/reports')}" href="#/reports" title="التقارير والتصدير">${icon('download')}<span>التقارير والتصدير</span></a>
    <a class="nav-item ${activePath('/audit')}" href="#/audit" title="سجل العمليات">${icon('audit')}<span>سجل العمليات</span></a>
    <a class="nav-item ${activePath('/settings')}" href="#/settings" title="الإعدادات والنسخ">${icon('settings')}<span>الإعدادات والنسخ</span></a>` : '';
  const typeLinks = state.types.map(type => `
    <a class="nav-item ${active === type.code ? 'active' : ''}" href="#/documents/${type.code}" title="${escapeHtml(type.name_ar)}">${icon('file')}<span>${escapeHtml(type.name_ar)}</span><span class="nav-badge">${state.counts[type.code] ?? ''}</span></a>
  `).join('');
  root.innerHTML = `
    <div class="app-shell ${state.sidebarCollapsed ? 'sidebar-collapsed' : ''}" id="app-shell">
      <div class="sidebar-backdrop" id="sidebar-backdrop"></div>
      <aside class="sidebar" id="sidebar">
        <div class="sidebar-head">
          <div class="brand"><div class="brand-mark">ZD</div><div class="brand-text"><strong>نظام المستندات</strong><span>الإصدار 3.3.4</span></div></div>
          <button id="sidebar-close" class="btn btn-icon btn-link sidebar-close" aria-label="إغلاق القائمة">${icon('close')}</button>
        </div>
        <nav class="sidebar-nav">
          <a class="nav-item ${activePath('/dashboard')}" href="#/dashboard" title="الداشبورد">${icon('dashboard')}<span>الداشبورد</span></a>
          <div class="nav-label">النماذج</div>
          ${typeLinks}${adminLinks}
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
  });
  document.getElementById('sidebar-close').addEventListener('click', closeMobileSidebar);
  document.getElementById('sidebar-backdrop').addEventListener('click', closeMobileSidebar);
  appShell.querySelectorAll('.sidebar a').forEach(link => link.addEventListener('click', () => { if (mobileQuery.matches) closeMobileSidebar(); }));
}

async function doLogout() {
  try { await api('/api/auth/logout', {method:'POST'}); } catch (_) {}
  state.token = ''; state.user = null; localStorage.removeItem('ziad_token');
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
  state.counts = Object.fromEntries(data.types.map(t => [t.code, t.count]));
  const weekly = data.weekly_activity || [];
  const maxActivity = Math.max(1, ...weekly.map(item => item.count));
  const activityBars = weekly.map(item => `<div class="activity-column" title="${escapeHtml(item.date)}: ${item.count}"><div class="activity-value">${item.count}</div><div class="activity-track"><span style="height:${Math.max(5, Math.round(item.count / maxActivity * 100))}%"></span></div><small>${escapeHtml(item.label)}</small></div>`).join('');
  const typeCards = data.types.map(type => `<a class="type-overview-card" href="#/documents/${type.code}"><div class="type-overview-icon">${icon('file')}</div><div class="type-overview-copy"><strong>${escapeHtml(type.name_ar)}</strong><span>${type.saved_count || 0} محفوظ · ${type.draft_count || 0} مسودة</span></div><div class="type-overview-count">${type.count}</div>${icon('chevron')}</a>`).join('');
  const recentRows = data.recent.length ? data.recent.map(doc => `<tr><td class="mono"><strong>${escapeHtml(doc.document_number)}</strong></td><td>${escapeHtml(doc.type.name_ar)}</td><td>${escapeHtml(doc.fields[doc.type.config.list_primary_field] || '-')}</td><td>${statusBadge(doc.status)}</td><td>${formatDate(doc.updated_at, true)}</td><td>${documentActionButtons(doc)}</td></tr>`).join('') : `<tr><td colspan="6"><div class="empty">لا توجد مستندات حتى الآن.</div></td></tr>`;
  const createAction = state.user.role !== 'viewer' ? `<button id="dashboard-create" class="btn btn-primary">${icon('plus')} إنشاء مستند</button>` : '';
  shell('الداشبورد', `
    <div class="page-header dashboard-header"><div><span class="eyebrow">مساحة العمل</span><h1>مرحباً، ${escapeHtml(state.user.full_name)}</h1><p>نظرة واضحة على المستندات وحالة العمل اليوم.</p></div><div class="page-actions">${createAction}</div></div>
    <div class="cards dashboard-cards">
      <article class="stat-card"><div class="stat-top"><span>جميع المستندات</span><div class="stat-icon">${icon('dashboard')}</div></div><strong>${data.total_documents}</strong><span>${data.today_documents} أُنشئت اليوم</span></article>
      <article class="stat-card"><div class="stat-top"><span>المستندات المحفوظة</span><div class="stat-icon">${icon('save')}</div></div><strong>${data.saved_documents || 0}</strong><span>جاهزة للمشاهدة والطباعة</span></article>
      <article class="stat-card"><div class="stat-top"><span>المسودات</span><div class="stat-icon warning">${icon('draft')}</div></div><strong>${data.draft_documents || 0}</strong><span>تحتاج إلى استكمال</span></article>
      <article class="stat-card"><div class="stat-top"><span>المرفقات</span><div class="stat-icon accent">${icon('attachment')}</div></div><strong>${data.total_attachments}</strong><span>${data.printed_total || 0} عملية طباعة</span></article>
    </div>
    <section class="dashboard-section"><div class="section-heading"><div><h2>الأقسام</h2><p>ادخل إلى كل نموذج وجميع المستندات المحفوظة فيه.</p></div></div><div class="type-overview-grid">${typeCards}</div></section>
    <div class="dashboard-grid dashboard-grid-balanced">
      <div class="panel"><div class="panel-head"><div><h2>آخر المستندات</h2><p>آخر التعديلات في جميع الأقسام.</p></div></div><div class="table-wrap"><table><thead><tr><th>الرقم</th><th>النموذج</th><th>الاسم/الجهة</th><th>الحالة</th><th>آخر تعديل</th><th>الإجراءات</th></tr></thead><tbody>${recentRows}</tbody></table></div></div>
      <div class="panel activity-panel"><div class="panel-head"><div><h2>نشاط آخر 7 أيام</h2><p>عدد المستندات الجديدة يومياً.</p></div><div class="stat-icon">${icon('chart')}</div></div><div class="panel-body"><div class="activity-chart">${activityBars}</div><div class="activity-summary"><span>اليوم</span><strong>${data.today_documents}</strong><span>إجمالي الطباعة</span><strong>${data.printed_total || 0}</strong></div></div></div>
    </div>`);
  document.getElementById('dashboard-create')?.addEventListener('click', openCreateMenu);
  wireDocumentActions(root);
}

async function renderDocumentList(code) {
  const type = state.types.find(item => item.code === code);
  if (!type) return navigate('/dashboard');
  pageLoading(type.name_ar);
  const documents = await api(`/api/documents?type_code=${encodeURIComponent(code)}&limit=500`);
  state.counts[code] = documents.length;
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

async function renderDocumentEditor(id, mode) {
  pageLoading(mode === 'view' ? 'عرض المستند' : 'تعديل المستند');
  const doc = await api(`/api/documents/${id}`);
  state.currentDocument = doc;
  state.dirty = false;
  const viewOnly = mode === 'view' || state.user.role === 'viewer';
  const fields = doc.type.config.fields.map(field => fieldHtml(field, doc.fields[field.key], viewOnly)).join('');
  const attachments = attachmentsHtml(doc.attachments || [], viewOnly);
  const primaryAction = viewOnly ? (state.user.role !== 'viewer' ? `<button id="edit-document" class="btn btn-primary">${icon('edit')} تعديل</button>` : '') : `<select id="document-status" class="control compact status-control"><option value="saved" ${doc.status === 'saved' ? 'selected' : ''}>محفوظ</option><option value="draft" ${doc.status === 'draft' ? 'selected' : ''}>مسودة</option></select><button id="save-document" class="btn btn-primary">${icon('save')} حفظ</button>`;
  const deleteAction = state.user.role === 'admin' ? `<button type="button" class="btn btn-danger-soft" id="delete-document" title="حذف المستند نهائياً">${icon('trash')}<span>حذف نهائي</span></button>` : '';
  shell(`${viewOnly ? 'عرض' : 'تعديل'} ${doc.type.name_ar}`, `
    <div class="page-header document-header"><div><span class="eyebrow">${escapeHtml(doc.type.name_ar)}</span><h1>${escapeHtml(doc.document_number)}</h1><p>الكتابة في طبقة مستقلة، والقالب الرسمي يبقى دون تعديل.</p></div><div class="page-actions"><a class="btn btn-secondary" href="#/documents/${doc.type.code}">${icon('chevron')} رجوع للقائمة</a></div></div>
    <div class="document-commandbar"><div class="commandbar-primary">${primaryAction}<button id="print-document" class="btn btn-secondary">${icon('print')} طباعة</button></div><div class="commandbar-secondary">${!viewOnly ? `<label class="field-guide-toggle"><input id="field-guide" type="checkbox" checked><span>إظهار حدود الكتابة</span></label>` : ''}${deleteAction}</div></div>
    <div class="editor-grid"><div class="editor-stage"><div id="template-page" class="template-page ${viewOnly ? 'view-only clean' : ''}"><img class="template-bg" src="${doc.type.image_url}" alt="${escapeHtml(doc.type.name_ar)}">${fields}</div></div><aside class="editor-side">
      <section class="panel"><div class="panel-head"><h3>معلومات المستند</h3>${statusBadge(doc.status)}</div><div class="panel-body"><div class="lock-note">${icon('lock')} القالب الرسمي محفوظ كما هو، ولا يتم تعديل أي صورة أو خط أو نقطة داخله.</div><div class="meta-list" style="margin-top:14px"><div class="meta-row"><span>أنشأه</span><strong>${escapeHtml(doc.created_by_name)}</strong></div><div class="meta-row"><span>آخر تعديل</span><strong>${escapeHtml(doc.updated_by_name)}</strong></div><div class="meta-row"><span>تاريخ الإنشاء</span><strong>${formatDate(doc.created_at, true)}</strong></div><div class="meta-row"><span>الإصدار</span><strong>${doc.revision}</strong></div><div class="meta-row"><span>مرات الطباعة</span><strong>${doc.print_count}</strong></div></div></div></section>
      <section class="panel attachments-panel"><div class="panel-head"><div><h3>المرفقات</h3><p>${doc.attachments.length} ملف مرتبط</p></div><span class="badge badge-saved">${doc.attachments.length}</span></div><div class="panel-body">${!viewOnly ? `<div class="attachment-uploader" id="attachment-dropzone"><input id="attachment-input" type="file" multiple hidden><div class="attachment-uploader-icon">${icon('upload')}</div><div class="attachment-uploader-copy"><strong>إضافة مرفقات</strong><span>اسحب الملفات إلى هذه المساحة</span><small>PDF، Word، Excel والصور · حتى 100MB</small></div><button type="button" class="btn btn-primary attachment-browse" id="attachment-browse">اختيار ملفات</button></div><div id="attachment-upload-status" class="attachment-upload-status" hidden></div>` : ''}<div class="attachment-list-head"><span>الملفات المحفوظة</span></div><div class="attachments" id="attachments-list">${attachments}</div></div></section>
    </aside></div>`, {active:doc.type.code, fullWidth:true});
  const page = document.getElementById('template-page');
  requestAnimationFrame(() => applyTemplateScale(page));
  if (window.ResizeObserver) { const observer = new ResizeObserver(() => applyTemplateScale(page)); observer.observe(page); }
  else window.addEventListener('resize', () => applyTemplateScale(page), {passive:true});
  document.getElementById('field-guide')?.addEventListener('change', event => page.classList.toggle('clean', !event.target.checked));
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

async function renderAudit() {
  pageLoading('سجل العمليات');
  const logs = await api('/api/audit?limit=500');
  const actionNames = {
    'auth.login':'تسجيل دخول','auth.logout':'تسجيل خروج','auth.login_failed':'محاولة دخول فاشلة','auth.password_changed':'تغيير كلمة المرور','system.setup':'إعداد النظام',
    'document.create':'إنشاء مستند','document.update':'تعديل مستند','document.delete_permanent':'حذف مستند نهائياً','document.print_export':'طباعة/تصدير',
    'attachment.upload':'رفع مرفق','attachment.delete':'حذف مرفق','attachment.update':'تعديل مرفق','user.create':'إنشاء مستخدم','user.update':'تعديل مستخدم','system.backup':'إنشاء نسخة احتياطية'
  };
  const categoryOf = action => action.startsWith('document.') ? 'documents' : action.startsWith('attachment.') ? 'attachments' : action.startsWith('user.') ? 'users' : action.startsWith('auth.') ? 'auth' : 'system';
  const failedLogins = logs.filter(item => item.action === 'auth.login_failed').length;
  const permanentDeletes = logs.filter(item => item.action === 'document.delete_permanent').length;
  const renderRows = items => {
    const body = document.getElementById('audit-rows');
    body.innerHTML = items.length ? items.map(log => `<tr><td>${formatDate(log.created_at, true)}</td><td>${escapeHtml(log.user_name || '-')}</td><td><strong>${escapeHtml(actionNames[log.action] || log.action)}</strong></td><td>${escapeHtml(log.entity_type)}</td><td class="mono">${escapeHtml(log.entity_id || '-')}</td><td><code class="audit-details">${escapeHtml(JSON.stringify(log.details))}</code></td></tr>`).join('') : `<tr><td colspan="6"><div class="empty"><div class="stat-icon">${icon('search')}</div><strong>لا توجد عمليات مطابقة</strong><p>غيّر البحث أو نوع العملية.</p></div></td></tr>`;
  };
  shell('سجل العمليات', `
    <div class="page-header"><div><span class="eyebrow">الرقابة والتدقيق</span><h1>سجل العمليات</h1><p>سجل فعلي لجميع عمليات الدخول والإنشاء والتعديل والطباعة والمرفقات والحذف النهائي.</p></div></div>
    <div class="list-summary"><div class="summary-pill"><strong>${logs.length}</strong><span>عملية مسجلة</span></div><div class="summary-pill"><strong>${failedLogins}</strong><span>محاولة دخول فاشلة</span></div><div class="summary-pill"><strong>${permanentDeletes}</strong><span>حذف نهائي</span></div></div>
    <div class="panel"><div class="document-toolbar"><div class="filters"><div class="search-box">${icon('search')}<input id="audit-search" class="control" placeholder="بحث بالمستخدم أو العملية أو المعرّف..."></div><select id="audit-category" class="control compact"><option value="">كل العمليات</option><option value="documents">المستندات</option><option value="attachments">المرفقات</option><option value="users">المستخدمون</option><option value="auth">الدخول والحساب</option><option value="system">النظام</option></select></div></div><div class="table-wrap"><table><thead><tr><th>التاريخ</th><th>المستخدم</th><th>العملية</th><th>النوع</th><th>المعرّف</th><th>التفاصيل</th></tr></thead><tbody id="audit-rows"></tbody></table></div></div>`);
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

async function route() {
  if (!state.user) return;
  try {
    await ensureTypes();
    const path = location.hash.replace(/^#/, '') || '/dashboard';
    if (path === '/dashboard') return renderDashboard();
    if (path === '/users' && state.user.role === 'admin') return renderUsers();
    if (path === '/reports' && state.user.role === 'admin') return renderReports();
    if (path === '/audit' && state.user.role === 'admin') return renderAudit();
    if (path === '/settings' && state.user.role === 'admin') return renderSettings();
    let match = path.match(/^\/documents\/(RV|PR|PV|VM)$/);
    if (match) return renderDocumentList(match[1]);
    match = path.match(/^\/documents\/new\/(RV|PR|PV|VM)$/);
    if (match) return createNewDocument(match[1]);
    match = path.match(/^\/documents\/(\d+)\/(view|edit)$/);
    if (match) return renderDocumentEditor(Number(match[1]), match[2]);
    navigate('/dashboard');
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
      if (!location.hash) location.hash = '/dashboard';
      else route();
    } catch (_) {
      state.token = ''; localStorage.removeItem('ziad_token'); renderLogin();
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
