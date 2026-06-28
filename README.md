# Clinic Platform

A full-stack patient data management system for TRT/HRT clinics. Consolidates patient-generated health data (Apple Health, wearables, lab PDFs) with clinician-managed protocols, pharmacokinetic drug-level modeling, and LLM-powered clinical chat.

Built end-to-end: **Next.js 16** frontend, **Python FastAPI** backend, **SQLite** data layer, **Claude API** for chat and data import parsing.

![Patient Roster](docs/screenshots/01-roster.png)

---

## Features

### Clinician View

**Patient Roster** — Alphabetical patient list with treatment status badges (active treatment, monitoring, tapering, discontinued, initial consult) and last sync timestamps. Search bar filters by name.

**Vitals Dashboard** — Weight, resting heart rate, HRV (RMSSD + SDNN), blood pressure, recovery score. All with interactive Recharts area charts and draggable brush sliders for date range selection.

![Vitals with interactive charts and range sliders](docs/screenshots/02-vitals.png)

**Bloodwork** — Lab results grouped by category (liver, metabolic, kidney, hematology, lipids) with flag badges (high/low/normal). Click any metric to expand into a full chart with reference range overlays and historical data table. Search bar filters across all tests.

![Bloodwork with expandable metric rows](docs/screenshots/03-bloodwork.png)

**Medication Management** — Full compound timeline with PK-modeled estimated levels. Clinician can prescribe via natural language ("add anastrozole 0.5mg twice weekly") or manual form. Estimated serum levels update in real time from the pharmacokinetic model.

![Medications with PK-modeled drug levels](docs/screenshots/04-medications.png)

**Clinical Notes** — SOAP-style note types (Assessment, Plan, Subjective, Objective, Follow-up, General). Searchable, date-stamped. Side panel for quick notes, dedicated tab for full clinical documentation.

![Clinical notes with SOAP types](docs/screenshots/05-notes.png)

**Follow-up Scheduling** — Schedule follow-up appointments with date, time, and description. Upcoming and past lists. Integrates with the notification system so patients see scheduled visits.

### Patient View

**Patient Dashboard** — Wearable trends (weight, HR, HRV, BP, dietary intake from Apple Health), PK-estimated drug levels for all medications, care plan set by clinician, and compound self-logging.

![Patient dashboard with wearable data and PK levels](docs/screenshots/06-patient-dashboard.png)

**LLM Chat** — Patients can ask about their data: "What are my testosterone levels?" or "If I skip my injection this week, what happens to my levels?" The LLM queries real patient data via tool-use and provides pharmacokinetically-grounded answers while deferring clinical decisions to the clinician.

**Notification Queue** — All clinician actions (medication changes, notes, scheduled follow-ups) appear as patient notifications with "Acknowledge all" workflow.

### Data Import

**Apple Health Integration** — Upload Apple Health XML exports. Streaming XML parser handles 100MB+ files. Extracts: weight, resting HR, HRV (SDNN), blood pressure, heart rate, dietary intake (calories, protein, fat, carbs), and workout summaries with activity type classification.

**Bloodwork PDF Upload** — Upload lab PDFs (LabCorp, Quest, etc.). Claude Vision extracts results, maps to LOINC codes, validates plausibility ranges, and stores with source document linkage for audit.

**Spreadsheet Onboarding** — LLM-powered Excel/CSV import wizard. Upload patient data spreadsheets, AI analyzes column headers and proposes mappings to the database schema, clinician reviews and confirms.

![Onboarding wizard](docs/screenshots/07-onboarding.png)

---

## Architecture

```
Next.js 16 Frontend (React 19, TypeScript, Tailwind CSS 4)
    |
    |  REST API
    v
FastAPI Backend (Python 3.11+)
    |
    |-- SQLite (WAL mode, 30+ tables)
    |-- Claude API (Sonnet 4.6 — chat, tool-use, PDF extraction, spreadsheet parsing)
    |-- PK Drug-Level Model (86 compounds, day-by-day pharmacokinetic estimates)
    |-- Apple Health XML Parser (streaming iterparse)
    |-- Bloodwork Extraction Pipeline (Vision → LOINC mapping → validation)
    `-- Compound Database (86 compounds with half-lives, dose ranges, monitoring markers)
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS 4, Recharts, Framer Motion |
| Backend | Python, FastAPI, Pydantic, SQLite (WAL mode) |
| AI/LLM | Claude API (Sonnet 4.6) — multi-turn tool-use chat, Vision PDF extraction, structured data parsing |
| Data | 30+ table schema, LOINC-normalized lab data, Apple Health XML streaming, pharmacokinetic modeling |

---

## Engineering Highlights

### Pharmacokinetic Drug-Level Model

86 compounds modeled with ester-specific half-lives, steady-state detection, and day-by-day level estimation. When a patient asks "what happens if I skip my injection?", the model calculates the decay curve from the logged protocol — not a lookup table, actual PK math. Supports dose changes, compound stacking, and ester switching with proper level transitions.

### Apple Health Streaming Parser

Apple Health exports are 100MB+ XML files. The parser uses `iterparse` to stream-process records without loading the entire file into memory. Extracts 10 metric types + workout summaries, normalizes units (lbs→kg, count/min→bpm), validates plausibility ranges, and produces daily aggregates — all in a single pass.

### LLM Chat with Tool-Use

Multi-turn chat with 20+ tools for querying patient data. The LLM calls tools to look up labs, wearables, drug levels, and compound history, then synthesizes grounded responses. Clinician and patient roles get different tool sets and system prompts. All responses cite specific data points from tool results — no hallucination.

### AI-Powered Spreadsheet Onboarding

Clinicians upload Excel/CSV files with patient data. Claude Haiku analyzes column headers + sample rows and proposes a mapping to the database schema (which column is "weight", which is "testosterone dose", etc.). Identifies ambiguous mappings and flags conflicts for clinician review before import.

### Typed Operation System

All write operations (medication changes, notes, nutrition targets) go through a typed operation pipeline: the operation is rendered to human-readable text via a pure template function, logged to an append-only operation log, and the patient is notified. No free-text writes — every mutation is auditable.

---

## Project Structure

```
Clinic Platform/
├── .frontend/              # Next.js 16 frontend
│   └── src/
│       ├── app/
│       │   ├── clinician/  # Clinician roster + patient detail
│       │   ├── patient/    # Patient dashboard
│       │   └── page.tsx    # Landing
│       ├── components/     # Shared UI components
│       └── lib/            # Types, API client, formatters
├── .src/
│   └── clinic/             # FastAPI backend
│       ├── api.py          # 40+ REST endpoints
│       ├── chat.py         # LLM chat engine with role-scoped tools
│       ├── compound_db.py  # 86 compounds with PK parameters
│       ├── pk_model.py     # Pharmacokinetic level estimation
│       ├── apple_health.py # Streaming XML parser
│       ├── extraction/     # Bloodwork PDF → LOINC pipeline
│       ├── llm/            # Tool definitions, context builders
│       ├── database.py     # SQLite schema (30+ tables)
│       └── onboarding.py   # LLM-powered spreadsheet import
└── docs/
    └── screenshots/
```

---

## Author

**Dhruv Singh** — University of Washington, Computer Science

Built with Claude Code (Anthropic CLI).
