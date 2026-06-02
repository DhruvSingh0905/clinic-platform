---
tags: [principles, spine, critical]
status: active
updated: 2026-06-01
---

# Principles

The spine of the project. Every other doc defers to this. Two things make the product viable: **the safety architecture that keeps the write path trustworthy**, and **the conservative posture that keeps the product clean** — specifically the hard separation between what the coach manages and what the user logs for themselves. Neither is a feature. Both are non-negotiable.

This project is a **refactor of the Cycle Data Engine (CDE) for a coaching context**, not a new app. CDE is the engine — extraction, PK model, detectors, the self-logging intake. This product wraps a coach-facing read layer around it for physique/bodybuilding coaches. See [[wiki/architecture/relationship-to-cde]].

---

## Part 1 — The safety architecture (the write path)

There is a write path: the coach manages training, nutrition, and recovery programming, and the user reports exceptions. Where software commits a change to a record, the same three tenets from CDE apply. They are enforced in *code and data design*, never in prompts or good intentions.

### Tenet 1 — Capability gating: the LLM stages, it never commits
Where an LLM is used at all, it can only emit a **typed operation from a closed, enumerated set**. It cannot reach the write path with free text, cannot author an arbitrary action, cannot commit. The commit endpoint accepts the typed payload and nothing else, reachable only through a confirmation the LLM does not control. A *wall*, not a promise — holds against misparse and injection. The LLM is a primary interface for both coach and athlete (same as CDE), which makes this tenet more important, not less — the surface is large, so the gate must be structural. See [[wiki/architecture/commit-model]].

### Tenet 2 — Non-destructive by construction: nothing can erase the record
The operation set contains **no destructive operation**, for any actor, through any interface. Changes append events; history is never deleted. Event-sourced, append-only. The worst any actor — user, coach, the LLM, or a bug — can do is write a wrong event, which is visible, attributed, and reversible by appending a correction. Holds even if Tenet 1 fails, because corruption isn't in the operation vocabulary. The integrity of the data record is the whole product; this is the load-bearing invariant. See [[wiki/architecture/commit-model]].

### Tenet 3 — Deterministic legibility: the human approves exactly what commits
Every staged operation is rendered to human-readable text by a **deterministic template function** (not an LLM, not regex), a pure mapping from the typed object's fields. What the user reads is byte-for-byte what executes. The only defense against a valid-but-wrong operation. See [[wiki/architecture/commit-model]].

### How the three compose
Tenet 1 stops the LLM acting unilaterally. Tenet 2 ensures the worst action is recoverable. Tenet 3 catches the wrong-but-valid action before commit. They fail independently — no single failure corrupts the record.

---

## Part 2 — The conservative posture (the line that keeps the product clean)

### The central line: coach manages everything, athlete confirms substance changes
The coach is the buyer and the authority. The coach manages the full stack: training, nutrition, recovery, AND the athlete's substance protocol. This reflects how physique coaching actually works — the coach directs the protocol, the athlete executes it.

- **Coach-managed:** training load, nutrition/macros, recovery, sleep, programming, AND substance protocols (anabolics, ancillaries, controlled/prescription compounds). The coach actively manages all of these through structured tools and LLM chat.
- **Athlete confirmation:** When the coach modifies the substance protocol, the athlete receives a notification and must confirm the change. This ensures the athlete is aware of and agrees to all protocol changes. The confirmation is a gate, not a formality.
- **Both can log:** The athlete can also self-log substance events (same as CDE). The coach can modify the protocol directly. Both write paths go through the same typed operation system.

### Why the coach has substance access
Physique coaches direct protocols — that's what the client pays for. A platform that makes the coach manage training and nutrition but forces substance conversations off-platform into DMs adds friction to the coach's primary workflow. The coach already has the substance context in the health data (compound levels, correlation with bloodwork, PK-modeled trends). Giving them the write path completes the loop.

The safety architecture still applies: capability gating (typed operations from a closed set), non-destructive (append-only events), deterministic confirmation (the coach sees the rendered text before committing), and athlete notification (the athlete confirms every substance change).

### Other conservative lines
- **The LLM is a primary interface, not the only one.** Both coach and athlete interact with the system through conversational LLM — pulling data, modifying protocols, managing the calendar, investigating findings — the same way CDE works. The structured UI (roster queue, forms, dashboards) coexists as a direct-access layer. The LLM is not bolted on; it is how users naturally interact with a complex data system. The safety tenets (capability gating, non-destructive ops, deterministic confirmation) hold regardless of whether the action originates from the LLM or a form. See [[wiki/architecture/interaction-model]].
- **Modeled is labeled modeled.** PK-estimated values (inherited from CDE) are never shown as measured fact. See [[wiki/architecture/coach-read-layer]].
- **Claim less than the system does.** Lead with the data moat, not the substance handling.

### The discipline behind the posture
The athlete-confirms gate is the structural safety net. The coach has authority; the athlete has veto. Every substance modification the coach makes is logged in the operation log, rendered deterministically, and the athlete must acknowledge it. This audit trail is the defense.

---

## Relationship to the rest of the wiki
- `MVP.md` arbitrates scope; this doc arbitrates *why*.
- Architecture docs implement Part 1 and the read-layer rule. Product/ops docs implement Part 2.
- If any doc drifts from these principles, the principles win — fix the doc.

Related: [[wiki/architecture/relationship-to-cde]] · [[wiki/architecture/coach-read-layer]] · [[wiki/architecture/commit-model]] · [[wiki/architecture/interaction-model]]
