-- BlueprintOS schema v2: Audity client work tables (projects, leads).
-- Apply once via Supabase Dashboard, SQL Editor, paste, Run.
-- Extends schema.sql; safe to run on an existing database (create if not exists).
-- After applying, ob-nucleus mirror sync populates these from listProjects and listLeads.

create table if not exists public.audity_projects (
  id text primary key,
  client_name text,
  status text,                   -- setup | interviews | analysis | ...
  industry text,
  company_size text,
  description text,
  currency text,
  created_at timestamptz,
  updated_at timestamptz,
  raw jsonb,
  synced_at timestamptz default now()
);
comment on table public.audity_projects is 'Read-only mirror of Audity projects (active audit and client work). Source of truth: Audity.';

create table if not exists public.audity_leads (
  id text primary key,
  business_name text,
  client_name text,
  client_email text,
  ai_readiness_score numeric,
  composite_score numeric,
  status text,                   -- pending | completed | converted
  converted_to_audit_id text,    -- the ONLY reliable conversion flag
  conversion_timestamp timestamptz,  -- NOT a conversion marker; populated on unconverted leads
  source text,
  created_at timestamptz,
  updated_at timestamptz,
  raw jsonb,
  synced_at timestamptz default now()
);
comment on table public.audity_leads is 'Read-only mirror of Audity leads. convertedToAuditId is the only reliable conversion flag (verified live 2026-06-07).';

create index if not exists idx_projects_status on public.audity_projects (status);
create index if not exists idx_leads_status on public.audity_leads (status);
create index if not exists idx_leads_readiness on public.audity_leads (ai_readiness_score desc);
create index if not exists idx_leads_unconverted on public.audity_leads (converted_to_audit_id) where converted_to_audit_id is null;

alter table public.audity_projects enable row level security;
alter table public.audity_leads enable row level security;
