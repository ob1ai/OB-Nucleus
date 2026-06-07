# OB-Nucleus

OB.1's reusable operations layer for Audity (AI readiness and discovery engine) and Nucleus (persistent cross-engagement memory). This repo turns an OB.1 audit into a tool call: a typed Python client over the Audity PAT allowlist, a CLI, a local read-only mirror of Nucleus, and the Supabase BlueprintOS data layer.

Built and maintained by Chief on OB1AIRIG. Canonical spec: `knowledge/ACTIVATION_BRIEF.md` (reference it by section, do not rewrite it).

## What lives here

```
OB-Nucleus/
  README.md            this file
  CLAUDE.md            persistent agent context (loads every session)
  .env.example         environment variable template (placeholders only)
  knowledge/           activation brief + QUICKREF.md (allowlist, errors, rate limits)
  src/ob_nucleus/      the typed Audity client library
  cli/                 CLI entrypoint wrapper
  config/              Nucleus conventions, taxonomy, SQLite schema
  supabase/            BlueprintOS Postgres schema for project mjbbpzwyamymboazabmx
  scripts/             read sweep and verification runners
  verification/        smoke test and check outputs (tokens always redacted)
  tests/               unit tests (write guard, error mapping)
  data/                local SQLite mirror (gitignored)
```

## Setup on Windows

1. Python 3.11 or newer with `httpx` (`pip install httpx`).
2. Set the read token persistently (PowerShell):

```powershell
setx AUDITY_TOKEN "aky_your_token_here"
```

`setx` does not affect the current shell. Open a new terminal before running anything. Verify with `$env:AUDITY_TOKEN`.

3. Optional, for the BlueprintOS mirror target:

```powershell
setx OBN_SUPABASE_URL "https://mjbbpzwyamymboazabmx.supabase.co"
setx OBN_SUPABASE_SERVICE_KEY "your_service_role_key"
```

4. Install the CLI from the repo root:

```powershell
pip install -e .
```

## Using the CLI

```
ob-nucleus <group> <command> [options]
```

Read commands (free, no credits):

```powershell
ob-nucleus account whoami        # identity check
ob-nucleus account tier          # plan, source of truth for gating
ob-nucleus account credits      # balance; always check before any write
ob-nucleus account preflight     # whoami + tier + credits in one shot
ob-nucleus projects list
ob-nucleus projects get <id>
ob-nucleus projects opportunities <id>
ob-nucleus projects deliverables <id>
ob-nucleus leads list
ob-nucleus leads get <id>
ob-nucleus nucleus memories [--type client|pattern|preference] [--project-id ID]
ob-nucleus nucleus captures [--status processed]
ob-nucleus nucleus capture <id>
ob-nucleus nucleus contacts [--search text]
ob-nucleus nucleus insights [--unread-only]
ob-nucleus nucleus suggestions [--project-id ID]
ob-nucleus mirror sync           # populate the local mirror from live reads
ob-nucleus mirror status         # row counts and last sync
ob-nucleus sweep run             # daily read-only digest
```

Write commands are guarded. Without `--confirm` they run a dry run: print the credit balance, the estimated cost, and the exact request that would be sent, then make no call. With `--confirm` they still check credits first. Writes also require a write-scoped token in `AUDITY_WRITE_TOKEN`; the default `AUDITY_TOKEN` is read only by design.

```powershell
ob-nucleus projects create --name "..."          # 1000 credits, requires --confirm
ob-nucleus leads convert <id>                     # 1000 credits, requires --confirm
ob-nucleus nucleus promote <capture-id>           # capture to explicit memories, requires --confirm
```

## The read sweep

The daily digest per brief Section 10 step 4: credits, lead triage, unread insights.

```powershell
ob-nucleus sweep run
```

Writes a dated digest to `verification/` and prints it. Reads only, zero credit risk.

## BlueprintOS (Supabase)

`supabase/schema.sql` defines the Postgres schema for the OB-Nucleus data layer in Supabase project `mjbbpzwyamymboazabmx`. Apply it once via the Supabase SQL editor (Dashboard, SQL Editor, paste, Run). After that, `ob-nucleus mirror sync` upserts the same rows it writes to SQLite into Supabase via PostgREST whenever `OBN_SUPABASE_URL` and `OBN_SUPABASE_SERVICE_KEY` are set.

## Guardrails (non-negotiable)

1. Reads are free. Writes cost credits and real money. No credit-spending write without an explicit instruction and a credit check first.
2. Tokens live in environment variables only. Never print, echo, or commit them. `.env` is gitignored.
3. Rate limits per token: reads 100/min, writes 20/min, job polling 120/min, captures 30/hr. The client honors 429 Retry-After automatically.
4. When the brief and a live API response disagree, the response wins. Log discrepancies in STATUS.md.
5. Windows conventions throughout. No em dashes anywhere, per OB.1 writing rule.

## Stack choice

Python with httpx and argparse (stdlib CLI, no typer/click dependency). Chosen for zero extra dependencies beyond httpx, which was already present on OB1AIRIG. See `knowledge/QUICKREF.md` for the endpoint allowlist, error codes, and rate limits.
