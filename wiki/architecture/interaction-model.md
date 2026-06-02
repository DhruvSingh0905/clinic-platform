---
tags: [architecture, llm, interaction, security, critical]
status: active
updated: 2026-06-01
---

# Interaction model

How users and coaches interact with the app. **The LLM is a primary interface for both roles** — the same conversational data access that CDE provides to a single user, extended to the two-actor coach/athlete model. Both sides can pull data, investigate findings, manage their respective write surfaces, and navigate the calendar through natural language. The structured UI (roster queue, forms, dashboards) coexists as a direct-access layer — not a replacement for the LLM, and not replaced by it.

The substance boundary still holds. The coach's LLM simply does not have substance-write tools. That's structural, not a prompt.

---

## What carries over from CDE

CDE's LLM layer is the reference implementation. The Coach Platform inherits it wholesale and extends it for two actors. Everything below exists in CDE and transfers.

### CDE's LLM engine (`cde.llm.engine`)

Two query modes:
- **Finding thread** (`query_finding`) — investigates a specific detector finding. Briefing includes that one finding + compounds + data snapshot. LLM stays focused on that issue, does not volunteer unrelated alerts.
- **Free chat** (`query_free`) — user asks any question about their data. Briefing includes compounds + data snapshot but NO findings, preventing alert injection.

Both modes share a tool loop: LLM calls tools (max 8 rounds), tools return pre-formatted strings, LLM reasons over results, produces final response. Uses Claude via Anthropic SDK.

System prompt (`BASE_RULES`) enforces:
- Informational only, never diagnose or prescribe
- Every numeric claim from tools or briefing, never fabricated
- Compound updates require `check_compound_active` before any write
- Phase transitions follow a multi-step protocol (enumerate compounds → confirm with user → execute each change → record phase)
- Symptom correlation pulls wearable + compound data before responding

### CDE's 20 tools (`cde.llm.tools`)

All 20 tools carry over. The coach and athlete each get a scoped subset.

**Bloodwork (4 tools):**
- `get_metric_summary` — single metric: latest, baseline, trend, change
- `get_metric_history` — full timeseries across all lab draws
- `get_panel_snapshot` — all metrics from one lab draw date
- `compare_panels` — side-by-side comparison of two lab dates

**Wearable (2 tools):**
- `get_wearable_trend` — rolling averages (3-day, 7-day), baseline, current, direction. Window default 90 days.
- `get_bp_summary` — BP-specific: morning/evening breakdown, trend, AHA classification

**Drug timeline (4 tools):**
- `get_compound_status` — current status, days on, level %, steady state
- `get_compounds_on_date` — all active compounds with levels on a specific date
- `get_compound_mechanism` — mechanism of action, monitoring markers, clinical notes
- `get_all_active_compounds` — every compound with level > 0. Used during phase transitions.

**Findings (2 tools):**
- `get_finding_detail` — full finding with signals, drug context, recommendations
- `get_finding_history` — historical findings for a theme over last N days

**Context (3 tools):**
- `get_hr_daily_stats` — detailed cardiac summary for a day (resting HR, HRV with methodology flag, recovery score, respiratory rate)
- `get_training_context` — exercise data for a date/window
- `get_nutrition_summary` — calorie + macro data

**Search (1 tool):**
- `search_drug_interaction` — web search for drug interactions, mechanisms, pharmacology

**Calendar (6 tools):**
- `get_day_summary` — everything that happened on a date
- `get_date_range_summary` — aggregated period summary
- `get_upcoming_schedule` — next N days of scheduled events
- `mark_dose_taken` — confirms dose, keeps PK model on track
- `mark_dose_missed` — logs miss, triggers PK recalc + detector re-eval
- `schedule_lab_draw` — adds lab reminder to calendar

**Compound management (4 tools):**
- `check_compound_active` — check status before any write (prevents duplicate STARTs)
- `add_compound_event` — log START/DOSE_CHANGE/STOP/MISSED_DOSE. Validates required fields. Regenerates drug levels after.
- `record_phase_change` — record blast/cruise/pct/off transition. Closes prior phase, opens new. Called AFTER all compound events logged.
- `get_phase_timeline` — full phase history with dates and durations

### CDE's briefing builder (`cde.llm.context`)

Three briefing variants:
- **Full briefing** — all findings + compounds + data snapshot. For diagnostics.
- **Finding briefing** — one specific finding + compounds + snapshot. For finding threads.
- **Minimal briefing** — compounds + snapshot only, NO findings. For free chat.

Each briefing assembles: active compounds (name, class, dose, frequency, days on, level, steady state), data snapshot (lab panel count, wearable days, date ranges), and current phase with days-in-phase.

### CDE's calendar system (`wiki/architecture/calendar-system`)

The calendar is a temporal index over existing data tables — not a separate data store. For any date, it composites: compound events + drug levels + wearable observations + lab results + findings + scheduled events.

The LLM navigates the calendar conversationally:
- "What was I on when my BP spiked?" → `get_day_summary` + `get_compounds_on_date`
- "When should I get labs?" → phase-aware suggestion based on protocol timing
- "I missed my pin yesterday" → `mark_dose_missed` → PK recalc → detector re-eval → LLM explains impact

Dosing schedule engine handles frequency patterns (daily, EOD, E3D, E3.5D, weekly, biweekly). Injection days highlighted. Lab scheduling suggests timing based on phase and time since last draw.

### CDE's two-surface UX (`wiki/architecture/interaction-model`)

Two interaction surfaces, both LLM-powered:
1. **Alerts** — finding cards ordered by severity. "Ask about this" button opens a finding thread. Cards persist until dismissed or resolved.
2. **Free chat** — open text input for any question. No findings injected. LLM uses tools as needed.

Compound management happens through conversation: "started deca 300mg weekly" → LLM checks status, asks missing details, logs START. Phase transitions are multi-step: enumerate all compounds → present defaults → user confirms → LLM executes each change → records phase.

---

## What changes for the two-actor model

CDE is single-user. The Coach Platform adds a second actor with different permissions. The LLM interface splits by role.

### Athlete-side LLM

Identical to CDE. The athlete gets all 20 tools, both query modes, full calendar access, and compound management through chat. They are the data owner — they can read everything, write to their own record, and manage their own compound stack and calendar.

Nothing is removed from the CDE experience. The athlete's LLM context is scoped to their own data only (enforced in the tool layer).

### Coach-side LLM

The coach gets a **subset** of tools, scoped to their client roster. The tool set is split by the substance boundary.

**Coach gets (read tools — all data):**
- All 4 bloodwork tools (get_metric_summary, get_metric_history, get_panel_snapshot, compare_panels)
- All 2 wearable tools (get_wearable_trend, get_bp_summary)
- All 4 drug timeline tools (get_compound_status, get_compounds_on_date, get_compound_mechanism, get_all_active_compounds) — **read-only**. The coach can see compound status and levels but cannot modify them.
- All 2 finding tools (get_finding_detail, get_finding_history)
- All 3 context tools (get_hr_daily_stats, get_training_context, get_nutrition_summary)
- search_drug_interaction
- Calendar read tools (get_day_summary, get_date_range_summary, get_upcoming_schedule)
- get_phase_timeline — read-only

**Coach gets (write tools — lawful coaching surface only):**
- The 5 coaching operations from the typed operation set: SetTrainingBlock, EndTrainingBlock, SetNutritionTarget, AddRecoveryNote, NudgeSensitivity
- Calendar write tools for coaching-surface items: schedule a check-in, set a training milestone, add a nutrition note

**Coach does NOT get:**
- `add_compound_event` — no START, STOP, DOSE_CHANGE, MISSED_DOSE for substances
- `check_compound_active` (write-gating tool for compounds — not needed if compounds aren't writable)
- `record_phase_change` — phase is derived from the athlete's compound events; coach doesn't control it
- `mark_dose_taken` / `mark_dose_missed` — these modify the substance record
- `schedule_lab_draw` (debatable — could be coaching-surface if framed as a training-context note, but for now deferred)

This is the same structural enforcement as the UI: the coach's LLM does not have substance-write tools because those tools do not exist in its tool set. Not a prompt instruction — an absent capability.

### Coach LLM use cases

The coach interacts with their client's data conversationally:

**Data investigation:**
- "What's Jordan's HR trend over the last 2 weeks?" → `get_wearable_trend(athlete_id=jordan, metric=resting_hr, window=14)`
- "Compare Marcus's last two lab panels" → `compare_panels(athlete_id=marcus, date1, date2)`
- "Show me everything from the day Alex's ALT spiked" → `get_day_summary(athlete_id=alex, date)`
- "What compounds is Riley on right now?" → `get_all_active_compounds(athlete_id=riley)` (read-only view)

**Finding investigation:**
- Coach taps a finding card in the roster queue → opens finding thread for that client
- "Explain this hematocrit drift — what's driving it?" → LLM pulls wearable + lab + compound timeline, explains mechanism
- "Is this ALT spike expected given the oral?" → LLM checks compound timeline, explains 17aa hepatic response curve

**Coaching surface management:**
- "Set Jordan's new training block — push/pull/legs, start Monday" → SetTrainingBlock operation → deterministic confirmation → commit
- "Bump Sam's protein to 180g, effective today" → SetNutritionTarget → confirmation → commit
- "Add a recovery note for Marcus — monitor BP, next draw in 2 weeks" → AddRecoveryNote → commit
- "End Riley's deload block as of yesterday" → EndTrainingBlock → confirmation → commit

**What the coach's LLM cannot do:**
- "Stop Marcus's EQ" → tool does not exist → LLM responds: "Compound management is on the athlete's side. Marcus updates his own protocol."
- "Adjust Jordan's AI dose" → same refusal.
- "Log a missed dose for Riley" → same.

The refusal is not a prompt — the tool is absent from the coach's tool set. The LLM cannot execute what it does not have.

### Briefing scoping per role

**Athlete briefing:** Same as CDE. Their own findings, compounds, snapshot.

**Coach briefing:** Scoped to one client at a time. When the coach opens a client or asks about a client by name, the briefing populates with that client's findings/compounds/snapshot. The coach's LLM context never mixes clients — single-client per conversation turn, enforced in the tool layer.

**Coach roster-level queries:** "Which of my clients need attention?" is not a tool call — it's the roster queue UI. The LLM can summarize what the coach is looking at ("You have 2 concerning findings — Marcus's hematocrit and Jordan's HR drift") but this reads from the roster API, not from a cross-client tool.

---

## The safety tenets still compose

The three tenets from [[wiki/principles]] hold for both LLM interfaces:

1. **Capability gating** — the LLM stages typed operations from a closed set. Coach and athlete have different operation sets. Neither can commit free text.
2. **Non-destructive by construction** — no operation erases the record. Append-only for both roles.
3. **Deterministic legibility** — every staged operation renders to human-readable text via template function. The human confirms before commit.

The substance boundary lives in the operation set itself: no coach-side substance-write operation exists. This holds whether the write originates from the LLM, a form, or a future API integration.

---

## Implementation status (2026-06-02)

**Fully built.** The complete product is operational — LLM, UI, bidirectional data flow, Hevy integration, notification system.

**What works:**
- **LLM chat for both roles.** Coach and athlete both get full tool access. Coach has all 20 CDE tools + coaching-surface write tools + Hevy tools (workout history, lift progression, routine push). Athlete has all 20 CDE tools + workout tools.
- **Coach manages everything.** Coach can modify training, nutrition, recovery, AND substances. All modifications trigger athlete notifications. The substance boundary was removed — the coach is the authority, the athlete confirms via notification banners.
- **Finding thread mode.** "Ask about this" button on finding cards opens chat with finding_id for focused investigation.
- **Deterministic confirmation.** All form-based writes show a confirmation dialog with the rendered operation text before committing.
- **Form submit handlers wired.** Training block, nutrition target, and recovery note forms call the API and reload data after commit.
- **Hevy integration.** Workout sync from Hevy API (15 real workouts synced), stall detector (bench stall at 100kg flagged), routine builder UI (push to Hevy), workout log viewer, exercise progression explorer.
- **Notification system.** All coach actions (training, nutrition, recovery, substance, routine pushes) create athlete notifications. Athlete sees banners at dashboard top with Confirm buttons.
- **Change log.** Per-client chronological log of every coach action.
- **Two-sided visibility verified.** Coach → athlete: training/nutrition/recovery/substance/routines all visible. Athlete → coach: substance events, workout data, wearable data all visible. Notification banners bridge the gap.
- **UI redesigned.** Tabbed layout (Findings, Vitals, Bloods, Training, Protocol, Nutrition, Log), collapsible notes panel, signal cards with mini charts, weight-prominent vitals, metric-centric bloodwork, inline NLP substance editing.

**What remains:**
- Auth (email/JWT sessions, coach invite flow)
- Billing
- Additional integrations (Withings, Dexcom)
- Real multi-user deployment
- Roster page UX improvements (compact cards, signal card redesign)
- Athlete-side display of coach-managed data in the frontend — the API returns training/nutrition/recovery, but the athlete page.tsx doesn't render these sections yet.
- Cross-client LLM queries — coach LLM operates on one client at a time.

Related: [[wiki/principles]] · [[wiki/architecture/commit-model]] · [[wiki/architecture/coach-read-layer]] · [[wiki/architecture/relationship-to-cde]] · [[wiki/architecture/two-sided-model]]
