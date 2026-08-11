-- Optional manual bootstrap for Ziad Invoices Professional 3.3.11.
-- The application creates the same schema automatically on startup.

create table if not exists public.schema_meta (
  key text primary key,
  value text not null
);

create table if not exists public.users (
  id bigserial primary key,
  full_name text not null,
  username text not null unique,
  password_salt text not null,
  password_hash text not null,
  role text not null check (role in ('admin','editor','viewer')),
  is_active integer not null default 1 check (is_active in (0,1)),
  must_change_password integer not null default 0 check (must_change_password in (0,1)),
  created_at text not null,
  updated_at text not null,
  last_login_at text,
  failed_login_count integer not null default 0,
  locked_until text
);
create unique index if not exists idx_users_username_lower on public.users ((lower(username)));

create table if not exists public.sessions (
  token_hash text primary key,
  user_id bigint not null references public.users(id) on delete cascade,
  expires_at text not null,
  created_at text not null
);
create index if not exists idx_sessions_user_id on public.sessions(user_id);
create index if not exists idx_sessions_expires_at on public.sessions(expires_at);


create table if not exists public.user_page_permissions (
  user_id bigint not null references public.users(id) on delete cascade,
  page_key text not null,
  can_view integer not null default 1 check (can_view in (0,1)),
  updated_at text not null,
  updated_by bigint references public.users(id) on delete set null,
  primary key(user_id, page_key)
);
create index if not exists idx_user_page_permissions_page on public.user_page_permissions(page_key, can_view);

create table if not exists public.document_types (
  id bigserial primary key,
  code text not null unique,
  name_ar text not null,
  name_en text not null,
  prefix text not null,
  image_filename text not null,
  docx_filename text not null,
  config_json text not null,
  is_active integer not null default 1 check (is_active in (0,1))
);

create table if not exists public.number_sequences (
  document_type_id bigint primary key references public.document_types(id) on delete cascade,
  next_value bigint not null default 1 check (next_value > 0)
);

create table if not exists public.documents (
  id bigserial primary key,
  document_type_id bigint not null references public.document_types(id),
  document_number text not null unique,
  status text not null default 'saved' check (status in ('draft','saved')),
  field_values_json text not null,
  created_by bigint not null references public.users(id),
  updated_by bigint not null references public.users(id),
  created_at text not null,
  updated_at text not null,
  print_count integer not null default 0,
  revision integer not null default 1
);
create index if not exists idx_documents_type on public.documents(document_type_id);
create index if not exists idx_documents_created_at on public.documents(created_at desc);
create index if not exists idx_documents_number on public.documents(document_number);

create table if not exists public.document_revisions (
  id bigserial primary key,
  document_id bigint not null references public.documents(id) on delete cascade,
  revision integer not null,
  field_values_json text not null,
  changed_by bigint not null references public.users(id),
  changed_at text not null,
  unique(document_id, revision)
);

create table if not exists public.attachments (
  id bigserial primary key,
  document_id bigint not null references public.documents(id) on delete cascade,
  original_name text not null,
  stored_name text not null unique,
  mime_type text not null,
  size_bytes bigint not null,
  sha256 text not null,
  notes text not null default '',
  print_order integer not null default 0,
  uploaded_by bigint not null references public.users(id),
  created_at text not null
);
create index if not exists idx_attachments_document on public.attachments(document_id, print_order, id);


create table if not exists public.loans (
  id bigserial primary key,
  borrower_name text not null,
  principal_amount_minor bigint not null check (principal_amount_minor > 0),
  months_total integer not null check (months_total > 0),
  minimum_payment_minor bigint not null check (minimum_payment_minor > 0),
  remaining_amount_minor bigint not null check (remaining_amount_minor >= 0),
  created_by bigint not null references public.users(id),
  updated_by bigint not null references public.users(id),
  created_at text not null,
  updated_at text not null
);
create index if not exists idx_loans_borrower_name on public.loans(borrower_name);
create index if not exists idx_loans_remaining on public.loans(remaining_amount_minor);
create index if not exists idx_loans_updated_at on public.loans(updated_at desc);

create table if not exists public.loan_payments (
  id bigserial primary key,
  loan_id bigint not null references public.loans(id) on delete cascade,
  amount_minor bigint not null check (amount_minor > 0),
  remaining_amount_minor_after bigint not null check (remaining_amount_minor_after >= 0),
  months_remaining_after integer not null check (months_remaining_after >= 0),
  notes text not null default '',
  paid_by bigint not null references public.users(id),
  paid_at text not null
);
create index if not exists idx_loan_payments_loan on public.loan_payments(loan_id, id);
create index if not exists idx_loan_payments_paid_at on public.loan_payments(paid_at desc);

create table if not exists public.audit_logs (
  id bigserial primary key,
  user_id bigint references public.users(id) on delete set null,
  action text not null,
  entity_type text not null,
  entity_id text,
  details_json text not null default '{}',
  created_at text not null
);
create index if not exists idx_audit_created_at on public.audit_logs(created_at desc);
create index if not exists idx_audit_entity on public.audit_logs(entity_type, entity_id);

create table if not exists public.settings (
  key text primary key,
  value_json text not null,
  updated_at text not null
);

insert into storage.buckets (id, name, public)
values ('ziad-invoices', 'ziad-invoices', false)
on conflict (id) do nothing;
