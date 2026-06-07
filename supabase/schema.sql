-- BlueprintOS data layer: Supabase project mjbbpzwyamymboazabmx
-- Postgres schema for the OB-Nucleus mirror (Nucleus models, brief Section 5.2).
-- Apply once via Supabase Dashboard, SQL Editor, paste, Run.
-- After applying, `ob-nucleus mirror sync` upserts via PostgREST using the
-- service role key (OBN_SUPABASE_URL / OBN_SUPABASE_SERVICE_KEY).
--
-- RLS is ENABLED with no policies: only the service role can read or write.
-- Add scoped policies deliberately when other consumers need access.

create table if not exists public.nucleus_memories (
  id text primary key,
  memory_type text,              -- client | pattern | preference
  subject text,
  content text,
  source_type text,              -- explicit | extracted | detected
  confidence numeric,
  user_id text,
  project_id text,
  stakeholder_id text,
  times_retrieved integer,
  created_at timestamptz,
  updated_at timestamptz,
  raw jsonb,
  synced_at timestamptz default now()
);
comment on table public.nucleus_memories is 'Read-only mirror of Audity Nucleus memories. Source of truth: Audity. Mirror, do not fork.';

create table if not exists public.nucleus_captures (
  id text primary key,
  channel text,
  status text,
  content_type text,
  raw_content text,
  processed_content text,
  processing_results jsonb,
  user_id text,
  project_id text,
  captured_at timestamptz,
  created_at timestamptz,
  updated_at timestamptz,
  raw jsonb,
  synced_at timestamptz default now()
);
comment on table public.nucleus_captures is 'Read-only mirror of Audity Nucleus captures (intake funnel).';

create table if not exists public.nucleus_contacts (
  id text primary key,
  name text,
  email text,
  phone text,
  company text,
  role text,
  notes text,
  relationship_type text,        -- client | prospect | partner | referral
  last_interaction_at timestamptz,
  created_at timestamptz,
  raw jsonb,
  synced_at timestamptz default now()
);
comment on table public.nucleus_contacts is 'Read-only mirror of Audity Nucleus contacts (lightweight CRM).';

create table if not exists public.nucleus_insights (
  id text primary key,
  type text,                     -- live: overdue_followup, pattern_detected, similar_lead, stale_client
  title text,
  body text,
  is_read boolean,
  is_dismissed boolean,
  project_id text,
  created_at timestamptz,
  raw jsonb,
  synced_at timestamptz default now()
);
comment on table public.nucleus_insights is 'Read-only mirror of Audity Nucleus proactive insights.';

create table if not exists public.sync_runs (
  id bigint generated always as identity primary key,
  started_at timestamptz,
  finished_at timestamptz,
  counts jsonb,
  supabase_pushed integer,
  status text
);
comment on table public.sync_runs is 'OB-Nucleus mirror sync audit log.';

-- Useful indexes for agent queries
create index if not exists idx_memories_project on public.nucleus_memories (project_id);
create index if not exists idx_memories_type on public.nucleus_memories (memory_type);
create index if not exists idx_captures_status on public.nucleus_captures (status);
create index if not exists idx_captures_project on public.nucleus_captures (project_id);
create index if not exists idx_contacts_company on public.nucleus_contacts (company);
create index if not exists idx_insights_unread on public.nucleus_insights (is_read) where is_read = false;

-- Lock down: service role only until policies are added deliberately
alter table public.nucleus_memories enable row level security;
alter table public.nucleus_captures enable row level security;
alter table public.nucleus_contacts enable row level security;
alter table public.nucleus_insights enable row level security;
alter table public.sync_runs enable row level security;
