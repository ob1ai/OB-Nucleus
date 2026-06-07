-- SQLite mirror schema for the Nucleus data models (brief Section 5.2).
-- Built and populated read-only by src/ob_nucleus/mirror.py from
-- listMemories, listCaptures, listContacts, listInsights.
-- The Postgres equivalent for Supabase BlueprintOS lives in supabase/schema.sql.

CREATE TABLE IF NOT EXISTS memories (
  id TEXT PRIMARY KEY,
  memory_type TEXT,            -- client | pattern | preference
  subject TEXT,
  content TEXT,
  source_type TEXT,            -- explicit | extracted | detected
  confidence REAL,
  user_id TEXT,
  project_id TEXT,
  stakeholder_id TEXT,
  times_retrieved INTEGER,
  created_at TEXT,
  updated_at TEXT,
  raw TEXT,                    -- full original JSON
  synced_at TEXT
);

CREATE TABLE IF NOT EXISTS captures (
  id TEXT PRIMARY KEY,
  channel TEXT,                -- transcript | voice_note | text_note | email | calendar | zoom | crm_sync | file_drop
  status TEXT,                 -- pending | processing | processed | needs_review | failed
  content_type TEXT,
  raw_content TEXT,
  processed_content TEXT,
  processing_results TEXT,     -- JSON: action items, decisions, key insights, contact mentions
  user_id TEXT,
  project_id TEXT,
  captured_at TEXT,
  created_at TEXT,
  updated_at TEXT,
  raw TEXT,
  synced_at TEXT
);

CREATE TABLE IF NOT EXISTS contacts (
  id TEXT PRIMARY KEY,
  name TEXT,
  email TEXT,
  phone TEXT,
  company TEXT,
  role TEXT,
  notes TEXT,
  relationship_type TEXT,      -- client | prospect | partner | referral
  last_interaction_at TEXT,
  created_at TEXT,
  raw TEXT,
  synced_at TEXT
);

CREATE TABLE IF NOT EXISTS insights (
  id TEXT PRIMARY KEY,
  type TEXT,                   -- see config/taxonomy.md, live vs reserved
  title TEXT,
  body TEXT,
  is_read INTEGER,
  is_dismissed INTEGER,
  project_id TEXT,
  created_at TEXT,
  raw TEXT,
  synced_at TEXT
);

CREATE TABLE IF NOT EXISTS sync_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  started_at TEXT,
  finished_at TEXT,
  counts TEXT,                 -- JSON row counts per table
  supabase_pushed INTEGER,
  status TEXT
);
