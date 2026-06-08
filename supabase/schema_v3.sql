-- BlueprintOS schema v3: revenue loop tables (PRD OB1-INT-2606-001, Section 6).
-- Apply once via Supabase Dashboard, SQL Editor, paste, Run.
-- Extends schema.sql and schema_v2.sql; safe to run on an existing database (create if not exists).
-- Populated by the lane 3 revenue loop agents (Scribe, Steward, Closer), not by mirror sync.
-- Source of truth for identity stays Audity; these tables hold cross-system state OB.1 owns.

-- Cross-system identity: one row per lead/company across Audity, Attio, Pipeline.
-- Keys on audity_lead_id when present; email_normalized and domain cover leads without one.
create table if not exists public.revenue_xref (
  id uuid primary key default gen_random_uuid(),
  audity_lead_id text unique,
  audity_project_id text,
  attio_company_id text,
  attio_deal_id text,
  pipeline_prospect_ref text,
  email_normalized text,         -- lowercased, trimmed, plus-addressing stripped
  domain text,
  display_name text,             -- normalized business name; dedupe key (Cleveland Candy case)
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
comment on table public.revenue_xref is 'Cross-system identity xref: Audity lead/project to Attio company/deal to Pipeline prospect. Dedupes on normalized display_name; duplicates flagged for human merge, never auto-merged.';

-- Agent run audit: every Scribe/Steward/Closer run appends rows here.
-- The 48h silent-agent health check and the under-5-minute cycle measurement read this table.
create table if not exists public.loop_events (
  id bigint generated always as identity primary key,
  run_id uuid,
  agent text,                    -- scribe | steward | closer
  action text,
  subject_ref text,              -- xref id, lead id, or external record ref the action touched
  status text,                   -- ok | failed | skipped | dry_run
  detail jsonb,
  created_at timestamptz default now()
);
comment on table public.loop_events is 'Revenue loop agent audit log. Every agent run writes rows (run id, agent, counts, status). Retries and failures land here per PRD error handling.';

-- Human-gated conversion proposals: Closer proposes, Chris approves, execution recorded.
-- convertLead costs 1000 credits and is non-idempotent; nothing executes from this table
-- without approved_by set by a human.
create table if not exists public.conversion_queue (
  id bigint generated always as identity primary key,
  audity_lead_id text,
  readiness numeric,
  credit_cost int,
  credits_remaining int,
  proposal text,
  status text default 'pending', -- pending | approved | rejected | executed | failed
  approved_by text,
  approved_at timestamptz,
  executed_at timestamptz,
  result jsonb
);
comment on table public.conversion_queue is 'Gated lead conversion queue. Closer writes proposals; a human sets approved_by before any credit spend. Conversion truth check remains convertedToAuditId on the lead.';

-- Indexes for agent query paths
create index if not exists idx_xref_domain on public.revenue_xref (domain);
create index if not exists idx_xref_email on public.revenue_xref (email_normalized);
create index if not exists idx_xref_attio_company on public.revenue_xref (attio_company_id);
create index if not exists idx_xref_display_name on public.revenue_xref (display_name);
create index if not exists idx_loop_events_run on public.loop_events (run_id);
create index if not exists idx_loop_events_agent_time on public.loop_events (agent, created_at desc);
create index if not exists idx_loop_events_failed on public.loop_events (status) where status = 'failed';
create index if not exists idx_queue_status on public.conversion_queue (status);
create index if not exists idx_queue_lead on public.conversion_queue (audity_lead_id);

-- Lock down: service role only until policies are added deliberately
alter table public.revenue_xref enable row level security;
alter table public.loop_events enable row level security;
alter table public.conversion_queue enable row level security;
