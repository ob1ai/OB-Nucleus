# OB.1 Data Contracts: Audity and BlueprintOS

Document ID: OB1-GOV-DATA-2606-001
Classification: OB.1 internal, approved for controlled client disclosure (derived client edition)
Version: 0.1.0 (draft; vendor-side lifecycle answers pending the Audity review)
Owner: Chief (lane 1, data layer). Accountable human: Chris McCarthy.
Last updated: 2026-06-08

## 1. Why this document exists

This is the single ratified source of truth for how client and operational data moves through OB.1's Audity and BlueprintOS stack: who owns it, what systems touch it, how it matures, how long it is kept, and what happens to it when an engagement ends. It exists so two audiences can rely on the same facts:

Internally, OB.1 agents and operators reference this contract instead of re-deriving policy from code comments. When a lane agent needs to know the sync scope rule, the staleness threshold, or the PII boundary, it cites a clause here rather than guessing. Numbers and rules defined in this document are authoritative; the code implements them, it does not define them.

Externally, client technical and compliance teams need a clear, accurate account of how their data is handled before and during an engagement. The branded client edition of this document is generated directly from this file so the story we tell a client matches the rules our systems actually enforce.

A claim in this document is either marked KNOWN (verified against the live API, the activation brief, or shipped code, with the basis cited) or OPEN (a vendor-side or contractual fact we have not yet confirmed and must not assert). Open items are listed in Section 11 and form the agenda for the Audity data review.

## 2. Core principles

OB.1 operates a Governance-as-a-Service discipline on its own data before applying it to clients: rules before tools. Five principles govern everything below.

Audity is the source of truth. BlueprintOS mirrors Audity; it never forks it. Any disagreement between a mirrored value and the live Audity API is resolved in favor of the API, and the discrepancy is logged. No OB.1 system is permitted to become an authoritative second copy of client audit data.

Reads are free; writes are gated. Every credit-spending or state-changing write defaults to a dry run and requires explicit human confirmation. Identity data is never mutated by an automated synthesis step.

Scope is least-data. BlueprintOS carries active client work only (engagement status past setup, not archived, no sandbox or test rigs). The broader universe lives only in the local mirror on a single controlled machine, not in the shared cloud layer.

Identity data is boundaried. Business contact PII (names, emails, phones) is confined to named systems and never enters source control or unredacted logs.

Every movement is auditable. Each sync writes an audit row locally and to BlueprintOS; each revenue-loop agent run writes an event row. Silence is detectable.

## 3. Data domains

Each domain below names what the data is, the system of record, where copies live, who owns it, what touches it, and its PII sensitivity. (KNOWN unless a cell is marked OPEN.)

| Domain | System of record | Copies held by OB.1 | Owner | What touches it | PII level |
|---|---|---|---|---|---|
| Audit projects (active client engagements) | Audity | BlueprintOS `audity_projects` (active scope), local SQLite (all) | Client (subject data); OB.1 (engagement artifacts) | Mirror sync (read), revenue-loop agents (read), Attio (active book) | Low (business descriptors) |
| Leads | Audity | BlueprintOS `audity_leads`, local SQLite | OB.1 pipeline; subject business is the data subject | Mirror sync, daily sweep triage, Closer proposals | Medium (business name, email, readiness) |
| Nucleus memories | Audity Nucleus | BlueprintOS `nucleus_memories`, local SQLite | OB.1 (cross-engagement knowledge derived from client work) | Mirror sync, capture extraction (auto-create), promote helper | Medium (may reference client facts) |
| Nucleus captures | Audity Nucleus | BlueprintOS `nucleus_captures`, local SQLite | OB.1 | Capture-note writes (gated), extraction pipeline | Medium (raw intake content) |
| Nucleus contacts | Audity Nucleus | BlueprintOS `nucleus_contacts`, local SQLite | OB.1 / client relationship | Mirror sync | High (name, email, phone) |
| Nucleus insights | Audity Nucleus | BlueprintOS `nucleus_insights`, local SQLite | OB.1 (generated) | Mirror sync, daily sweep | Low to medium |
| Cross-system identity (xref) | BlueprintOS (OB.1-owned) | BlueprintOS `revenue_xref` | OB.1 | Revenue-loop agents (Scribe, Steward, Closer) | Medium (email, domain, name) |
| Agent run events | BlueprintOS (OB.1-owned) | BlueprintOS `loop_events`, `sync_runs` | OB.1 | All agents and the mirror | None (operational metadata; emails redacted) |
| Conversion proposals | BlueprintOS (OB.1-owned) | BlueprintOS `conversion_queue` | OB.1, human-approved | Closer (write), Chris (approve) | Low |

Two ownership distinctions matter and are OPEN pending the vendor review. First, the contractual owner of the audit analysis Audity produces from a client's inputs (the client, OB.1, or joint) is not yet documented and must be confirmed. Second, Nucleus memories auto-extracted from client engagements are cross-engagement OB.1 knowledge, but whether any client-identifiable content within them is contractually the client's is OPEN.

## 4. Data lifecycle

Client and operational data moves through six stages. The five questions raised for the vendor review map onto these stages and are answered here where KNOWN, flagged where OPEN.

Stage 1, Capture and discovery. Data enters through Audity: a lead survey, a project, or a Nucleus capture. Audity is the system of record from this moment. OB.1 holds nothing yet.

Stage 2, Mirror. The daily sweep (07:00, OB1AIRIG Task Scheduler) reads the six Audity collections and writes them to the local SQLite mirror (everything) and to BlueprintOS (active clients only). This is a read from Audity and a write to OB.1-owned storage; it never writes back to Audity.

Stage 3, Active use. Agents query BlueprintOS and the live API to triage leads, surface stale-client insights, and (in the revenue loop) build the cross-system identity xref and propose conversions. Maturation happens here: a lead matures toward an engagement, a capture matures into extracted memories, an insight is actioned. Conversion is the one maturation step that spends credits and is therefore gated behind explicit human approval; the only reliable signal that a lead has converted is `convertedToAuditId` on the lead record.

Stage 4, Archive. When Audity archives a project (observed live: statuses can flip to archived between reads), it falls out of OB.1's active scope. The next sync purges the corresponding row from BlueprintOS, with a guard that refuses to purge when the live read returns an empty set so a transient API hiccup cannot wipe the table. The full record is retained in the local SQLite mirror and in preserved raw JSON, so archival in the cloud layer is descoping, not destruction.

Stage 5, End of engagement. When an OB.1 client engagement formally ends, the disposition of that client's data across Audity, BlueprintOS, and the local mirror is governed by Section 5. The vendor-side half of this stage (what Audity does with the data, on what schedule, and under what contractual ownership) is OPEN.

Stage 6, Disposition. Deletion, export, or retention per the rules in Section 5 and the deletion semantics in Section 10.

## 5. End-of-engagement disposition

This is the section clients ask about first and the one with the most OPEN dependencies. What is KNOWN today:

On the OB.1-controlled side, BlueprintOS already excludes non-active engagements by scope and purges archived projects automatically, so a concluded engagement's project row leaves the shared cloud layer on the next sync. The local SQLite mirror retains a full historical copy on a single controlled machine; a documented offboarding step to prune or export a specific client's mirrored rows on engagement close is a planned addition owned by lane 1 and is not yet automated.

What is OPEN and required before we can give a client a complete answer: Audity's retention period for project, lead, and Nucleus data after an engagement or account closes; whether Audity supports a client-data export on offboarding and in what format; whether deletion at the Audity storage layer is soft (flag) or a true purge, and on what schedule a soft delete becomes a hard delete; and the contractual ownership and permitted retention of derived artifacts (the audit analysis and any Nucleus memories extracted from the engagement). These are items in Section 11.

The honest current posture, which is the right thing to tell a client technical team: OB.1 controls and can describe the mirror and BlueprintOS layers precisely today, and is formalizing the Audity-layer answers with the vendor so the end-to-end lifecycle is documented rather than assumed.

## 6. Storage layer contract (BlueprintOS)

BlueprintOS is Supabase project `mjbbpzwyamymboazabmx`. Row Level Security is enabled on every table with no permissive policies, so only the service role can read or write; there is no anonymous or client-role access path. (KNOWN: schema.sql, schema_v2.sql, schema_v3.sql.) Scoped policies will be added deliberately if and when another consumer needs access, and any such addition is a change to this contract.

The local SQLite mirror at `data/nucleus_mirror.sqlite` lives only on OB1AIRIG, is excluded from source control, and holds the full unfiltered universe for offline work and as the historical record behind the active-scope cloud layer.

Sync runs daily at 07:00 and writes an audit row to both SQLite and the BlueprintOS `sync_runs` table. Drift between the live API, SQLite, and BlueprintOS is checked on every sweep and flagged in the digest. (KNOWN: mirror.py, sweep.py.)

The Supabase storage region, encryption-at-rest configuration, and backup retention are OPEN and listed in Section 11; the service-role and RLS posture is KNOWN and stated above.

## 7. Access and identity contract

Audity's v1 authorization model is per user, not per organization. Personal Access Tokens are scoped to a single Audity user, capped at ten per user, and created or revoked only from that user's browser session. Row Level Security and ownership filters scope every read and write to the owning user's data, so an agent authenticated with one PAT sees only that user's projects, leads, and Nucleus. (KNOWN: brief 4.3.)

OB.1 operates on Chris's agency seat as the owning account, with one labeled PAT per agent surface and no token sharing, so any single agent can be revoked without breaking the rest. Tokens live only in OB1AIRIG user environment variables and are recorded by fingerprint in the token registry, never in source control, logs, or chat. Read tokens are the working default; the write token is gated and used only for explicitly approved writes. (KNOWN: brief 4.3, TOKEN_REGISTRY.)

Audity v1 has no per-token activity feed, so attribution to a specific agent relies on per-surface tokens plus OB.1's own run logs. (KNOWN: connector qualification.)

## 8. Ratified operational thresholds

These values are authoritative. Code implements them; changing one is a change to this contract.

| Parameter | Value | Meaning |
|---|---|---|
| Sync scope (`OBN_SYNC_SCOPE`) | `active` (default) | BlueprintOS carries active clients only; `all` overrides for a full push |
| Active definition | status past `setup`, not `archived`, no test prefix | Governs the Supabase push, not the SQLite mirror |
| Test-rig exclusion (`OBN_TEST_CLIENT_PREFIXES`) | `sandbox` (default, extensible) | Client-name prefixes excluded from the cloud layer |
| Staleness flag (`STALE_HOURS`) | 26 hours | Drift check flags any table whose freshest cloud row is older; allows one delayed daily run |
| Stale-project purge guard | refuse on empty live set | A transient empty API read cannot wipe the cloud table |
| Upsert batch size | 500 rows | PostgREST chunk size for the mirror push |
| Conversion truth signal | `convertedToAuditId` is set | The only reliable conversion flag; `conversionTimestamp` is not |
| Duplicate detection | normalized name, legal suffix stripped | Flags duplicates for human merge; never auto-merges |

## 9. PII and redaction contract

Business contact PII (names, emails, phones) is permitted only in Audity, BlueprintOS, Attio, and Pipeline. It is never committed to source control and never written to logs unredacted; log output redacts emails to a first-three-characters-plus-domain form. (KNOWN: PRD section 5; mirror and MCP redaction behavior.) The highest-sensitivity domain is Nucleus contacts (name, email, phone together); the xref table holds email and domain for identity resolution and is RLS-locked to the service role.

## 10. Deletion and retention semantics (Audity API)

The behavior of the Audity delete endpoints is KNOWN from the brief and matters for any deletion request:

Memories delete as a soft delete (`is_archived=true`), idempotent, via the preferred path form. Captures delete as a soft delete, idempotent. Contacts are a hard delete (id passed in the body, returns success). The transition from a soft-deleted state to a true storage purge, and the retention window before that transition, is OPEN (Section 11).

## 11. Open items (agenda for the Audity data review)

Each item names the question, the owner, and why it blocks a complete client answer. These are the items to close with Jeremy.

| # | Open question | Owner | Why it matters |
|---|---|---|---|
| O-1 | Audity data retention period after engagement or account closure | Audity (Jeremy) | Clients require a stated retention window |
| O-2 | Soft vs hard delete at Audity storage; purge schedule for soft-deleted records | Audity (Jeremy) | Determines whether deletion is final and when |
| O-3 | Client-data export on offboarding: supported, format, scope | Audity (Jeremy) | Required for portability and exit clauses |
| O-4 | Contractual ownership of derived artifacts (audit analysis, extracted memories) | Audity + OB.1 legal | Sets what OB.1 may retain post-engagement |
| O-5 | Data residency region (Audity storage and Supabase project) | Audity (Jeremy); OB.1 for Supabase | Jurisdiction and compliance commitments |
| O-6 | Encryption at rest and backup retention (both layers) | Audity (Jeremy); OB.1 for Supabase | Standard vendor-compliance questionnaire fields |
| O-7 | Sub-processor list and DPA availability from Audity | Audity (Jeremy) | Needed for client DPAs and vendor diligence |
| O-8 | Local SQLite mirror offboarding routine (prune or export per client on close) | OB.1 lane 1 | OB.1-side action; not vendor-blocked |

## 12. Change control

This contract is versioned. Any change to a ratified threshold (Section 8), the scope rule, the PII boundary, the access model, or the resolution of an open item is a versioned edit with a dated entry below and, where it affects code, a corresponding commit on the data-layer branch. The client edition is regenerated from this file on every material change so the two never drift.

Revision history: 0.1.0 (2026-06-08, Chief) initial draft, vendor-side items O-1 through O-7 open pending the Audity data review.
