---
tags: [product, thesis]
status: active
updated: 2026-05-31
---

# Product thesis

## The fragmentation, and the moat
A serious physique athlete generates data everywhere: Whoop for recovery/HR/sleep, a nutrition app for macros, a scale, periodic bloodwork PDFs, training logs, and their own substance log. Their coach sees almost none of it coherently — check-ins are a Sunday form and a few screenshots. The coach is making programming decisions on a fraction of the picture, reconstructed by hand.

We give the coach one continuous, domain-aware view of each client. That consolidation — plus enhanced-athlete-aware detection that knows what the numbers mean for *this* population — is the product. It's CDE's engine with a coach read layer on top. The data moat is the thing; everything else is around it.

## What we build
A refactor of CDE for coaches. The user's data syncs continuously to the platform (one-way). CDE's detectors run over it. The coach gets a **ranked review queue** across their roster — which clients have something worth attention this week, severity-ordered — and structured tools to manage the lawful coaching surface (training, nutrition, recovery). The user keeps their own substance log exactly as CDE does today; the coach can view it read-only and nothing more. See [[wiki/architecture/coach-read-layer]].

## The two-sided requirement
- **Coach-only value** → users don't sync → data starves → detectors have nothing. Dead.
- **User-only value** → coach won't pay. Dead.
- **Both** → user syncs because their coach acts on it; coach pays because it makes them a better, faster coach. Alive.

The user side is mostly passive: continuous sync that flows without effort, plus light structured input (daily notes, exceptions, their own substance log). Adherence is favorable — a paying physique client is dedicated by selection. See [[wiki/architecture/two-sided-model]].

## Why the coach customer (and why physique first)
A paying physique client is reliably adherent (helps the data spine). Coaches are reachable, decide fast, and the founder has native credibility in this world — GTM is far easier than cold-pitching a cautious clinician. Physique/bodybuilding specifically because the enhanced-athlete data is exactly what CDE already models, and these coaches feel the data-fragmentation pain acutely. See [[wiki/product/buyer]].

## What actually makes the thesis hold
Two things, both non-negotiable, both in [[wiki/principles]]: the **safety architecture** on any write path (inherited from CDE — nothing can erase the record, the human approves exactly what commits), and the **clean line** that keeps the product defensible — the coach manages the lawful side; the user self-logs substances; the coach view of that is strictly read-only. The data consolidation is already a lot of value. The thesis is to deliver that and not reach past the line into substance management.

Related: [[wiki/principles]] · [[wiki/product/moat]] · [[wiki/product/buyer]] · [[wiki/architecture/coach-read-layer]] · [[wiki/architecture/two-sided-model]]
