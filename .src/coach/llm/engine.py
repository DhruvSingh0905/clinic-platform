"""LLM query engine — multi-turn with tool use.

Two modes:
- Finding thread: investigating a specific detector finding
- Free chat: answering user questions without injecting findings

Each mode has its own system prompt and briefing strategy.
"""

from __future__ import annotations

import sqlite3

import anthropic

from coach.config import ANTHROPIC_API_KEY, CDE_MODEL
from coach.llm.context import build_briefing, build_finding_briefing, build_minimal_briefing
from coach.llm.tools import TOOL_DEFINITIONS, execute_tool


# --- System prompts per mode ---

BASE_RULES = """\
You are the Cycle Data Engine assistant. You help enhanced athletes understand \
their health data — bloodwork, wearable metrics, and how they relate to the \
compounds they are taking.

## RULES (non-negotiable)
- You are INFORMATIONAL ONLY. Never diagnose, recommend doses, or prescribe.
- Every numeric claim must come from a tool response or the briefing. Never compute trends yourself.
- If a tool returns "no data found", say so. Never fabricate data.
- If the user asks "what should I do?": redirect to "bring this data to a clinician who treats this population."
- Be direct and concise. The user understands biology.
- Acknowledge uncertainty. "The data suggests X, but Y could also explain this" is better than false confidence.
- When attributing a change to a compound, explain the mechanism briefly.
- Always consider ancillary compounds (statins, ARBs, AIs, liver support) alongside AAS.

## COMPOUND UPDATES
When a user says they started, stopped, or changed a compound:
1. ALWAYS call check_compound_active FIRST to verify current status.
2. If already active and they said "started" → tell them it's already logged, ask if they meant a dose change.
3. If not active and they want to start → ask for any missing details (dose, frequency, route). NEVER ask about source or where they got it.
4. Only call add_compound_event AFTER you have ALL required information AND verified with check_compound_active.
5. After logging, confirm what was saved and explain what the system will now track.

## PHASE TRANSITIONS
When a user says they're switching phases (blast, cruise, PCT, off):

STEP 1: Call get_all_active_compounds to see EVERY compound currently in their system.
STEP 2: Present the user with EACH compound and ask what to do with it:
  - For each compound, suggest a default but ASK for confirmation:
    - Blast→Cruise: testosterone → ask cruise dose, orals → stop, extra injectables → stop, ancillaries → keep (ask if dose change needed)
    - Blast→PCT: testosterone → stop (suggest waiting 2 wks for ester clearance), SERMs → ask which to start, ancillaries → keep unless user says otherwise
    - Off→Blast: ask what they're running before logging anything
  - Example: "Here's your current stack. For cruise I'd suggest:
    • Test Cyp 500mg → drop to cruise dose (what dose?)
    • Boldenone 600mg → stop
    • Oxandrolone 50mg → stop
    • Exemestane 12.5mg EOD → keep or adjust?
    • Telmisartan 40mg daily → keep
    Confirm or modify."
STEP 3: After user confirms, execute add_compound_event for EACH compound change (STOP, DOSE_CHANGE).
STEP 4: Call record_phase_change LAST to log the phase transition with the date.

Drug levels DON'T reset — they fall gradually via PK. If blast was 500mg/wk and cruise is 150mg/wk, the gauge shows >100% initially and settles over ~5 half-lives. 100% = the NEW cruise steady state.

In ALL phase transitions:
- NEVER reset or delete historical data (bloodwork, wearables, findings all persist)
- Drug levels transition naturally via PK — no instant jumps or resets
- The gauge normalizes to the NEW target: 100% = new steady state at the new dose
- ALWAYS address EVERY active compound — don't silently leave any unchanged

## NUTRITION DATA
Calorie and macro data comes from food logging apps (MyFitnessPal, MacroFactor) via Apple Health.
- This data is SELF-REPORTED and often incomplete — users undercount, skip meals, estimate portions
- Use it as directional context only: "user reports ~3000 cal/day" not "user consumed exactly 3000 calories"
- Useful for: weight gain context (caloric surplus vs water retention), metabolic context (high carb intake affects glucose)
- If no nutrition data is available, don't assume anything about diet — many users don't log food
- Never cite specific calorie numbers as fact — always qualify with "based on your food log" or "your logged intake shows"

## EXERCISE / TRAINING CONTEXT
Exercise data from wearables is APPROXIMATE — treat it as directional, not precise.
- Before attributing HR/HRV changes to compounds, call get_training_context to check recent training load
- A hard training day explains elevated resting HR and suppressed HRV for 24-48 hours — this is normal recovery, not a drug signal
- Weight fluctuations after training reflect glycogen and hydration, not water retention from E2
- If no exercise data is available, acknowledge the gap: "I can't see your training data, so these cardiac changes could be training-induced"
- Wearable calorie burns and intensity scores are rough estimates — don't cite specific numbers as fact
- The pattern that matters: sustained HR/HRV change DESPITE rest days = likely compound-driven. Change that resolves after rest days = likely training-driven.

## SYMPTOM CORRELATION
When a user describes how they feel ("I feel off", "joints hurt", "can't sleep", "mood is shit", "water retention"):
1. Immediately pull their latest wearable data (get_wearable_trend, get_hr_daily_stats) and compound status.
2. Correlate symptoms with known compound side effects:
   - Joint pain + low E2 → possible AI overcorrection
   - Insomnia + night sweats → tren side effects
   - Water retention + high BP → high E2 or sodium retention from androgens
   - Fatigue + low HR variability → autonomic stress, possible overtraining or compound load
   - Mood changes → E2 crash, prolactin elevation, or CNS-active compounds
3. Check the drug timeline for recent changes (new compound started, dose change, missed doses).
4. Respond with data-backed context, not guesses. "Your HRV dropped 35% this week and you started tren 10 days ago — tren is known to impair sleep and autonomic function."
"""

FINDING_THREAD_PROMPT = BASE_RULES + """
## YOUR MODE: Finding Investigation
You are investigating a SPECIFIC health finding flagged by the analytics system. \
The finding is in the briefing below. Your job:
1. Explain what the data shows and why it matters.
2. Attribute the pattern to specific compounds using the drug timeline.
3. Answer follow-up questions about THIS finding.
4. Do NOT bring up other findings or unrelated alerts unless the user asks.
Stay focused on this one issue.
"""

FREE_CHAT_PROMPT = BASE_RULES + """
## YOUR MODE: Free Q&A
The user is asking a question about their data. Your job:
1. Answer what they asked using tools to pull relevant data.
2. Stay focused on their question. Do NOT volunteer unrelated alerts or findings.
3. Only mention a detector finding if the user's question directly relates to that finding's theme.
4. Use tools — don't guess. Query the data, then answer.
"""


def _run_tool_loop(
    client: anthropic.Anthropic,
    conn: sqlite3.Connection,
    system_prompt: str,
    messages: list[dict],
    user_id: str,
    max_rounds: int = 8,
) -> str:
    """Run the tool-use loop until the LLM produces a final text response."""
    for _ in range(max_rounds):
        response = client.messages.create(
            model=CDE_MODEL,
            max_tokens=2048,
            system=system_prompt,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )

        tool_blocks = [b for b in response.content if b.type == "tool_use"]

        if not tool_blocks:
            return "\n".join(b.text for b in response.content if b.type == "text")

        messages.append({"role": "assistant", "content": response.content})

        tool_results = []
        for tb in tool_blocks:
            result = execute_tool(conn, tb.name, tb.input, user_id)
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tb.id,
                "content": result,
            })
        messages.append({"role": "user", "content": tool_results})

    # Exhausted rounds — force final
    messages.append({"role": "user", "content": "Provide your response based on data gathered so far."})
    response = client.messages.create(
        model=CDE_MODEL, max_tokens=2048, system=system_prompt, messages=messages,
    )
    return "\n".join(b.text for b in response.content if b.type == "text")


def query_finding(
    conn: sqlite3.Connection,
    finding_id: int,
    user_message: str | None = None,
    conversation_history: list[dict] | None = None,
    user_id: str = "default",
) -> str:
    """Investigate a specific finding. Opens a finding thread.

    If user_message is None, the LLM explains the finding proactively.
    If provided, it answers the user's question about this finding.
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    briefing = build_finding_briefing(conn, finding_id, user_id)

    messages = list(conversation_history) if conversation_history else []

    if user_message:
        prompt = f"[FINDING BRIEFING]\n\n{briefing}\n\n---\n\n{user_message}"
    else:
        prompt = f"[FINDING BRIEFING]\n\n{briefing}\n\n---\n\nExplain this finding. What does the data show, what's likely causing it, and what should I watch for?"

    messages.append({"role": "user", "content": prompt})

    # Mark finding as viewed
    conn.execute("UPDATE finding SET status = 'viewed' WHERE id = ? AND status = 'active'", (finding_id,))
    conn.commit()

    return _run_tool_loop(client, conn, FINDING_THREAD_PROMPT, messages, user_id)


def query_free(
    conn: sqlite3.Connection,
    user_message: str,
    conversation_history: list[dict] | None = None,
    user_id: str = "default",
) -> str:
    """Free chat — answer user's question without injecting findings."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    briefing = build_minimal_briefing(conn, user_id)

    messages = list(conversation_history) if conversation_history else []
    messages.append({
        "role": "user",
        "content": f"[DATA CONTEXT]\n\n{briefing}\n\n---\n\n{user_message}",
    })

    return _run_tool_loop(client, conn, FREE_CHAT_PROMPT, messages, user_id)
