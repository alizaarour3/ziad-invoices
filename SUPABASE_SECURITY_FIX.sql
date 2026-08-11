-- Ziad Invoices Professional v3.3.16
-- One-time Supabase hardening for an existing production database.
-- This application uses its FastAPI backend for database access; browser roles do not
-- need direct access to these tables through the Supabase Data API.

begin;

do $$
declare
  table_name text;
begin
  foreach table_name in array array[
    'schema_meta',
    'users',
    'sessions',
    'user_page_permissions',
    'document_types',
    'number_sequences',
    'documents',
    'document_revisions',
    'attachments',
    'loans',
    'loan_payments',
    'audit_logs',
    'settings'
  ]
  loop
    if to_regclass(format('public.%I', table_name)) is not null then
      execute format('alter table public.%I enable row level security', table_name);
      execute format('revoke all privileges on table public.%I from anon, authenticated', table_name);
    end if;
  end loop;
end $$;

revoke usage, select on all sequences in schema public from anon, authenticated;

-- Keep future tables/sequences created by the postgres owner private from browser roles.
alter default privileges for role postgres in schema public
  revoke select, insert, update, delete on tables from anon, authenticated;
alter default privileges for role postgres in schema public
  revoke usage, select on sequences from anon, authenticated;

commit;

-- Verification 1: every application table below should show rls_enabled = true.
select
  c.relname as table_name,
  c.relrowsecurity as rls_enabled
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public'
  and c.relkind = 'r'
  and c.relname in (
    'schema_meta','users','sessions','user_page_permissions','document_types',
    'number_sequences','documents','document_revisions','attachments','loans',
    'loan_payments','audit_logs','settings'
  )
order by c.relname;

-- Verification 2: this should return zero rows for anon/authenticated on app tables.
select grantee, table_name, privilege_type
from information_schema.role_table_grants
where table_schema = 'public'
  and grantee in ('anon','authenticated')
  and table_name in (
    'schema_meta','users','sessions','user_page_permissions','document_types',
    'number_sequences','documents','document_revisions','attachments','loans',
    'loan_payments','audit_logs','settings'
  )
order by grantee, table_name, privilege_type;
