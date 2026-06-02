---
tags: [product, moat]
status: active
updated: 2026-05-31
---

# The moat

## What it is NOT
It is not "a coaching app." Generic coaching platforms (Trainerize, TrueCoach, etc.) already do programming delivery, check-in forms, and habit tracking. If we pitch "manage your clients," we lose to tools coaches already use. We are not competing on coaching-workflow table-stakes.

## What it is
**Continuous health-data consolidation + domain-aware detection for enhanced-athlete physiology.** Generic tools show a number or a check-in note. None of them ingest Whoop + nutrition + labs + substance log together and know:
- A rising creatinine in a 230-lb AAS user is muscle-mass confound, not renal decline (cystatin-C disambiguates).
- An ALT spike time-locked to a 17aa oral start at 2–6 weeks is expected, not alarming.
- A test:EQ ratio at a level that predicts an E2 crash via EQ's AI metabolite.
- HR/HRV + lipids + BP drifting together as a compound cardiovascular signal no single metric catches.

That domain logic is the asset, and it already exists in CDE — detector themes, PK model, compound database. Years of biology depth, not ML novelty. A generic coaching-app vendor can't replicate it without the domain knowledge; a domain expert without the systems engineering can't ship it. The intersection is the defensibility.

## The engine (inherited from CDE)
- **8 detector themes** (cardiovascular, hepatic, hormonal, metabolic, renal, hematological, inflammation, HPTA) — CDE `src/cde/detectors/themes.py`
- **PK drug-level model** (86 compounds, day-by-day levels, adherence-aware recalc) — CDE `src/cde/store/pk_model.py`
- **Bloodwork extraction** (LOINC-normalized, 58/58 validated, zero silent wrongness) — CDE `src/cde/extraction/`
- **Compound database** (verified half-lives, mechanisms, monitoring markers)

See [[wiki/architecture/relationship-to-cde]].

## The new layer (coach refactor)
The **roster review queue**: detector output ranked across all of a coach's clients into "these few need your eyes this week," one line each, one click to detail. The ranking is CDE's detector severity; the multi-tenant roster view is net-new. This is what makes a coach open it on a Sunday.

## The moat does not require crossing the line
The detection + consolidation depth is worth paying for on its own (the removal test in [[wiki/principles]] confirms it). The temptation will be to extend into coach-directed substance management because the market pulls there — that trades a clean, defensible product for a worse one to own. The moat is *consolidating data and surfacing what matters*; the coach acts on the lawful side and the user owns their substance log. Keep it there.

Related: [[wiki/principles]] · [[wiki/product/thesis]] · [[wiki/architecture/relationship-to-cde]] · [[wiki/architecture/coach-read-layer]]
