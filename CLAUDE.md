# CLAUDE.md

Operating instructions for Claude when working in `Cycle Data Platform/Coach Platform/`. Sibling project: `../Cycle Data Engine/` (the engine). Workspace overview and the refactor plan live in `../CLAUDE.md`.

## What this project is
A **refactor of the sibling `../Cycle Data Engine/` (CDE) for physique/bodybuilding coaches.** CDE is the engine — extraction, PK model, detectors, user self-logging intake. This product adds a coach-facing read layer: users continuously sync their data, coaches view it with domain-aware trends and a ranked roster queue, and coaches manage the lawful coaching surface (training/nutrition/recovery). It is CDE + a coach read layer, not a new system. See [[wiki/architecture/relationship-to-cde]].

History note: this started as a clinic product, then pivoted to coaches. Files tagged `status: superseded` (reuse-from-cde, llm-native-interaction, legal/*) are the clinic-era versions, stubbed to point at replacements. Don't revive their framing.

## The spine: read [[wiki/principles]]
Everything defers to [[wiki/principles]]:
1. **Safety architecture** (write path) — three tenets enforced in code/data: (a) capability gating — the LLM stages typed operations, never commits; (b) non-destructive by construction — no operation erases the record, for any actor; (c) deterministic legibility — the human approves byte-for-byte what commits.
2. **The central line** — the coach manages the lawful side (training/nutrition/recovery); the **user self-logs** anabolics/controlled/prescription substances exactly as CDE does; the **coach view of substance data is a strictly read-only mirror with NO interactive elements.** Substance conversations happen off-platform. This line is enforced in the operation set (no coach substance-write operation exists), not in a prompt or a UI choice.

If a proposal violates a tenet or crosses the substance line, say so before writing it in. Principles win over any doc, including this one.

## Session start protocol
1. Read `MVP.md` (scope) and [[wiki/principles]] (why).
2. Read [[wiki/ops/mvp-plan]] (current build focus) and [[wiki/ops/customer-discovery]] (the build is gated on coach conversations).
3. Then specific wiki files.

## Relationship to CDE
- CDE is the parent engine. Reference its components (e.g. `../Cycle Data Engine/src/cde/detectors/themes.py`) and its wiki (`../Cycle Data Engine/wiki/`, authoritative and current) but NEVER edit the CDE project from here. Keep the boundary clean.
- CDE-inherited vs. coach-added breakdown lives in [[wiki/architecture/relationship-to-cde]].

## Writing style for wiki files
Direct, concise, load-bearing claim first, no marketing voice, no optimism inflation. Prose over bullets where reasoning matters. Cross-link generously. YAML frontmatter + a `Related:` line on every file.

## Pushback expectations
The user asked for candor, not pandering. Say so directly, before writing, if a proposal:
- Crosses the substance line (any coach affordance on substance data; any coach-side substance-write operation)
- Violates a safety tenet (LLM commits directly / a destructive operation / LLM-authored confirmations)
- Gives the coach's LLM substance-write tools (the tool set boundary is the enforcement)
- Bypasses the deterministic confirmation step on LLM-staged operations
- Competes with generic coaching tools on workflow table-stakes instead of leading with the data moat
- Treats modeled PK values as measured fact
- Builds the real system before the customer-discovery gate

## Legal posture in the wiki
Per user decision, legal *reasoning* is kept out of the wiki. The read-only substance boundary is documented as an architecture/product rule (not legal justification) because it's load-bearing for the design. Note for the human, not the docs: the substance-data-sharing feature is the part that genuinely warrants a controlled-substance attorney's review before it ships — out of the wiki is fine, out of mind is not.

## The discipline that matters most
The load-bearing *commercial* uncertainty is whether coaches feel the data-fragmentation pain enough to pay. Every design decision is provisional until real coaches react. The MVP is a prop for conversations, not a product. Don't let a tidy wiki substitute for the calls.

## What to never do without explicit user approval
- Edit anything in the sibling `../Cycle Data Engine/`
- Add any coach affordance/action on substance data, or any coach-side substance-write operation
- Add any destructive operation
- Have the LLM commit without a deterministic, human-confirmed typed operation
- Promote the LLM to primary interface
- Restructure the wiki layout
