---
tags: [architecture, integration, training, hevy]
status: active
updated: 2026-06-01
---

# Hevy integration

The training half of the data moat. Hevy is how this population logs their lifts. The integration is bidirectional and automatic: athlete logs a workout in Hevy → it appears in Coach Platform without the athlete doing anything extra → coach sees lift numbers, spots weight stalls, adjusts the program → the updated program syncs back to the athlete's Hevy.

For bodybuilding coaches the signal that matters is: **are working weights going up, stalling, or dropping.** Everything else — volume, frequency, RPE — is context for that question. A weight stall on compounds lifts during a blast is a red flag. A weight drop during prep is expected. The detector needs to know the difference.

---

## The loop

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  ATHLETE                           COACH                        │
│                                                                 │
│  1. Opens Hevy                     4. Roster queue shows:       │
│  2. Trains using the routine          "Marcus — bench stalled   │
│     the coach pushed                   3 weeks, 100kg×8 flat"  │
│  3. Logs sets/reps/weight                                       │
│     → auto-syncs to Coach          5. Coach clicks in, sees     │
│       Platform (no action             full workout history +    │
│       needed from athlete)            health data side by side  │
│                                                                 │
│                                    6. Coach adjusts program:    │
│                                       "drop bench to 3×6 at    │
│  8. Athlete opens Hevy,              105kg, add paused reps"   │
│     sees updated routine                                        │
│     with coach's changes           7. Updated routine pushes    │
│                                       to athlete's Hevy        │
│  9. Athlete gets a notification                                 │
│     in Coach Platform:             │                            │
│     "Your coach updated                                         │
│      Push Day A"                                                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

Both sides are passive where they should be. The athlete just uses Hevy. The coach just reviews the roster. The platform handles the sync in both directions.

---

## Hevy API (what exists)

REST API at `https://api.hevyapp.com/v1/`. Requires Hevy Pro ($9.99/mo per athlete). API key from `hevy.com/settings?developer`.

| What we do | Endpoint | Method |
|---|---|---|
| Pull new workouts | `/v1/workouts/events?since={last_sync}` | GET |
| Pull workout detail | `/v1/workouts/{id}` | GET |
| Pull exercise history | `/v1/exercise_history/{templateId}` | GET |
| Push a routine | `/v1/routines` | POST |
| Update a routine | `/v1/routines/{id}` | PUT |
| List routines | `/v1/routines` | GET |
| Cache exercise library | `/v1/exercise_templates` | GET |
| Create custom exercise | `/v1/exercise_templates` | POST |
| Pull body measurements | `/v1/body_measurements` | GET |

The events endpoint is the key for sync — returns creates, updates, and deletes since a given date, ordered newest-first. One call catches everything.

---

## Athlete side: auto-export

The athlete doesn't do anything. After connecting Hevy (paste API key once), their workouts flow automatically.

**Sync trigger:** Background job runs every 15 minutes per connected athlete, or on-demand when athlete/coach opens the dashboard. Calls `GET /v1/workouts/events?since={last_sync_timestamp}`.

**What gets stored per workout:**
- Session: title, date, duration, notes
- Per exercise: exercise name, muscle group
- Per set: weight_kg, reps, set_type (warmup/normal/failure/dropset), RPE if logged
- Computed: estimated 1RM per exercise (Epley: weight × (1 + reps/30)), tonnage (weight × reps), working weight (heaviest normal set)

**What the athlete sees in their dashboard:**
- "Last workout: Push Day A, 2 hours ago" — no new section needed, just a line in the sync status area
- Their lift progression is visible through the LLM: "How's my bench going?" → pulls from workout data
- If the coach updates their routine: **notification** — "Your coach updated Push Day A. Changes: bench press sets changed from 4×10 to 3×6, weight target increased to 105kg."

**Athlete notifications (new):**
Stored in a `notification` table, displayed as a banner or in-app alert:
- "Your coach updated Push Day A" (with diff of what changed)
- "Your coach created a new routine: Pull Day B"
- "Your coach added a recovery note: Reduce volume 30% this week"

These are one-way informational — not a conversation, not a reply mechanism. The athlete opens Hevy and sees the new routine.

---

## Coach side: alerts and programming

### What the coach sees in client detail

**New "Workouts" section** (between Wearables and Labs):

```
┌──────────────────────────────────────────────────────┐
│ Workouts                                    Last 7d  │
│                                                      │
│ ● Push Day A — Jun 1                                │
│   Bench Press    4×10 @ 100kg (est 1RM: 133kg)     │
│   Incline DB     3×12 @ 32.5kg                      │
│   Lat Raise      4×15 @ 12.5kg                      │
│   Tricep PD      3×12 @ 27.5kg                      │
│   Tonnage: 8,420kg · Duration: 58min                │
│                                                      │
│ ● Pull Day A — May 30                               │
│   Barbell Row    4×8 @ 120kg (est 1RM: 152kg)      │
│   ...                                                │
│                                                      │
│ ─── Key Lifts (4-week trend) ───                    │
│ Bench Press:  100kg×10 → 100kg×10 → 100kg×8  ⚠ STALL│
│ Squat:        160kg×6  → 165kg×5  → 170kg×5  ↑ +6% │
│ Barbell Row:  115kg×8  → 117.5×8  → 120kg×8  ↑ +4% │
│ RDL:          140kg×10 → 140kg×10 → 140kg×10  ⚠ STALL│
│                                                      │
└──────────────────────────────────────────────────────┘
```

The "Key Lifts" section is the money view. At a glance: what's progressing, what's stalling. The coach doesn't need to scroll through individual workouts — they see the trend per compound lift.

### Detector: weight stall / drop

The primary training detector. Runs after each workout sync.

**Stall detection:**
For each exercise the athlete performs regularly (≥ 2x in 3 weeks):
1. Compute working weight per session (heaviest normal/failure set weight)
2. Compare last 3 sessions of the same exercise
3. **Stall**: working weight flat (within ±2%) across 3+ sessions AND reps not increasing
4. **Drop**: working weight decreased ≥5% with no planned deload active

**Context matters — the detector checks phase:**
- During **blast**: a stall after week 6+ is a flag. Androgens should be driving progression. If weights aren't moving, something is wrong (recovery, nutrition, training stimulus, or the compounds aren't doing what they should).
- During **prep/cut**: weight drops are expected. The detector only flags drops >10% or drops that outpace the programmed deficit.
- During **deload**: everything is suppressed. No alerts.
- During **cruise/off**: moderate stalls are normal. Only flag multi-week drops.

**Finding format (same as health findings):**

```
⚠ TRAINING · NOTABLE
Bench press stalled — 100kg×8-10 for 3 consecutive sessions

Signals:
  Working weight: 100kg → 100kg → 100kg (flat 3wk)
  Reps: 10 → 10 → 8 (declining at same weight)
  Phase: Blast day 42
  Est 1RM: 133kg (flat)

Context:
  Recovery score trending down (65% → 52%)
  Resting HR elevated (+9 bpm from baseline)
  Test Cyp at steady state (85%), EQ still ramping (62%)
```

The cross-metric context is what makes this different from Hevy's own stagnation warnings. We know it's happening during a blast with declining recovery and elevated HR — that's an overreaching pattern, not just "lift more."

**Severity:**
- **Info**: Stall during cruise/off/prep (expected)
- **Notable**: Stall during blast (shouldn't be stalling if androgens are working and recovery is adequate)
- **Concerning**: Stall + declining recovery + elevated HR during blast (overreaching pattern)
- **Notable**: Weight drop >5% outside of planned deload/prep

### Coach gets alerts in the roster queue

The roster queue already ranks by severity. Training findings appear alongside health findings:

```
Jordan K.    Blast · Day 42    ⚠ bench stalled 3wk + HR↑ + recovery↓    2 findings
Marcus D.    Blast · Day 28    🔴 HCT 52.1% above range                 1 finding
Alex M.      Cruise · Day 18   ⚠ ALT elevated (oral)                    1 finding
Sam T.       Prep · Day 65     ℹ weight plateau (expected prep wall)    1 finding
```

Jordan's bench stall now appears in the roster. The coach clicks in, sees the full workout history + health data, and makes a decision.

### Coach adjusts → syncs to Hevy

When the coach decides to change the program:

1. **Through LLM chat:**
   > "Jordan's bench has stalled. Switch him to 3×6 at 105kg with paused reps, and add a second bench variation — close grip 3×8."
   > → LLM builds the updated routine JSON
   > → Confirmation dialog shows the diff: "Push Day A: Bench Press changed from 4×10@100kg to 3×6@105kg (paused). Added Close Grip Bench 3×8."
   > → Coach confirms
   > → `PUT /v1/routines/{id}` updates the routine in Jordan's Hevy
   > → Notification created for Jordan: "Your coach updated Push Day A"

2. **Through structured UI:**
   > Coach opens the routine editor, modifies exercises/sets/weight, clicks Save
   > → Same confirmation → push to Hevy → notification to athlete

**What gets pushed to Hevy:**
The full routine object (Hevy's format). Hevy replaces the existing routine with the updated version. Next time the athlete opens Hevy, they see the new program.

**What the athlete sees in Coach Platform:**
A notification: "Your coach updated Push Day A. Changes: Bench Press → 3×6 @ 105kg (was 4×10 @ 100kg). Added: Close Grip Bench Press 3×8."

The notification shows a **diff** — what changed, not just "something changed." The athlete knows exactly what's different before they walk into the gym.

---

## Data model

```sql
CREATE TABLE IF NOT EXISTS workout_session (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    hevy_id TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    duration_seconds INTEGER,
    notes TEXT,
    synced_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS workout_set (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL REFERENCES workout_session(id),
    user_id TEXT NOT NULL,
    exercise_template_id TEXT NOT NULL,
    exercise_name TEXT NOT NULL,
    set_index INTEGER NOT NULL,
    set_type TEXT NOT NULL,
    weight_kg REAL,
    reps INTEGER,
    rpe REAL,
    estimated_1rm REAL,
    UNIQUE(session_id, exercise_template_id, set_index)
);

CREATE TABLE IF NOT EXISTS exercise_template (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    muscle_group TEXT,
    equipment TEXT,
    is_custom INTEGER DEFAULT 0
);

-- What the coach pushed to the athlete's Hevy
CREATE TABLE IF NOT EXISTS routine_push (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    coach_id TEXT NOT NULL,
    athlete_id TEXT NOT NULL,
    hevy_routine_id TEXT,
    title TEXT NOT NULL,
    routine_json TEXT NOT NULL,
    pushed_at TEXT NOT NULL DEFAULT (datetime('now')),
    status TEXT DEFAULT 'active'
);

-- Notifications for both sides
CREATE TABLE IF NOT EXISTS notification (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    actor_id TEXT,
    actor_role TEXT,
    type TEXT NOT NULL,         -- routine_updated, routine_created, recovery_note, finding_new
    title TEXT NOT NULL,
    body TEXT,
    detail_json TEXT,           -- diff, metadata
    read INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Lift progression tracking (computed from workout_set, materialized for fast queries)
CREATE TABLE IF NOT EXISTS lift_progression (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    exercise_template_id TEXT NOT NULL,
    exercise_name TEXT NOT NULL,
    session_date TEXT NOT NULL,
    working_weight_kg REAL,     -- heaviest normal/failure set
    best_set_reps INTEGER,      -- reps at working weight
    estimated_1rm REAL,
    total_volume_kg REAL,       -- weight × reps summed across all sets
    set_count INTEGER,
    UNIQUE(user_id, exercise_template_id, session_date)
);

CREATE INDEX IF NOT EXISTS idx_lift_prog_user_ex ON lift_progression(user_id, exercise_template_id, session_date);
CREATE INDEX IF NOT EXISTS idx_workout_session_user ON workout_session(user_id, started_at);
CREATE INDEX IF NOT EXISTS idx_notification_user ON notification(user_id, read, created_at);
```

The `lift_progression` table is the key query surface. Instead of joining workout_session → workout_set → aggregating per exercise every time, we materialize the per-exercise-per-session summary after each sync. The stall detector reads from this table.

---

## Stall detector (concrete implementation)

```python
def detect_training_stall(conn, user_id, as_of):
    """Detect weight stalls/drops on compound lifts."""
    # Get current phase
    phase = get_current_phase(conn, user_id)
    if phase == "deload":
        return None  # suppress during deload

    # Get exercises performed ≥2x in last 21 days
    frequent_exercises = conn.execute("""
        SELECT exercise_template_id, exercise_name, COUNT(*) as sessions
        FROM lift_progression
        WHERE user_id = ? AND session_date >= date(?, '-21 days')
        GROUP BY exercise_template_id
        HAVING sessions >= 2
    """, (user_id, as_of)).fetchall()

    stalls = []
    drops = []

    for ex in frequent_exercises:
        # Last 4 sessions of this exercise
        history = conn.execute("""
            SELECT session_date, working_weight_kg, best_set_reps, estimated_1rm
            FROM lift_progression
            WHERE user_id = ? AND exercise_template_id = ?
            ORDER BY session_date DESC LIMIT 4
        """, (user_id, ex["exercise_template_id"])).fetchall()

        if len(history) < 3:
            continue

        weights = [h["working_weight_kg"] for h in history if h["working_weight_kg"]]
        if not weights:
            continue

        latest = weights[0]
        oldest = weights[-1]

        # Stall: within ±2% across 3+ sessions
        if len(weights) >= 3:
            max_w = max(weights[:3])
            min_w = min(weights[:3])
            if max_w > 0 and (max_w - min_w) / max_w < 0.02:
                # Also check reps aren't increasing (true stall vs. rep progression)
                reps = [h["best_set_reps"] for h in history[:3] if h["best_set_reps"]]
                if reps and reps[0] <= reps[-1]:  # reps flat or declining
                    stalls.append({
                        "exercise": ex["exercise_name"],
                        "weight": latest,
                        "sessions": len(weights),
                        "reps_trend": reps,
                    })

        # Drop: ≥5% decrease from peak in window
        if len(weights) >= 2:
            peak = max(weights[1:])  # peak excluding latest
            if peak > 0 and (peak - latest) / peak >= 0.05:
                if phase not in ("prep", "off"):  # expected during prep
                    drops.append({
                        "exercise": ex["exercise_name"],
                        "current": latest,
                        "peak": peak,
                        "drop_pct": round((peak - latest) / peak * 100, 1),
                    })

    if not stalls and not drops:
        return None

    # Build finding
    severity = "info"
    if phase == "blast" and stalls:
        severity = "notable"  # shouldn't stall on blast
    if phase == "blast" and (stalls or drops):
        # Check if recovery is also declining (cross-metric)
        recovery_trend = get_wearable_trend(conn, user_id, "recovery_score", 14)
        if recovery_trend and recovery_trend["direction"] == "falling":
            severity = "concerning"  # stall + declining recovery on blast = overreaching

    signals = []
    for s in stalls:
        signals.append({
            "label": s["exercise"],
            "value": f"{s['weight']}kg",
            "direction": "flat",
            "delta": f"flat {s['sessions']} sessions, reps {s['reps_trend']}"
        })
    for d in drops:
        signals.append({
            "label": d["exercise"],
            "value": f"{d['current']}kg",
            "direction": "down",
            "delta": f"-{d['drop_pct']}% from {d['peak']}kg"
        })

    headline_parts = []
    if stalls:
        headline_parts.append(f"{stalls[0]['exercise']} stalled at {stalls[0]['weight']}kg")
    if drops:
        headline_parts.append(f"{drops[0]['exercise']} dropped {drops[0]['drop_pct']}%")

    return Finding(
        detector_id="training_stall",
        theme="training",
        severity=severity,
        headline=" — ".join(headline_parts),
        summary=f"{len(stalls)} stall(s) and {len(drops)} drop(s) detected across compound lifts.",
        signals=signals,
        # drug_context and recommendations populated by framework
    )
```

This runs after every workout sync. Findings go into the same `finding` table as health findings. The roster queue ranks them alongside hematocrit drift, ALT spikes, and everything else.

---

## Notification system

Both sides get notifications for actions the other side takes.

**Athlete receives notifications when:**
- Coach creates a new routine → "Your coach created Pull Day B"
- Coach updates a routine → "Your coach updated Push Day A" with diff
- Coach adds a recovery note → "Your coach added a note: Reduce volume 30%"
- Coach changes nutrition targets → "Your coach updated nutrition: 3400cal, 280g protein"

**Coach receives notifications when (via the roster queue, not a separate notification):**
- Athlete completes a workout → workout appears in client detail (passive, no alert unless stall detected)
- Training stall/drop detected → finding in roster queue
- Athlete changes compounds → visible in substance mirror (passive)

Athlete notifications are stored in the `notification` table and displayed as a list in the athlete dashboard (new section, above or below "Your Programming"). Unread count badge in the header.

**Notification when routine changes (the diff):**

When coach calls `PUT /v1/routines/{id}`, the platform compares the old routine_json (from routine_push table) with the new one and generates a human-readable diff:

```
Push Day A updated by your coach:
  Bench Press: 4×10 @ 100kg → 3×6 @ 105kg (paused reps)
  + Close Grip Bench Press: 3×8 @ 80kg (new)
  Lateral Raise: unchanged
  Tricep Pushdown: unchanged
```

This is the deterministic render of the change — not LLM-generated, not vague. The athlete knows exactly what's different.

---

## LLM tools

**Coach tools:**
- `get_workout_history(athlete_id, days)` — recent workouts with per-exercise sets/reps/weight
- `get_lift_progression(athlete_id, exercise_name, days)` — working weight trend for a specific lift
- `get_training_summary(athlete_id, days)` — frequency, total volume, key lift trends, stalls/drops
- `push_routine(athlete_id, title, exercises)` — create routine in athlete's Hevy (coaching surface write)
- `update_routine(athlete_id, routine_id, exercises)` — modify existing routine in athlete's Hevy

**Athlete tools:**
- `get_workout_history(days)` — own workouts
- `get_lift_progression(exercise_name, days)` — own progression
- `get_training_summary(days)` — own volume/frequency

Coach example:
> "Jordan's bench has been flat for 3 weeks. What do his other chest movements look like?"
> → calls get_lift_progression for bench, incline DB, cable fly
> → "Bench: 100kg flat 3 weeks. Incline DB: 32.5→35kg, progressing. Cable fly: 20kg flat. The stall is on pressing movements specifically. His overhead press is also flat at 60kg. Recovery score is down 15% over the same period. This looks like pressing-specific fatigue with a recovery component — consider reducing pressing volume and adding a deload week."

> "Update his push day — drop bench to 3×6 at 105kg paused, add close grip 3×8, cut lateral raises to 3 sets"
> → builds routine diff → confirmation dialog → pushes to Hevy → notification to athlete

---

## Build order

1. **Tables + sync** — Add tables to database.py. Build Hevy sync module (incremental via events endpoint). Compute lift_progression after each sync.
2. **Coach client detail** — New "Workouts" section with recent sessions + key lift trends + stall indicators.
3. **Stall detector** — Detect weight stalls/drops, create findings with phase-aware severity.
4. **Routine push** — Coach builds/updates routines, pushes to Hevy via API.
5. **Notifications** — Athlete sees coach changes, coach sees training findings in roster.
6. **LLM tools** — get_workout_history, get_lift_progression, get_training_summary, push_routine, update_routine.

---

## Authentication & onboarding

**No OAuth available.** Hevy built OAuth exclusively for their ChatGPT integration (HevyGPT). Third-party apps cannot register OAuth clients — there is no developer portal, no client_id provisioning, no redirect URI registration. The only third-party auth method is the **per-user API key** from `hevy.com/settings?developer`. Contact pedro@hevyapp.com if this changes.

**What this means for onboarding:** The athlete pastes their API key during intake. This is a one-time step, same friction as any "connect your account" flow — but it's a copy-paste, not a one-click OAuth authorize.

**Intake flow (during athlete onboarding):**
1. Coach invites athlete to the platform
2. Athlete signs up, connects integrations
3. For Hevy: the app shows a step-by-step with a direct link to `hevy.com/settings?developer`
4. Athlete copies their API key, pastes it into the integration field
5. Platform validates the key immediately (`GET /v1/user/info` — if 200, the key works)
6. Platform syncs all workout history in the background
7. Done — everything auto-syncs from here

**Reducing friction:**
- The Hevy settings page is one click from the integration screen (direct link)
- The key validates instantly — athlete gets immediate feedback ("Connected! Syncing 331 workouts...")
- If the athlete doesn't have Hevy Pro, show a clear message: "Hevy Pro ($9.99/mo) is required for training data sync. Most serious lifters already have it."
- The key is stored encrypted per athlete. The coach never sees it.

**If Hevy adds OAuth later:** The integration is structured so that swapping API key auth for OAuth is a config change in the sync module, not a rewrite. The workout data format and storage are the same regardless of auth method.

---

## What this does NOT do

- Replace Hevy. Athletes train in Hevy. We read from it and write routines to it.
- Track cardio. Bodybuilding coaches don't care. This is resistance training only.
- Require the coach to have Hevy. Coach works in Coach Platform; platform talks to Hevy.
- Generate programs automatically. The coach programs. The platform delivers and monitors.

Related: [[wiki/architecture/coach-read-layer]] · [[wiki/architecture/two-sided-model]] · [[wiki/architecture/interaction-model]] · [[wiki/architecture/commit-model]] · [[wiki/ops/mvp-plan]]
