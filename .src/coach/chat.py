"""Chat engine for Coach Platform — role-scoped LLM interaction.

Wraps the copied CDE LLM engine with:
- Two tool sets: athlete (all 20 CDE tools) and coach (read + coaching-surface)
- Substance boundary enforcement via tool set absence
- Multi-tenant briefings scoped by athlete_id (passed as user_id to CDE functions)
"""
import sqlite3
import anthropic

from coach.config import ANTHROPIC_API_KEY, CDE_MODEL
from coach.llm.tools import TOOL_DEFINITIONS, execute_tool
from coach.llm.context import build_minimal_briefing, build_finding_briefing
from coach.operations import (
    SetTrainingBlock, EndTrainingBlock, SetNutritionTarget,
    AddRecoveryNote, commit_operation,
)

# Coach now has substance-write access — athlete gets notified
# All CDE tools available to coach
COACH_CDE_TOOLS = list(TOOL_DEFINITIONS)

COACHING_SURFACE_TOOLS = [
    {
        "name": "set_training_block",
        "description": "Set a new training block for this client.",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Block name"},
                "block_type": {"type": "string", "enum": ["hypertrophy", "strength", "deload", "prep", "offseason"]},
                "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "YYYY-MM-DD (optional)"},
                "notes": {"type": "string"},
            },
            "required": ["name", "block_type", "start_date"],
        },
    },
    {
        "name": "set_nutrition_target",
        "description": "Set calorie and macro targets for this client.",
        "input_schema": {
            "type": "object",
            "properties": {
                "calories": {"type": "integer"},
                "protein_g": {"type": "integer"},
                "carbs_g": {"type": "integer"},
                "fat_g": {"type": "integer"},
                "effective_date": {"type": "string", "description": "YYYY-MM-DD"},
                "notes": {"type": "string"},
            },
            "required": ["calories", "protein_g", "carbs_g", "fat_g", "effective_date"],
        },
    },
    {
        "name": "add_recovery_note",
        "description": "Add a recovery note for this client.",
        "input_schema": {
            "type": "object",
            "properties": {
                "note_type": {"type": "string", "enum": ["sleep", "deload", "rest_day", "active_recovery", "note"]},
                "content": {"type": "string"},
            },
            "required": ["note_type", "content"],
        },
    },
]

HEVY_TOOLS = [
    {
        "name": "get_workout_history",
        "description": "Get recent workout sessions with exercises, sets, reps, and weights. Shows what was actually logged in the gym.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Days to look back (default 14)", "default": 14},
            },
        },
    },
    {
        "name": "get_lift_progression",
        "description": "Get per-exercise weight progression — working weight trend, est 1RM, stall detection. Use to answer 'how is bench/squat/etc going?'",
        "input_schema": {
            "type": "object",
            "properties": {
                "exercise_name": {"type": "string", "description": "Exercise name or partial match (e.g. 'bench', 'squat')"},
                "days": {"type": "integer", "description": "Days to look back (default 28)", "default": 28},
            },
            "required": ["exercise_name"],
        },
    },
    {
        "name": "get_training_summary",
        "description": "Training summary: session count, total volume, key lift trends with stall/progress indicators.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Days to look back (default 14)", "default": 14},
            },
        },
    },
]

CHECKIN_TOOLS = [
    {
        "name": "schedule_checkin",
        "description": "Schedule a check-in meeting with the athlete. Syncs to Google Calendar if configured.",
        "input_schema": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "YYYY-MM-DD"},
                "time": {"type": "string", "description": "HH:MM (24h format)", "default": "12:00"},
                "description": {"type": "string", "description": "Check-in agenda or notes"},
            },
            "required": ["date"],
        },
    },
    {
        "name": "get_checkin_notes",
        "description": "Get recent check-in notes. Use when coach asks 'what did we discuss last time?' or 'last check-in notes'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "Number of recent check-ins", "default": 5},
            },
        },
    },
    {
        "name": "add_checkin_notes",
        "description": "Add notes after a completed check-in. These become data the LLM can reference later.",
        "input_schema": {
            "type": "object",
            "properties": {
                "event_id": {"type": "integer", "description": "The check-in event ID"},
                "notes_text": {"type": "string", "description": "Check-in notes content"},
            },
            "required": ["event_id", "notes_text"],
        },
    },
    {
        "name": "get_bloodwork_document",
        "description": "Look up bloodwork for a specific date. Returns extracted lab values and a link to the source PDF if available.",
        "input_schema": {
            "type": "object",
            "properties": {
                "draw_date": {"type": "string", "description": "Date to look up (YYYY-MM-DD)"},
            },
            "required": ["draw_date"],
        },
    },
]

HEVY_WRITE_TOOLS = [
    {
        "name": "push_routine_to_hevy",
        "description": "Push a training routine to the athlete's Hevy app. The routine will appear in their app ready to use. Specify exercises with sets, reps, and weight targets.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Routine name (e.g. 'Push Day B — Bench Focus')"},
                "exercises": {
                    "type": "array",
                    "description": "List of exercises with sets",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Exercise name"},
                            "exercise_template_id": {"type": "string", "description": "Use exercise name as ID if unknown"},
                            "rest_seconds": {"type": "integer"},
                            "notes": {"type": "string"},
                            "sets": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "type": {"type": "string", "enum": ["warmup", "normal", "failure", "dropset"]},
                                        "weight_kg": {"type": "number"},
                                        "reps": {"type": "integer"},
                                    },
                                },
                            },
                        },
                        "required": ["title", "sets"],
                    },
                },
            },
            "required": ["title", "exercises"],
        },
    },
]

COACH_TOOLS = COACH_CDE_TOOLS + COACHING_SURFACE_TOOLS + HEVY_TOOLS + HEVY_WRITE_TOOLS + CHECKIN_TOOLS
ATHLETE_TOOLS = TOOL_DEFINITIONS + HEVY_TOOLS  # All CDE tools + workout tools

BASE_RULES = """You are the Coach Platform assistant — a health data intelligence system for enhanced athletes and their physique coaches.

RULES:
- Informational only. Never diagnose, prescribe, or recommend dose changes.
- Every numeric claim must come from a tool response or briefing. Never fabricate data.
- If user asks "what should I do?" — redirect to their clinician.
- When attributing changes to compounds, explain the mechanism. Always mention other factors (training, diet, sleep, stress).
- Be direct and concise. Acknowledge uncertainty when data is insufficient.
- PK-estimated drug levels are modeled from the logged protocol, not measured. Always say "estimated" or "modeled."
"""

COACH_ADDENDUM = """
ROLE: You are assisting a physique coach managing a client's data.
- You can READ all health data: labs, wearables, compounds, findings, calendar.
- You can MANAGE training, nutrition, recovery, AND the client's substance protocol through tools.
- When modifying substances: always call check_compound_active first, confirm details with the coach, then log the event. The athlete will be notified and must confirm.
- For phase transitions: enumerate all active compounds, confirm each change with the coach, then record the phase.
- When presenting drug levels, note they are estimated from the logged protocol, not measured.
"""

ATHLETE_ADDENDUM = """
ROLE: You are assisting an enhanced athlete with their own health data.
- You can read all your health data and manage your own compound stack.
- For compound updates: always call check_compound_active first. Confirm details before logging.
- For phase transitions: enumerate all active compounds, confirm each change, then record the phase.
"""


def _execute_tool_for_role(
    conn: sqlite3.Connection,
    tool_name: str,
    tool_input: dict,
    user_id: str,
    role: str,
    coach_id: str | None = None,
) -> str:
    """Execute a tool with role enforcement."""
    # Coach-only coaching surface tools
    if tool_name == "set_training_block":
        op = SetTrainingBlock(athlete_id=user_id, **tool_input)
        result = commit_operation(conn, coach_id or "unknown", "coach", op)
        from coach.hevy import create_notification
        create_notification(conn, user_id, coach_id, "coach", "training_updated", f"Your coach set a new training block: {tool_input.get('name', '')}", result["rendered"], None)
        return f"Committed: {result['rendered']}"
    if tool_name == "set_nutrition_target":
        op = SetNutritionTarget(athlete_id=user_id, **tool_input)
        result = commit_operation(conn, coach_id or "unknown", "coach", op)
        from coach.hevy import create_notification
        create_notification(conn, user_id, coach_id, "coach", "nutrition_updated", f"Your coach updated your nutrition targets", result["rendered"], None)
        return f"Committed: {result['rendered']}"
    if tool_name == "add_recovery_note":
        op = AddRecoveryNote(athlete_id=user_id, **tool_input)
        result = commit_operation(conn, coach_id or "unknown", "coach", op)
        from coach.hevy import create_notification
        create_notification(conn, user_id, coach_id, "coach", "recovery_note", f"Your coach added a recovery note", result["rendered"], None)
        return f"Committed: {result['rendered']}"

    # Coach substance modifications — notify athlete
    if role == "coach" and tool_name == "add_compound_event":
        result = execute_tool(conn, tool_name, tool_input, user_id=user_id)
        # Create notification for athlete
        from coach.hevy import create_notification
        import json as _json
        compound = tool_input.get("compound_name", "compound")
        event_type = tool_input.get("event_type", "modification")
        dose = tool_input.get("dose_mg", "")
        rendered = f"Coach {event_type.lower()} {compound}{f' {dose}mg' if dose else ''}"
        create_notification(conn, user_id, coach_id, "coach",
                            "substance_modified", f"Your coach modified your protocol: {rendered}",
                            f"{rendered}. Please review and confirm.", _json.dumps(tool_input))
        return result

    if role == "coach" and tool_name == "record_phase_change":
        result = execute_tool(conn, tool_name, tool_input, user_id=user_id)
        from coach.hevy import create_notification
        new_phase = tool_input.get("new_phase", "unknown")
        create_notification(conn, user_id, coach_id, "coach",
                            "phase_changed", f"Your coach changed your phase to {new_phase}",
                            f"Phase changed to {new_phase}. Please review.", None)
        return result

    # Coach coaching-surface writes — also notify athlete
    if role == "coach" and tool_name in ("set_training_block", "set_nutrition_target", "add_recovery_note"):
        pass  # handled above with commit_operation, notification handled at API level

    # Check-in tools
    if tool_name == "schedule_checkin":
        from coach.database import get_db as _get_db
        _conn = conn
        _conn.execute("""
            INSERT INTO scheduled_event (user_id, event_type, scheduled_date, scheduled_time, description, coach_id, status, created_by)
            VALUES (?, 'check_in', ?, ?, ?, ?, 'upcoming', ?)
        """, (user_id, tool_input.get("date"), tool_input.get("time", "12:00"), tool_input.get("description"), coach_id, coach_id))
        _conn.commit()
        from coach.hevy import create_notification
        create_notification(_conn, user_id, coach_id, "coach", "checkin_scheduled",
                            f"Check-in scheduled for {tool_input.get('date')} at {tool_input.get('time', '12:00')}", tool_input.get("description"), None)
        return f"Check-in scheduled for {tool_input.get('date')} at {tool_input.get('time', '12:00')}. Athlete notified."

    if tool_name == "get_checkin_notes":
        limit = tool_input.get("limit", 5)
        rows = conn.execute("""
            SELECT se.scheduled_date, se.description, cin.notes_text, cin.created_at
            FROM check_in_note cin
            JOIN scheduled_event se ON cin.scheduled_event_id = se.id
            WHERE cin.athlete_id = ?
            ORDER BY cin.created_at DESC LIMIT ?
        """, (user_id, limit)).fetchall()
        if not rows:
            return "No check-in notes found."
        lines = ["RECENT CHECK-IN NOTES:\n"]
        for r in rows:
            lines.append(f"Date: {r['scheduled_date']}")
            if r["description"]:
                lines.append(f"Agenda: {r['description']}")
            lines.append(f"Notes: {r['notes_text']}")
            lines.append("")
        return "\n".join(lines)

    if tool_name == "add_checkin_notes":
        conn.execute("INSERT INTO check_in_note (scheduled_event_id, coach_id, athlete_id, notes_text) VALUES (?, ?, ?, ?)",
                     (tool_input["event_id"], coach_id or "unknown", user_id, tool_input["notes_text"]))
        conn.execute("UPDATE scheduled_event SET status = 'completed' WHERE id = ?", (tool_input["event_id"],))
        conn.commit()
        return f"Check-in notes saved for event {tool_input['event_id']}."

    if tool_name == "get_bloodwork_document":
        draw_date = tool_input.get("draw_date", "")
        # Get panel snapshot for that date
        panel = execute_tool(conn, "get_panel_snapshot", {"draw_date": draw_date}, user_id=user_id)
        # Check if source PDF exists
        doc = conn.execute("""
            SELECT id, raw_storage_path, metadata_json FROM source_document
            WHERE user_id = ? AND source_type = 'LAB_PDF' AND metadata_json LIKE ?
        """, (user_id, f'%{draw_date}%')).fetchone()
        if doc and doc["raw_storage_path"]:
            return f"{panel}\n\n[PDF:doc_id={doc['id']}] Source PDF available — view in Documents tab."
        return panel

    # Hevy routine push (coach only)
    if tool_name == "push_routine_to_hevy":
        from coach.hevy import push_routine_to_hevy
        result = push_routine_to_hevy(conn, coach_id or "unknown", user_id, tool_input["title"], tool_input["exercises"])
        return f"Routine '{result['title']}' pushed to athlete's Hevy ({result['exercise_count']} exercises). Athlete has been notified."

    # Hevy workout tools
    if tool_name == "get_workout_history":
        from coach.hevy import get_workout_history
        return get_workout_history(conn, user_id, tool_input.get("days", 14))
    if tool_name == "get_lift_progression":
        from coach.hevy import get_lift_progression
        return get_lift_progression(conn, user_id, tool_input["exercise_name"], tool_input.get("days", 28))
    if tool_name == "get_training_summary":
        from coach.hevy import get_training_summary
        return get_training_summary(conn, user_id, tool_input.get("days", 14))

    # All other tools → CDE's execute_tool with user_id
    return execute_tool(conn, tool_name, tool_input, user_id=user_id)


def _run_tool_loop(
    conn: sqlite3.Connection,
    system_prompt: str,
    messages: list[dict],
    tools: list[dict],
    user_id: str,
    role: str,
    coach_id: str | None = None,
    max_rounds: int = 8,
) -> str:
    """Execute tool-use loop until LLM produces final text."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    for _ in range(max_rounds):
        response = client.messages.create(
            model=CDE_MODEL,
            max_tokens=4096,
            system=system_prompt,
            messages=messages,
            tools=tools,
        )

        # If LLM produced text (no more tool calls), return it
        if response.stop_reason == "end_turn":
            return "".join(b.text for b in response.content if b.type == "text")

        # Process tool calls
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = _execute_tool_for_role(
                    conn, block.name, block.input,
                    user_id=user_id, role=role, coach_id=coach_id,
                )
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

        messages.append({"role": "assistant", "content": [{"type": b.type, **({"text": b.text} if b.type == "text" else {"id": b.id, "name": b.name, "input": b.input})} for b in response.content]})
        messages.append({"role": "user", "content": tool_results})

    return "I wasn't able to complete the analysis. Could you try a more specific question?"


def chat_coach(
    conn: sqlite3.Connection,
    coach_id: str,
    athlete_id: str,
    message: str,
    finding_id: str | None = None,
    history: list[dict] | None = None,
) -> str:
    """Coach chat — reads client data, manages training/nutrition/recovery."""
    # Get athlete name for context
    athlete = conn.execute("SELECT name FROM athlete WHERE id = ?", (athlete_id,)).fetchone()
    athlete_name = athlete["name"] if athlete else athlete_id

    if finding_id:
        briefing = build_finding_briefing(conn, int(finding_id), user_id=athlete_id)
    else:
        briefing = build_minimal_briefing(conn, user_id=athlete_id)

    system = BASE_RULES + COACH_ADDENDUM + f"\nCLIENT: {athlete_name}\n\n" + briefing

    messages = list(history or [])
    messages.append({"role": "user", "content": message})

    return _run_tool_loop(conn, system, messages, COACH_TOOLS,
                          user_id=athlete_id, role="coach", coach_id=coach_id)


def chat_athlete(
    conn: sqlite3.Connection,
    athlete_id: str,
    message: str,
    finding_id: str | None = None,
    history: list[dict] | None = None,
) -> str:
    """Athlete chat — full CDE experience, all 20 tools."""
    if finding_id:
        briefing = build_finding_briefing(conn, int(finding_id), user_id=athlete_id)
    else:
        briefing = build_minimal_briefing(conn, user_id=athlete_id)

    system = BASE_RULES + ATHLETE_ADDENDUM + "\n\n" + briefing

    messages = list(history or [])
    messages.append({"role": "user", "content": message})

    return _run_tool_loop(conn, system, messages, ATHLETE_TOOLS,
                          user_id=athlete_id, role="athlete")
