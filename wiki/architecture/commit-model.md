---
tags: [architecture, llm, commit, security, critical]
status: active
updated: 2026-06-01
---

# The commit model

How a parsed or structured intent becomes a committed change on any write path (coach-managed coaching surface, or a user logging their own data). This is the concrete implementation of the capability gate referenced in [[wiki/architecture/interaction-model]]. Two guardrail layers that fail independently. Note: the LLM is demoted in the coach refactor (see [[wiki/architecture/interaction-model]]), so much of this applies wherever the LLM *does* mediate a write; the structured-UI write path obeys the same operation set and non-destructive rule.

## The chain
intent (LLM-parsed or structured input) → **typed operation from a closed set** → (deterministic render) → **human-legible confirmation** → same typed object commits

When the LLM is the parser, it is in exactly one link (intent → typed operation). The riskiest output is human-readable before commit. What the user approves is byte-for-byte what executes.

## Guardrail layer 1: capability — the LLM can only stage typed operations
The commit endpoint accepts a typed payload from a **closed, enumerated set of operation types** and nothing else. Free text cannot reach the write path. The LLM's job is reduced to *classify intent into one of N operations and fill its typed fields* — constrained extraction, not authoring an action.

- Closed set, e.g. (coaching surface): `ADJUST_TRAINING_BLOCK`, `SET_MACRO_TARGET`, `LOG_BODYWEIGHT`, `MARK_WORKOUT_MISSED`, `ROUTE_QUESTION`, `SCHEDULE_CHECKIN`, … and (user's own log): `USER_LOG_SUBSTANCE_EVENT`, `MARK_DOSE_MISSED`.
- Each operation has a fixed, typed field set. Fields are constrained: exercise/compound from an enum, dose or load parses to structured quantity+frequency, dates validate.
- The endpoint validates against the closed set and rejects anything else. "Valid JSON" is NOT the guarantee — the *enumerated operation set* is. Constraining syntax isn't enough; the semantics are constrained by there being only N representable actions.
- **The substance boundary lives in the operation set itself.** There is no coach-side substance-write operation. `USER_LOG_SUBSTANCE_EVENT` is scoped to the *user* actor only; no operation exists for a coach to set/adjust/comment-on a user's substance data. The coach read-only rule (see [[wiki/architecture/coach-read-layer]]) is therefore enforced the same way non-destructiveness is — by what's representable, not by a prompt or a UI choice.
- If intent doesn't map cleanly to an operation, the LLM stages NOTHING and says "I'm not sure how to do that — here's what I think you mean, or do it manually." It never improvises a payload.

## Guardrail layer 2: operation design — operations are non-destructive by construction
This is the layer that actually protects the data, and it holds even if layer 1 fails. Authority lives in *what operations exist at all*, defined by what's safe for the data — not by interface.

- **No destructive operation exists in the set.** There is no `DELETE_SUBSTANCE_HISTORY`. No actor — user, coach, admin, the LLM — can erase the record, because erasure is not a representable operation.
- **Event-sourced, append-only.** "Stopped my test" does not delete or mutate — the user appends `USER_LOG_SUBSTANCE_EVENT{type: stop, compound, effective_date}`, a stop *event* on the timeline. History is never removed. The PK model and detectors reconstruct state by reading the event log.
- **Worst case is a wrong event, not a deletion.** A wrong event is visible, attributed, and reversible by appending a correcting event. Never a silent erasure.
- **Consequences are baked into the operation, not LLM actions.** An event committing *is* what surfaces it in the relevant view (e.g. the coach's read-only mirror, or the roster queue for a coaching-surface finding). The surfacing is a code-enforced downstream effect of the event being written, not something the LLM must remember to do.

Why this is stronger than gating the LLM: even a bug, a future feature, or a direct admin write cannot silently corrupt the data record, because corruption isn't in the operation vocabulary. For a system whose entire value is the integrity of the data record, this is the right invariant.

## Deterministic render: templating, NOT regex, NOT an LLM
The typed object is precise but not automatically *legible* to a busy coach or user. `{type: CHANGE_DOSE, compound: testosterone_cypionate, from:{mg:250,freq:E3.5D}, to:{mg:200,freq:E3.5D}, effective:2026-05-16}` is faster to misread than a sentence.

- Render with a **per-operation-type template function**: a pure mapping from the typed object's fields to a sentence. `MARK_COMPOUND_STOPPED{compound: testcyp}` → look up display name → "Completely stop Testosterone Cypionate."
- **Not an LLM** — LLM prose can drift from the payload, reopening the gap layer 1 closed.
- **Not regex** — regex re-parses a serialized string, fragile and backwards. We already *have* the structure; we're formatting *out of* it (templating), not pulling structure *out of* text (parsing). Operate on the typed fields directly.
- Multi-part requests render as a **numbered list of discrete operations**, each separately legible and approvable.

## Escape hatches (keep the operation set small)
- **Follow-up prompt:** user corrects the parse in natural language; LLM re-stages.
- **Manual entry, always:** anything the LLM can't express, the user/coach does by hand through structured UI. This is the pressure-release valve that lets the operation set stay small — graceful refusal ("I can't do that one — do it manually") beats schema sprawl. Each new operation is a new parse-target and a new commit path to secure.

## The honest residual
Layer 1 makes the system safe against the LLM doing something *unrepresentable*. It does NOT make it safe against the LLM choosing the *wrong representable thing* — a user saying "pause my test a week" mis-staged as a permanent stop. The typed object is valid and the render is faithful, but the intent was wrong. The **deterministic render is the only defense** — it surfaces the misclassification legibly ("Stop Testosterone Cypionate, no resume date — correct?") for the human to catch. Which is why render quality and stakes-weighted confirmation still matter under a perfect type system, and why this is non-destructive by design: a caught-too-late wrong event is recoverable; a deletion wouldn't be.

## Implementation status (2026-06-01)

The operation set described above is implemented in `.src/coach/operations.py`. The actual operations built:

**Coach operations (5):**
- `SetTrainingBlock` — athlete_id, name, block_type, start_date, end_date, notes
- `EndTrainingBlock` — athlete_id, block_id, end_date
- `SetNutritionTarget` — athlete_id, calories, protein_g, carbs_g, fat_g, effective_date, notes
- `AddRecoveryNote` — athlete_id, note_type, content
- `NudgeSensitivity` — athlete_id, detector_id, direction (backend only, no UI built)

**User-only operation (1):**
- `UserLogSubstanceEvent` — athlete_id, compound_name, compound_class, event_type (START/DOSE_CHANGE/STOP/MISSED_DOSE), dose_mg, frequency, route

**Substance boundary enforcement:** `commit_operation()` checks `actor_role` — if a coach actor invokes `UserLogSubstanceEvent`, it raises `PermissionError`. This is a code-level enforcement, not a prompt.

**Deterministic render:** Each operation dataclass has a `.render()` method that produces a human-readable sentence from its typed fields. This is a pure template function, not an LLM.

**Operation log:** Every committed operation is recorded in the `operation_log` table with actor_id, actor_role, operation_type, payload_json, rendered_text, and committed_at.

**What changed since Phase 0:** The LLM is connected. Coach LLM creates training blocks, nutrition targets, and recovery notes through the typed operation path (e.g., "set a deload block" → SetTrainingBlock operation → commit_operation → operation_log). Athlete LLM manages compounds through add_compound_event (e.g., "drop my test to 300mg" → DOSE_CHANGE logged). Substance boundary enforced: coach LLM refuses compound operations because the tools don't exist in its set. Alias lookup for compound names added (e.g., "Nolvadex" resolves to tamoxifen via compound_db aliases).

**What is not yet built:** The human confirmation step before commit. Both LLM-mediated and form-based writes commit directly without showing the deterministic render for approval. The `.render()` methods exist and the operation_log stores rendered text, but the UI doesn't pause for confirmation. Frontend form Save buttons don't call the API yet (writes work through LLM chat or direct curl). The operation set is still smaller than the full spec (no MARK_WORKOUT_MISSED, ROUTE_QUESTION, SCHEDULE_CHECKIN, mark_dose_taken, mark_dose_missed, reschedule_dose).

Related: [[wiki/principles]] · [[wiki/architecture/interaction-model]] · [[wiki/architecture/coach-read-layer]] · [[wiki/architecture/two-sided-model]] · [[wiki/architecture/relationship-to-cde]]
