# Pennant Fever Code State Analysis

*Analysis Date: 2024-12-21*

---

## Executive Summary

The current `pennant_fever_game.py` is in a **broken/experimental state** with two competing simulation models coexisting in the same file. The code cannot run because an experimental Pygame-based micro-simulation main loop was added but left incomplete, overriding the working macro engine.

---

## The Core Problem

### Two `main()` Functions

| Location | Type | Purpose | Status |
|----------|------|---------|--------|
| Line 2512 | Macro Engine | Season simulation, loads teams/schedule, plays 186-day season | **Working** (but shadowed) |
| Line 2701 | Micro/Pygame | At-bat-by-at-bat GUI simulation | **Broken** (incomplete) |

Python only recognizes the **last** `def main():` definition, so line 2701 shadows line 2512.

### Two `Game` Class Concepts

**Actual Game class (line 39):**
```python
def __init__(self, home_team, away_team, day, power_chart, speed_bench_chart, relief_defense_chart):
```

**What the Pygame main() expects (line 2703):**
```python
game = Game(mode)  # Expects Game(mode) with mode="human" or "ai"
```

This causes the immediate error:
```
TypeError: Game.__init__() missing 5 required positional arguments:
'away_team', 'day', 'power_chart', 'speed_bench_chart', and 'relief_defense_chart'
```

---

## Two Competing Simulation Models

### Model 1: Macro Engine (Original - Working)

**Philosophy:** Faithful to original Pennant Race board game
- Resolves entire games with dice rolls + charts → runs
- No play-by-play, no individual at-bats
- BV (Batter Value) aggregated at team level
- Fast season simulation (186 games × 30 teams)

**Key locations:**
- `Game.play_game()` - macro resolution
- `Game.resolve_scoring()` - dice + charts → runs
- `main()` at line 2512 - season loop

### Model 2: Micro Engine (Experimental - Incomplete)

**Philosophy:** Play-by-play simulation with GUI
- Individual at-bats with outcomes (walk, strikeout, single, HR, etc.)
- Inning/outs/baserunner tracking
- Pygame visual interface
- Per-batter resolution

**Key locations:**
- `SimulateStats` class (line ~1821) - generates detailed stats
- GUI class (line ~2645) - Pygame interface
- `main()` at line 2701 - at-bat loop

**Missing pieces for micro engine:**
- `Game.at_bat()` method
- `Game.update_baserunners()` method
- `Game.switch_sides()` method
- `Game.game_over()` method
- `Game.declare_winner()` method
- `Game.current_batting_team` attribute
- `Game.current_batter_index` attribute
- `Game.outs` attribute
- `Game.mode` attribute
- `Game.play_by_play` attribute

---

## File Structure Issues

### Classes and Their Purpose

| Class | Purpose | Model | Status |
|-------|---------|-------|--------|
| `Game` | Core game simulation | Macro | Working |
| `Team` | Team data container | Both | Working |
| `Player` | Batter data | Both | Working |
| `Pitcher` | Pitcher data | Both | Working |
| `Dice` | Dice rolling | Macro | Working |
| `Standings` | League standings | Macro | Working |
| `Schedule` | Game schedule | Macro | Working |
| `Injury` | Injury mechanics | Macro | Working |
| `TeamStats` | Season statistics | Macro | Working |
| `SimulateStats` | Detailed box scores | Micro | Partial |
| `GUI` | Pygame interface | Micro | Incomplete |

### Pylance Errors (Expected)

The IDE shows errors because the micro engine code references methods/attributes that don't exist:
- `game.at_bat` - undefined
- `game.update_baserunners` - undefined
- `game.switch_sides` - undefined
- `game.game_over` - undefined
- `game.current_batting_team` - undefined
- etc.

---

## Comparison: v0.0.62 vs Current

| Aspect | v0.0.62 (Working) | Current (Broken) |
|--------|-------------------|------------------|
| `main()` functions | 1 (line 2551) | 2 (lines 2512, 2701) |
| Simulation model | Macro only | Macro + incomplete Micro |
| GUI | None | Partial Pygame |
| Runnable | Yes (CLI) | No |
| Lines of code | ~2600 | ~2757 |

**What was added in v0.0.64:**
- `SimulateStats` class (~line 1821) - box score generation
- `GUI` class (~line 2645) - Pygame interface
- Second `main()` (~line 2701) - at-bat game loop
- Pygame imports and initialization

---

## Recommended Paths Forward

### Option A: Restore Macro-Only (Quick Fix)

1. Comment out or delete the Pygame `main()` at line 2701
2. Rename the macro `main()` at line 2512 to be the active entry point
3. Result: Working CLI season simulator

**Pros:** Immediate working state
**Cons:** Loses experimental micro work

### Option B: Separate the Models (Clean Architecture)

1. Extract macro engine to `pennant_fever_engine.py`
2. Extract micro/GUI experiment to `pennant_fever_gui.py` (or delete)
3. Keep `pennant_fever_game.py` as entry point that imports the engine
4. Result: Clean separation, both models preserved

**Pros:** Clean architecture, can develop both paths
**Cons:** More refactoring work

### Option C: Complete the Micro Engine (Major Work)

1. Implement all missing methods in Game class for at-bat simulation
2. Reconcile the two models (macro for season sim, micro for individual games?)
3. Complete the GUI
4. Result: Hybrid system

**Pros:** Achieves the vision described in pennant_fever.md
**Cons:** Significant development effort

---

## Quick Fix to Make Code Runnable

To immediately restore functionality, change the end of the file:

**Current (broken):**
```python
if __name__ == "__main__":
    main()  # Calls the Pygame main() at line 2701
```

**Quick fix:**
```python
if __name__ == "__main__":
    # main()  # Pygame version - incomplete

    # Use the macro engine main() instead
    # (Rename the function at line 2512 to main_season() first)
    main_season()
```

Or simply delete/comment out the entire Pygame `main()` function (lines 2698-2750).

---

## Relevant Files for Reference

| File | Purpose |
|------|---------|
| `pennant_fever_game.py` | Current broken state |
| `old_versions/pennant_race_v.0.0.62.py` | Last working macro-only version |
| `old_versions/pennant_race_v.0.0.64.py` | Same as current (with micro additions) |
| `pennant_fever_generator.py` | League/roster generation (working) |
| `docs/pennant_fever.md` | Design spec and TODO list |
| `docs/game_analysis.md` | Previous analysis notes |

---

## Design Philosophy Reminder

From your design doc:
> "You wouldn't actually simulate the game inning by inning, rather you would generate the result of the game with a few dice rolls. This allowed you to simulate a full season fairly quickly."

The macro engine aligns with this. The micro engine (at-bat simulation) is a departure from this philosophy. Consider whether the micro approach is actually desired, or if the goal is to add visual polish to the macro approach (show results, not simulate at-bats).

---

*Next steps: Decide which path to take (A, B, or C) and I can help implement it.*
