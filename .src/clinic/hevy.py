"""Hevy integration — bidirectional sync, stall detection, routine push, notifications.

Patient trains in Hevy -> workouts auto-sync here -> stall detector runs ->
clinician sees findings in roster -> clinician adjusts routine -> pushes back to Hevy ->
patient gets notified.
"""
import sqlite3
import json
import uuid
import math
from datetime import date, datetime, timedelta
from typing import Optional

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

HEVY_BASE = "https://api.hevyapp.com/v1"


# ═══════════════════════════════════════════════════════════════
# Hevy API client
# ═══════════════════════════════════════════════════════════════

def _hevy_headers(api_key: str) -> dict:
    return {"api-key": api_key, "Content-Type": "application/json"}


def _hevy_get(path: str, api_key: str, params: dict | None = None) -> dict:
    """GET from Hevy API. Returns parsed JSON."""
    if not HAS_HTTPX:
        raise RuntimeError("httpx not installed — run: pip install httpx")
    r = httpx.get(f"{HEVY_BASE}{path}", headers=_hevy_headers(api_key), params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def _hevy_post(path: str, api_key: str, body: dict) -> dict:
    if not HAS_HTTPX:
        raise RuntimeError("httpx not installed — run: pip install httpx")
    r = httpx.post(f"{HEVY_BASE}{path}", headers=_hevy_headers(api_key), json=body, timeout=30)
    r.raise_for_status()
    return r.json()


def _hevy_put(path: str, api_key: str, body: dict) -> dict:
    if not HAS_HTTPX:
        raise RuntimeError("httpx not installed — run: pip install httpx")
    r = httpx.put(f"{HEVY_BASE}{path}", headers=_hevy_headers(api_key), json=body, timeout=30)
    r.raise_for_status()
    return r.json()


def get_hevy_api_key(conn: sqlite3.Connection, user_id: str) -> str | None:
    """Get stored Hevy API key for a patient."""
    row = conn.execute(
        "SELECT last_sync FROM integration_status WHERE patient_id = ? AND provider = 'hevy'",
        (user_id,)
    ).fetchone()
    # API key stored in a metadata column or separate field — for now use last_sync as placeholder
    # TODO: proper encrypted key storage
    meta = conn.execute(
        "SELECT status FROM integration_status WHERE patient_id = ? AND provider = 'hevy'",
        (user_id,)
    ).fetchone()
    return None  # Will be implemented when real keys are available


# ═══════════════════════════════════════════════════════════════
# Workout sync (Hevy → Clinic Platform)
# ═══════════════════════════════════════════════════════════════

def _epley_1rm(weight: float, reps: int) -> float:
    """Estimate 1RM using Epley formula."""
    if reps <= 0 or weight <= 0:
        return 0
    if reps == 1:
        return round(weight, 1)
    return round(weight * (1 + reps / 30), 1)


def _clean_weight(kg: float) -> float:
    """Round weights to nearest 0.5kg for display (Hevy stores exact lbs-to-kg conversions)."""
    return round(kg * 2) / 2


def store_workout(conn: sqlite3.Connection, user_id: str, workout: dict) -> str:
    """Store a single workout from Hevy API response format.

    workout format (from Hevy API):
    {
        "id": "...",
        "title": "Push Day A",
        "start_time": "2026-06-01T10:00:00Z",
        "end_time": "2026-06-01T11:05:00Z",
        "exercises": [
            {
                "exercise_template_id": "D04AC939",
                "title": "Bench Press (Barbell)",
                "sets": [
                    {"type": "normal", "weight_kg": 100, "reps": 10, "rpe": 7},
                    ...
                ]
            }
        ]
    }
    """
    hevy_id = workout["id"]
    title = workout.get("title", "Untitled")
    started = workout.get("start_time", datetime.now().isoformat())
    ended = workout.get("end_time")
    duration = None
    if started and ended:
        try:
            s = datetime.fromisoformat(started.replace("Z", "+00:00"))
            e = datetime.fromisoformat(ended.replace("Z", "+00:00"))
            duration = int((e - s).total_seconds())
        except (ValueError, TypeError):
            pass

    session_id = str(uuid.uuid4())

    conn.execute("""
        INSERT OR REPLACE INTO workout_session (id, user_id, hevy_id, title, started_at, ended_at, duration_seconds, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (session_id, user_id, hevy_id, title, started, ended, duration, workout.get("description")))

    # Store sets + compute progression
    session_date = started[:10]  # YYYY-MM-DD
    exercise_stats: dict[str, dict] = {}

    for ex in workout.get("exercises", []):
        template_id = ex.get("exercise_template_id", "unknown")
        ex_name = ex.get("title", template_id)

        # Cache exercise template
        conn.execute("""
            INSERT OR IGNORE INTO exercise_template (id, title, muscle_group, equipment)
            VALUES (?, ?, ?, ?)
        """, (template_id, ex_name, ex.get("muscle_group"), ex.get("equipment")))

        for i, s in enumerate(ex.get("sets", [])):
            weight = s.get("weight_kg") or 0
            reps = s.get("reps") or 0
            rpe = s.get("rpe")
            e1rm = _epley_1rm(weight, reps) if weight and reps else None

            conn.execute("""
                INSERT OR REPLACE INTO workout_set
                (session_id, user_id, exercise_template_id, exercise_name, set_index, set_type, weight_kg, reps, rpe, estimated_1rm)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (session_id, user_id, template_id, ex_name, i, s.get("type", "normal"), weight, reps, rpe, e1rm))

            # Accumulate stats for lift_progression
            if template_id not in exercise_stats:
                exercise_stats[template_id] = {
                    "name": ex_name, "working_weight": 0, "best_reps": 0,
                    "best_1rm": 0, "total_volume": 0, "set_count": 0,
                }
            stats = exercise_stats[template_id]
            if s.get("type") in ("normal", "failure") and weight > 0:
                if weight > stats["working_weight"]:
                    stats["working_weight"] = weight
                    stats["best_reps"] = reps
                if e1rm and e1rm > stats["best_1rm"]:
                    stats["best_1rm"] = e1rm
            stats["total_volume"] += weight * reps
            stats["set_count"] += 1

    # Materialize lift_progression
    for template_id, stats in exercise_stats.items():
        if stats["working_weight"] > 0:
            conn.execute("""
                INSERT OR REPLACE INTO lift_progression
                (user_id, exercise_template_id, exercise_name, session_date,
                 working_weight_kg, best_set_reps, estimated_1rm, total_volume_kg, set_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_id, template_id, stats["name"], session_date,
                  stats["working_weight"], stats["best_reps"], stats["best_1rm"],
                  round(stats["total_volume"], 1), stats["set_count"]))

    conn.commit()
    return session_id


def sync_workouts_from_hevy(conn: sqlite3.Connection, user_id: str, api_key: str) -> int:
    """Incremental sync from Hevy. Returns number of workouts synced."""
    # Get last sync time
    row = conn.execute(
        "SELECT MAX(synced_at) as last FROM workout_session WHERE user_id = ?", (user_id,)
    ).fetchone()
    since = row["last"] if row and row["last"] else "2020-01-01T00:00:00Z"

    data = _hevy_get("/workouts/events", api_key, params={"since": since})
    count = 0
    # Hevy uses "workouts" or "data" depending on endpoint
    workouts = data.get("workouts", data.get("data", []))
    for workout in workouts:
        store_workout(conn, user_id, workout)
        count += 1

    # Update integration last_sync
    conn.execute(
        "UPDATE integration_status SET last_sync = ? WHERE patient_id = ? AND provider = 'hevy'",
        (datetime.now().isoformat(), user_id)
    )
    conn.commit()
    return count


# ═══════════════════════════════════════════════════════════════
# Stall detector
# ═══════════════════════════════════════════════════════════════

def detect_training_stall(conn: sqlite3.Connection, user_id: str, as_of: str | None = None) -> dict | None:
    """Detect weight stalls/drops on compound lifts. Returns a finding dict or None."""
    if not as_of:
        as_of = date.today().isoformat()

    # Exercises performed >=2x in last 21 days
    cutoff = (date.fromisoformat(as_of) - timedelta(days=21)).isoformat()
    frequent = conn.execute("""
        SELECT exercise_template_id, exercise_name, COUNT(*) as sessions
        FROM lift_progression
        WHERE user_id = ? AND session_date >= ?
        GROUP BY exercise_template_id HAVING sessions >= 2
    """, (user_id, cutoff)).fetchall()

    stalls = []
    drops = []

    for ex in frequent:
        history = conn.execute("""
            SELECT session_date, working_weight_kg, best_set_reps, estimated_1rm
            FROM lift_progression
            WHERE user_id = ? AND exercise_template_id = ?
            ORDER BY session_date DESC LIMIT 4
        """, (user_id, ex["exercise_template_id"])).fetchall()

        if len(history) < 3:
            continue

        weights = [h["working_weight_kg"] for h in history if h["working_weight_kg"]]
        if not weights or len(weights) < 3:
            continue

        latest = weights[0]

        # Stall: +/-2% across 3+ sessions
        recent_3 = weights[:3]
        max_w = max(recent_3)
        min_w = min(recent_3)
        if max_w > 0 and (max_w - min_w) / max_w < 0.02:
            reps = [h["best_set_reps"] for h in history[:3] if h["best_set_reps"]]
            if reps and reps[0] <= reps[-1]:
                stalls.append({
                    "exercise": ex["exercise_name"],
                    "weight": latest,
                    "sessions": 3,
                    "reps": reps,
                })

        # Drop: >=5% from peak
        if len(weights) >= 2:
            peak = max(weights[1:])
            if peak > 0 and (peak - latest) / peak >= 0.05:
                drops.append({
                    "exercise": ex["exercise_name"],
                    "current": latest,
                    "peak": peak,
                    "drop_pct": round((peak - latest) / peak * 100, 1),
                })

    if not stalls and not drops:
        return None

    # Severity based on recovery trend
    severity = "info"
    if stalls:
        severity = "notable"
    # Check recovery trend for escalation
    recovery = conn.execute("""
        SELECT value_mean FROM wearable_observation
        WHERE user_id = ? AND metric IN ('recovery_score', 'recovery')
        ORDER BY observation_date DESC LIMIT 7
    """, (user_id,)).fetchall()
    if len(recovery) >= 3:
        recent_avg = sum(r["value_mean"] for r in recovery[:3]) / 3
        older_avg = sum(r["value_mean"] for r in recovery[3:min(7, len(recovery))]) / max(1, len(recovery[3:7]))
        if older_avg > 0 and recent_avg < older_avg * 0.85:
            severity = "concerning"

    signals = []
    for s in stalls:
        signals.append({
            "label": s["exercise"], "value": f"{int(s['weight']) if s['weight'] == int(s['weight']) else s['weight']}kg",
            "direction": "flat", "delta": f"flat {s['sessions']} sessions at {s['reps'][-1] if s['reps'] else '?'} reps",
        })
    for d in drops:
        signals.append({
            "label": d["exercise"], "value": f"{int(d['current']) if d['current'] == int(d['current']) else d['current']}kg",
            "direction": "down", "delta": f"-{d['drop_pct']}% from {d['peak']}kg",
        })

    headline_parts = []
    if stalls:
        w = stalls[0]['weight']
        w_str = f"{int(w)}kg" if w == int(w) else f"{w}kg"
        headline_parts.append(f"{stalls[0]['exercise']} stalled at {w_str}")
    if drops:
        headline_parts.append(f"{drops[0]['exercise']} dropped {drops[0]['drop_pct']}%")

    finding_id = str(uuid.uuid4())[:8]

    # Store finding
    detail = json.dumps({
        "headline": " — ".join(headline_parts),
        "theme": "training",
        "signals": signals,
        "stalls": stalls,
        "drops": drops,
    })

    conn.execute("""
        UPDATE finding SET status = 'resolved'
        WHERE user_id = ? AND detector_id = 'training_stall' AND status = 'active'
    """, (user_id,))

    conn.execute("""
        INSERT INTO finding (user_id, detector_id, severity, summary, detail, status, time_window_start, time_window_end)
        VALUES (?, 'training_stall', ?, ?, ?, 'active', ?, ?)
    """, (user_id, severity,
          f"{len(stalls)} stall(s) and {len(drops)} drop(s) detected across compound lifts.",
          detail, cutoff, as_of))
    conn.commit()

    return {"severity": severity, "headline": " — ".join(headline_parts), "stalls": len(stalls), "drops": len(drops)}


# ═══════════════════════════════════════════════════════════════
# Routine push (Clinic Platform → Hevy)
# ═══════════════════════════════════════════════════════════════

def push_routine_to_hevy(
    conn: sqlite3.Connection,
    clinician_id: str,
    patient_id: str,
    title: str,
    exercises: list[dict],
    api_key: str | None = None,
) -> dict:
    """Push a routine to the patient's Hevy account.

    exercises format:
    [
        {
            "exercise_template_id": "D04AC939",
            "title": "Bench Press (Barbell)",
            "sets": [{"type": "normal", "weight_kg": 100, "reps": 10}],
            "rest_seconds": 90,
            "notes": "Pause at bottom"
        }
    ]
    """
    routine_json = json.dumps({"routine": {"title": title, "exercises": exercises}})

    # If we have a real API key, push to Hevy
    hevy_routine_id = None
    if api_key:
        result = _hevy_post("/routines", api_key, {"routine": {"title": title, "exercises": exercises}})
        hevy_routine_id = result.get("routine", {}).get("id")

    # Record the push
    conn.execute("""
        INSERT INTO routine_push (clinician_id, patient_id, hevy_routine_id, title, routine_json)
        VALUES (?, ?, ?, ?, ?)
    """, (clinician_id, patient_id, hevy_routine_id, title, routine_json))
    conn.commit()

    # Notify patient
    create_notification(conn, patient_id, clinician_id, "clinician",
                        "routine_created", f"Your clinician created {title}",
                        f"New routine '{title}' is ready in your Hevy app.",
                        json.dumps({"title": title, "exercise_count": len(exercises)}))

    return {"title": title, "hevy_routine_id": hevy_routine_id, "exercise_count": len(exercises)}


def update_routine_in_hevy(
    conn: sqlite3.Connection,
    clinician_id: str,
    patient_id: str,
    routine_push_id: int,
    title: str,
    exercises: list[dict],
    api_key: str | None = None,
) -> dict:
    """Update an existing routine in the patient's Hevy."""
    # Get old routine for diff
    old = conn.execute("SELECT title, routine_json FROM routine_push WHERE id = ?", (routine_push_id,)).fetchone()
    old_exercises = json.loads(old["routine_json"]).get("routine", {}).get("exercises", []) if old else []

    new_json = json.dumps({"routine": {"title": title, "exercises": exercises}})

    # Compute diff
    diff_lines = _compute_routine_diff(old_exercises, exercises)

    # Push to Hevy if we have the key + hevy_routine_id
    hevy_routine_id = None
    if api_key:
        old_hevy_id = conn.execute("SELECT hevy_routine_id FROM routine_push WHERE id = ?", (routine_push_id,)).fetchone()
        if old_hevy_id and old_hevy_id["hevy_routine_id"]:
            _hevy_put(f"/routines/{old_hevy_id['hevy_routine_id']}", api_key,
                       {"routine": {"title": title, "exercises": exercises}})
            hevy_routine_id = old_hevy_id["hevy_routine_id"]

    # Mark old as superseded, insert new
    conn.execute("UPDATE routine_push SET status = 'superseded' WHERE id = ?", (routine_push_id,))
    conn.execute("""
        INSERT INTO routine_push (clinician_id, patient_id, hevy_routine_id, title, routine_json)
        VALUES (?, ?, ?, ?, ?)
    """, (clinician_id, patient_id, hevy_routine_id, title, new_json))
    conn.commit()

    # Notify patient with diff
    diff_text = "\n".join(diff_lines) if diff_lines else "Minor adjustments"
    create_notification(conn, patient_id, clinician_id, "clinician",
                        "routine_updated", f"Your clinician updated {title}",
                        diff_text, json.dumps({"title": title, "diff": diff_lines}))

    return {"title": title, "diff": diff_lines}


def _compute_routine_diff(old_exercises: list, new_exercises: list) -> list[str]:
    """Human-readable diff between old and new routine exercises."""
    old_by_id = {e.get("exercise_template_id", ""): e for e in old_exercises}
    new_by_id = {e.get("exercise_template_id", ""): e for e in new_exercises}
    lines = []

    for eid, new_ex in new_by_id.items():
        name = new_ex.get("title", eid)
        if eid not in old_by_id:
            sets_desc = f"{len(new_ex.get('sets', []))} sets"
            lines.append(f"+ {name}: {sets_desc} (new)")
        else:
            old_ex = old_by_id[eid]
            old_sets = old_ex.get("sets", [])
            new_sets = new_ex.get("sets", [])
            changes = []
            if len(old_sets) != len(new_sets):
                changes.append(f"sets {len(old_sets)} → {len(new_sets)}")
            if old_sets and new_sets:
                ow = old_sets[0].get("weight_kg", 0)
                nw = new_sets[0].get("weight_kg", 0)
                if ow != nw:
                    changes.append(f"weight {ow}kg → {nw}kg")
                oreps = old_sets[0].get("reps", 0)
                nreps = new_sets[0].get("reps", 0)
                if oreps != nreps:
                    changes.append(f"reps {oreps} → {nreps}")
            if changes:
                lines.append(f"~ {name}: {', '.join(changes)}")

    for eid in old_by_id:
        if eid not in new_by_id:
            name = old_by_id[eid].get("title", eid)
            lines.append(f"- {name} (removed)")

    return lines


# ═══════════════════════════════════════════════════════════════
# Notifications
# ═══════════════════════════════════════════════════════════════

def create_notification(
    conn: sqlite3.Connection,
    user_id: str,
    actor_id: str | None,
    actor_role: str | None,
    notif_type: str,
    title: str,
    body: str | None = None,
    detail_json: str | None = None,
):
    """Create a notification for a user."""
    conn.execute("""
        INSERT INTO notification (user_id, actor_id, actor_role, type, title, body, detail_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, actor_id, actor_role, notif_type, title, body, detail_json))
    conn.commit()


def get_notifications(conn: sqlite3.Connection, user_id: str, unread_only: bool = False, limit: int = 20) -> list[dict]:
    """Get notifications for a user."""
    where = "WHERE user_id = ?"
    if unread_only:
        where += " AND read = 0"
    rows = conn.execute(f"""
        SELECT id, type, title, body, detail_json, read, created_at
        FROM notification {where}
        ORDER BY created_at DESC LIMIT ?
    """, (user_id, limit)).fetchall()
    return [dict(r) for r in rows]


def mark_notifications_read(conn: sqlite3.Connection, user_id: str, notification_ids: list[int] | None = None):
    """Mark notifications as read."""
    if notification_ids:
        placeholders = ",".join("?" for _ in notification_ids)
        conn.execute(f"UPDATE notification SET read = 1 WHERE user_id = ? AND id IN ({placeholders})",
                     [user_id] + notification_ids)
    else:
        conn.execute("UPDATE notification SET read = 1 WHERE user_id = ?", (user_id,))
    conn.commit()


# ═══════════════════════════════════════════════════════════════
# Structured lift data (for frontend charts, not LLM text)
# ═══════════════════════════════════════════════════════════════

def get_structured_lifts(conn: sqlite3.Connection, user_id: str, days: int = 28) -> dict:
    """Structured lift progression data for frontend rendering.

    Returns: {
        lifts: [{exercise_name, exercise_template_id, sessions: [{date, working_weight_kg, ...}], status, trend_pct}],
        flagged: [exercise_template_ids that are stalling/dropping]
    }
    """
    cutoff = (date.today() - timedelta(days=days)).isoformat()

    exercises = conn.execute("""
        SELECT exercise_template_id, exercise_name, COUNT(*) as session_count
        FROM lift_progression
        WHERE user_id = ? AND session_date >= ?
        GROUP BY exercise_template_id
        ORDER BY MAX(total_volume_kg) DESC
    """, (user_id, cutoff)).fetchall()

    lifts = []
    flagged = []

    for ex in exercises:
        sessions_raw = conn.execute("""
            SELECT session_date, working_weight_kg, best_set_reps, estimated_1rm, total_volume_kg, set_count
            FROM lift_progression
            WHERE user_id = ? AND exercise_template_id = ? AND session_date >= ?
            ORDER BY session_date ASC
        """, (user_id, ex["exercise_template_id"], cutoff)).fetchall()

        sessions = [{
            "date": s["session_date"],
            "working_weight_kg": round(s["working_weight_kg"] * 2) / 2 if s["working_weight_kg"] else 0,
            "best_set_reps": s["best_set_reps"] or 0,
            "estimated_1rm": round(s["estimated_1rm"], 1) if s["estimated_1rm"] else 0,
            "total_volume_kg": round(s["total_volume_kg"]) if s["total_volume_kg"] else 0,
            "set_count": s["set_count"] or 0,
        } for s in sessions_raw]

        # Determine status
        status = "progressing"
        trend_pct = 0
        weights = [s["working_weight_kg"] for s in sessions if s["working_weight_kg"] > 0]

        if len(weights) >= 2:
            first = weights[0]
            last = weights[-1]
            trend_pct = round((last - first) / first * 100, 1) if first > 0 else 0

            if len(weights) >= 3:
                recent = weights[-3:]
                max_w = max(recent)
                min_w = min(recent)
                if max_w > 0 and (max_w - min_w) / max_w < 0.02:
                    status = "stall"
                    flagged.append(ex["exercise_template_id"])

            if len(weights) >= 2 and weights[-1] < weights[-2] * 0.95:
                status = "drop"
                if ex["exercise_template_id"] not in flagged:
                    flagged.append(ex["exercise_template_id"])

        lifts.append({
            "exercise_name": ex["exercise_name"],
            "exercise_template_id": ex["exercise_template_id"],
            "sessions": sessions,
            "status": status,
            "trend_pct": trend_pct,
        })

    return {"lifts": lifts, "flagged": flagged}


# ═══════════════════════════════════════════════════════════════
# LLM tool handlers
# ═══════════════════════════════════════════════════════════════

def get_workout_history(conn: sqlite3.Connection, user_id: str, days: int = 14) -> str:
    """Get recent workouts formatted for LLM consumption."""
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    sessions = conn.execute("""
        SELECT id, title, started_at, duration_seconds FROM workout_session
        WHERE user_id = ? AND started_at >= ? ORDER BY started_at DESC
    """, (user_id, cutoff)).fetchall()

    if not sessions:
        return f"No workouts logged in the last {days} days."

    lines = [f"RECENT WORKOUTS (last {days} days): {len(sessions)} sessions\n"]
    for s in sessions[:10]:
        dur = f"{s['duration_seconds'] // 60}min" if s['duration_seconds'] else "?"
        lines.append(f"● {s['title']} — {s['started_at'][:10]} ({dur})")
        sets = conn.execute("""
            SELECT exercise_name, set_type, weight_kg, reps, rpe
            FROM workout_set WHERE session_id = ? AND set_type IN ('normal', 'failure')
            ORDER BY set_index
        """, (s['id'],)).fetchall()
        # Group by exercise
        by_ex: dict[str, list] = {}
        for st in sets:
            by_ex.setdefault(st['exercise_name'], []).append(st)
        for ex_name, ex_sets in by_ex.items():
            set_strs = [f"{st['weight_kg']}kg×{st['reps']}" for st in ex_sets]
            lines.append(f"  {ex_name}: {', '.join(set_strs)}")
        lines.append("")

    return "\n".join(lines)


def get_lift_progression(conn: sqlite3.Connection, user_id: str, exercise_name: str, days: int = 28) -> str:
    """Get per-exercise weight progression formatted for LLM."""
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    rows = conn.execute("""
        SELECT exercise_name, session_date, working_weight_kg, best_set_reps, estimated_1rm, total_volume_kg, set_count
        FROM lift_progression
        WHERE user_id = ? AND exercise_name LIKE ? AND session_date >= ?
        ORDER BY session_date
    """, (user_id, f"%{exercise_name}%", cutoff)).fetchall()

    if not rows:
        return f"No data for '{exercise_name}' in the last {days} days."

    lines = [f"LIFT PROGRESSION: {rows[0]['exercise_name'] if rows else exercise_name} (last {days}d)\n"]
    for r in rows:
        lines.append(f"  {r['session_date']}: {r['working_weight_kg']}kg × {r['best_set_reps']} "
                      f"(est 1RM: {r['estimated_1rm']}kg, volume: {r['total_volume_kg']}kg, {r['set_count']} sets)")

    # Trend
    if len(rows) >= 2:
        first_w = rows[0]["working_weight_kg"]
        last_w = rows[-1]["working_weight_kg"]
        if first_w and last_w and first_w > 0:
            pct = round((last_w - first_w) / first_w * 100, 1)
            direction = "↑" if pct > 2 else "↓" if pct < -2 else "→"
            lines.append(f"\nTrend: {first_w}kg → {last_w}kg ({direction} {pct:+.1f}%)")
            if abs(pct) < 2 and len(rows) >= 3:
                lines.append("⚠ STALL DETECTED — weight flat across sessions")

    return "\n".join(lines)


def get_training_summary(conn: sqlite3.Connection, user_id: str, days: int = 14) -> str:
    """Weekly training summary for LLM."""
    cutoff = (date.today() - timedelta(days=days)).isoformat()

    session_count = conn.execute(
        "SELECT COUNT(*) as c FROM workout_session WHERE user_id = ? AND started_at >= ?",
        (user_id, cutoff)
    ).fetchone()["c"]

    total_volume = conn.execute(
        "SELECT SUM(total_volume_kg) as v FROM lift_progression WHERE user_id = ? AND session_date >= ?",
        (user_id, cutoff)
    ).fetchone()["v"] or 0

    # Key lifts with stall status
    lifts = conn.execute("""
        SELECT exercise_name,
               GROUP_CONCAT(working_weight_kg) as weights,
               GROUP_CONCAT(best_set_reps) as reps_list,
               COUNT(*) as sessions
        FROM lift_progression
        WHERE user_id = ? AND session_date >= ?
        GROUP BY exercise_template_id
        HAVING sessions >= 2
        ORDER BY MAX(total_volume_kg) DESC
        LIMIT 6
    """, (user_id, cutoff)).fetchall()

    lines = [f"TRAINING SUMMARY (last {days}d)\n",
             f"Sessions: {session_count}",
             f"Total volume: {round(total_volume)}kg",
             f"\nKey lifts:"]

    for lift in lifts:
        weights = [float(w) for w in lift["weights"].split(",") if w]
        if len(weights) >= 2:
            trend = "→ STALL" if max(weights) - min(weights) < max(weights) * 0.02 else (
                "↑" if weights[-1] > weights[0] else "↓")
        else:
            trend = ""
        lines.append(f"  {lift['exercise_name']}: {' → '.join(f'{w}kg' for w in weights)} {trend}")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# Mock data for demo (replaces real Hevy sync)
# ═══════════════════════════════════════════════════════════════

def seed_mock_workouts(conn: sqlite3.Connection, user_id: str):
    """Seed realistic workout data for demo purposes."""
    # Marcus (patient-001): Push/Pull/Legs, bench stalling
    workouts = [
        {
            "id": f"hevy-{user_id}-w1",
            "title": "Push Day A",
            "start_time": (datetime.now() - timedelta(days=1)).isoformat(),
            "end_time": (datetime.now() - timedelta(days=1) + timedelta(hours=1, minutes=5)).isoformat(),
            "exercises": [
                {"exercise_template_id": "bench_bb", "title": "Bench Press (Barbell)", "sets": [
                    {"type": "warmup", "weight_kg": 60, "reps": 10},
                    {"type": "normal", "weight_kg": 100, "reps": 10, "rpe": 7},
                    {"type": "normal", "weight_kg": 100, "reps": 10, "rpe": 8},
                    {"type": "normal", "weight_kg": 100, "reps": 9, "rpe": 8.5},
                    {"type": "failure", "weight_kg": 100, "reps": 8, "rpe": 10},
                ]},
                {"exercise_template_id": "incline_db", "title": "Incline Dumbbell Press", "sets": [
                    {"type": "normal", "weight_kg": 35, "reps": 12},
                    {"type": "normal", "weight_kg": 35, "reps": 11},
                    {"type": "normal", "weight_kg": 35, "reps": 10},
                ]},
                {"exercise_template_id": "lat_raise", "title": "Lateral Raise", "sets": [
                    {"type": "normal", "weight_kg": 12.5, "reps": 15},
                    {"type": "normal", "weight_kg": 12.5, "reps": 14},
                    {"type": "normal", "weight_kg": 12.5, "reps": 13},
                    {"type": "normal", "weight_kg": 12.5, "reps": 12},
                ]},
                {"exercise_template_id": "tricep_pd", "title": "Tricep Pushdown", "sets": [
                    {"type": "normal", "weight_kg": 27.5, "reps": 12},
                    {"type": "normal", "weight_kg": 27.5, "reps": 12},
                    {"type": "normal", "weight_kg": 27.5, "reps": 11},
                ]},
            ],
        },
        {
            "id": f"hevy-{user_id}-w2",
            "title": "Push Day A",
            "start_time": (datetime.now() - timedelta(days=8)).isoformat(),
            "end_time": (datetime.now() - timedelta(days=8) + timedelta(hours=1)).isoformat(),
            "exercises": [
                {"exercise_template_id": "bench_bb", "title": "Bench Press (Barbell)", "sets": [
                    {"type": "warmup", "weight_kg": 60, "reps": 10},
                    {"type": "normal", "weight_kg": 100, "reps": 10, "rpe": 7},
                    {"type": "normal", "weight_kg": 100, "reps": 10, "rpe": 7.5},
                    {"type": "normal", "weight_kg": 100, "reps": 10, "rpe": 8},
                    {"type": "failure", "weight_kg": 100, "reps": 9, "rpe": 9.5},
                ]},
                {"exercise_template_id": "incline_db", "title": "Incline Dumbbell Press", "sets": [
                    {"type": "normal", "weight_kg": 32.5, "reps": 12},
                    {"type": "normal", "weight_kg": 32.5, "reps": 12},
                    {"type": "normal", "weight_kg": 32.5, "reps": 11},
                ]},
            ],
        },
        {
            "id": f"hevy-{user_id}-w3",
            "title": "Push Day A",
            "start_time": (datetime.now() - timedelta(days=15)).isoformat(),
            "end_time": (datetime.now() - timedelta(days=15) + timedelta(hours=1, minutes=10)).isoformat(),
            "exercises": [
                {"exercise_template_id": "bench_bb", "title": "Bench Press (Barbell)", "sets": [
                    {"type": "warmup", "weight_kg": 60, "reps": 10},
                    {"type": "normal", "weight_kg": 100, "reps": 10, "rpe": 7},
                    {"type": "normal", "weight_kg": 100, "reps": 10, "rpe": 7},
                    {"type": "normal", "weight_kg": 100, "reps": 10, "rpe": 7.5},
                    {"type": "normal", "weight_kg": 100, "reps": 10, "rpe": 8},
                ]},
            ],
        },
        {
            "id": f"hevy-{user_id}-w4",
            "title": "Pull Day A",
            "start_time": (datetime.now() - timedelta(days=3)).isoformat(),
            "end_time": (datetime.now() - timedelta(days=3) + timedelta(hours=1, minutes=15)).isoformat(),
            "exercises": [
                {"exercise_template_id": "row_bb", "title": "Barbell Row", "sets": [
                    {"type": "normal", "weight_kg": 120, "reps": 8, "rpe": 7},
                    {"type": "normal", "weight_kg": 120, "reps": 8, "rpe": 7.5},
                    {"type": "normal", "weight_kg": 120, "reps": 7, "rpe": 8},
                    {"type": "failure", "weight_kg": 120, "reps": 6, "rpe": 10},
                ]},
                {"exercise_template_id": "lat_pd", "title": "Lat Pulldown", "sets": [
                    {"type": "normal", "weight_kg": 75, "reps": 12},
                    {"type": "normal", "weight_kg": 75, "reps": 11},
                    {"type": "normal", "weight_kg": 75, "reps": 10},
                ]},
                {"exercise_template_id": "face_pull", "title": "Face Pull", "sets": [
                    {"type": "normal", "weight_kg": 20, "reps": 15},
                    {"type": "normal", "weight_kg": 20, "reps": 15},
                    {"type": "normal", "weight_kg": 20, "reps": 14},
                ]},
                {"exercise_template_id": "bicep_curl", "title": "Barbell Curl", "sets": [
                    {"type": "normal", "weight_kg": 35, "reps": 12},
                    {"type": "normal", "weight_kg": 35, "reps": 10},
                    {"type": "normal", "weight_kg": 35, "reps": 9},
                ]},
            ],
        },
        {
            "id": f"hevy-{user_id}-w5",
            "title": "Leg Day A",
            "start_time": (datetime.now() - timedelta(days=5)).isoformat(),
            "end_time": (datetime.now() - timedelta(days=5) + timedelta(hours=1, minutes=20)).isoformat(),
            "exercises": [
                {"exercise_template_id": "squat_bb", "title": "Squat (Barbell)", "sets": [
                    {"type": "warmup", "weight_kg": 80, "reps": 8},
                    {"type": "normal", "weight_kg": 170, "reps": 5, "rpe": 8},
                    {"type": "normal", "weight_kg": 170, "reps": 5, "rpe": 8.5},
                    {"type": "normal", "weight_kg": 170, "reps": 4, "rpe": 9},
                ]},
                {"exercise_template_id": "rdl", "title": "Romanian Deadlift", "sets": [
                    {"type": "normal", "weight_kg": 140, "reps": 10},
                    {"type": "normal", "weight_kg": 140, "reps": 10},
                    {"type": "normal", "weight_kg": 140, "reps": 9},
                ]},
                {"exercise_template_id": "leg_press", "title": "Leg Press", "sets": [
                    {"type": "normal", "weight_kg": 250, "reps": 12},
                    {"type": "normal", "weight_kg": 250, "reps": 11},
                    {"type": "normal", "weight_kg": 250, "reps": 10},
                ]},
            ],
        },
    ]

    for w in workouts:
        store_workout(conn, user_id, w)
