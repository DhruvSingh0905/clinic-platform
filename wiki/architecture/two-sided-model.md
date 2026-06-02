---
tags: [architecture, two-sided]
status: active
updated: 2026-05-31
---

# Two-sided model

Both sides must benefit or the loop dies: users sync because their coach acts on it; coaches pay because it makes them better and faster. The design splits cleanly by side.

## Data spine: passive first, exception-based second
**The durable data is passive.** It flows whether or not the user actively engages:
- Whoop (dominant in this population) → recovery, HRV (RMSSD), resting HR, respiratory rate, sleep
- Apple Health (the hub — most devices sync to it) → HRV (SDNN), weight, BP, and whatever routes through it
- Nutrition app → macros/calories
- CGM (Dexcom) → glucose, where relevant
- Scale / BP cuff (Withings) → weight, BP
- Lab PDFs (periodic) → bloodwork panel

**Active input is exception-based, not daily.** Mirrors how a coach already reasons: *assume the plan is being followed unless the client says otherwise.* The client speaks up on exceptions ("skipped Tuesday's session," "felt flat all week"). For their own substance log, the same: they log starts/stops/changes as events. Exceptions can go through the (demoted) LLM as a one-line interaction → staged typed operation → confirm → commit (see [[wiki/architecture/commit-model]]), or through plain structured UI. Subjective "how do you feel" decays fast — enrichment, not foundation. Adherence is favorable here: a paying physique client is dedicated by selection.

## Honesty constraint on the user-facing view
Users see their own **deterministic, modeled** trends — PK-estimated levels (from CDE's model), HR/HRV/weight trends, lab history. Modeled given logged adherence, not measured. Label "estimated from your logged protocol," never a hard measured number. This is the [[wiki/principles]] conservative posture applied to display: claim less than the number implies.

## Coach side: the roster review queue
The unit is a **ranked exception list across the roster**, not a wall of dashboards. A coach with 40 clients wants "these 6 need your eyes this week," severity-ordered, one line each, one click to detail. Detector severity (info/notable/concerning) is the ranking function. The coach manages training/nutrition/recovery from here; substance data appears read-only (see [[wiki/architecture/coach-read-layer]]).

## Per-client sensitivity: nudge, don't set
Coaches do NOT hand-set raw detector thresholds. Detectors carry population-derived defaults (the thing the coach can't build); the coach nudges *sensitivity* within guardrails ("watch this client's HR more aggressively") via toggle, not raw number. Hand-set thresholds drift into noise/silence and explode support. The moat is knowing what the thresholds should be — don't hand that judgment back.

## What each side's job actually is
- **User side:** keep passive sync authorized; log exceptions and their own substance events; see their own trends. Narrow.
- **Coach side:** review the ranked roster queue on their cadence; manage the lawful coaching surface; view (read-only) the substance context; nudge sensitivity. That's it.

Related: [[wiki/principles]] · [[wiki/product/thesis]] · [[wiki/architecture/relationship-to-cde]] · [[wiki/architecture/coach-read-layer]] · [[wiki/architecture/interaction-model]]
