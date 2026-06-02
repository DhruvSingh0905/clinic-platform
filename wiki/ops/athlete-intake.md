---
tags: [ops, intake, onboarding]
status: active
updated: 2026-06-01
---

# Athlete intake

What happens when a new athlete joins a coach's roster. The goal: the coach should have a full picture of the athlete's health and training data within 24 hours of signup, with zero manual data entry.

## The intake sequence

### Step 1 — Coach invites athlete
Coach enters athlete's email in Coach Platform. System sends an invite link. Athlete clicks and creates an account.

### Step 2 — Connect integrations (athlete does this once)

The athlete connects their data sources during onboarding. Each is a one-time step.

**Hevy (workout data):**
- Requires Hevy Pro ($9.99/mo) — most serious lifters already have it
- Athlete clicks "Connect Hevy" → opens `hevy.com/settings?developer` in a new tab
- Athlete copies their API key, pastes it into Coach Platform
- Platform validates instantly (`GET /v1/user/info` — if 200, connected)
- Platform syncs full workout history in the background (can be 300+ workouts)
- **Why API key, not OAuth:** Hevy only offers OAuth for their ChatGPT integration. Third-party apps use API keys. There's no developer portal or OAuth app registration. If this changes, the integration is structured to swap auth methods without a rewrite. Contact: pedro@hevyapp.com.

**Apple Health (wearables — HR, HRV, weight, BP, steps):**
- Athlete exports from iPhone Health app → uploads ZIP/XML to Coach Platform
- One-time bulk import, then periodic re-exports
- No OAuth available — Apple Health doesn't expose a cloud API

**Whoop (recovery, HRV RMSSD, resting HR, sleep):**
- Athlete clicks "Connect Whoop" → OAuth flow → one-click authorize
- Auto-syncs after authorization

**Withings (weight, BP, body composition):**
- OAuth flow, same as Whoop
- Phase 2 integration

**Dexcom/CGM (glucose):**
- OAuth flow
- Phase 2, relevant for athletes on GH/insulin/MK-677

### Step 3 — Log current compounds (athlete does this)
The athlete enters their current compound stack through the LLM chat:
> "I'm on test cyp 500mg twice a week, anavar 50mg daily, and anastrozole 0.5mg every other day. Started 4 weeks ago."

The LLM parses this into structured compound events, confirms with the athlete, and logs START events with doses/frequencies. PK model generates drug level estimates. Detectors start correlating.

This is the CDE model — the user self-logs substances through natural conversation. The coach sees it read-only after.

### Step 4 — Upload recent bloodwork (if available)
Athlete uploads lab PDF(s) through the upload button:
- Coach Platform extracts via Claude Vision → LOINC-normalized → stored
- Detectors run against the bloodwork + compound context
- If the athlete has multiple draws, upload all — the system builds a timeline

### Step 5 — Platform builds the picture
With integrations connected and initial data in:
- Detectors run across wearable + lab + compound data
- Findings generated (or not — "no issues detected" is also a finding)
- Athlete appears in coach's roster with severity-ranked status
- Workout data from Hevy starts flowing in (stall detection begins after 2-3 sessions)

## What the coach sees after intake

Within 24 hours of a new athlete completing onboarding, the coach has:
- Wearable trends (HR, HRV, weight, recovery) — from Whoop/Apple Health
- Lab history with flags — from uploaded bloodwork PDFs
- Compound stack with PK-modeled drug levels — from the athlete's self-report
- Workout history with lift progression — from Hevy
- Any detector findings (hematocrit drift, hepatic response, training stalls, etc.)
- The athlete's current training block and nutrition targets (if the coach has already set them)

This is the demo moment for the platform: "I can see everything about this client in one place, with the stuff that matters flagged."

## What intake does NOT include

- Coach setting up compounds for the athlete (substances are athlete-self-logged, never coach-managed — see [[wiki/principles]])
- Medical history or intake forms (we're a data platform, not an EHR)
- Billing setup (deferred — see [[wiki/ops/mvp-plan]])
- Identity verification (the athlete is invited by a coach they already know)

## Friction reality

The coach is the buyer. The coach puts the athlete on the platform. The athlete doesn't choose — they're told "sign up and connect your stuff." This is how coaching already works (Trainerize, TrueCoach — the coach sends a link, the client does what they're told).

Total athlete onboarding time from a desktop: **~3 minutes.** Hevy key paste, Whoop OAuth click, upload a lab PDF, tell the chat what you're on. That's it. The coach-as-buyer dynamic means we don't need to optimize for casual drop-in users who might bounce at a copy-paste step. The athlete is already paying this coach $200+/month — they'll spend 3 minutes.

If Hevy ever opens third-party OAuth, take it — one less step. But don't over-engineer around it. The API key works and the population will do it.

Related: [[wiki/architecture/hevy-integration]] · [[wiki/architecture/two-sided-model]] · [[wiki/architecture/interaction-model]] · [[wiki/architecture/relationship-to-cde]]
