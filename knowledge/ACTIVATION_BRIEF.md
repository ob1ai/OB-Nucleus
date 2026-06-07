# AUDITY x OB.1: Knowledge Base Transfer and Chief Activation Brief

**Classification:** OB.1 Internal. Agent training data. Not client-facing.
**Primary consumer:** Chief (Claude Code agent on OB1AIRIG).
**Secondary consumers:** Buddy (EA), Sales Commander, Ops Commander, CFO Agent, and any new human onboarding into the OB.1 audit workflow.
**Authoring agent:** Buddy.
**Owner:** Chris McCarthy.
**Source of record:** docs.auditynow.com (Audity for Agents) and code.claude.com/docs (Anthropic Claude Code).
**Standard:** Rules Before Tools. This document encodes the rules so the tools behave.

---

## 0. How Chief should use this document

This is a reference brain, not a script. Read it once end to end to build the model, then treat Sections 7 through 9 as lookup tables during execution.

Three operating rules govern every Audity action Chief takes:

1. **Reads are cheap, writes cost credits and money.** Never trigger a write that spends credits (create project, convert lead, run audit synthesis) without an explicit instruction from Chris or a standing OB.1 workflow that authorizes it. Always check credits first.
2. **The token is the keys to the workspace.** Treat the Personal Access Token like a production secret. Never print it, never echo it into a chat body, never commit it to version control. Reference it through an environment variable or the credential store only.
3. **When the doc and reality disagree, the API response wins.** Audity ships a deliberately small v1 surface and iterates. Tier names, credit numbers, and a few insight types are explicitly flagged as moving targets. Trust `GET /api/user/tier` and `GET /api/user/credits` over any number written here.

If anything in this document conflicts with what Chief observes at runtime, flag it to Chris, Chloe, or Claudia rather than guessing. That is the standard.

---

## 1. What Audity is, and where it sits in the OB.1 stack

Audity (auditynow.com, app at app.auditynow.com) is a structured AI discovery and readiness system built for solo consultants and small firms. It turns stakeholder interviews, uploaded documents, and process notes into evidence backed findings, ROI models, opportunity matrices, and client ready roadmaps, so every paid discovery runs the same repeatable way. Built by a consultant (Ed) who runs real discoveries, it leans on Big 4 style frameworks and an audit methodology rather than being a generic chatbot.

Two product layers matter to OB.1:

- **The Audit pipeline.** A 13 step engagement lifecycle that produces deliverables (executive summary, opportunity matrix, risk assessment, stakeholder memos). This is the production line.
- **Nucleus.** Audity's always on persistent memory layer. It stores facts about clients (memories), ingests outside text like meeting transcripts (captures), runs a lightweight CRM (contacts), and produces proactive observations from background jobs (insights). Unlike the audit pipeline, Nucleus accumulates knowledge across every engagement.

**Where this maps for OB.1.** Audity's audit-first arc (AI Readiness Score, Discovery, Diagnostics, Opportunity, Roadmap) is the same shape as the OB.1 methodology: Audity (AI Readiness Score) to Clinical Discovery to Diagnostics to Operational Blueprint to Architecture. Audity is the readiness and discovery engine that feeds the front of the OB.1 funnel. Nucleus is the cross-engagement memory that should mirror, not replace, the Notion 6 database spine (Companies, Contacts, Deals, Engagements, Tasks, Decisions Log) and the OB1-Brain vault. The goal of this transfer is to let Chief and the agent fleet read and write Audity programmatically, so an OB.1 audit is a tool call, not a tab.

---

## 2. The agent surface at a glance

Audity exposes a deliberately narrow agent API. Everything below is reachable two ways, both pointed at the same backend.

| Thing | Value |
| --- | --- |
| Web app / API base URL | `https://app.auditynow.com` (REST paths under `/api`) |
| Remote MCP endpoint | `https://docs.auditynow.com/mcp` |
| OpenAPI spec (for OpenAPI based clients) | `https://docs.auditynow.com/api-reference/openapi.json` |
| Docs root | `https://docs.auditynow.com` |
| Token management UI | app.auditynow.com to Settings to API Tokens |
| Privacy policy (needed by some clients) | `https://auditynow.com/privacy` |
| Support | support@auditynow.com |

**Operations exposed.** The MCP connector surfaces the full agent surface as typed tools whose names match the `operationId` in the OpenAPI spec. The Connect Claude page cites 28 operations; the Claude Code page lists the same set plus `triggerAsyncAuditAnalysis` and `getJobStatus`. Treat the live tool list from `claude mcp get audity` or the `/mcp` panel as authoritative, because the published count lags the spec. The full operation set:

```
getCurrentUser   getCurrentTier   getCredits
listProjects     createProject    getProject      patchProject
triggerAuditAnalysis   triggerAsyncAuditAnalysis   getJobStatus   getAuditAnalysis
listOpportunities      getDeliverables
listLeads        getLead          convertLead
listMemories     createMemory     deleteMemory
listCaptures     createCaptureNote   getCapture   reprocessCapture   deleteCapture
listContacts     createContact    updateContact   deleteContact
listInsights     getSuggestions
```

A useful side effect of the MCP route: the Audity docs themselves are searchable through the connector, so Chief can answer "how do I X in Audity" by reading the doc page directly, without spending an API call.

---

## 3. Authentication and Personal Access Tokens (PATs)

Audity uses Bearer token auth for every agent call. Human web sessions use Clerk; agents use a PAT.

### 3.1 Token format and header

Every request carries:

```
Authorization: Bearer aky_<your-token>
Content-Type: application/json        (on writes)
```

The token is a Personal Access Token. It always starts with `aky_` followed by 32 characters. The single most common setup failure across every client is a doubled prefix: if a field already adds `Bearer` for you and you paste `Bearer aky_...`, the server receives `Authorization: Bearer Bearer aky_...` and returns `401 PAT_MALFORMED` on every request. Know whether the field you are pasting into wants the raw token or the full `Bearer aky_...` string.

- Claude Code MCP config `headers` field: full string, `Bearer aky_...`.
- Cursor headers field: full string, `Bearer aky_...`.
- ChatGPT Custom GPT API key field: raw token only, `aky_...` (ChatGPT prepends `Bearer`).
- Claude Desktop connector: depends on the flow; if it shows an API key field, paste full `Bearer aky_...`; if it runs an OAuth redirect first then asks for the key, paste raw `aky_...`.

### 3.2 Generating a token (browser only)

1. Sign in at app.auditynow.com.
2. Go to Settings to API Tokens.
3. Click Create Token.
4. Label it clearly (the label is how you will identify and rotate it later). Use OB.1 convention: `Chief - OB1AIRIG`, `Buddy EA - Cowork`, `Sales Commander - n8n prod`.
5. Select scopes: **Read + Write** for any agent that creates projects, captures notes, or writes memories. Read only for pure reporting agents.
6. Copy the token immediately. The plaintext is shown exactly once and cannot be recovered. If lost, revoke and reissue.

Under the hood this calls `POST /api/user/api-keys`, which returns the `plaintext` field once and never again.

### 3.3 PAT rules and constraints

- **Scopes:** `read`, `write`. Defaults to `["read"]` if omitted. A token with no valid scopes returns 400.
- **Read endpoints** succeed if the token has `read` OR has no explicit scopes. **Write endpoints** require `write`.
- **Cap:** maximum 10 active tokens per user. Creating an 11th returns `409`. Revoke an old one first.
- **Expiry:** no default expiry is enforced. You may set an optional `expiresAt`. OB.1 should set rotation dates anyway (see Section 4.3).
- **PATs cannot manage PATs.** Token creation, listing, and revocation are browser session only. A PAT hitting `/api/user/api-keys` returns `403 PAT_NOT_SUPPORTED_FOR_ENDPOINT`. This is intentional anti recursion.
- **Revocation is permanent and idempotent.** `DELETE /api/user/api-keys/{id}` (browser session) sets `revoked_at`; it returns `{ success: true }` whether the key existed or not. You cannot un-revoke.
- **Kill switch.** The whole agent API sits behind `AUDITY_AGENT_API_ENABLED`. If off, every call returns `503 PAT_DISABLED`; contact support@auditynow.com.

### 3.4 Rate limits (per token)

| Endpoint class | Limit |
| --- | --- |
| Standard reads | 100 / minute |
| Writes (create, update, delete) | 20 / minute |
| Async job polling (`GET /api/agent/jobs/{id}`) | 120 / minute |
| Capture submissions (`POST /api/nucleus/capture/note`) | 30 / hour |
| Expensive operations (audit synthesis) | Lower internal guardrails may apply |

A `429` includes a `Retry-After` header in seconds. Honor it and back off. The write ceiling (20/min) and the capture ceiling (30/hr) are the two most common limits an OB.1 batch will hit. Serialize batch writes and insert delays.

### 3.5 Logging and audit trail (compliance note)

There are two logging systems, and only one covers agents. The `nucleus_actions` table logs Nucleus tool calls made **inside the web app** via the `withAudit` wrapper. The **agent API is not mirrored into `nucleus_actions`**. PAT writes persist in their own tables (the rows are the record), but there is no per-call audit trail in v1. For OB.1 compliance and cost attribution, route agent calls through OB.1's own logging layer (Cowork task logs, a logging proxy, or Claude Code session transcripts) until Audity ships a dedicated PAT activity feed.

---

## 4. PART A: Connection setup for Chief

Chief runs on **OB1AIRIG (Windows 11)**. Every path, command, and environment variable below uses Windows conventions. There are two connection paths. Path 1 (MCP) is the default and what Chief should use. Path 2 (direct API via CLAUDE.md) is the zero dependency fallback.

### 4.1 Path 1: MCP via config (recommended)

This gives Chief typed tools with full schemas and validation. It requires `docs.auditynow.com/mcp` to be reachable from OB1AIRIG.

#### 4.1.1 Method A: the `claude mcp add` CLI (most robust)

This is Anthropic's canonical way to register a remote HTTP MCP server. It writes the entry to the correct config file automatically, so you do not have to hand edit JSON or guess the path. Run this in a normal terminal on OB1AIRIG (PowerShell or CMD), not inside an active Claude Code session:

```powershell
claude mcp add --transport http --scope user audity https://docs.auditynow.com/mcp --header "Authorization: Bearer aky_your_token_here"
```

Scope choice (this is the lever that decides who sees the server):

- `--scope local` (default): only Chief, only in the current project. Stored in `%USERPROFILE%\.claude.json` under that project path.
- `--scope user`: available to Chief across every project on OB1AIRIG, private to this machine account. Stored in `%USERPROFILE%\.claude.json`. **Recommended for Chief**, because Audity is a cross project capability.
- `--scope project`: shared with the team via a `.mcp.json` file committed to the repo. Use this only for the OB.1 agent repos where you want every clone to inherit Audity, and pair it with environment variable expansion so the token never lands in git (see 4.1.3).

Then verify and load:

```powershell
claude mcp list
claude mcp get audity
```

Inside a Claude Code session, run `/mcp` to confirm a green status and a non zero tool count. If you added it while a session was open, run `claude mcp reload` and start a new session, because reload alone does not refresh an already running session.

#### 4.1.2 Method B: JSON config file (as documented by Audity)

Audity's own guide documents a config file form. The server object shape is identical to the CLI result; only the file location differs. Audity documents the path as `.claude/mcp_servers.json` (project) or `%USERPROFILE%\.claude\mcp_servers.json` (global). The current Anthropic standard locations are `%USERPROFILE%\.claude.json` (local and user scope) and a project root `.mcp.json` (project scope). If Method A does not behave on a given Claude Code build, fall back to writing this object into the location your version reads:

```json
{
  "mcpServers": {
    "audity": {
      "type": "http",
      "url": "https://docs.auditynow.com/mcp",
      "headers": {
        "Authorization": "Bearer aky_your_token_here"
      }
    }
  }
}
```

Notes: `type` may be `http` or `streamable-http` (the spec name); Claude Code treats them as aliases. After saving, `claude mcp reload` and open a new session.

#### 4.1.3 Keep the token out of version control (project scope only)

If Chief's config lives in a committed `.mcp.json`, do not inline the token. Claude Code expands environment variables inside `.mcp.json` in `command`, `args`, `env`, `url`, and `headers`. Store the token in a machine environment variable and reference it:

```json
{
  "mcpServers": {
    "audity": {
      "type": "http",
      "url": "https://docs.auditynow.com/mcp",
      "headers": {
        "Authorization": "Bearer ${AUDITY_TOKEN}"
      }
    }
  }
}
```

Set the variable persistently on Windows:

```powershell
setx AUDITY_TOKEN "aky_your_token_here"
```

`setx` writes to the user environment but does not affect the shell that ran it; open a new terminal (and restart Claude Code) for it to take effect. If a referenced variable is unset and has no default, Claude Code fails to parse the config, so confirm the variable resolves with `echo %AUDITY_TOKEN%` (CMD) or `$env:AUDITY_TOKEN` (PowerShell) before launching.

#### 4.1.4 Smoke test

Open a fresh Claude Code session and prompt:

```
List my Audity projects.
```

Chief should call `listProjects` and return the real workspace projects. If it does, the connection is live and Chief now has the Audity operation set as first class tools. Save any returned project IDs; follow up prompts ("pull the deliverables for <id>", "patch the description on <id>") need them.

### 4.2 Path 2: Direct API via CLAUDE.md (zero dependency fallback)

Use this when `docs.auditynow.com` is unreachable from the environment, or when you want no external MCP dependency at all. Claude Code calls the REST API directly using its built in Bash tool. The tradeoff is that Chief constructs curl commands from a text description rather than calling typed, schema validated tools, so it is slightly more error prone and you must be explicit about the long synthesis timeout.

**Step 1.** Set the token in the shell that launches Claude Code. Persistent:

```powershell
setx AUDITY_TOKEN "aky_your_token_here"
```

Session only (PowerShell): `$env:AUDITY_TOKEN="aky_your_token_here"`. Session only (CMD): `set AUDITY_TOKEN=aky_your_token_here`. Or prefix a single session, which on Windows PowerShell looks like `$env:AUDITY_TOKEN="aky_..."; claude`.

**Step 2.** Add an Audity block to Chief's CLAUDE.md. Global lives at `%USERPROFILE%\.claude\CLAUDE.md`; project lives at the repo root. Paste this OB.1 maintained block (it teaches Chief the surface so it builds correct curls):

```markdown
## Audity (AI readiness audits + Nucleus memory)

Base URL: https://app.auditynow.com
Auth header on every call: `Authorization: Bearer $AUDITY_TOKEN`
Add `Content-Type: application/json` on writes. The token is in the AUDITY_TOKEN env var; never print it.

Use the Bash tool with curl. Long synthesis calls need an explicit long timeout.

Identity / account:
- GET  /api/user/current        identity check (run once at session start)
- GET  /api/user/tier           plan + gating; source of truth for what is allowed
- GET  /api/user/credits        balance; ALWAYS check before any write that costs credits

Projects / audits:
- GET  /api/projects                          list projects (status flags + progress)
- POST /api/projects                          create project (COSTS 1000 CREDITS)
- GET  /api/projects/{id}                     full project detail incl. documents
- PATCH /api/projects/{id}                    update project fields
- POST /api/projects/{id}/audit-analysis      run synthesis SYNCHRONOUSLY (60-300s; use --max-time 360)
- GET  /api/projects/{id}/audit-analysis      latest analysis (status: running|complete|failed)
- POST /api/agent/projects/{id}/audit-analysis/async   enqueue async job (needs current doc + interview analysis)
- GET  /api/agent/jobs/{id}                   poll job (pending|processing|completed|failed)
- GET  /api/projects/{id}/opportunities       opportunity list
- GET  /api/projects/{id}/deliverables        deliverables dashboard (wrapped: {success,data})

Leads:
- GET  /api/lead-generation/leads             list leads (wrapped: {data,pagination,filters})
- GET  /api/lead-generation/leads/{id}        one lead
- POST /api/lead-generation/leads/{id}/convert  convert to project (COSTS 1000 CREDITS, non-idempotent)

Nucleus memory:
- GET  /api/nucleus/memories?type=&projectId=    list (types: client|pattern|preference)
- POST /api/nucleus/memories                     create explicit memory {subject,content,memoryType,projectId}
- PATCH /api/nucleus/memories                    update {memoryId, subject?, content?}
- DELETE /api/nucleus/memories/{id}              soft delete (idempotent 204) -- prefer this form
- GET  /api/nucleus/captures?channel=&status=&projectId=   list captures
- GET  /api/nucleus/captures/{id}                capture + extracted items
- POST /api/nucleus/capture/note                 submit text note {content<=50000, projectId?} (30/hr)
- POST /api/nucleus/captures/{id}                reprocess a capture
- DELETE /api/nucleus/captures/{id}              soft delete capture
- GET  /api/nucleus/contacts?search=             list contacts
- POST/PATCH/DELETE /api/nucleus/contacts        body-passed id (contactId)
- GET  /api/nucleus/insights?type=&unreadOnly=   proactive insights
- GET  /api/nucleus/suggestions?projectId=       3 prompt suggestions

Rules:
- Reads are cheap. Writes cost credits/money. Never trigger create/convert/synthesis without explicit go-ahead.
- Always GET /api/user/credits before a credit-spending write.
- Rate limits: reads 100/min, writes 20/min, job polling 120/min, captures 30/hr. On 429 honor Retry-After.
```

**Step 3.** Start a new Claude Code session (CLAUDE.md is read at session start). Confirm with `echo %AUDITY_TOKEN%` that the variable is set in that shell.

### 4.3 Bringing Audity into the OB.1 org account

Chris's intent is to bring this functionality over into the org account so agents can align around OB.1 internal workflows. Read this before issuing tokens at scale, because Audity's v1 auth model is per user, not per org.

**Reality of the v1 model:**

- PATs are scoped to a single Audity user, capped at 10 per user, created and revoked only from that user's browser session. There is no org level service credential in v1.
- Row level security and ownership filters scope every read and write to the owning user's data. An agent authenticated with user A's PAT sees only user A's projects, leads, and Nucleus.
- Tier gating follows the owning user's plan. Team and Enterprise plans unlock seats, SSO, and higher quotas; contact Audity for Enterprise configuration.

**OB.1 implementation pattern:**

1. **Pick the owning seat.** Decide which Audity user owns the workspace the agent fleet should act inside (the one whose projects and Nucleus are the OB.1 system of record). Today that is Chris's Audity account; if OB.1 moves to a Team/Enterprise plan, designate the owning seat deliberately.
2. **Issue one PAT per agent surface, clearly labeled.** Do not share one token across agents. Suggested registry entries: `Chief - OB1AIRIG (read+write)`, `Buddy EA - Cowork (read+write)`, `Sales Commander - n8n prod (read+write)`, `CFO Agent - read only`. Per surface tokens give you blast radius isolation and let you revoke one agent without breaking the rest.
3. **Right size scopes.** Reporting only agents get `read`. Only agents that create projects, convert leads, write memories, or submit captures get `write`.
4. **Keep a token registry in OB1-Brain.** One row per token: label, purpose, owning agent, machine, scope, created date, rotation date. Because there is no PAT activity feed in v1, this registry plus your own logging layer is the audit trail.
5. **Rotate on a schedule and on suspicion.** Set a quarterly rotation. Revoke immediately on any suspected exposure. Reissue, update the env var, restart the agent.
6. **Never commit tokens.** Use env var expansion (4.1.3) for any committed `.mcp.json`; use the credential store for n8n and Cowork.

**Anthropic layer governance (for the OB.1 Claude org).** When Chief logs into Claude Code with the OB.1 claude.ai account, MCP servers added in claude.ai become available in Claude Code automatically; on Team and Enterprise only admins add them at claude.ai/customize/connectors. If OB.1 wants to centrally enforce which MCP servers agents may use on managed machines, Claude Code supports a managed configuration (`managed-mcp.json` with `allowedMcpServers` and `deniedMcpServers`) that no user or project setting can override. This is the enterprise control plane if the fleet grows.

### 4.4 Anthropic best practices to layer on (Claude Code + MCP)

These are general Claude Code behaviors that change how the Audity connector performs. Configure them once on OB1AIRIG.

- **Tool Search is on by default and is your friend.** Claude Code defers MCP tool definitions and loads them on demand, so adding Audity's ~30 tools costs almost no context. Leave it on. Control with `ENABLE_TOOL_SEARCH` (`auto`, `auto:N`, `true`, `false`). If you need Audity tools visible on every turn without a search step, set `"alwaysLoad": true` on the audity server entry, but use this sparingly because each upfront tool eats context.
- **Raise the MCP output ceiling for big audits.** Claude Code warns when a tool output exceeds 10,000 tokens and caps at 25,000 by default. The deliverables dashboard and full audit analysis can be large. If Chief truncates, raise it: `setx MAX_MCP_OUTPUT_TOKENS 50000`.
- **Mind timeouts on synthesis.** The synchronous audit endpoint blocks 60 to 300 seconds. MCP startup timeout is `MCP_TIMEOUT`; per tool execution timeout is `MCP_TOOL_TIMEOUT` or a per server `timeout` field in milliseconds. For direct curl, pass `--max-time 360`. If the project already has current document and interview analyses, prefer the async endpoint plus polling so a short client timeout cannot strand a paid call.
- **Manage servers explicitly.** `claude mcp list`, `claude mcp get audity`, `claude mcp remove audity`, and the in session `/mcp` panel are your control surface. Project scoped servers show as pending approval until accepted; `claude mcp reset-project-choices` clears those choices.
- **Treat the connector as untrusted input.** Anthropic flags prompt injection risk for any MCP server that fetches external content. Audity returns client data and AI generated text; do not let synthesis output silently drive a credit spending write. Keep a human or an explicit rule in the loop for create, convert, and synthesis.
- **Auto reconnect exists, do not panic on a blip.** HTTP servers reconnect with exponential backoff (up to five attempts) on mid session disconnect, and retry the initial connection up to three times on transient 5xx or timeout. Auth and not found errors are not retried because they need a config fix.

### 4.5 Verification and smoke test checklist

Run in order. Stop and fix at the first failure.

1. `claude mcp list` shows `audity` registered. If missing, re add (4.1.1).
2. `claude mcp get audity` shows the URL and the auth header configured. If listed but no tools, `claude mcp reload` + new session.
3. New session, `/mcp` shows audity green with a tool count above zero.
4. Prompt "run an identity check on Audity" or call `getCurrentUser`. Expect `userId` and `userEmail`. A `401 PAT_MALFORMED` means the token format or the doubled `Bearer` prefix is wrong; a `401` with no code means the token is shaped right but revoked or expired.
5. Prompt "what tier am I on and how many Audity credits do I have." Expect tier name plus `remaining`, `canCreateProject`, `nextReset`.
6. Prompt "list my Audity projects." Expect real projects.
7. Prompt "show me my unread Nucleus insights." Confirms Nucleus is enabled for this user. A `403` that is not `PAT_SCOPE_INSUFFICIENT` means Nucleus is disabled for the account.

### 4.6 Troubleshooting matrix

| Symptom | Cause | Fix |
| --- | --- | --- |
| Every call `401 PAT_MALFORMED` | Doubled `Bearer` prefix, or malformed token | Header must be exactly `Authorization: Bearer aky_<token>`. Remove the extra `Bearer`. If still failing, regenerate. |
| `401` with no code | Token revoked, expired, or never existed | Create a fresh token. |
| `403 PAT_SCOPE_INSUFFICIENT` | Token missing `write` | Revoke, reissue with Read + Write, update the env var or header. |
| `403 PAT_ROUTE_NOT_ALLOWED` | Route not on the agent allowlist (web research, billing, admin) | Use the web app for that action. |
| `403 PAT_NOT_SUPPORTED_FOR_ENDPOINT` | PAT hit a browser only route (PAT management) | PATs cannot manage PATs. Use the browser. |
| `403` on Nucleus, not a scope code | Nucleus not enabled for the user | Branch on `code`: if not `PAT_SCOPE_INSUFFICIENT`, treat as Nucleus disabled; check the account flag. |
| `503 PAT_DISABLED` | Agent API kill switch off | Contact support@auditynow.com. |
| Server registered, no tools appear | Stale session | `claude mcp reload`, start a new session. |
| Cannot reach the server | Network or proxy blocks `*.auditynow.com` | From OB1AIRIG, test reachability of `https://docs.auditynow.com/mcp`. Add an outbound firewall rule for `*.auditynow.com` if behind a proxy. |
| CLAUDE.md block ignored | Wrong path or stale session | Confirm `%USERPROFILE%\.claude\CLAUDE.md` (global) or repo root; start a new session. |
| Synthesis times out | Sync call exceeded client timeout | Use `--max-time 360`, or switch to async + poll. Verify with `GET /api/projects/{id}/audit-analysis` before re triggering, because re triggering an in flight synthesis wastes credits. |
| `429` mid batch | Write (20/min) or capture (30/hr) ceiling | Honor `Retry-After`, serialize writes, add delays. |

---

## 5. PART B: Nucleus configuration and best practices

Nucleus is the part Chris most wants right, because it is the cross engagement memory that the agent fleet will lean on. Get the mental model first, then the schemas, then the conventions.

### 5.1 The mental model

Nucleus has four object families, all under `/api/nucleus/*`:

- **Memories.** Durable facts and hypotheses. Three types and three source types (below). This is the long term knowledge.
- **Captures.** Raw text ingested from outside (transcripts, notes, emails). A background job extracts structured items (action items, decisions, key insights) from each capture. This is the intake funnel that feeds knowledge in.
- **Insights.** Proactive observations produced by background cron jobs (overdue follow ups, detected patterns, similar leads, stale clients). This is Nucleus telling you something unprompted.
- **Contacts.** A lightweight CRM (name, company, role, relationship type). This is the relationship index.

One distinction to hold firmly. The Nucleus **store** persists across every engagement and session; that is the whole point. But a Nucleus chat **session** is context aware, not persistent between sessions, meaning the conversational thread resets even though the stored memories do not. For the agent API this matters because your agent IS the conversational layer; you read and write the persistent store directly and carry session context yourself.

### 5.2 Data models (full field shapes)

**Memory** (`nucleus_memories`):

| Field | Type | Notes |
| --- | --- | --- |
| `id` | uuid | |
| `memoryType` | enum | `client` (facts about a specific client/project), `pattern` (cross client insight you developed), `preference` (your working style). Default `client`. |
| `subject` | string, required | Short label, e.g. "Initech security posture". |
| `content` | string, required | The full memory text. |
| `sourceType` | enum | `explicit` (user asserted), `extracted` (pulled from a capture), `detected` (hypothesis from a background job). API created memories are `explicit`. |
| `confidence` | number | High confidence explicit memories are facts; detected patterns are hypotheses. |
| `userId` | string | Owner. |
| `projectId` | uuid \| null | Optional link to a project. |
| `stakeholderId` | uuid \| null | Optional link to a stakeholder. |
| `timesRetrieved` | integer | How often it has been surfaced. |
| `createdAt`, `updatedAt` | datetime | |

Memories are automatically embedded for semantic search on create.

**Capture** (`nucleus_captures`):

| Field | Type | Notes |
| --- | --- | --- |
| `id` | uuid | |
| `channel` | enum | One of 8: `transcript`, `voice_note`, `text_note`, `email`, `calendar`, `zoom`, `crm_sync`, `file_drop`. The text note API creates `text_note`. |
| `rawContent` | string | Original captured content. |
| `status` | enum | `pending`, `processing`, `processed`, `needs_review`, `failed`. |
| `capturedAt` | datetime | |
| `userId`, `projectId` | | Owner and optional project link. |
| `contentType` | string | MIME style label. |
| `processedContent` | string \| null | Cleaned/normalized version from the extraction job. |
| `processingResults` | object \| null | Structured extraction: action items, decisions, key insights, contact mentions. |
| `createdAt`, `updatedAt` | datetime | |

**Insight:**

| Field | Type | Notes |
| --- | --- | --- |
| `id` | uuid | |
| `type` | enum | See 5.6. |
| `title`, `body` | string | |
| `isRead` | boolean | |
| `isDismissed` | boolean | |
| `projectId` | uuid \| null | |
| `createdAt` | datetime | |

**Contact** (lightweight CRM):

| Field | Type | Notes |
| --- | --- | --- |
| `id` | uuid | |
| `name` | string, required | Trimmed on save. |
| `email`, `phone`, `company`, `role`, `notes` | string \| null | |
| `relationshipType` | enum \| null | `client`, `prospect`, `partner`, `referral`. Silently coerced to null if not one of these. |
| `lastInteractionAt` | datetime \| null | |
| `createdAt` | datetime | |

### 5.3 The full Nucleus endpoint surface

| Capability | Endpoint | Notes |
| --- | --- | --- |
| List memories | `GET /api/nucleus/memories?type=&projectId=` | Filter by type and project. |
| Create memory | `POST /api/nucleus/memories` | Body `{subject, content, memoryType, projectId}`. Source defaults to `explicit`. Returns 201 with the memory. |
| Update memory | `PATCH /api/nucleus/memories` | Body `{memoryId, subject?, content?}`. ID is in the body, not the path. At least one of subject/content required. Returns `{success:true}`. |
| Delete memory (preferred) | `DELETE /api/nucleus/memories/{id}` | Soft delete (`is_archived=true`). Idempotent 204. |
| Delete memory (alt) | `DELETE /api/nucleus/memories` | Body `{memoryId}`. Returns 200; returns 500 on failure rather than 204. Prefer the path form. |
| List captures | `GET /api/nucleus/captures?channel=&status=&projectId=` | Wrapper `{captures: [...]}`. |
| Get capture + items | `GET /api/nucleus/captures/{id}` | Returns `{capture, items}` with the extracted action items, decisions, key insights. |
| Submit text capture | `POST /api/nucleus/capture/note` | Body `{content (<=50,000 chars), projectId?}`. Wrapper `{capture}`, status `pending`. Async extraction runs ~15 to 60 seconds. Rate limited 30/hour. |
| Reprocess capture | `POST /api/nucleus/captures/{id}` | Resets status to `pending` and re runs extraction. Use after a failure. |
| Delete capture | `DELETE /api/nucleus/captures/{id}` | Soft delete, idempotent. |
| List contacts | `GET /api/nucleus/contacts?search=` | Search matches name + company, case insensitive. Wrapper `{contacts: [...]}`. |
| Create contact | `POST /api/nucleus/contacts` | Only `name` required. Returns the contact directly, NOT wrapped under `{contact}`. |
| Update contact | `PATCH /api/nucleus/contacts` | Body `{contactId, ...fields}`. At least one field. 404 if not owned. |
| Delete contact | `DELETE /api/nucleus/contacts` | Body `{contactId}`. Hard delete. Returns `{success:true}`. |
| List insights | `GET /api/nucleus/insights?type=&unreadOnly=&limit=25` | Background generated. |
| Prompt suggestions | `GET /api/nucleus/suggestions?projectId=` | Returns 3 contextual prompt strings. |

Two response shape traps worth memorizing: contacts come back **unwrapped** on create but **wrapped** (`{contacts}`) on list; memory and contact updates and deletes pass the ID **in the body**, not the path (except the preferred path form delete for memories).

### 5.4 Memory type and source type, the working model

`memoryType` is what the memory is about; `sourceType` is how Nucleus knows it.

- `client` memory: a fact about one engagement. Scope it with `projectId`. Example subject "Berman Killeen HIPAA posture".
- `pattern` memory: a reusable cross client lesson. Leave `projectId` null. Example subject "Healthcare data governance lift".
- `preference` memory: how the consultant (or OB.1) likes to work. Leave `projectId` null. Example subject "OB.1 deliverable cadence".

- `explicit`: a human or agent asserted it on purpose (everything you create via the API). Highest trust; treat as fact.
- `extracted`: pulled from a capture by the extraction job. Trust but verify.
- `detected`: a hypothesis a background job inferred. Treat as a lead, not a fact, and weigh `confidence`.

When Chief reads memory to inform a deliverable, prefer high confidence `explicit` memories as ground truth and label `detected` content as hypothesis.

### 5.5 The capture pipeline

A capture is the on ramp for outside text. Flow:

1. Chief submits a note: `POST /api/nucleus/capture/note` with the raw text and an optional `projectId`. Response wraps it as `{capture}` with `status: pending`.
2. An Inngest background job processes it asynchronously (roughly 15 to 60 seconds), moving status through `processing` to `processed` (or `needs_review` / `failed`).
3. Chief polls `GET /api/nucleus/captures/{id}` and reads `{capture, items}`; `items` holds the extracted action items, decisions, and key insights.
4. On `failed`, `POST /api/nucleus/captures/{id}` reprocesses.

Constraints: content up to 50,000 characters; 30 captures per hour per user. For OB.1 this is the bridge from Granola transcripts and meeting notes into Nucleus, mirrored into the Notion Decisions Log. Note the v1 ceiling: the API only creates `text_note` captures; the other seven channels are populated by Audity's own integrations, not the agent API.

### 5.6 Insights, what is live vs reserved

`GET /api/nucleus/insights` can return eight types, but only four are actually generated by background jobs in v1. Do not promise the reserved four to clients as if they are live.

| Type | Status in v1 | Meaning |
| --- | --- | --- |
| `overdue_followup` | LIVE | A lead or client you said you would follow up with, where the date has passed. |
| `pattern_detected` | LIVE | A cross client pattern Nucleus noticed in your portfolio. |
| `similar_lead` | LIVE | A new lead matches the profile of a past project. |
| `stale_client` | LIVE | A client quiet long enough to risk going cold. |
| `pre_meeting` | reserved | In the schema, not yet produced. |
| `referral_opportunity` | reserved | In the schema, not yet produced. |
| `portfolio_insight` | reserved | In the schema, not yet produced. |
| `content_suggestion` | reserved | In the schema, not yet produced. |

Use `?unreadOnly=true` for a clean queue. This is the natural input to a daily OB.1 pipeline sweep.

### 5.7 Best practices (Audity plus Anthropic memory principles)

**From Audity's own guidance:**

- Write an explicit memory the moment Chief learns something during a conversation that should outlive the session. That is exactly what `POST /api/nucleus/memories` is for.
- Keep `subject` short and specific; it is the label that makes the memory findable. Put the substance in `content`.
- Use `projectId` discipline. Client facts get a `projectId`; patterns and preferences do not. This keeps `GET /api/nucleus/memories?type=client&projectId=<id>` clean per engagement.
- Capture transcripts as captures, not memories. Let the extraction job distill them; then promote the distilled facts to explicit memories.
- Prefer the idempotent path form delete for memories so retries are safe.

**From Anthropic's memory and context engineering principles, applied to Nucleus:**

- Memory is a tool for continuity, not a dumping ground. Store decisions, durable facts, and stable preferences. Do not store transient chatter or anything you would not want surfaced unprompted later.
- Be careful with sensitive content. Nucleus memories can be retrieved into future contexts automatically. Do not write anything into a memory that should not resurface in an unrelated future session.
- Treat low confidence `detected` memories as hypotheses and let them earn their place. Validate before acting.
- Keep memories concise and self contained so they read well out of context, the same way a good CLAUDE.md entry reads.

### 5.8 Enabling, disabling, and what is not exposed

- **Disable at the environment level** (self hosted or enterprise): set `NUCLEUS_ENABLED=false` before starting the server. This hides the Nucleus panel and toggle for all users in that deployment. For OB.1's hosted use this stays on.
- **Per user gating:** if Nucleus is not enabled for the account (a free Nucleus flag), Nucleus writes return `403`. Branch on the `code` field: `PAT_SCOPE_INSUFFICIENT` means a scope problem, anything else means Nucleus is disabled.
- **Not exposed to agents, on purpose:** `/api/nucleus/chat` (your agent is the chatbot; use the underlying memory and capture endpoints), `/api/nucleus/live` (real time co pilot, needs a UI), backfill and admin operations (internal), and slash commands (internal chat affordances).

### 5.9 OB.1 Nucleus conventions (write these down and follow them)

To keep Nucleus aligned with the Notion spine and the OB1-Brain vault, OB.1 standardizes how agents write memory. Chief follows these:

- **Subjects are addressable.** Lead a client memory subject with the client name as it appears in the Notion Companies database, e.g. "Berman Killeen: HIPAA scoping status". Lead a pattern with the domain, e.g. "Pattern: forensic psychology automation phasing".
- **One fact per memory.** If it has two clauses joined by "and", it is two memories. Findable beats comprehensive.
- **projectId is mandatory for client memories.** Resolve the Audity project ID once per engagement and reuse it. Patterns and preferences never carry a projectId.
- **Promote, do not duplicate.** Transcript goes in as a capture; the distilled decision becomes an explicit memory and a row in the Notion Decisions Log. Do not paste a whole transcript as a memory.
- **No em dashes, ever**, including inside memory content, per OB.1 writing rules.
- **Mirror, do not fork.** Nucleus is the readiness and discovery memory; Notion remains the system of record for deals and engagements. When the two could drift, Notion wins and Chief updates Nucleus to match.

---

## 6. PART C: The audit pipeline (so Chief can align internal workflows)

This is the production line OB.1 is wrapping agents around. Chief should understand the full arc even though several steps are web app only in v1.

### 6.1 The 13 step lifecycle

```
1. Project setup   ->  2. Client profile   ->  3. Web intelligence  ->  4. Discovery
->  5. Documents   ->  6. Interviews       ->  7. Analysis          ->  8. Frameworks
->  9. ROI calculations  ->  10. Stakeholder memos  ->  11. Opportunity matrix
->  12. Final report     ->  13. Deliverables
```

The dashboard renders these as a lifecycle stepper with status badges (Complete, In progress, Locked, Available, Attention), summary cards (opportunities, documents, interviews, framework radar, estimated ROI), and an activity feed.

### 6.2 What the agent can drive vs what is web app only

| Step | Agent can drive? | Endpoint / note |
| --- | --- | --- |
| Create project | Yes | `POST /api/projects` (1,000 credits). Returns status `setup`. |
| Upload documents | No (v1) | Web app only. Multipart upload is coming in v2. Agents read documents via project detail. |
| Run analysis / synthesis | Yes | `POST /api/projects/{id}/audit-analysis` (synchronous, 60 to 300s) or async + poll. |
| Read opportunities | Yes | `GET /api/projects/{id}/opportunities`. |
| Read deliverables | Yes | `GET /api/projects/{id}/deliverables`. |
| Web research | No (v1) | Route exists, not on the agent allowlist; runs from the web app. |
| Stakeholder CRUD | No (v1) | Low agent leverage in v1. |
| Deliverable regeneration | No (v1) | Produced by the synthesis pipeline; agents read, they do not re trigger. |

### 6.3 The deliverables shape

`GET /api/projects/{id}/deliverables` returns `{success:true, data:{...}}` with:

- `executiveSummary`: high level AI readiness narrative.
- `opportunities[]`: each with `title`, `category` (`quick_wins`, `big_swings`, `nice_to_haves`, `deprioritize`), `impactScore` (1 to 10), `effortScore` (1 to 10), `roiPotential` (free text, e.g. "$200K annually"), `implementationTimeline`, plus strategy, dependencies, and risk mitigation fields.
- `risks[]`: `title`, `severity` (`low`, `medium`, `high`, `critical`), `description`.
- `stakeholderMemos[]`: `stakeholderName`, `stakeholderRole`, `memo`.

Returns 404 if no analysis has run yet, so call synthesis first. The opportunity matrix (impact vs effort) is the artifact OB.1 leans on for the Operational Blueprint.

### 6.4 Credits and tiers (the cost model)

Credits are the unit of consumption for AI intensive operations. They reset each billing period and do not roll over.

| Operation | Credit cost |
| --- | --- |
| Create a project (`POST /api/projects`) | 1,000 |
| Convert a lead (`POST /api/lead-generation/leads/{id}/convert`) | 1,000 |
| Trigger audit analysis (`POST /api/projects/{id}/audit-analysis`) | Varies by depth |

`GET /api/user/credits` returns `remaining`, `allocated`, `used`, `usagePercentage`, `lastReset`, `nextReset`, `daysUntilReset`, `canCreateProject`, `projectCreationCost`, `projectsRemaining`, `billingProvider` (`paddle` or `stripe`), and a `tier` object. Tier enum ids: `solo`, `starter`, `growth`, `agency`, `team`, `professional`, `enterprise`, `scale`.

Gating rules: a `402` means insufficient credits; a `403` with `requiredTier` and `upgradeUrl` means the plan does not include the feature. Public pricing names move faster than the enum, so treat `GET /api/user/tier` as the source of truth. The published credit and seat numbers in the docs are explicitly flagged as placeholders pending confirmation; verify against the live pricing page before quoting them to anyone.

### 6.5 Three OB.1 ready recipes

**Recipe 1, minimum viable audit (fast read on a client).**
`POST /api/projects` to create (1,000 credits, returns `{id, status:"setup"}`), then `POST /api/projects/{id}/audit-analysis` synchronously (set client timeout to at least 360s), then `GET /api/projects/{id}/opportunities` and `GET /api/projects/{id}/deliverables` to read the matrix and summary. Chief synthesizes, citing the opportunity IDs.

**Recipe 2, document backed audit (deeper).**
Documents are uploaded in the web app first. Chief calls `GET /api/projects/{id}` to confirm documents are present, then triggers synthesis (sync, or async if current document and interview analyses already exist), then compares against the prior analysis (`GET /api/projects/{id}/audit-analysis` returns the most recent; multiple versions are stored) and synthesizes the diff.

**Recipe 3, lead triage and convert.**
`GET /api/lead-generation/leads?status=active&sortBy=ai_readiness_score&sortOrder=desc&limit=50` (wrapped `{data, pagination, filters}`). Filter client side for `surveyStatus !== 'converted'` and recent `createdAt` (the list endpoint has no `since` parameter). Check `surveyStatus` before converting and skip already converted leads. `POST /api/lead-generation/leads/{id}/convert` spends 1,000 credits, is non idempotent (re calling a converted lead returns 400), and returns `{success:true, data:{auditId, creditsUsed, pdfAttached}}`. Always check `GET /api/user/credits` before a batch; respect the 20/min write and 120/min poll ceilings.

---

## 7. Complete API reference: the PAT route allowlist (v1)

The allowlist is intentionally narrow. Anything outside it returns `403 PAT_ROUTE_NOT_ALLOWED`.

**Account / identity**
- `GET /api/user/current`: identity check (`userId`, `userEmail`, auth metadata). Operation `getCurrentUser`.
- `GET /api/user/tier`: plan + gating, source of truth. Operation `getCurrentTier`.
- `GET /api/user/credits`: balance and reset. Operation `getCredits`.

**Projects / audits**
- `GET /api/projects`: list (`listProjects`).
- `POST /api/projects`: create, 1,000 credits (`createProject`).
- `GET /api/projects/{id}`: detail incl. documents (`getProject`).
- `PATCH /api/projects/{id}`: update (`patchProject`).
- `POST /api/projects/{id}/audit-analysis`: synchronous synthesis (`triggerAuditAnalysis`).
- `GET /api/projects/{id}/audit-analysis`: latest analysis (`getAuditAnalysis`).
- `POST /api/agent/projects/{id}/audit-analysis/async`: enqueue async job (`triggerAsyncAuditAnalysis`).
- `GET /api/agent/jobs/{id}`: poll job (`getJobStatus`).
- `GET /api/projects/{id}/opportunities`: opportunities (`listOpportunities`).
- `GET /api/projects/{id}/deliverables`: deliverables dashboard (`getDeliverables`).

**Leads**
- `GET /api/lead-generation/leads`: list (`listLeads`).
- `GET /api/lead-generation/leads/{id}`: one lead (`getLead`).
- `POST /api/lead-generation/leads/{id}/convert`: convert, 1,000 credits, non idempotent (`convertLead`).

**ReadyLinks** (survey distribution links + lead tracking; feature gated on `multiReadyLink`)
- `GET/POST/PATCH/DELETE /api/agent/readylinks` and `/api/agent/readylinks/{id}`.

**Assessment configs** (templates for ReadyLink assessments)
- `GET/POST/PATCH/DELETE /api/agent/assessment-configs` and `/api/agent/assessment-configs/{id}`.

**Nucleus** (all documented in Section 5.3)
- `/api/nucleus/memories`, `/api/nucleus/captures`, `/api/nucleus/capture/note`, `/api/nucleus/contacts`, `/api/nucleus/insights`, `/api/nucleus/suggestions`.

**Browser session only (NOT PAT accessible):** `POST/GET/DELETE /api/user/api-keys` (PAT management). A PAT here returns `403 PAT_NOT_SUPPORTED_FOR_ENDPOINT`.

---

## 8. Error codes and rate limits, consolidated

**HTTP status guide**

| Status | Meaning | Action |
| --- | --- | --- |
| 200 / 201 / 202 / 204 | Success (202 = async job enqueued; 204 = no content) | Continue |
| 400 | Validation failed; codes include `EMPTY_PATCH`, `DESCRIPTION_TOO_LONG`, `INVALID_DESCRIPTION_TYPE`. Also "lead already converted". | Fix the body / skip converted leads |
| 401 `PAT_MALFORMED` | Token format invalid | Regenerate (and check the doubled `Bearer`) |
| 401 (no code) | Token does not resolve (revoked/expired/never existed) | New token |
| 402 | Insufficient credits, or estimated cost exceeds limit | Top up or upgrade; check `GET /api/user/credits` first |
| 403 `PAT_SCOPE_INSUFFICIENT` | Missing scope | Reissue with `write` |
| 403 `PAT_ROUTE_NOT_ALLOWED` | Route not on allowlist | Use the web app |
| 403 `PAT_NOT_SUPPORTED_FOR_ENDPOINT` | PAT hit a browser only route | Use the browser |
| 403 (tier) | Plan lacks the feature; body has `requiredTier`, `upgradeUrl` | Upgrade |
| 404 | Not found, or not owned (RLS) | Check the ID and ownership |
| 409 | Active token cap reached (10) | Revoke an old token |
| 413 | Content too large to analyze | Reduce input |
| 422 | Missing prerequisite analysis records (async audit) | Use the sync endpoint for the end to end path |
| 429 | Rate limit exceeded; `Retry-After` in seconds | Back off and retry |
| 500 / 502 / 503 | Server side or kill switch (`PAT_DISABLED`) | Exponential backoff; if persistent, contact support |

**Rate limits** (per token): reads 100/min, writes 20/min, async polling 120/min, captures 30/hour, audit synthesis lower internal guardrails.

---

## 9. v1 boundaries (what is not exposed, and why)

Audity ships the v1 agent surface deliberately small. These are intentional exclusions; do not build OB.1 workflows that assume them, and do not promise them to clients:

- **Document file upload (multipart).** Web app only; v2 will add it. Agents read uploaded documents via project detail and run analysis on what is already there.
- **Real time Nucleus co pilot (`/live`) and Nucleus chat (`/api/nucleus/chat`).** Need a UI; your agent is the conversational layer.
- **Web research** (`POST /api/projects/{id}/web-research`). Route exists, not on the allowlist; runs from the web app.
- **Deliverable regeneration.** Produced by synthesis; agents read, they do not re trigger.
- **Streaming responses.** Audity returns structured output, not token by token completion. Stream prose with your own model; use Audity for synthesis, memory, and project state.
- **Stakeholder CRUD** and **admin routes.** Internal or low leverage in v1.
- **PAT management via PAT.** Browser session only.

If OB.1 needs any of these sooner, the docs explicitly invite a request to Audity. That is a channel partner conversation worth having if a workflow depends on document upload or web research at scale.

---

## 10. OB.1 activation plan (concrete next steps)

Sequenced so Chris and Chief can execute today. Recovery, Family, Revenue, Growth stays the order of operations; this is Revenue and Growth infrastructure.

1. **Issue Chief's token.** Chris signs in to app.auditynow.com, Settings to API Tokens, creates `Chief - OB1AIRIG` with Read + Write, copies it once. Log it in the OB1-Brain token registry with a quarterly rotation date. Do not paste it into chat.
2. **Connect Chief (Path 1, user scope).** On OB1AIRIG, run the `claude mcp add --transport http --scope user audity ...` command from 4.1.1 with the token in the header. Verify with the 4.5 checklist. If `docs.auditynow.com/mcp` is blocked, fall back to Path 2 with the CLAUDE.md block.
3. **Run the smoke test.** Identity check, tier, credits, list projects, list unread insights. Confirm Nucleus is enabled. Stop and flag if any step fails.
4. **Wire the read only sweeps first.** Stand up a daily Cowork or Chief task that calls `GET /api/user/credits`, `GET /api/lead-generation/leads` (triage), and `GET /api/nucleus/insights?unreadOnly=true`, then posts a digest to the OB.1 pipeline. Reads are free; this proves the loop with zero credit risk.
5. **Codify the write guardrail.** Before any agent runs `createProject`, `convertLead`, or `triggerAuditAnalysis`, it must (a) check credits, and (b) have an explicit instruction or an authorized standing workflow. Encode this in Chief's CLAUDE.md and in the Cowork task prompts.
6. **Adopt the Nucleus conventions (5.9).** Add them to the OB.1 SOP and to Chief's CLAUDE.md so memory stays aligned with the Notion spine. Decide the promote rule: transcript to capture to distilled explicit memory to Notion Decisions Log row.
7. **Plan the org model (4.3).** When OB.1 moves Audity onto a Team or Enterprise seat, designate the owning seat, issue per agent tokens, and stand up the managed MCP control plane if the fleet grows beyond Chief.
8. **Train the humans.** This document is the curriculum. A new OB.1 teammate reads Sections 1, 3, 5, and 6 to understand the methodology, then watches Chief run Recipe 1 end to end. The audit pipeline plus Nucleus is the OB.1 discovery muscle; the agents are how it scales.

---

## 11. Source index

All facts above are drawn from the Audity for Agents documentation and Anthropic's Claude Code documentation as of the build date. Primary sources:

**Audity (docs.auditynow.com)**
- /introduction, /quickstart, /api-quickstart
- /authentication (auth, scopes, rate limits, error codes, logging, v1 scope)
- /guides/claude, /guides/claude-code, /guides/cursor, /guides/chatgpt, /guides/n8n
- /guides/working-with-nucleus, /guides/running-an-audit, /guides/lead-conversion
- /guide/nucleus/overview, /guide/nucleus/asking-questions, /guide/nucleus/memory-and-context
- /guide/run-an-audit/overview, /guide/run-an-audit/documents, /guide/run-an-audit/project-dashboard
- /guide/reference/error-codes, /guide/reference/glossary, /guide/reference/tier-limits, /guide/reference/file-types
- /guide/account-billing/credits-and-usage, /guide/account-billing/ai-provider
- /api-reference/* (account, projects, leads, jobs, readylinks, assessment-configs, nucleus)
- OpenAPI spec: docs.auditynow.com/api-reference/openapi.json
- Support: support@auditynow.com

**Anthropic (code.claude.com / docs.claude.com)**
- code.claude.com/docs/en/mcp (Connect Claude Code to tools via MCP: transports, scopes, env var expansion, OAuth, headersHelper, tool search, output limits, managed MCP, security)
- docs.claude.com/en/docs/claude-code/overview (Claude Code overview)

---

*Buddy's note to Chris, Chloe, and Claudia:* this brief is built to the OB.1 standard and is ready to drop into Chief's context or the OB1-Brain vault as is. Two items are governance decisions only you can make, so I am flagging them rather than assuming: first, the org seat question in 4.3 (Audity has no org level service token in v1, so the owning Audity seat is a deliberate choice, not a default); second, the v1 boundaries in Section 9 (document upload and web research are web app only, so any workflow that depends on them at scale is a channel partner conversation with Audity, not a config change). Everything else is execution ready. Rules before tools.
