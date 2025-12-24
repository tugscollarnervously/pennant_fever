# Codex Prompt Playbook (for VS Code)

This document is designed to be a **living reference** you can keep at the root of your workspace and explicitly point Codex at. It encodes *how* you want Codex to behave and *how* your projects are structured.

## locations
the top level coding folder is /Users/sputnik69/Documents/_code - this contains all of my projects.
pennant fever is in: /Users/sputnik69/Documents/_code/pennant_fever

---

## How to Use This Document

When working with Codex, start prompts like this:

> **"Use the Codex Prompt Playbook and the Pennant Fever Codex Spec below as source-of-truth. Read them fully before responding."**

Then add a role and task:

> **"Act as a debugger."**  
> **"Review `game_engine.py` for state bugs around innings and outs."**

Codex performs best when:
- It is told **what role to play**
- It is told **what files to read**
- It is told **what must not change**

---

## Canonical Codex Roles

Use these phrases verbatim.

### 1. Debugger
**Intent:** Find failure paths, not solutions.

**Prompt pattern:**
> Act as a debugger. Do not refactor. Identify invalid state transitions and edge cases.

Best for:
- Game state bugs
- Fatigue / rest issues
- Off-by-one errors
- Possession / inning logic

---

### 2. Rules Auditor
**Intent:** Verify code against written rules.

**Prompt pattern:**
> Act as a rules auditor. Compare the implementation to the design spec and list mismatches.

Best for:
- Dice resolution
- Chart lookups
- Ratings → outcome translation

---

### 3. Refactor Assistant
**Intent:** Improve clarity without changing behavior.

**Prompt pattern:**
> Act as a refactor assistant. Preserve behavior, randomness, and public APIs.

Best for:
- Large functions
- State machines
- Repeated logic

---

### 4. Systems Designer
**Intent:** Propose bounded features.

**Prompt pattern:**
> Act as a systems designer. Suggest the smallest mechanic that adds variance using existing data.

Best for:
- Feature expansion
- Rating usage
- Manager / morale mechanics

---

### 5. Translator (Rules → Code)
**Intent:** Deterministic logic first.

**Prompt pattern:**
> Translate section X into deterministic Python logic. No UI, no randomness yet.

Best for:
- Tabletop rules
- Dice charts
- Threshold logic

---

## Golden Codex Rules (Read This)

1. **Explain before modifying**
2. **Never change randomness unless explicitly asked**
3. **Do not rename domain concepts** (inning, BV, triad, etc.)
4. **Summarize changes + risks at the end of every response**

---

# Pennant Fever – Codex Design Spec

This section is the **authoritative high-level description** Codex should use when reasoning about the Pennant Fever codebase.

---

## Project Overview

**Pennant Fever** is a computerized remake of the Avalon Hill board game *Pennant Race*.

Core design goals:
- Fast, season-scale simulation
- Dice-driven, abstract resolution
- Roster and lineup management as the primary skill
- Faithful to the *spirit* of the original, not strict historical realism

The game does **not** simulate baseball pitch-by-pitch or at-bat-by-at-bat.
All mechanics exist to support **run generation and season outcomes**.

---

## What Exists Today

### 1. Core Simulation Engine
- Headless, command-line
- Simulates:
  - Regular season
  - Playoffs
  - Injuries
  - Fatigue
- Used primarily for balance and validation

### 2. Fictional League Generator
- Generates:
  - Teams
  - Players
  - Ballparks
  - Schedules
- Outputs JSON used directly by the engine

### 3. Historical Import Module
- Imports real MLB seasons
- Generates compatible player/team data
- **Currently missing support for splits**

### 4. Shared Data Assets
- Names
- Ballparks
- Schools
- Geographic / economic data

---

## Core Game Abstractions

### Batter Ratings
- `batting` (contact)
- `power`
- `eye`

**Batter Value (BV):**
```
BV = batting + eye + (power * 0.6)
```

Splits:
- `splits_L`
- `splits_R`

These modify BV contextually.

---

### Pitcher Ratings (Current)
- `start_value`
- `relief_value`

### Pitcher Ratings (Planned)
- `stuff`
- `command`
- `movement`

Goal: combine these meaningfully rather than treating them as cosmetic numbers.

---

## Resolution Philosophy

- Dice rolls determine **when** charts are consulted
- Ratings determine **how much impact** they have
- The game never needs to know:
  - Walks
  - Strikeouts
  - Singles vs outs

All logic exists to generate:
- Runs
- Earned vs unearned runs
- Pitcher responsibility

---

## Known Gaps / Active Work

- Historical importer lacks split ratings
- No visual interface (planned: pygame, ASCII-style)
- No interactive team control
- No persistent database (planned: SQL-first)
- No box score generation

---

## Planned Expansions (Bounded)

- Simple newspaper-style box scores
- Closer / leverage logic
- Manager ratings affecting edge cases
- Morale and leadership as modifiers

All expansions must:
- Preserve fast simulation
- Avoid play-by-play explosion
- Reuse existing ratings when possible

---

## Codex Evaluation Request Template

Use this verbatim when testing Codex:

> Use the Pennant Fever Codex Design Spec as source of truth.
> Review the relevant files and return:
> 1. Architectural strengths
> 2. Fragile or risky areas
> 3. Violations of the design philosophy
> 4. The single most impactful improvement

---

## Non-Goals (Important)

- No real-time animation
- No sabermetrics modeling
- No full PBP simulation
- No micro-optimizations

This is a **macro baseball game**.

---

## Final Instruction to Codex

When uncertain:
- Prefer clarity over cleverness
- Prefer determinism over realism
- Prefer fewer mechanics with clearer impact

