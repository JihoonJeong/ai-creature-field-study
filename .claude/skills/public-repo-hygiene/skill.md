---
name: public-repo-hygiene
description: Scan for and prevent Ludex-private content (GRAND_PLAN, design decisions, living creatures, authority boundaries) from appearing in this public repo. Use before any commit, PR, README update, or when auditing files for public release.
---

# Public Repo Hygiene

This repo is the **public companion** to Ludex (private). Certain internal content must never appear in committed files here (CLAUDE.md and CODY_HANDOFF.md are the sanctioned exceptions — they live locally and explain the boundary).

## Forbidden content taxonomy

### 1. GRAND_PLAN references
Any mention of Ludex's GRAND_PLAN document, its phases, or roadmap items by name.

- **Block patterns:** `GRAND_PLAN`, `grand plan`, references to internal milestone codes.

### 2. Design decisions log
Ludex maintains a numbered design-decisions log (D-001, D-002, ...). These identifiers are internal.

- **Block patterns:** `D-\d{3}` (e.g. `D-025`), `design-decisions-log`, "per decision D-..."
- **Sanitize:** replace `D-025` with a descriptive phrase like "the creature-first design principle" — state the idea without the identifier.

### 3. Living creatures
Named individual creatures from Ludex's private habitat (Primo, Spark, and any future named instances) must not appear. The public repo only uses generic names (A, B, creature_1) or paper-specific pseudonyms.

- **Block patterns:** `Primo`, `Spark`, any proper name that maps to a private habitat.

### 4. Authority boundaries / internal governance
Internal authority levels, approval structures, or governance language from Ludex.

- **Block patterns:** "authority boundary," specific role titles that are Ludex-internal.

### 5. Internal paths
Absolute paths pointing into the private Ludex repo.

- **Block patterns:** paths containing `ludex-private`, or `~/Projects/ludex/` without qualification.

## Authorized exceptions

- `CLAUDE.md` — contains operator identity; may reference "Ludex" as the parent project by name, and list principles like D-025 as context. Not published to readers, used by Cody only.
- `CODY_HANDOFF.md` — same rationale.

These two files are allowed to reference internal structure *as context for the operator*, but their content must not be copy-pasted into user-facing docs (README, experiment_design.md, paper text).

## Audit procedure

When auditing files or diffs:

1. Grep each forbidden pattern across the target (respecting the exception list).
2. For each hit, record `file:line`, matched pattern, and severity:
   - `block` — unambiguous leak (e.g. `D-\d{3}` in README)
   - `review` — ambiguous (e.g. the word "ludex" in a new doc — is it the public-facing acknowledgment or an internal reference?)
   - `info` — in an authorized file, reported for awareness
3. For `block` findings, suggest a sanitized replacement that preserves the idea without the identifier.

## Sanitization patterns

| Forbidden | Sanitized |
|---|---|
| "Per D-025, creatures come first." | "This codebase follows a creature-first design: fields serve creatures, humans observe through viewers." |
| "Primo demonstrated X in field trials" | "One of our test creatures demonstrated X" or use paper pseudonym |
| "From Ludex's GRAND_PLAN phase 3" | cut the reference; state the idea directly |

## Why this matters

The paper's credibility depends on the public repo being self-contained and reproducible. Leaking internal identifiers (D-025, GRAND_PLAN) invites questions that can't be answered without opening private material, and erodes the boundary between the research artifact and the parent project. Never trade specificity of internal reference for accessibility; always restate the underlying idea.
