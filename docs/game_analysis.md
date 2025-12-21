Here’s a systems-auditor read of the main engine in pennant_race_v.0.0.64.py against the Pennant Fever design spec.

# Alignment with the design philosophy

- The core resolution stays macro and dice‑driven: BV + dice + charts → runs without play-by-play (e.g., pennant_race_v.0.0.64.py (line 501), pennant_race_v.0.0.64.py (line 585), pennant_race_v.0.0.64.py (line 692)).
- Team BV uses batter ratings + splits vs pitcher handedness, matching the spec’s BV/splits model (pennant_race_v.0.0.64.py (line 1290)).
- Relief usage and inning allocation are abstracted and chart‑based rather than batter-by-batter (pennant_race_v.0.0.64.py (line 1431), pennant_race_v.0.0.64.py (line 1478)).
- Extra-innings are resolved via a compact dice/ratings comparison, still macro (pennant_race_v.0.0.64.py (line 783)).

# Where abstraction is leaking / becoming too detailed

- A full stat simulator is embedded that generates walks, strikeouts, hits, doubles, HRs, innings pitched, etc. (pennant_race_v.0.0.64.py (line 1821)). This drifts toward play-by-play artifacts.
- The Pygame loop references inning/outs, baserunners, and at_bat flow (pennant_race_v.0.0.64.py (line 2714), pennant_race_v.0.0.64.py (line 2745)), which are micro concepts not present in the macro engine.
- The GUI expects game.at_bat, update_baserunners, switch_sides, and game_over behaviors that aren’t part of the macro resolution path, implying two competing simulation models in one file (pennant_race_v.0.0.64.py (line 2745)).

# Mechanics that violate the “macro baseball” intent

- Explicit walks/strikeouts/hit types (including singles/doubles) contradict “the game never needs to know walks/strikeouts/singles vs outs” (pennant_race_v.0.0.64.py (line 1841), pennant_race_v.0.0.64.py (line 1894)).
- The at‑bat loop and baserunner updates are effectively a micro sim, which conflicts with “no pitch-by-pitch or at-bat” (pennant_race_v.0.0.64.py (line 2745)).
- One improvement with biggest quality boost / minimal complexity

- Quarantine the micro-sim paths (GUI/at-bat loop and SimulateStats) into separate modules or guard them behind an explicit “experimental” flag so the canonical engine remains purely macro. This keeps the source-of-truth resolution path clean without reworking any mechanics.
