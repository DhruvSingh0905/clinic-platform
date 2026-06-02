---
tags: [ops, mvp, plan]
status: living
updated: 2026-06-01
---

# MVP plan

## The MVP is a prop, not a product
Coaches can't imagine what's possible — show them. The MVP's only job is to produce the demo moment in a coach conversation and let them point at what they want. Start with **diagrams + clickable mock**, not a working system. Iterate on what people ask for. Building the real multi-tenant system before the conversations is the failure mode (see [[wiki/ops/customer-discovery]]).

## The demo moment (the one thing the mock must land)
One client → Whoop HR/HRV drift + nutrition + a lab → domain-aware detector fires → **one-line ranked finding in the coach's roster queue** → coach reaction: "I'd never have spotted that across three apps."

That single end-to-end thread IS the pitch. Everything else is set dressing.

## Phase 0 — Clickable mock ✅ BUILT (2026-06-01)
**Status: built.** Not a static Figma mock — a working Next.js + FastAPI app with mock data, running on `localhost:3001` (frontend) and `localhost:8001` (backend). 28 Playwright E2E tests pass.

### What exists
A Next.js 16 / React 19 frontend + FastAPI backend with SQLite, seeded with 6 mock clients. The demo thread works end-to-end: mock clients have wearable data, labs, compound stacks, and detector findings → the coach sees a severity-ranked roster queue → clicks through to a client detail view with cross-metric patterns.

Both views built:
1. **Coach roster queue** — 6 mock clients, severity-ranked (concerning → notable → info). Each card shows athlete name, phase badge, integration icons, top finding headline, signals with directional arrows, finding count. Click navigates to client detail.
2. **Client detail** — collapsible sections: Findings (severity-colored, expandable summaries, signal badges), Wearables (grouped by metric with sparkline charts from 30 days of data), Lab Results (grouped by category, flag-colored), Substance Log (read-only, lock icon, "Athlete self-reported" label, compound timeline + estimated drug level bars), Training (active block + "Set New Block" form), Nutrition (calorie/macro breakdown + "Update Targets" form), Recovery Notes ("Add Note" form).
3. **Athlete view** — personal dashboard with sync status, active findings, wearable trend cards with sparklines, drug level progress bars labeled "Estimated from logged protocol", and substance logging forms (Start/Stop/Dose Change).

### What is mock data, not real
- All 6 clients and their data are seeded from `.src/coach/mock_data.py`. No real data flows.
- Wearable data is generated with synthetic trend profiles (e.g. Jordan's HR trending up, Riley's HRV recovering).
- Lab results are manually specified realistic values.
- Findings are hand-written summaries mimicking what CDE's detectors would produce. CDE's actual detector code is not connected.
- Drug levels are pre-computed static values. CDE's PK model is not connected.
- No OAuth, no real Whoop/Apple Health sync, no real bloodwork extraction.

### What is real code, not mock
- The FastAPI backend serves real API responses from SQLite — not hardcoded JSON in the frontend.
- The typed operation set (`.src/coach/operations.py`) enforces the substance boundary: `commit_operation()` raises `PermissionError` if a coach actor attempts `UserLogSubstanceEvent`.
- The operation log table records every committed operation with actor, role, type, payload, and deterministic rendered text.
- The multi-tenant schema (coach → athlete relationship, per-client isolation in queries) is real, not faked.
- The coach write surface forms (training/nutrition/recovery) call real API endpoints that commit through the typed operation path.
- The substance mirror in the client detail view has zero interactive elements — verified by 6 Playwright tests that assert no inputs, no buttons, no action affordances in that section.

### Stack
- Backend: Python 3.13 / FastAPI / SQLite / Pydantic / uvicorn. Source: `.src/coach/`.
- Frontend: Next.js 16 / React 19 / TypeScript / Tailwind CSS 4 / framer-motion / Recharts. Source: `.frontend/`.
- Fonts: Crimson Pro (headings), Outfit (body), IBM Plex Mono (data values).
- Tests: 28 Playwright E2E tests across landing, roster, client detail, substance read-only enforcement, and athlete dashboard.

### How to run
```bash
# Backend (terminal 1)
cd "Coach Platform" && source .venv/bin/activate && python -m coach
# → http://localhost:8001

# Frontend (terminal 2)
cd "Coach Platform/.frontend" && pnpm dev
# → http://localhost:3001

# Tests
cd "Coach Platform/.frontend" && npx playwright test
```

### What this is NOT
This is a demo prop with mock data. It is not the real multi-tenant system. CDE's engine (extraction, PK, detectors, integrations) is not connected. There is no auth, no real data sync, no billing. The original Phase 0 spec called for "faked data, no backend" — what was built exceeds that (it has a real backend with a real schema), but it is still a prop. The customer-discovery gate still applies before Phase 1.

## Phase 0.5 — Use the existing CDE system as a live prop
The founder already has working CDE on personal data (detectors, PK, display). Show the *enhanced-athlete-aware detector output* on real data in coach conversations NOW, before the coach mock is polished. Tests whether the consolidation + detection value lands without building anything coach-specific.

## Phase 1 — Real data, CDE engine connected (ONLY after customer-discovery gate passes)

The Phase 0 build proved the UI and the data model work. Phase 1 replaces mock data with CDE's actual engine — real detectors, real PK model, real extraction, real wearable sync. One consenting coach, a handful of their clients.

### What CDE already provides (code-level audit, 2026-06-01)

All CDE functions already accept a `user_id` parameter (defaulting to `"default"`). The adaptation is: pass explicit `athlete_id` instead of relying on the default. No rewrite — parameter threading.

| CDE component | Location | Interface | Reuse cost |
|---|---|---|---|
| Detector orchestrator | `cde.detectors.themes.run_all_detectors(conn, user_id, as_of)` | Returns list of Finding objects. Calls all 8 theme detectors. | Pass athlete_id instead of default user_id. |
| Individual detectors | `cde.detectors.themes.detect_cardiovascular_stress(conn, user_id, as_of)` etc. | Each returns Finding or None. Uses `get_metric_series()`, `get_wearable_series()`, `get_active_compounds()` from framework. | Same — explicit athlete_id. |
| Framework query helpers | `cde.detectors.framework.get_metric_series(conn, metric_loinc, user_id, start_date, end_date)` | Returns list of (date, value) tuples from metric_observation. | Same. |
| PK drug-level model | `cde.store.pk_model.generate_drug_levels(conn, user_id, start_date, end_date)` | Reads compound_event, writes drug_level table. Returns row count. | Same. Depends on COMPOUNDS dict from `cde.ingestion.compound_db`. |
| Bloodwork extraction | `cde.extraction.extractor` | Uses Claude Vision API. Returns structured ExtractionResponse with per-field confidence. Stateless — no user_id dependency. | Attach athlete_id when writing extracted results to DB. |
| Apple Health import | `cde.ingestion.apple_health` | Streaming XML parse. Maps Apple Health type identifiers to canonical metric names. | Thread athlete_id through parse → DB write. |
| Integration base class | `cde.integrations.base.IntegrationAdapter` | ABC with `get_auth_url()`, `exchange_code()`, `refresh_tokens()`, `sync(conn, config)`. IntegrationConfig has user_id field. | Set athlete_id in IntegrationConfig. sync() receives it via config. |
| Whoop adapter | `cde.integrations.whoop.WhoopAdapter` | OAuth flow + data pull. Registered via @register_integration. | Works through the base class pattern above. |
| Compound library | `cde.ingestion.compound_db.COMPOUNDS` | Dict of 86 compounds with half-lives, classes, monitoring markers. | Reference data. Import directly. |
| LOINC mappings | `cde.extraction.loinc` | Canonical metric name → LOINC code mappings. | Reference data. Import directly. |

### The integration approach

CDE's code lives in `../Cycle Data Engine/.src/cde/`. The Coach Platform imports from it as a library — `from cde.detectors.themes import run_all_detectors`. This requires CDE's package to be importable (install it as an editable dependency or add its `.src/` to the Python path). The Coach Platform does NOT modify CDE code.

The Coach Platform's own database schema (`.src/coach/database.py`) already matches CDE's table names and column conventions. CDE's functions expect a `sqlite3.Connection` with the right tables — the Coach Platform's DB has those tables. The connection passed to CDE functions is the Coach Platform's multi-tenant database, scoped by athlete_id.

### Phase 1 build list

**1. Connect CDE as a dependency**
- Add `../Cycle Data Engine` as a dependency in `pyproject.toml` (editable install or path dependency).
- Verify CDE's functions work against the Coach Platform's database schema — the table structures match by design, but column-level compatibility needs a test.

**2. Wire detectors to real data**
- After any data write (wearable sync, lab upload, compound event), call `run_all_detectors(conn, athlete_id)`.
- Store returned Finding objects in the Coach Platform's `finding` table (same schema as CDE's).
- Replace mock findings with real detector output. The roster queue already sorts by severity — it will rank real findings the same way.

**3. Wire PK model**
- After compound events are logged, call `generate_drug_levels(conn, athlete_id, start_date, end_date)`.
- Replace mock drug levels with computed values. The substance mirror and athlete dashboard already display them.

**4. Bloodwork upload endpoint**
- Add `POST /api/athlete/{athlete_id}/upload` endpoint. Accept PDF/image.
- Call CDE's extraction pipeline (`cde.extraction.extractor`). Write extracted results to `metric_observation` with the athlete's ID.
- Run detectors after extraction.
- The client detail view already renders lab results from `metric_observation` — no frontend change needed.

**5. Apple Health import endpoint**
- Add `POST /api/athlete/{athlete_id}/import/apple-health` endpoint. Accept ZIP/XML.
- Call CDE's Apple Health parser. Write to `wearable_observation` with athlete_id.
- Run detectors after import.
- The wearable cards already render from `wearable_observation` — no frontend change needed.

**6. Whoop OAuth + sync**
- Add OAuth flow endpoints: `GET /api/athlete/{athlete_id}/integrations/whoop/auth-url`, `GET /auth/whoop/callback`.
- Store tokens in `integration_status` table (already exists).
- Add `POST /api/athlete/{athlete_id}/integrations/whoop/sync` endpoint.
- Call CDE's `WhoopAdapter.sync(conn, config)` with athlete_id in the config.
- Run detectors after sync.
- The integration badges in the frontend already read from `integration_status`.

**7. Auth — minimal, not enterprise**
- Athlete signup/login: email + password or magic link. One athlete per account.
- Coach signup/login: same. Coach invites athlete by email → creates coach_athlete row.
- Session tokens (JWT or cookie). Middleware that sets `athlete_id` or `coach_id` on the request.
- The API endpoints already take coach_id and athlete_id in the URL path — auth middleware validates the caller matches.
- No RBAC framework, no SSO, no team management. Just: are you this coach, and is this athlete on your roster.

**8. Deterministic confirmation step**
- The typed operation set (`.src/coach/operations.py`) already has `.render()` methods.
- Add a two-step flow in the frontend: form submit → show rendered confirmation text → user confirms → commit.
- This closes the gap noted in the commit-model implementation status.
- Applies to both LLM-staged and form-submitted operations.

**9. LLM layer — primary interface for both roles**

The LLM is not bolted on. Both coach and athlete interact with the system through conversational LLM — the same way CDE works. This is a core Phase 1 deliverable, not deferred. Full spec: [[wiki/architecture/interaction-model]].

**What to import from CDE:**
- `cde.llm.engine` — query_finding, query_free, _run_tool_loop, system prompts (BASE_RULES, FINDING_THREAD_PROMPT, FREE_CHAT_PROMPT)
- `cde.llm.context` — build_finding_briefing, build_minimal_briefing, _build_compound_section, _build_snapshot_section, _build_phase_section
- `cde.llm.tools` — all 20 tool definitions and handler functions

**Adaptation for multi-tenant:**
- Every tool handler currently passes `user_id="default"` to framework queries. Replace with explicit `athlete_id` from the request context.
- Briefing builder queries (`drug_level`, `compound_event`, `cycle_phase`, etc.) need the same athlete_id threading.
- The tool loop receives `conn` and `athlete_id` — these scope all data access.

**Two tool sets (the substance boundary):**

Athlete tool set — all 20 tools, same as CDE:
- All bloodwork, wearable, drug timeline, finding, context, calendar, search tools
- All compound management tools: `check_compound_active`, `add_compound_event`, `record_phase_change`
- Calendar write tools: `mark_dose_taken`, `mark_dose_missed`, `schedule_lab_draw`

Coach tool set — 15 read tools + coaching-surface write tools:
- All bloodwork, wearable, drug timeline (read-only), finding, context, search tools
- Calendar read tools: `get_day_summary`, `get_date_range_summary`, `get_upcoming_schedule`
- `get_phase_timeline` (read-only)
- Coaching-surface write tools mapped to the typed operations: SetTrainingBlock, EndTrainingBlock, SetNutritionTarget, AddRecoveryNote, NudgeSensitivity
- **Excluded:** `add_compound_event`, `check_compound_active`, `record_phase_change`, `mark_dose_taken`, `mark_dose_missed`. These tools do not exist in the coach's tool set. The LLM cannot call what it doesn't have.

**Coach LLM system prompt additions (beyond CDE's BASE_RULES):**
- "You are assisting a coach reviewing a client's data. You can read all health data, investigate findings, and manage training/nutrition/recovery. You cannot modify the client's substance protocol — that is the athlete's own record."
- Multi-client awareness: "When the coach asks about a client, scope all tool calls to that client's data."

**Frontend chat integration (both roles):**
- `POST /api/chat` endpoint (same pattern as CDE's `api.py` chat endpoint)
- Request: `{ message, thread_type: "free" | "finding", finding_id?, history[], athlete_id, role: "coach" | "athlete" }`
- Backend selects tool set based on role, scopes data access to athlete_id, runs tool loop
- Response streams back to chat UI (ChatBubble component already exists in Phase 0 frontend — wire it up)

**Chat UI per role:**
- Athlete: chat tab or overlay on their dashboard (same as CDE's ChatBubble pattern)
- Coach: chat overlay on client detail view. Coach selects which client they're chatting about (implicit from the client detail page they're viewing).
- Both: finding cards have "Ask about this" button → opens finding thread

**What the coach can do through LLM:**
- "What's Jordan's HR trend over the last 2 weeks?" → wearable tool scoped to Jordan
- "Compare Marcus's last two lab panels" → compare_panels tool
- "Show me everything from the day Alex's ALT spiked" → get_day_summary tool
- "Set Jordan's new training block — push/pull/legs, start Monday" → SetTrainingBlock → deterministic confirmation → commit
- "Bump Sam's protein to 180g" → SetNutritionTarget → confirmation → commit
- "Explain this hematocrit finding for Marcus" → finding thread with full data context

**What the coach cannot do through LLM:**
- "Stop Marcus's EQ" → tool absent → LLM responds: "Compound management is on the athlete's side."
- "Adjust Jordan's AI dose" → same.
- "Log a missed dose for Riley" → same.

**What the athlete can do through LLM (same as CDE):**
- All of the above read operations for their own data
- "I started deca 300mg weekly" → check_compound_active → add_compound_event → PK regeneration
- "Dropping to cruise" → multi-step phase transition (enumerate → confirm → execute → record)
- "I missed my pin yesterday" → mark_dose_missed → PK recalc → detector re-eval
- "When should I get labs?" → phase-aware schedule suggestion
- Symptom correlation: "joints hurt" → pull compound status + wearable data → correlate with known mechanisms

**10. Calendar system**

Import CDE's calendar view and tools. The Coach Platform's database already has the necessary tables (wearable_observation, metric_observation, compound_event, drug_level, finding). Add the `scheduled_event` table from CDE's calendar spec.

- `GET /api/athlete/{athlete_id}/calendar/{date}` — day view (compounds + levels + wearables + labs + findings + scheduled events)
- `GET /api/athlete/{athlete_id}/calendar/range/{start}/{end}` — which days have data
- `GET /api/athlete/{athlete_id}/schedule/upcoming` — next N days
- Coach can read the same calendar data via `GET /api/coach/{coach_id}/client/{athlete_id}/calendar/{date}`

Dosing schedule engine: generates injection/dosing days based on compound frequency + start date. Lab scheduling: suggests timing based on phase, protocol, and time since last draw.

### What Phase 1 defers

- **Withings, Dexcom, other integrations.** Whoop is the dominant wearable in this population. Others are Phase 2.
- **Per-client detector sensitivity nudge UI.** The operation exists in the backend (`NudgeSensitivity`). The coach LLM tool set includes it. No dedicated UI panel yet. Phase 2.
- **Billing.** No payment until value is validated with a real coach.
- **Hardening.** Rate limiting, abuse prevention, audit log maturity, backup strategy. Phase 2.
- **Mobile.** Web-first. Mobile wrapper (Capacitor/PWA) is a Phase 2+ consideration.
- **Cross-client LLM queries.** The coach LLM operates on one client at a time. "Which of my clients has the worst lipids?" is answered by the roster queue UI, not a cross-client LLM tool. Phase 2 consideration.

### Success criteria for Phase 1

- One real coach with 3–5 real clients, using real data.
- At least one detector fires on real client data and surfaces in the roster queue.
- The coach opens it unprompted on their review cadence (e.g. Sunday).
- The coach can investigate findings and manage training/nutrition/recovery through the LLM chat.
- The athlete can manage their compound stack, log events, and navigate the calendar through the LLM chat.
- The substance mirror stays read-only — when the coach's LLM is asked to modify a compound, it refuses because the tool doesn't exist.

## Phase 2+ — Product, not demo
Multi-tenancy hardening, role scoping, audit/event-log maturity, broader integrations (Withings, Dexcom, nutrition apps), sensitivity-nudge config and UI, billing, mobile wrapper. None of it before a coach has used Phase 1 with real data and real clients.

## Sequencing rule
Conversations run *ahead of or alongside* the build, using the mock and the existing CDE system as props. Expensive coach-specific engineering is gated on real coach reactions. A built MVP can bias the conversation (polite "neat" instead of truth) — lead with the prop, listen for whether the pain is real.

## Even the mock obeys the principles
The demo shows the clean structure, not a substance-management tool: the coach manages training/nutrition; the substance view is read-only with no buttons; modeled values are labeled modeled. The data-consolidation value is the lead, not the substance handling. See [[wiki/principles]].

Related: [[wiki/principles]] · [[wiki/ops/customer-discovery]] · [[wiki/architecture/relationship-to-cde]] · [[wiki/architecture/coach-read-layer]] · [[wiki/product/moat]]
