# CLAUDE.md

Operating instructions for Claude when working in `Cycle Data Platform/Clinic Platform/`. Sibling project: `../Cycle Data Engine/` (the engine). Workspace overview lives in `../CLAUDE.md`.

## What this project is

A **refactor of `../Cycle Data Engine/` (CDE) for small TRT/hormone optimization clinics.** CDE is the engine — extraction, PK model, detectors, user self-logging intake. This product adds a clinician-facing read layer: patients continuously sync their data, clinicians view it with domain-aware trends and a ranked roster queue, and clinicians manage the full clinical surface (medications, assessments, nutrition, follow-ups). It is CDE + a clinical read/write layer, not a new system.

History: this started as a consumer app (CDE), pivoted to a coach-facing product (Coach Platform, abandoned after customer discovery showed coaches unwilling to adopt new systems), then pivoted to clinics. Small TRT/wellness clinics (1-3 clinicians) have no system for consolidating patient-generated health data — they work from screenshots and scattered spreadsheets. This is the gap.

## Key architectural decisions

### The clinician has FULL write access
Unlike the previous coach product (where substance management was restricted), the clinician IS the prescriber. They have full write access to:
- Medications/compounds (prescribe, adjust, discontinue)
- Assessments and clinical notes
- Nutrition targets
- Follow-up scheduling
- Training guidance

There is no substance boundary. The clinician manages the entire protocol.

### Safety architecture (write path) — inherited from CDE
Three tenets enforced in code/data:
1. **Capability gating** — the LLM stages typed operations from a closed enumerated set, never commits free text
2. **Non-destructive by construction** — no operation erases the record, for any actor; event-sourced, append-only
3. **Deterministic legibility** — the human approves byte-for-byte what commits via pure template render

### Patient data ownership
The patient owns their data. They can:
- Self-log compound events (for off-protocol tracking the clinic should know about)
- Upload bloodwork PDFs
- Import Apple Health data
- View their own findings, trends, and clinician-set care plan

## Relationship to CDE
- CDE is the parent engine. Reference its wiki (`../Cycle Data Engine/wiki/`, authoritative) but NEVER edit the CDE project from here.
- Copied CDE modules: extraction, PK model, 8 detectors, LLM engine (20 tools), compound DB (86 compounds), integration adapters

## Development

### Backend (from `Clinic Platform/`)
```bash
source .venv/bin/activate
python3 -m clinic                    # Start FastAPI server (localhost:8001)
```
Source is in `.src/clinic/`. Config: `pyproject.toml`.

### Frontend (from `Clinic Platform/.frontend/`)
```bash
pnpm install && pnpm dev             # Dev server (localhost:3001)
```
Next.js 16 / React 19 / TypeScript / Tailwind CSS 4.

### Environment
`.env` holds `ANTHROPIC_API_KEY` and integration credentials.

## What to never do without explicit user approval
- Edit anything in `../Cycle Data Engine/`
- Add destructive operations (delete, overwrite)
- Have the LLM commit without a deterministic, human-confirmed typed operation
- Restructure the wiki layout
