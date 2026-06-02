---
tags: [architecture, coach, read-layer, critical]
status: active
updated: 2026-06-01
---

# Coach read layer

The net-new surface this product adds on top of CDE: what the coach sees and what the coach can do. The defining design constraint lives here.

## Two data categories, two different treatments
The coach interacts with client data in exactly two modes, split by whether the underlying thing is lawful for a coach to direct.

### Coach-managed (active write surface)
Training load, nutrition/macros, recovery, sleep targets, bodyweight goals, programming. The coach actively manages these through structured tools. Writes go through the safety tenets (typed operations, non-destructive, deterministic confirm — see [[wiki/architecture/commit-model]]). This is normal coaching and carries no special constraint beyond the standard write-path safety.

### User-self-logged (strictly read-only mirror)
Anabolics and any controlled or prescription substance. The **user** logs these on their own side, exactly as CDE intakes cycle data — their own record. The coach sees a **read-only mirror** and nothing else.

## The read-only mirror has NO interactive elements
This is the hard rule that defines the product. The coach-side substance view:
- has **no comment field** on a dose or compound
- has **no suggest / adjust / approve** affordance
- has **no routing** of a dosing question through the app
- has **no notification workflow** that turns viewing into a back-and-forth

The coach sees exactly what the user logged, the way they'd see a screenshot the user texted them. If the coach wants to discuss the substance side, that happens **off-platform** on whatever they already use to text. The user updates their own record; the coach sees the result. The app is where the user keeps their record — never where the substance side is coached.

An interactive element on this view changes what the product *is* (from a data platform into a substance-management tool). So this is enforced as a hard product/architecture rule: the substance view renders display components only, no inputs, no actions. If someone later adds a button because nothing stopped them, the design breaks — the rule has to survive in the code and the docs.

## The roster + review queue (over the manageable + viewable data)
The coach's home is a **ranked review queue** across their client roster: which clients have something worth attention this week, severity-ordered, one line each, one click to detail. Built from CDE's detector severity output. This spans all data the coach can see (training, nutrition, recovery, wearable trends, and — read-only — the user's logged substances as context), but the queue surfacing a substance-related detector finding is still just *surfacing*, never a prompt to act through the app.

## Modeled values stay labeled modeled
PK-estimated levels (from CDE's model) shown to either side are labeled "estimated from logged protocol," never as measured fact. Inherited discipline from CDE's silent-wrongness rule.

## The removal test (why this is safe to ship)
Delete every substance feature and a physique coach still pays for consolidated, domain-aware client data. The substance side is the user's own diary that they share read-only; it is not the product. That's the whole reason the read-only line costs us little. See [[wiki/principles]].

## Implementation status (2026-06-02)

**Fully built.** The coach read layer + write layer are both operational.

**Roster queue:** Severity-ranked client cards with findings, phase badges, sync times. Training stall findings from Hevy integration appear alongside health findings.

**Client detail (redesigned):** Tabbed layout — Findings (signal cards with mini charts + provenance), Vitals (weight-prominent AreaCharts with trend deltas), Bloods (metric-centric expandable rows with ref range bands), Training (flagged lifts + exercise explorer + routine builder + workout log), Protocol (timeline + NLP input + form for coach modifications), Nutrition (macro breakdown + form), Log (universal change log). Always-visible collapsible notes panel on the right.

**Coach substance access:** The substance boundary was reversed. The coach can now modify the athlete's protocol (START/STOP/DOSE_CHANGE) through both the Protocol tab UI (NLP input or manual form) and the LLM chat. All modifications create athlete notifications requiring confirmation. `POST /api/coach/{id}/client/{id}/substance` endpoint exists.

**Coach write surface:** All write operations (training, nutrition, recovery, substances, routine pushes) go through typed operations with deterministic confirmation dialogs. All create athlete notifications.

**What remains:** Multi-tenant auth, billing, sensitivity nudge UI, roster page UX improvements (compact cards).

Related: [[wiki/principles]] · [[wiki/architecture/relationship-to-cde]] · [[wiki/architecture/commit-model]] · [[wiki/architecture/two-sided-model]]
