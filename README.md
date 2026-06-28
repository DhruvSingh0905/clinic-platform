# Clinic Platform

Full-stack patient data consolidation system featuring pharmacokinetic modeling, streaming health data ingestion, LLM-grounded tool-use chat, and a deterministic append-only audit layer. Applied to clinical patient management; the underlying engineering generalizes.

**Next.js 16** · **FastAPI** · **SQLite** · **Claude API** · **TypeScript** · **Python**

![Patient Roster](docs/screenshots/01-roster.png)

---

## Technical Highlights

### Pharmacokinetic Drug-Level Model

Models 86 compounds with ester-specific half-lives, steady-state detection, and day-by-day serum level estimation. Computes actual decay curves from logged protocols rather than static lookups. Supports dose changes, compound stacking, and ester switching with correct level transitions across discontinuities.

### Streaming Health Data Parser

Apple Health exports routinely exceed 100MB. The parser uses `iterparse` for single-pass, constant-memory XML processing. Extracts 10 metric types and workout summaries, normalizes units (lbs→kg, count/min→bpm), validates plausibility ranges, and produces daily aggregates without loading the document into memory.

### LLM Tool-Use with Data Grounding

Multi-turn chat engine backed by 20+ tools for querying structured patient data. The model calls tools to retrieve labs, vitals, drug levels, and compound history, then synthesizes responses anchored to specific returned values. Role-scoped tool sets enforce access boundaries: clinicians receive write tools, patients receive read-only access with self-logging.

### Deterministic Operation Audit

Write operations are constrained to a closed enumerable set. Each operation renders to human-readable text through a pure template function, logs to an append-only record, and triggers a downstream notification. No free-text mutations — every state change is reproducible and auditable.

### Schema-Aware Data Import

Accepts Excel and CSV uploads for structured data onboarding. An LLM analyzes column headers and sample rows, proposes mappings to the target schema, identifies ambiguous columns, and surfaces conflicts for human resolution before execution.

---

## Feature Overview

### Clinician Interface

**Vitals** — Weight, resting heart rate, HRV (RMSSD and SDNN), blood pressure. Interactive area charts with adjustable date range selection.

![Vitals with interactive charts and range controls](docs/screenshots/02-vitals.png)

**Bloodwork** — Lab results organized by category with flag indicators. Each metric expands to a full chart with reference range overlays and a historical data table. Search filters across all tests.

![Bloodwork with expandable metric detail](docs/screenshots/03-bloodwork.png)

**Medications** — Compound timeline with pharmacokinetically-modeled estimated levels. Supports natural language input or structured form entry. Estimated serum concentrations update from the PK model.

![Medication management with PK-modeled levels](docs/screenshots/04-medications.png)

**Clinical Notes** — Structured note types (Assessment, Plan, Subjective, Objective, Follow-up, General). Searchable and date-indexed. Side panel for rapid entry alongside a dedicated documentation tab.

![Clinical notes](docs/screenshots/05-notes.png)

### Patient Interface

**Dashboard** — Consolidated wearable trends from Apple Health, PK-estimated drug levels for all active medications, clinician-defined care plan, compound self-logging, and a notification queue for clinician actions.

![Patient dashboard](docs/screenshots/06-patient-dashboard.png)

**Onboarding** — Multi-step import wizard with AI-powered column mapping for migrating existing patient data from spreadsheets.

![Onboarding wizard](docs/screenshots/07-onboarding.png)

---

## Architecture

```
Next.js 16 (React 19, TypeScript, Tailwind CSS 4)
    │
    │  REST API · 40+ endpoints
    ▼
FastAPI (Python 3.11+)
    │
    ├── SQLite · WAL mode · 30+ tables
    ├── Claude API · tool-use chat · Vision PDF extraction · structured parsing
    ├── PK Model · 86 compounds · day-by-day level estimation
    ├── Health Parser · streaming iterparse · 10 metric types
    ├── Extraction Pipeline · PDF → LOINC normalization → validation
    └── Compound Database · 86 entries · half-lives · dose ranges · monitoring markers
```

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS 4, Recharts, Framer Motion |
| Backend | Python, FastAPI, Pydantic, SQLite (WAL) |
| AI | Claude API — multi-turn tool-use, Vision extraction, structured data parsing |
| Data | LOINC-normalized labs, Apple Health streaming ingestion, pharmacokinetic modeling |

## Structure

```
.frontend/src/
├── app/clinician/          Roster · patient detail (9 tabs) · onboarding
├── app/patient/            Dashboard · self-logging
├── components/             15 shared components
└── lib/                    Types · API client · formatters

.src/clinic/
├── api.py                  40+ endpoints · role-scoped access
├── chat.py                 LLM engine · tool dispatch · role scoping
├── pk_model.py             Pharmacokinetic level estimation
├── compound_db.py          86 compounds with PK parameters
├── apple_health.py         Streaming XML parser
├── extraction/             PDF → LOINC pipeline
├── llm/                    20+ tool definitions · context builders
├── database.py             Schema (30+ tables)
├── operations.py           Typed operations · deterministic rendering
└── onboarding.py           LLM-powered spreadsheet import
```

---

**Dhruv Singh** · University of Washington · Computer Science
