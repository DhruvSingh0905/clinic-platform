---
tags: [architecture, cde, refactor, critical]
status: active
updated: 2026-06-01
---

# Relationship to Cycle Data Engine

This product is a **refactor of CDE for coaches**, not a new build and not merely a parts donor. CDE is the engine. This wraps a coach-facing read layer around it. Understanding what's inherited vs. added keeps the scope honest.

## Inherited from CDE, essentially unchanged
- **Self-logging intake + display of cycle/substance data.** This is the exact model the coach product uses for the user side: the user logs their own substances, their own record. We do not rebuild this into a coach-managed protocol tool — we keep CDE's user-owned framing. This is what makes the substance side defensible (see [[wiki/principles]]).
- **Extraction pipeline** — bloodwork PDF → LOINC-normalized JSON, 58/58 validated, zero silent wrongness. `src/cde/extraction/`.
- **PK drug-level model** — 86 compounds, day-by-day levels, adherence-aware recalc. `src/cde/store/pk_model.py`. (Used for the user's own display; modeled values stay labeled modeled.)
- **Detector themes** — all 8, thresholds, drug-correlation logic. `src/cde/detectors/themes.py`. The domain-aware detection IS the moat.
- **Integration adapters** — Whoop (RMSSD), Apple Health (SDNN — not comparable, methodology flag is load-bearing), Withings, Dexcom CGM. `wiki/data/integrations.md`.
- **Safety tenets** — capability gating, non-destructive append-only ops, deterministic legibility. See [[wiki/architecture/commit-model]].
- **LLM layer** — engine (two-mode: finding thread + free chat), briefing builder (compound/snapshot/phase/finding sections), 20 tools (bloodwork, wearable, drug timeline, findings, context, calendar, compound management, search), tool loop (max 8 rounds), system prompts (BASE_RULES + mode-specific lens). `src/cde/llm/engine.py`, `context.py`, `tools.py`. The athlete side inherits all 20 tools unchanged. The coach side inherits the read tools and gets new coaching-surface write tools. See [[wiki/architecture/interaction-model]].
- **Calendar system** — temporal index over compound events + drug levels + wearables + labs + findings + scheduled events. Day view, range view, dosing schedule engine, lab scheduling, phase awareness. LLM tools for read/write. See CDE `wiki/architecture/calendar-system.md`.
- **Compound management through chat** — natural language compound logging (start/stop/dose change/missed dose), phase transition protocol (enumerate → confirm → execute → record), symptom correlation. The athlete side inherits this unchanged. The coach side does not get compound-write tools.
- **Data loaders** — `cde.store.loaders`: load_bloodwork, load_apple_health, load_compound_events, load_bp_reading. Write extracted/parsed data to canonical tables. `cde.store.triggers.on_data_changed`: marks old findings resolved, runs relevant detectors after any data write.

## Added for the coach refactor
- **Multi-tenant model** — coach → roster of clients, hard per-client isolation, role scoping (coach vs. user). CDE was single-user; this is the main net-new data work.
- **Coach read layer** — the roster view, the ranked review queue, and the strictly-read-only substance mirror. See [[wiki/architecture/coach-read-layer]].
- **Coach-managed coaching surface** — training/nutrition/recovery programming the coach actively manages (the lawful write path). New typed operations and LLM tools for these.
- **Role-scoped tool sets** — the coach's LLM gets a subset of CDE's tools: all read tools + coaching-surface write tools. Substance-write tools (add_compound_event, record_phase_change, mark_dose_taken, mark_dose_missed) are excluded from the coach's tool set. The absence is the enforcement.
- **Coach LLM system prompt** — extends CDE's BASE_RULES with role awareness: coach reads all data, manages training/nutrition/recovery, cannot modify substance protocol.
- **Continuous one-way sync** — user→platform, always-on, the durable data spine.

## Changed from CDE's assumptions
- **Two actors, not one.** CDE is the user alone. Here a coach views the user's data. This is the entire source of the substance-handling care: the second actor must not be able to *direct* the substance side. CDE never had to think about this because there was no second actor.
- **LLM stays primary but splits by role.** CDE's LLM is the primary interface for a single user. The coach refactor keeps the LLM as a primary interface for both roles, but scopes it: the athlete gets CDE's full tool set, the coach gets a read-heavy subset with coaching-surface write tools and no substance-write tools. The safety tenets still compose — the LLM stages typed operations, operations are non-destructive, the human confirms. See [[wiki/architecture/interaction-model]].
- **Keystone adherence advantage** — a paying physique client is more reliably adherent than CDE's self-managing solo user, so assume-adherence is safer here.

## Do NOT edit CDE from this project
Reference CDE components (e.g. `src/cde/detectors/themes.py`); never modify the CDE project from here. This is a separate app that depends on CDE's engine conceptually — keep the boundary clean.

## Implementation status (2026-06-01)

CDE code was **copied** into the Coach Platform (`Coach Platform/.src/coach/`) and adapted — not imported as a dependency, not linked at runtime. CDE's source was not modified. The Coach Platform is fully self-contained.

**Copied and working:**
- LLM layer: engine.py (tool loop), context.py (briefing builder), tools.py (20 tools) — all imports rewritten from `cde.*` to `coach.*`. Metric alias resolution added for weight_kg/hrv_rmssd compatibility.
- Detectors: framework.py + themes.py (8 domain-aware detectors). Real findings generated from mock wearable data (cv_stress fires on HR trends).
- PK model: pk_model.py — drug level regeneration on compound events. Levels computed and stored in drug_level table.
- Extraction: bloodwork PDF pipeline (extractor, validator, schema, LOINC mappings, reference data). Upload endpoint exists but requires Anthropic API key for Vision extraction.
- Ingestion: Apple Health parser, compound DB (86 compounds with aliases), cycle log model, BP entry with AHA classification.
- Integrations: Whoop OAuth adapter (requires credentials to test).
- Data loading: loaders.py (metric/compound definition seeding), triggers.py (detector dispatch on data writes).
- Calendar: day/range/upcoming queries over compound + wearable + lab + finding + scheduled data.

**Schema:** CDE-compatible tables use `user_id` (= athlete.id), `compound_id` (FK to compound_definition), `estimated_level`. Coach Platform tables use `athlete_id`/`coach_id`. Reference data (86 compounds, LOINC definitions) seeded on startup from copied CDE reference_data.py and compound_db.py.

**Not copied:** CDE's api.py (replaced by Coach Platform's own), cli.py, config.py, store/database.py, store/persistent.py, eval/, integrations/withings.py, integrations/dexcom.py.

Related: [[wiki/principles]] · [[wiki/architecture/coach-read-layer]] · [[wiki/architecture/commit-model]] · [[wiki/architecture/interaction-model]] · [[wiki/product/moat]]
