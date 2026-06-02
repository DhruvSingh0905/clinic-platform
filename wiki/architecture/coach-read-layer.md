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

## Implementation status (2026-06-01)

The read layer described above is implemented in the Phase 0 build with mock data. Specifically:

**Roster queue:** `GET /api/coach/{coach_id}/roster` returns clients sorted by top-finding severity (concerning → notable → info). The frontend at `/coach` renders this as a ranked card list. Each card shows athlete name, phase, integrations, top finding headline, and signal badges.

**Client detail:** `GET /api/coach/{coach_id}/client/{athlete_id}` returns findings, wearables, labs, substance events, drug levels, training, nutrition, and recovery. The frontend at `/coach/client/[id]` renders these as collapsible sections.

**Read-only substance mirror:** The client detail view renders substance events as a timeline and drug levels as static progress bars. The section has a lock icon, a "Read-only · Athlete self-reported" label, and a muted background. 6 Playwright tests verify zero inputs, buttons, or action affordances in this section. The backend has no `POST /api/coach/.../substance` endpoint — the absence is the enforcement.

**Coach write surface:** Training, nutrition, and recovery sections have inline forms that call `POST` endpoints through the typed operation path in `.src/coach/operations.py`.

**What is not yet real:** Multi-tenant auth does not exist (coach ID is passed in the URL). No sensitivity nudge UI is built. Training/nutrition/recovery form Save buttons in the frontend don't call the API (writes work through LLM chat or direct API calls). The "Ask about this" button on findings doesn't open chat in finding-thread mode yet.

**What changed since Phase 0:** CDE detectors now run against the mock data — real cv_stress findings generated. PK model connected — drug levels recomputed on compound events. The roster queue sorts by live severity from both mock and detector-generated findings. The LLM chat is operational for both roles with tool-based data access. Two-sided visibility confirmed: coach sets training/nutrition/recovery → athlete sees it; athlete logs substances → coach sees it read-only.

Related: [[wiki/principles]] · [[wiki/architecture/relationship-to-cde]] · [[wiki/architecture/commit-model]] · [[wiki/architecture/two-sided-model]]
