---
tags: [mvp, project-root]
status: active
updated: 2026-06-01
---

# MVP — Coach Data Platform (working name; refactor of Cycle Data Engine)

## What this is
A **refactor of the Cycle Data Engine (CDE) for physique/bodybuilding coaches.** CDE already ingests and displays an enhanced athlete's health, nutrition, training, wearable, and self-logged cycle data with domain-aware detection. This product keeps that engine and adds a **coach-facing read layer**: the user continuously syncs their data, the coach views it (with domain-aware trends and a ranked review queue), and the coach actively manages the lawful side of coaching — training, nutrition, recovery. It is CDE plus a coach view, not a new system.

## Read this first
[[wiki/principles]] is the spine. Two non-negotiables: the **safety architecture** on the write path (capability gating, non-destructive append-only operations, deterministic legibility — inherited from CDE) and the **central conservative line** — the coach manages the lawful stuff; the user self-logs anabolics/controlled/prescription substances exactly as CDE does today, and the coach view of that data is a **strictly read-only mirror with no interactive elements.** Substance coaching, if any, happens off-platform.

## The one-line value prop
Physique coaches fly blind between check-ins, stitching together screenshots of Whoop, MyFitnessPal, and lab PDFs. This gives them one continuous, domain-aware view of each client's data — the consolidation + enhanced-athlete-aware detection no generic coaching app does. The data moat is the product.

## Why the coach pivot (vs. the earlier clinic framing)
- **Adherence:** a paying physique-coaching client is self-selected for dedication; the assume-adherence model and passive-sync loop get more reliable.
- **Go-to-market:** coaches are reachable, decide fast, and the founder has native credibility and warm-intro access to this world. Far easier than cold-pitching a cautious licensed clinician.
- **The substance question is resolved by the read-only line**, not by framing — see [[wiki/principles]] and [[wiki/architecture/coach-read-layer]].

## What we are building (and not)
- ✅ CDE's engine: extraction, PK model, detectors, self-logging intake (reused, see [[wiki/architecture/relationship-to-cde]])
- ✅ Continuous one-way user→platform data sync (Whoop/Apple Health/CGM/BP/nutrition/labs)
- ✅ User daily notes + their own substance log (CDE-style, user-owned)
- ✅ Coach read layer: domain-aware trends + ranked review queue over the client roster
- ✅ Coach active management of training / nutrition / recovery (the lawful coaching surface)
- ✅ Hevy integration: coach pushes training routines → athlete logs in Hevy → workout data (sets/reps/weight/RPE) flows back to coach with cross-metric correlation. See [[wiki/architecture/hevy-integration]].
- ✅ Safety tenets on any write path (inherited from CDE)
- ❌ Coach managing/scheduling/adjusting anabolics or any controlled/prescription substance through the app
- ❌ ANY interactive element on the coach-side substance view (no comments, no suggestions, no routing)
- ✅ LLM as a primary interface for both roles — coach investigates data, manages training/nutrition/recovery through chat; athlete manages compounds, navigates calendar, logs events through chat. Same as CDE. Safety tenets still apply (capability gate, non-destructive, deterministic confirmation).
- ❌ Coach's LLM having substance-write tools (add_compound_event, record_phase_change, mark_dose_taken, mark_dose_missed are excluded from the coach's tool set)
- ❌ Any destructive operation, for any actor

## The actual MVP (what we build FIRST)
**Phase 0 is built (2026-06-01).** A working Next.js + FastAPI app with mock data for 6 clients. The demo thread works: mock clients with wearable/lab/compound data → severity-ranked roster queue → click-through to client detail with cross-metric findings, wearables, labs, read-only substance mirror, and coaching surface forms.

This is a demo prop, not the real system. All data is mock — CDE's engine (extraction, PK, detectors, integrations) is not connected. No auth, no real sync, no billing. See [[wiki/ops/mvp-plan]] for full details of what was built and what remains mock.

The customer-discovery gate still applies before Phase 1. See [[wiki/ops/customer-discovery]].

## Why this is defensible
Generic coaching apps (Trainerize, TrueCoach) don't consolidate health data or do enhanced-athlete-aware detection. CDE's detector logic + PK model + extraction is the moat, and it already exists. See [[wiki/product/moat]].

## What kills this project
- Reintroducing coach-side substance management (the line in [[wiki/principles]])
- Adding any interactive element to the coach substance view
- Building the real system before validating coaches want it (see [[wiki/ops/customer-discovery]])
- Giving the coach's LLM substance-write tools (the tool set boundary is the enforcement)
- Bypassing the deterministic confirmation step on LLM-staged operations
- Treating modeled PK values as measured fact

## The one load-bearing uncertainty
Do physique coaches feel the data-fragmentation pain acutely enough to pay for a consolidation + detection layer — or do they get by fine on screenshots and check-in forms? Adherence and GTM are easier than the clinic version, but this question still gates the build. See [[wiki/ops/customer-discovery]].

## Wiki index
- **Spine**: [[wiki/principles]] ← safety tenets + the coach/user substance line; everything defers here
- **Product**: [[wiki/product/thesis]] · [[wiki/product/moat]] · [[wiki/product/buyer]]
- **Architecture**: [[wiki/architecture/relationship-to-cde]] · [[wiki/architecture/coach-read-layer]] · [[wiki/architecture/commit-model]] · [[wiki/architecture/interaction-model]] · [[wiki/architecture/two-sided-model]]
- **Ops**: [[wiki/ops/mvp-plan]] · [[wiki/ops/customer-discovery]] · [[wiki/ops/market]]
