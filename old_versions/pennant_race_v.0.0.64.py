import random
import pandas as pd
import pygame
import json
import os
import sys
import math
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Add /Documents/_CODE/common to sys.path
COMMON_PATH = Path.home() / "Documents/_code/common"
sys.path.insert(0, str(COMMON_PATH))

from data_paths_pennant_fever import *

from common_logger import setup_logger

# Guard against multiple initializations (e.g., if module is reimported)
if not logging.getLogger("pennant_fever").hasHandlers():
    logger = setup_logger(
        name="pennant_fever",
        log_dir=PENNANT_FEVER_LOGS_GAME_DIR,
        prefix="pennant_fever",
        console_level=logging.DEBUG
    )
    logger.debug("Logger initialized. Starting the pennant_fever module.")
else:
    # Logger already exists, reuse it
    logger = logging.getLogger("pennant_fever")
    logger.debug("Logger reused (module reimport detected).")

PENNANT_FEVER_DIR.mkdir(parents=True, exist_ok=True)

BASE_DIRECTORY = '/Users/sputnik69/Documents/_CODE/_pennant_race/'

# Ensure the base directory exists
if not os.path.exists(BASE_DIRECTORY):
    os.makedirs(BASE_DIRECTORY)

class Game:
    def __init__(self, home_team, away_team, day, power_chart, speed_bench_chart, relief_defense_chart):
        self.home_team = home_team
        self.away_team = away_team
        self.home_team_ballpark = home_team.ballpark  # Assign ballparks here
        self.away_team_ballpark = away_team.ballpark
        self.day = day
        if self.day is None:
            logger.debug("Warning: Game day (self.day) is None. Defaulting to day 0.")
            self.day = 0  # This should now no longer default to 0, since 'day' is passed correctly
        self.dice = Dice(6)
        self.power_chart = power_chart  # Dictionary mapping to player indices or names
        self.speed_bench_chart = speed_bench_chart  # Similarly mapped
        self.relief_defense_chart = relief_defense_chart  # Similarly mapped
        self.result = {'home_runs': 0, 'away_runs': 0}

        self.used_relievers_home = []
        self.used_relievers_away = []

    def injury_check(self, team):
        injury = Injury(team)
        injured_player = injury.check_injury()
        return injured_player

    def roll_dice(self):
        white_die = self.dice.roll()
        red_die = self.dice.roll()
        green_die = self.dice.roll()
        return white_die, red_die, green_die

    def has_doubles(self, dice):
        white, red, green = dice
        return white == red or white == green or red == green

    def sum_dice(self, dice):
        return sum(dice)

    def consult_power_chart(self, white_die, red_die, green_die, team, ballpark):
        # Step 1: Check for doubles (white == red or white == green) or even triad (222, 444, 666)
        if white_die == red_die or white_die == green_die:
            # Step 2: Determine which dice are matching and select the chart key
            if white_die == red_die:
                # Matching white and red, use (white, red) as the chart key
                chart_key = (white_die, red_die)
                non_matching_die = green_die  # The non-matching die is the green one
            else:
                # Matching white and green, use (white, green) as the chart key
                chart_key = (white_die, green_die)
                non_matching_die = red_die  # The non-matching die is the red one

            # Step 3: Look up the correct row in the power_chart
            chart_row = self.power_chart.get(chart_key)
            if chart_row is None:
                logger.debug(f"Power chart did not return a valid entry for dice {white_die} + {red_die} + {green_die}")
                return None

            # Step 4: Use the non-matching die to select the correct spot
            chart_entry = chart_row.get(non_matching_die)
            if not chart_entry:
                logger.debug(f"Power chart did not return a valid entry for dice {white_die} + {non_matching_die}")
                return None

            # Step 5: Determine if the chart entry is a lineup or bench spot
            if "Spot" in chart_entry:
                # It’s a starter, map to the correct lineup spot (1-9)
                spot_number = int(chart_entry.split(" ")[1])
                player = team.players[spot_number - 1]  # Assuming the lineup is 1-based
                logger.debug(f"Power bonus from player in lineup Spot {spot_number}: {player.name}")
                return player
            elif "Bench" in chart_entry:
                # It's a bench player, map to the correct bench spot (10-15)
                bench_number = int(chart_entry.split(" ")[1])
                player = team.players[9 + bench_number - 1]  # Bench starts at index 9
                logger.debug(f"Power bonus from bench player Bench {bench_number}: {player.name}")
                return player
            else:
                logger.debug(f"Invalid chart entry: {chart_entry}")
                return None
        else:
            logger.debug(f"No power bonus. Dice combination: white={white_die}, red={red_die}, green={green_die}")
            return None

    def consult_speed_bench_chart(self, red_die, green_die, white_die, team):
        # Look up the chart entry based on the dice combination
        chart_entry = self.speed_bench_chart.get((red_die, green_die), {}).get(white_die, None)

        if chart_entry is None:
            logger.debug(f"No valid chart entry for Red={red_die}, Green={green_die}, White={white_die}.")
            return None

        # Handle lineup (Spot) or bench (Bench) spots from the chart
        if "Spot" in chart_entry:
            # It's a starter, map to the correct lineup spot (1-9)
            spot_number = int(chart_entry.split(" ")[1])
            player = team.players[spot_number - 1]  # Assuming lineup is 1-based
            logger.debug(f"Speed bonus from player in lineup Spot {spot_number}: {player.name} with speed value {player.speed}")
            return ("SP", player.speed)
        
        elif "Bench" in chart_entry:
            # It's a bench player, map to the correct bench spot (10-15)
            bench_number = int(chart_entry.split(" ")[1])
            player = team.players[9 + bench_number - 1]  # Bench starts at index 9
            logger.debug(f"Speed bonus from bench player Bench {bench_number}: {player.name} with speed value {player.speed}")
            return ("BN", player.speed)

        logger.debug(f"Invalid chart entry: {chart_entry}")
        return None

    # Define consult_relief_defense_chart inside Game class
    def consult_relief_defense_chart(self, dice_sum, green_die, team): # this is just the defense chart now, relief removed
        # New chart based on dice sum and whether the green die is even or odd
        relief_defense_chart = {
            3: {"odd": "Bench 5", "even": "CF"}, # CF needs to be changed to P but we need P (or SP/RP) as a position in the player json first
            4: {"odd": "Bench 4", "even": "Bench 6"},
            5: {"odd": "Bench 2", "even": "Bench 3"},
            6: {"odd": "C", "even": "Bench 1"},
            7: {"odd": "SS", "even": "1B"},
            8: {"odd": "3B", "even": "SS"},
            9: {"odd": "CF", "even": "LF"},
            10: {"odd": "2B", "even": "RF"}
        }
        
        chart_entry = relief_defense_chart.get(dice_sum, None)
        if not chart_entry:
            logger.debug(f"No valid chart entry for dice sum {dice_sum}.")
            return {"fielding_value": 0}
        
        # Determine if green die is odd or even and get the field position
        field_position = chart_entry["odd"] if green_die % 2 == 1 else chart_entry["even"]
        
        # Find the player based on field position
        if "Bench" in field_position:
            # Get the bench spot number from the string
            bench_number = int(field_position.split(" ")[1])
            player_at_position = team.players[9 + bench_number - 1]  # Bench starts at index 9
        else:
            # Look for the player in the given fielding position
            player_at_position = next((p for p in team.players if p.position == field_position), None)
        
        if player_at_position:
            logger.debug(f"Using {player_at_position.name} at position {field_position} with fielding value {player_at_position.fielding}")
            return {"fielding_value": player_at_position.fielding}
        else:
            logger.debug(f"No player found at position {field_position}.")
            return {"fielding_value": 0}

    def check_pitcher_shutout_or_complete_game(self, triad, pitcher, white_die):
        """
        Checks if the pitcher can achieve a complete game or shutout based on the triad rolled, their ratings, and endurance.
        A short-rested pitcher cannot achieve a CG or SHO.
        """

        # Check if the pitcher is short-rested
        # Handle unstarted pitchers (first start of the season)
        if pitcher.last_start_day is None or pitcher.last_start_day == 0:
            days_since_last_start = float('inf')  # Treat as infinitely rested for the first start
        else:
            days_since_last_start = self.day - pitcher.last_start_day

        logger.debug(f"Current day: {self.day}, Last start day: {pitcher.last_start_day}, Required rest: {pitcher.rest}, Days since last start: {days_since_last_start}")

        # Pitcher must not be short-rested to qualify for CG or SHO
        if days_since_last_start < pitcher.rest:
            logger.debug(f"{pitcher.name} is short-rested and ineligible for CG or SHO.")
            return False, False, False  # No shutout, no complete game, no CG/SHO combo
        
        # Adjust the thresholds for complete game and shutout
        sho_threshold = pitcher.sho_rating
        cg_threshold = pitcher.cg_rating

        if triad == 666:
            logger.debug("Special case: triad is 666, no CG or SHO can happen")
            return False, False, False  # No shutout, no complete game, no CG/SHO combo

        # Step 1: Check if the pitcher throws a shutout (independent of CG)
        is_shutout = triad > sho_threshold and white_die >= 5 and pitcher.start_value >= 3.0
        logger.debug(f"triad: {triad}, sho_threshold: {sho_threshold}, white_die: {white_die}, pitcher.start_value: {pitcher.start_value}")
        logger.debug(f"is_shutout: {is_shutout}")

        # Step 2: Check if the pitcher throws a complete game (independent of shutout)
        is_complete_game = triad > cg_threshold and white_die >= 6  and pitcher.endurance >= 5
        logger.debug(f"triad: {triad}, cg_threshold: {cg_threshold}, white_die: {white_die}, pitcher.endurance: {pitcher.endurance}")
        logger.debug(f"is_complete_game: {is_complete_game}")

        # Step 3: Handle the rare case of a complete game shutout (CG/SHO combo)
        if is_shutout and is_complete_game:
            logger.info(f"{pitcher.name} throws a complete game shutout! (triad: {triad}, cg_threshold: {cg_threshold}, sho_threshold: {sho_threshold}, white_die: {white_die}, pitcher endurance: {pitcher.endurance})")
            return True, True, True  # Shutout, complete game, and a CG/SHO combo

        # Step 4: Handle the case where it's a shutout but NOT a complete game
        if is_shutout and not is_complete_game:
            logger.debug(f"is shutout: {is_shutout} / pitcher SHO rating: {pitcher.sho_rating}; is complete game: {is_complete_game} / pitcher CG rating: {pitcher.cg_rating}")
            logger.info(f"{pitcher.name} throws a shutout but does not complete the game!")
            return True, False, False  # Shutout but not a complete game
        
        # Step 5: If only a complete game
        if is_complete_game:
            logger.info(f"{pitcher.name} throws a complete game!")
            return False, True, False  # Complete game but not a shutout

        # Step 6: No shutout or complete game
        return False, False, False

    def find_individual_bat_player(self, team, dice_sum):
        """Find the player whose lineup position corresponds to the specific dice sum."""
        # Map dice sums to lineup positions as specified
        dice_sum_to_slot = {
            11: 1,
            12: 2,
            13: 3,
            14: 4,
            15: 5,
            16: 6,
            17: 7,
            18: 8
        }

        # Check if the dice sum is in our mapping
        if dice_sum in dice_sum_to_slot:
            slot = dice_sum_to_slot[dice_sum]
            player = team.players[slot - 1]  # Assuming lineup positions are 1-based
            logger.debug(f"Step 5: Individual bat bonus from {player.name} with a batting value of {player.batting}.")
            return player
        else:
            # If the dice sum isn't in the mapping, return None and log the result
            logger.debug(f"Step 5: No individual bat bonus player found for dice sum {dice_sum}.")
            return None

    def calculate_runs_for_starter(self, total_earned_runs, total_unearned_runs, starter, relief_pitching, current_day):
        # Step 1: Calculate how many outs the starter pitched
        bullpen_innings = relief_pitching.innings_pitched_by_bullpen() if relief_pitching else 0
        total_outs = 27  # Total outs in a full game
        bullpen_outs = int(bullpen_innings) * 3 + round((bullpen_innings % 1) * 10)
        starter_outs = total_outs - bullpen_outs
        
        # Convert starter_outs to innings format (1 out = 0.1 innings, 3 outs = 1.0 innings)
        starter_innings = starter_outs // 3 + (starter_outs % 3) * 0.1
        logger.debug(f"Starter innings: {starter_innings}")

        # Step 2: Check if the opposing team has exceeded a run threshold
        RUN_THRESHOLD = 8  # Default run threshold for pulling a starter early

        if total_earned_runs >= RUN_THRESHOLD:
            logger.debug(f"Runs exceeded threshold of {RUN_THRESHOLD}. Starter will be pulled early.")

            # Assume better starters last longer when runs exceed the threshold
            if starter.start_value >= 5:
                starter_innings = max(starter_innings - 1, 3)  # Keep at least 3 innings
            else:
                starter_innings = max(starter_innings - 2, 2)  # Lower quality starters pulled earlier
            logger.debug(f"Adjusted innings due to exceeded runs: {starter_innings}")

        # Check for short rest
        if starter.last_start_day is None or starter.last_start_day == 0:
            days_since_last_start = float('inf')  # Treat as infinitely rested for first start
        else:
            days_since_last_start = current_day - starter.last_start_day

        if days_since_last_start < starter.rest:
            logger.debug(f"Short rest: {days_since_last_start} days since last start (Rest needed: {starter.rest})")
            endurance_penalty = 1 if starter.endurance >= 4 else 2  # Higher endurance starters penalized less
            starter_innings = max(starter_innings - endurance_penalty, 2)  # Limit to at least 2 innings
            logger.debug(f"Adjusted innings due to short rest: {starter_innings}")

        # Step 3: Calculate the portion of earned and unearned runs the starter is responsible for
        starter_proportion = starter_innings / 9.0  # Starter's portion of the game
        starter_earned_runs = round(total_earned_runs * starter_proportion)  # Assign earned runs proportionally
        starter_unearned_runs = round(total_unearned_runs * starter_proportion)  # Assign unearned runs proportionally

        # Step 4: Apply extra runs logic based on the total earned runs
        if total_earned_runs >= 16:
            starter_earned_runs += 8
        elif total_earned_runs >= 14:
            starter_earned_runs += 4
        elif total_earned_runs >= 12:
            starter_earned_runs += 2
        elif total_earned_runs >= 10:
            starter_earned_runs += 1
        
        # Ensure we don't exceed the total earned runs
        starter_earned_runs = min(starter_earned_runs, total_earned_runs)

        logger.debug(f"Starter responsible for {starter_earned_runs} earned runs and {starter_unearned_runs} unearned runs out of {total_earned_runs + total_unearned_runs} total.")

        # Return the earned and unearned runs assigned to the starter, so the rest can be passed to relievers
        return starter_earned_runs, starter_unearned_runs, starter_innings

    @staticmethod
    def convert_innings_to_float(innings_str):
        whole, fractional = innings_str.split('.')
        return int(whole) + (int(fractional) * 1/3)

    def adjust_bv_for_relievers(self, team, relief_pitching, opponent_pitcher, reliever_innings_distribution, chosen_relievers):
        """
        Adjust the team's batting value based on the handedness of the chosen relievers, looping through the lineup until outs are distributed.
        """
        total_modifier = 0  # Will accumulate the net effect of all relievers
        total_outs_distributed = 0  # Track the total outs distributed to relievers
        lineup = [player for player in team.players if player.role == 'Starter']  # Filter starters
        lineup_size = len(lineup)  # Usually 9 batters in a lineup

        for reliever in chosen_relievers:
            reliever_throws = reliever.throws  # 'L' or 'R'

            # Fetch innings pitched from reliever_innings_distribution dictionary and convert to float
            innings_pitched_str = reliever_innings_distribution.get(reliever.name, "0.0")
            innings_pitched = self.convert_innings_to_float(innings_pitched_str)  # Convert to float

            # Ignore relievers who didn't pitch
            if innings_pitched == 0:
                continue

            outs_for_this_reliever = int(innings_pitched * 3)  # Convert innings to outs
            logger.debug(f"{reliever.name} responsible for {outs_for_this_reliever} outs.")

            # Distribute outs by looping through the lineup until all outs are accounted for
            while outs_for_this_reliever > 0:
                batter_index = total_outs_distributed % lineup_size  # Wrap around the lineup using modulus
                player = lineup[batter_index]  # Get the current batter

                player_bv = player.batting + player.eye + (player.power * 0.6)
                batter_modifier = 0  # Default modifier for switch-hitters
                reliever_modifier = 0  # Initialize reliever modifier

                logger.debug(f"Processing {player.name} (Bats: {player.bats}) vs. Reliever {reliever.name} (Throws: {reliever_throws})")

                # Determine the batter's splits against the reliever's handedness
                if reliever_throws == 'L':
                    if player.bats == 'L':
                        batter_modifier = player.splits_L  # Batter's split against LHP
                        reliever_modifier = reliever.splits_L  # Reliever's split against LHB
                    elif player.bats == 'R':
                        batter_modifier = player.splits_L  # Batter's split against LHP
                        reliever_modifier = reliever.splits_R  # Reliever's split against RHB
                    elif player.bats == 'S':
                        batter_modifier = 0  # Switch-hitter neutral
                        reliever_modifier = 0

                elif reliever_throws == 'R':
                    if player.bats == 'L':
                        batter_modifier = player.splits_R  # Batter's split against RHP
                        reliever_modifier = reliever.splits_L  # Reliever's split against LHB
                    elif player.bats == 'R':
                        batter_modifier = player.splits_R  # Batter's split against RHP
                        reliever_modifier = reliever.splits_R  # Reliever's split against RHB
                    elif player.bats == 'S':
                        batter_modifier = 0
                        reliever_modifier = 0

                # Adjust player BV by batter's and reliever's split modifiers
                adjusted_player_bv = player_bv + (batter_modifier - reliever_modifier)

                # Clamp adjusted_player_bv to a minimum of 0
                adjusted_player_bv = max(0, adjusted_player_bv)

                # Add to total modifier, weighted by innings pitched
                total_modifier += (adjusted_player_bv) * (innings_pitched / 9.0)

                logger.debug(f"{player.name} BV: {player_bv} / Modifier: {batter_modifier} vs {reliever.name} Modifier: {reliever_modifier}, Adjusted BV: {adjusted_player_bv}")

                # Update outs processed
                total_outs_distributed += 1
                outs_for_this_reliever -= 1  # Decrement outs for this reliever

        logger.debug(f"Total modifier after reliever adjustments: {total_modifier}")

        # Adjust the original BV based on the cumulative effect of all relievers
        if total_outs_distributed > 0:
            return total_modifier

        return 0


    def recalculate_relief_innings(self, starter_innings, relief_pitching, current_day):
        """Recalculate bullpen innings after starter adjustments using proper baseball notation."""
        fatigue_cache = relief_pitching.fatigue_cache
        fatigue_debug_info = {r.name: fatigue_cache[r] for r in fatigue_cache}
        logger.debug(f"LINE 430 Fatigue cache: {fatigue_debug_info}")

        logger.debug(f"Recalculating relief innings due to starter adjustment. Starter innings: {starter_innings}")

        # Step 1: Calculate updated bullpen innings based on reduced starter innings
        total_game_outs = 27  # Total outs in a 9-inning game
        starter_outs = int(starter_innings) * 3 + round((starter_innings % 1) * 10)
        updated_bullpen_outs = total_game_outs - starter_outs
        logger.debug(f"Starter pitched {starter_outs} outs, bullpen needs to cover {updated_bullpen_outs} outs.")

        # Convert the updated bullpen outs back into innings notation
        bullpen_innings_whole = updated_bullpen_outs // 3
        bullpen_innings_fractional = updated_bullpen_outs % 3
        updated_bullpen_innings = float(f"{bullpen_innings_whole}.{bullpen_innings_fractional}")
        logger.debug(f"Updated bullpen innings in baseball notation: {updated_bullpen_innings}")

        # Step 2: Recalculate how many relievers to use based on the new bullpen innings
        relievers_used = relief_pitching.number_of_relievers_used(updated_bullpen_innings)
        logger.debug(f"Recalculating relievers used: {relievers_used} relievers for {updated_bullpen_innings} innings.")

        # Step 3: Recalculate the innings distribution among the relievers
        chosen_relievers = relief_pitching.used_relievers  # Ensure this is the list of relievers chosen earlier
        logger.debug(f"LINE 452 Chosen relievers: {chosen_relievers}")

        fatigue_cache = relief_pitching.fatigue_cache
        fatigue_debug_info = {r.name: fatigue_cache[r] for r in fatigue_cache}
        logger.debug(f"LINE 456 Fatigue cache: {fatigue_debug_info}")

        # Ensure all relievers have precomputed fatigue multipliers
        for reliever in chosen_relievers:
            if reliever not in fatigue_cache:
                fatigue_cache[reliever] = relief_pitching.get_fatigue_multiplier(reliever, current_day, fatigue_cache)

        # Distribute innings among the chosen relievers based on the recalculated bullpen innings
        innings_distribution = relief_pitching.distribute_innings_among_relievers(
            chosen_relievers, updated_bullpen_innings, fatigue_cache
        )

        logger.debug(f"LINE 524 Relief innings distribution after recalculation: {innings_distribution}")
        return innings_distribution

    def resolve_team_runs(self, team, opponent_pitcher, current_day, is_visiting=True):
        # Step 0: Roll the dice
        dice = self.roll_dice()
        white_die, red_die, green_die = dice
        dice_sum = self.sum_dice(dice)
        doubles = self.has_doubles(dice)
        triples = (white_die == red_die == green_die)
        triad = int(f"{white_die}{red_die}{green_die}")  # Create the three-digit triad number

        # Set ballpark for the current game
        ballpark = self.home_team_ballpark if not is_visiting else self.away_team_ballpark

        logger.debug(f"Step 0: Rolling dice for {'visiting' if is_visiting else 'home'} team: White={white_die}, Red={red_die}, Green={green_die}, Triad={triad}, Sum={dice_sum}")

        # Step 1: Check for Shutout, Complete Game, or CG/SHO combo
        is_shutout, is_complete_game, is_cg_sho_combo = self.check_pitcher_shutout_or_complete_game(triad, opponent_pitcher, white_die)

        # Initialize relief_pitching to None
        relief_pitching = None
        chosen_relievers = None

        # If it's a complete game shutout, return 0 runs and mark it as a CG/SHO
        if is_cg_sho_combo:
            logger.debug(f"Step 1: Complete Game Shutout! {opponent_pitcher.name} prevents the {team.team_name} from scoring.")
            
            # Since it's a complete game shutout, assume no bullpen innings, no earned/unearned runs for relievers
            starter_innings = 9.0  # The starter pitched a complete game
            reliever_innings_distribution = {}
            earned_runs_distribution = {}
            unearned_runs_distribution = {}
            total_relief_value = 0  # No relief needed, so total relief value is 0
            
            return 0, total_relief_value, starter_innings, reliever_innings_distribution, earned_runs_distribution, unearned_runs_distribution, chosen_relievers

        # If it's a shutout but not a complete game, relief pitching will be needed for the team shutout
        if is_shutout and not is_complete_game:
            logger.debug(f"Step 1: Shutout but not a complete game! {opponent_pitcher.name} holds the {team.team_name} scoreless, bullpen finishes the game.")
            
            # Process relief pitching to complete the shutout
            relief_pitching = ReliefPitching(opponent_pitcher, team, dice, self)
            total_relief_value, chosen_relievers, fatigue_cache = relief_pitching.process_relief_pitching(current_day)
            
            # We still need to calculate innings and runs for the relievers
            starter_innings = 0  # Adjust as necessary if some starter innings are to be counted
            reliever_innings_distribution = relief_pitching.distribute_innings_among_relievers(
                chosen_relievers, relief_pitching.innings_pitched_by_bullpen(), fatigue_cache)
            
            earned_runs_distribution, unearned_runs_distribution = relief_pitching.distribute_runs_among_relievers(
                chosen_relievers, 0, 0, current_day, fatigue_cache)  # No runs, since it's a shutout
            
            logger.debug(f"Step 1a: Total relief value after adjustments: {total_relief_value}")
            
            # No runs as it’s a team shutout
            logger.debug(f"Step 1b: Team completes the shutout with relief pitching.")
            
            return 0, total_relief_value, starter_innings, reliever_innings_distribution, earned_runs_distribution, unearned_runs_distribution, chosen_relievers

        # Step 2: If no shutout, continue to determine Batting Value (BV)
        total_relief_value = 0  # Initialize total relief value to 0
        BV = team.get_batting_value(opponent_pitcher)
        logger.debug(f"Step 2: No Shutout, Initial Batting Value (BV) for {team.team_name}: {BV}")

        # Step 3: Check for complete game and handle relief pitching
        if not is_complete_game:
            logger.debug(f"Step 3: {opponent_pitcher.name} did not complete the game. Proceeding with relief pitching.")
            relief_pitching = ReliefPitching(opponent_pitcher, team, dice, self)
            total_relief_value, chosen_relievers, fatigue_cache = relief_pitching.process_relief_pitching(current_day)

            # Get the distribution of innings and runs for the relievers
            reliever_innings_distribution = relief_pitching.distribute_innings_among_relievers(
                chosen_relievers, relief_pitching.innings_pitched_by_bullpen(), fatigue_cache
            )

            # Adjust BV based on the chosen relievers' impact
            reliever_bv_modifier = self.adjust_bv_for_relievers(team, relief_pitching, opponent_pitcher, reliever_innings_distribution, chosen_relievers)

            # Apply the modifier to the original BV, rather than replacing it
            BV = max(0, BV + reliever_bv_modifier)  # Ensure BV doesn't drop below 0
            logger.debug(f"Step 3a: Adjusted Batting Value (BV) for {team.team_name}: {BV}")

        # Cap the BV at 135 before applying any bonuses
        if BV > 135:
            BV = 135

        # Step 4: Handle triples (all dice are the same)
        if triples:

            if triad % 2 == 0:
                # Even triad - Apply Power/Speed/Bench bonus
                power_player = self.consult_power_chart(white_die, red_die, green_die, team, ballpark)

                # Check if power_player is valid
                if power_player and hasattr(power_player, 'name') and hasattr(power_player, 'batting'):
                    logger.debug(f"Step 4: Power bonus for {power_player.name} with a batting value of {power_player.batting}.")
                    power_bonus = power_player.power * dice_sum
                    power_bonus += ballpark.stadium_value  # Apply the ballpark modifier
                    logger.debug(f"Step 4: Stadium value for {ballpark.ballpark_name}: {ballpark.stadium_value}")
                    logger.debug(f"Step 4a: Power bonus adjusted with ballpark ({ballpark.stadium_value}) for a total of: {power_bonus}")
                    BV += power_bonus
                else:
                    logger.debug(f"Step 4: Invalid power player or missing attributes in power_player: {power_player}")
                
                speed_bench_result = self.consult_speed_bench_chart(red_die, green_die, white_die, team)
                
                # Step 4b: Check if we got a valid player or a tuple for the bonus
                if isinstance(speed_bench_result, tuple):
                    # Handle the case where it's a tuple representing the bonus type and value
                    bonus_type, bonus_value = speed_bench_result
                    BV += bonus_value * dice_sum
                    logger.debug(f"Step 4b: Triple: {bonus_type} bonus (+{bonus_value * dice_sum})")
                    logger.debug(f"BV after speed/bench bonus: {BV}")
                else:
                    # Check if speed_bench_result contains a valid player object
                    if speed_bench_result and isinstance(speed_bench_result, tuple):
                        bonus_type, bonus_value = speed_bench_result
                        logger.debug(f"Step 4b: Speed/Bench bonus for bonus type {bonus_type} with value {bonus_value}.")
                        BV += bonus_value * dice_sum
                        logger.debug(f"Step 4b: Triple: {bonus_type} bonus (+{bonus_value * dice_sum})")
                        logger.debug(f"BV after speed/bench bonus: {BV}")
                    else:
                        logger.debug(f"Step 4b: Invalid speed/bench result or missing attributes in result: {speed_bench_result}")

            else:
                # Odd triad - Trigger injury check
                injured_player = self.injury_check(team)
                
                if injured_player and hasattr(injured_player, 'name') and hasattr(injured_player, 'injury_days'):
                    logger.info(f"Step 4c: Injury: {injured_player.name} is injured for {injured_player.injury_days} days.")
                else:
                    logger.debug(f"Step 4c: Injury check failed or invalid injured_player: {injured_player}")

        # Cap the BV at 135 after handling triples
        if BV > 135:
            BV = 135

        # Step 5: Handle individual bat bonus if the sum of dice is greater than 10
        if dice_sum > 10:
            individual_bat_player = self.find_individual_bat_player(team, dice_sum)
            if individual_bat_player:
                bat_bonus = individual_bat_player.batting
                BV += bat_bonus
                logger.debug(f"Step 5: {dice_sum} is greater than 10, applying individual bat bonus from {individual_bat_player.name}.")
                logger.debug(f"Step 5: Individual Bat Bonus: {individual_bat_player.name} adds {bat_bonus} to the Team Bat Value: {BV}.")

        # Cap the BV at 135 after individual bat bonus
        if BV > 135:
            BV = 135

        # Step 6: Handle doubles (power/speed/bench bonuses)
        if doubles:
            # consider adding an even/odd variation like i have for triples (maybe we get the eye modifier involved?)
            if white_die == red_die or white_die == green_die:
                power_player = self.consult_power_chart(white_die, red_die, green_die, team, ballpark)
                logger.debug(f"Step 6: Power bonus for {power_player.name} with a batting value of {power_player.batting}.")

                if power_player:
                    power_bonus = power_player.power * dice_sum
                    power_bonus += ballpark.stadium_value  # Apply the ballpark modifier
                    logger.debug(f"Step 6: Stadium value for {ballpark.ballpark_name}: {ballpark.stadium_value}")
                    logger.debug(f"Step 6a: Power bonus adjusted with ballpark ({ballpark.stadium_value}) for a total of: {power_bonus}")
                    BV += power_bonus
                    logger.debug(f"Step 6b: Doubles: Power bonus from {power_player.name} (+{power_bonus})")
                    logger.debug(f"BV after power bonus: {BV}")

            if red_die == green_die:
                logger.debug(f"Step 6c: Red and Green dice are the same (doubles): {red_die} == {green_die}")
                speed_bench_result = self.consult_speed_bench_chart(red_die, green_die, white_die, team)
                
                # Step 6c: Check if we got a valid player or a tuple for the bonus
                if isinstance(speed_bench_result, tuple):
                    # Handle the case where it's a tuple representing the bonus type and value
                    bonus_type, bonus_value = speed_bench_result
                    BV += bonus_value * dice_sum
                    logger.debug(f"Step 6c: Doubles: {bonus_type} bonus (+{bonus_value * dice_sum})")
                    logger.debug(f"BV after doubles bonus: {BV}")

                else:
                    # Check if speed_bench_result contains a valid player object
                    if isinstance(speed_bench_result, list) and len(speed_bench_result) > 0 and hasattr(speed_bench_result[0], 'name'):
                        logger.debug(f"Step 6c: Speed/Bench bonus for {speed_bench_result[0].name} with a batting value of {speed_bench_result[0].batting}.")
                        bonus_type, bonus_value = speed_bench_result
                        BV += bonus_value * dice_sum
                        logger.debug(f"Step 6c: Doubles: {bonus_type} bonus (+{bonus_value * dice_sum})")
                        logger.debug(f"BV after doubles bonus: {BV}")
                    else:
                        logger.debug(f"Step 6c: No valid speed/bench bonus player found or invalid data in result: {speed_bench_result}")

        # Cap the BV at 135 after handling doubles
        if BV > 135:
            BV = 135

        # Step 7: Handle relief/defense (when dice_sum <= 10)
        if dice_sum <= 10:
            logger.debug(f"Step 7: Dice sum is {dice_sum}, <= 10. Proceeding with defense.")
            logger.debug(f"Step 7a: Handling defense for dice sum {dice_sum}.")
            
            # Get fielding adjustment from the new consult_relief_defense_chart (now only for defense)
            relief_defense_result = self.consult_relief_defense_chart(dice_sum, green_die, team)
            logger.debug(f"Step 7b: Checking relief_defense_chart")
            
            fielding_value = relief_defense_result["fielding_value"]
            
            # Adjust the white die by the fielder's value
            adjusted_white_die = max(white_die + fielding_value, 1)
            logger.debug(f"Step 7c: Fielding adjustment: White die is now {adjusted_white_die} (was {white_die}, fielding {fielding_value}).")
            
            # Calculate runs based on Batting Value (BV) and the adjusted white die
            SV = opponent_pitcher.start_value
            logger.debug(f"Step 7: Opponent Pitcher Start Value SV: {SV}")
            product = SV * adjusted_white_die
            logger.debug(f"Step 7: Product of SV {SV} * white_die {white_die}: {product}")
            if product < 6:
                product = 6  # Ensure total defense is at least 6
            runs = BV // product
            logger.debug(f"Step 7d: Defense handled. BV: {BV} / {product}  Runs scored: {runs}")

        # Step 8: Calculate runs based on BV and SV (earned runs calculation)
        SV = opponent_pitcher.start_value
        logger.debug(f"Step 8: Opponent Pitcher Start Value SV: {SV}")
        product = SV * white_die
        logger.debug(f"Step 8: Product of SV {SV} * white_die {white_die}: {product}")
        if product < 6:
            product = 6
        earned_runs = BV // product
        logger.debug(f"Step 8: BV: {BV} / {product} = Earned runs scored: {earned_runs}")

        # Step 9: Calculate unearned runs if sum of dice is 10 or less
        unearned_runs = 0
        logger.debug(f"Step 9: Checking if dice_sum {dice_sum} is <= 10.")
        if dice_sum <= 10:
            logger.debug(f"Dice sum {dice_sum} is <= 10, fetching unearned runs.")
            unearned_runs = team.get_unearned_runs(dice_sum)
            logger.debug(f"Step 9: Unearned runs retrieved for dice_sum {dice_sum}: {unearned_runs}")
        else:
            logger.debug(f"Dice sum {dice_sum} is greater than 10, no unearned runs to fetch.")

        # Step 10: Final earned and unearned runs total and assigning runs to relievers
        total_earned_runs = earned_runs
        total_unearned_runs = unearned_runs
        total_runs = total_earned_runs + total_unearned_runs  # Maintain the total_runs value for other calculations
        logger.debug(f"Step 10: Final earned runs: {total_earned_runs}, unearned runs: {total_unearned_runs}, total runs: {total_runs}")

        # Step 10a: Calculate runs assigned to the starter
        starter_earned_runs, starter_unearned_runs, starter_innings = self.calculate_runs_for_starter(total_earned_runs, total_unearned_runs, opponent_pitcher, relief_pitching, current_day)

        # If the starter's innings were reduced, recalculate the bullpen innings and get the distribution
        if starter_innings < 9.0:
            logger.debug("Starter innings were reduced, recalculating relief innings.")
            reliever_innings_distribution = self.recalculate_relief_innings(starter_innings, relief_pitching, current_day)
        else:
            reliever_innings_distribution = {}

        # Step 10b: Remaining runs to distribute among relievers
        remaining_earned_runs = total_earned_runs - starter_earned_runs
        remaining_unearned_runs = total_unearned_runs - starter_unearned_runs

        earned_runs_distribution, unearned_runs_distribution = {}, {}
        # Distribute runs among relievers if relief_pitching was processed and relievers were chosen
        if relief_pitching and chosen_relievers:
            earned_runs_distribution, unearned_runs_distribution = relief_pitching.distribute_runs_among_relievers(
                chosen_relievers, remaining_earned_runs, remaining_unearned_runs, current_day, fatigue_cache
            )
            logger.debug(f"Step 10: Distributed earned runs among relievers: {earned_runs_distribution}")
            logger.debug(f"Step 10: Distributed unearned runs among relievers: {unearned_runs_distribution}")

        # Return the total runs as before, since other calculations might still rely on total runs
        return total_runs, total_relief_value, starter_innings, reliever_innings_distribution, earned_runs_distribution, unearned_runs_distribution, chosen_relievers

    def get_available_relievers_for_extras(self, team, used_relievers):
        """
        Return available relievers for extra innings, excluding those who have already pitched.
        """
        used_relievers = self.used_relievers_home if team == self.home_team else self.used_relievers_away
        available_relievers = [
            p for p in team.pitchers 
            if p.type == 'Reliever' and p not in used_relievers
        ]
        
        logger.debug(f"Available relievers for {team.team_name} (excluding those already used): {[p.name for p in available_relievers]}")
        
        return available_relievers

    def handle_extra_innings(self):
        logger.debug("Game tied, proceeding to extra innings...")

        # Roll the dice for both teams
        visiting_red_die, visiting_green_die = self.dice.roll(), self.dice.roll()
        home_red_die, home_green_die = self.dice.roll(), self.dice.roll()

        # Create two-digit numbers for both teams to select batters
        visiting_two_digit = int(f"{visiting_red_die}{visiting_green_die}")
        home_two_digit = int(f"{home_red_die}{home_green_die}")

        logger.debug(f"Visiting team's two-digit number: {visiting_two_digit}")
        logger.debug(f"Home team's two-digit number: {home_two_digit}")

        # Select batters for extra innings
        visiting_batter = self.away_team.get_batter_for_extra_innings(visiting_two_digit)
        home_batter = self.home_team.get_batter_for_extra_innings(home_two_digit)

        logger.debug(f"Visiting team's selected batter: {visiting_batter.name}, Batting: {visiting_batter.batting}, Clutch: {visiting_batter.clutch}")
        logger.debug(f"Home team's selected batter: {home_batter.name}, Batting: {home_batter.batting}, Clutch: {home_batter.clutch}")

        # Get available relievers for extra innings (excluding those already used)
        available_relievers_away = self.get_available_relievers_for_extras(self.away_team, self.used_relievers_away)
        available_relievers_home = self.get_available_relievers_for_extras(self.home_team, self.used_relievers_home)

        # Handle away team relievers
        if not available_relievers_away:
            last_used_away = self.away_team.get_last_used_reliever(self.used_relievers_away)
            if last_used_away:
                # Apply fatigue penalty and clutch rating to relief value
                visiting_reliever_value = max(last_used_away.relief_value - self.calculate_fatigue_penalty(last_used_away) + last_used_away.clutch, 0)
                logger.debug(f"Using last used away reliever: {last_used_away.name} with penalty-adjusted relief value: {visiting_reliever_value} (Clutch: {last_used_away.clutch})")
            else:
                logger.debug("No relievers available, visiting reliever value defaults to 0")
                visiting_reliever_value = 0
        else:
            # Get best reliever value and adjust with clutch
            best_reliever_away = max(available_relievers_away, key=lambda r: r.relief_value)
            visiting_reliever_value = best_reliever_away.relief_value + best_reliever_away.clutch
            logger.debug(f"Visiting team's best reliever: {best_reliever_away.name}, Relief Value: {best_reliever_away.relief_value}, Clutch: {best_reliever_away.clutch}")
        
        # Handle home team relievers
        if not available_relievers_home:
            last_used_home = self.home_team.get_last_used_reliever(self.used_relievers_home)
            if last_used_home:
                # Apply fatigue penalty and clutch rating to relief value
                home_reliever_value = max(last_used_home.relief_value - self.calculate_fatigue_penalty(last_used_home) + last_used_home.clutch, 0)
                logger.debug(f"Using last used home reliever: {last_used_home.name} with penalty-adjusted relief value: {home_reliever_value} (Clutch: {last_used_home.clutch})")
            else:
                logger.debug("No relievers available, home reliever value defaults to 0")
                home_reliever_value = 0
        else:
            # Get best reliever value and adjust with clutch
            best_reliever_home = max(available_relievers_home, key=lambda r: r.relief_value)
            home_reliever_value = best_reliever_home.relief_value + best_reliever_home.clutch
            logger.debug(f"Home team's best reliever: {best_reliever_home.name}, Relief Value: {best_reliever_home.relief_value}, Clutch: {best_reliever_home.clutch}")

        logger.debug(f"Visiting team's best reliever value (after clutch): {visiting_reliever_value}")
        logger.debug(f"Home team's best reliever value (after clutch): {home_reliever_value}")

        # Calculate extra-inning values
        visiting_special_value = visiting_batter.batting + visiting_batter.clutch - home_reliever_value
        home_special_value = home_batter.batting + home_batter.clutch - visiting_reliever_value

        logger.debug(f"Visiting team's special value: {visiting_special_value}")
        logger.debug(f"Home team's special value: {home_special_value}")

        # Determine the winner based on special values
        if visiting_special_value > home_special_value:
            logger.debug(f"Visiting team wins in extra innings!")
            return 'visiting'
        elif home_special_value > visiting_special_value:
            logger.debug(f"Home team wins in extra innings!")
            return 'home'
        else:
            return self.break_tie_in_extra_innings()


    def calculate_fatigue_penalty(self, reliever):
        """
        Calculate the fatigue penalty based on the reliever's fatigue rating.
        """
        if reliever.fatigue >= 7:
            return 1  # Lose 1 relief value point
        elif reliever.fatigue >= 5:
            return 2  # Lose 2 relief value points
        elif reliever.fatigue >= 3:
            return 3  # Lose 3 relief value points
        else:
            return 4  # Lose 4 relief value points

    def break_tie_in_extra_innings(self):
        # If the special values are tied, we resolve using the green, red, and white dice in that order
        logger.debug("Extra innings are still tied, resolving with dice BV additions...")

        # Add green die to each team’s BV and compare
        green_die = self.dice.roll()

        # Visiting team BV only gets the green die value
        visiting_bv = green_die

        # Home team BV gets the green die value plus home field advantage
        home_bv = green_die + self.home_team.home_field_advantage

        logger.debug(f"Visiting team BV + green die: {visiting_bv}")
        logger.debug(f"Home team BV + green die + home field advantage: {home_bv}")

        if visiting_bv > home_bv:
            logger.debug(f"Visiting team wins by green die adjustment!")
            return 'visiting'
        elif home_bv > visiting_bv:
            logger.debug(f"Home team wins by green die and home field advantage!")
            return 'home'
        else:
            # If still tied, add red die
            red_die = self.dice.roll()
            visiting_bv += red_die
            home_bv += red_die

            logger.debug(f"Visiting team BV + red die: {visiting_bv}")
            logger.debug(f"Home team BV + red die: {home_bv}")

            if visiting_bv > home_bv:
                logger.debug(f"Visiting team wins by red die adjustment!")
                return 'visiting'
            elif home_bv > visiting_bv:
                logger.debug(f"Home team wins by red die adjustment!")
                return 'home'
            else:
                # If still tied, add white die
                white_die = self.dice.roll()
                visiting_bv += white_die
                home_bv += white_die

                logger.debug(f"Visiting team BV + white die: {visiting_bv}")
                logger.debug(f"Home team BV + white die: {home_bv}")

                if visiting_bv > home_bv:
                    logger.debug(f"Visiting team wins by white die adjustment!")
                    return 'visiting'
                else:
                    logger.debug(f"Home team wins by white die adjustment!")
                    return 'home'

    def get_best_relief_value(self, team):
        # Find the best reliever who hasn’t been used yet
        available_relievers = [p for p in team.pitchers if p.relief_value is not None]
        logger.debug(f"Available relievers for {team.team_name}: {[p.name for p in available_relievers]}")
        if available_relievers:
            best_relief_value = max(available_relievers, key=lambda p: p.relief_value).relief_value
            return best_relief_value
        else:
            return -6  # No reliever available, subtract 6 as per the rules

    def find_winning_reliever(self, team, used_relievers, reliever_innings_distribution, earned_runs_distribution):
        # Filter relievers who have actually pitched (convert innings to float for comparison)
        relievers = [reliever for reliever in used_relievers if float(reliever_innings_distribution.get(reliever.name, 0)) > 0]

        # Sort relievers by total relief value (higher is better), innings pitched (higher is better), and runs allowed (lower is better)
        if relievers:
            sorted_relievers = sorted(
                relievers,
                key=lambda r: (
                    -r.total_relief_value,  # Sort by higher total relief value
                    -float(reliever_innings_distribution.get(r.name, 0)),  # Sort by higher innings pitched
                    earned_runs_distribution.get(r.name, 0)  # Sort by lower runs allowed
                )
            )
            # Return the top reliever after sorting
            return sorted_relievers[0]

        # If no reliever qualifies, return None
        return None

    def find_losing_reliever(self, team, used_relievers, reliever_innings_distribution, earned_runs_distribution):
        # Filter relievers who have allowed runs (convert innings to float for comparison)
        relievers = [reliever for reliever in used_relievers if float(earned_runs_distribution.get(reliever.name, 0)) > 0]

        # Sort relievers by runs allowed (higher is worse), innings pitched (higher is better), and relief value (lower is worse)
        if relievers:
            sorted_relievers = sorted(
                relievers,
                key=lambda r: (
                    -earned_runs_distribution.get(r.name, 0),  # Sort by more runs allowed (higher first)
                    -float(reliever_innings_distribution.get(r.name, 0)),  # Sort by more innings pitched (higher is better)
                    r.total_relief_value  # Sort by lower total relief value (worse)
                )
            )
            # Return the top reliever after sorting
            return sorted_relievers[0]

        # If no reliever qualifies, return None
        return None


    def determine_pitcher_decision(self, away_pitcher, home_pitcher):
        # Use already calculated runs and innings
        away_runs = self.result['away_runs']
        home_runs = self.result['home_runs']

        # Assume we have stored away/home starter innings and runs in self.result or similar
        away_starter_innings = self.result.get('away_starter_innings')
        home_starter_innings = self.result.get('home_starter_innings')

        # If innings data is not stored, log an error and exit
        if away_starter_innings is None or home_starter_innings is None:
            logger.error("Starter innings for away/home not available in result.")
            return

        # Determine if the starter qualifies for the decision
        if away_starter_innings >= 5:
            away_pitcher.decision = 'W' if away_runs > home_runs else 'L'
        else:
            away_pitcher.decision = None

        if home_starter_innings >= 5:
            home_pitcher.decision = 'W' if home_runs > away_runs else 'L'
        else:
            home_pitcher.decision = None

        # If neither starter qualifies for the win/loss, find the relievers with the decision
        winning_reliever, losing_reliever = None, None

        if away_pitcher.decision is None:
            winning_reliever = self.find_winning_reliever(self.away_team, self.used_relievers_away, 
                                                        self.result['away_reliever_innings_distribution'], 
                                                        self.result['away_reliever_earned_runs'])

        if home_pitcher.decision is None:
            losing_reliever = self.find_losing_reliever(self.home_team, self.used_relievers_home, 
                                                        self.result['home_reliever_innings_distribution'], 
                                                        self.result['home_reliever_earned_runs'])

        # If the game outcome requires the opposite reliever for win/loss
        if home_pitcher.decision is None and winning_reliever is None:
            winning_reliever = self.find_winning_reliever(self.home_team, self.used_relievers_home, 
                                                        self.result['home_reliever_innings_distribution'], 
                                                        self.result['home_reliever_earned_runs'])

        if away_pitcher.decision is None and losing_reliever is None:
            losing_reliever = self.find_losing_reliever(self.away_team, self.used_relievers_away, 
                                                        self.result['away_reliever_innings_distribution'], 
                                                        self.result['away_reliever_earned_runs'])

        # Log the final decisions
        logger.info(f"Winning Pitcher: {winning_reliever.name if winning_reliever else away_pitcher.name}")
        logger.info(f"Losing Pitcher: {losing_reliever.name if losing_reliever else home_pitcher.name}")

        return winning_reliever, losing_reliever

    def determine_save_situation(self, winning_reliever, chosen_relievers, is_extra_innings, starter_innings, reliever_innings_distribution, winning_team, home_runs, away_runs):
        """
        Determine if a reliever is eligible for a save and award it if appropriate.
        """

        # 1. Check if the game went into extra innings; if so, no save is possible.
        if is_extra_innings:
            return None

        # 1. Check if the starter finished 9 innings. If they did, no save is possible.
        if starter_innings == 9.0:
            return None

        # 2. Check if the score difference is 3 or less
        score_diff = abs(home_runs - away_runs)
        if score_diff > 3:
            return None

        # 2. Only consider relievers from the winning team
        team_relievers = chosen_relievers
        logger.debug(f"Winning Team: {winning_team}")
        logger.debug(f"Chosen Relievers: {chosen_relievers}")
        logger.debug(f"Team Relievers: {team_relievers}")

        # 3. Remove the reliever who got the win from consideration for the save
        eligible_relievers = [reliever for reliever in team_relievers if reliever != winning_reliever]
        logger.debug(f"Eligible Relievers: {eligible_relievers}")

        # 4. Check if any relievers pitched at least 3 innings (automatic save qualification)
        long_relievers = [
            reliever for reliever in eligible_relievers 
            if float(reliever_innings_distribution.get(reliever.name, "0.0")) >= 3
        ]
        logger.debug(f"Long Relievers: {long_relievers}")

        # 5. Check if there are eligible relievers remaining
        if not eligible_relievers:
            logger.debug("No eligible relievers for the save.")
            return None  # No relievers available, so no save can be awarded

        # 5. If a reliever pitched 3 or more innings, they get the save
        if long_relievers:
            best_reliever = max(long_relievers, key=lambda reliever: reliever.relief_value)
        else:
            # Otherwise, select the best eligible reliever based on relief value or performance metrics
            best_reliever = max(eligible_relievers, key=lambda reliever: reliever.relief_value)

        # 5. Award the save to the best reliever
        # best_reliever.award_save()
        logger.debug(f"Save awarded to {best_reliever.name}")

    def play_game(self, current_day):
        # Ensure self.day (current_day) is not None
        if self.day is None:
            logger.debug(f"Warning: Game day (self.day) is None. Defaulting to day 0.")
            self.day = 0

        # Step 1: Initialize used relievers lists
        self.used_relievers_away = []
        self.used_relievers_home = []

        # Step 2: Select starting pitchers once and store them
        away_pitcher = self.away_team.select_starting_pitcher(self.day)
        home_pitcher = self.home_team.select_starting_pitcher(self.day)

        # Handle pitchers' first start (if last_start_day is None or 0)
        if away_pitcher.last_start_day == 0:
            away_pitcher.last_start_day = None
        if home_pitcher.last_start_day == 0:
            home_pitcher.last_start_day = None

        # Add pitchers' handedness (throws) to the result
        self.result['away_pitcher_throws'] = away_pitcher.throws
        self.result['home_pitcher_throws'] = home_pitcher.throws

        # Step 3: Resolve runs for visiting team and store runs and reliever stats
        away_runs, away_total_relief_value, away_starter_innings, away_reliever_innings_distribution, away_earned_runs_distribution, away_unearned_runs_distribution, away_chosen_relievers = self.resolve_team_runs(
            self.away_team, home_pitcher, current_day, is_visiting=True)
        self.result['away_runs'] = away_runs
        self.result['away_total_relief_value'] = away_total_relief_value  # Store total relief value
        self.result['away_starter_innings'] = away_starter_innings
        self.result['away_reliever_innings_distribution'] = away_reliever_innings_distribution  # Store reliever innings from recalculation
        self.result['away_reliever_earned_runs'] = away_earned_runs_distribution
        self.result['away_reliever_unearned_runs'] = away_unearned_runs_distribution
        self.result['away_chosen_relievers'] = away_chosen_relievers  # Store chosen relievers

        # Step 4: Resolve runs for home team and store runs and reliever stats
        home_runs, home_total_relief_value, home_starter_innings, home_reliever_innings_distribution, home_earned_runs_distribution, home_unearned_runs_distribution, home_chosen_relievers = self.resolve_team_runs(
            self.home_team, away_pitcher, current_day, is_visiting=False)
        self.result['home_runs'] = home_runs
        self.result['home_total_relief_value'] = home_total_relief_value  # Store total relief value
        self.result['home_starter_innings'] = home_starter_innings
        self.result['home_reliever_innings_distribution'] = home_reliever_innings_distribution  # Store reliever innings from recalculation
        self.result['home_reliever_earned_runs'] = home_earned_runs_distribution
        self.result['home_reliever_unearned_runs'] = home_unearned_runs_distribution
        self.result['home_chosen_relievers'] = home_chosen_relievers  # Store chosen relievers

        # Step 5: Check if it's a one-run game
        self.result['is_one_run'] = abs(home_runs - away_runs) == 1

        # Step 6: If tied at the end, proceed to extra innings
        if home_runs == away_runs:
            self.result['is_extra_innings'] = True
            winner = self.handle_extra_innings()
            if winner == 'home':
                self.result['home_runs'] += 1
            else:
                self.result['away_runs'] += 1
        else:
            self.result['is_extra_innings'] = False

        # Determine the winning team based on the final score
        if home_runs > away_runs:
            winning_team = self.home_team
            chosen_relievers = self.result['home_chosen_relievers']
            starter_innings = self.result['home_starter_innings']
            reliever_innings_distribution = self.result['home_reliever_innings_distribution']
            logger.debug(f"Winning team (home): {winning_team.team_name}")
        else:
            winning_team = self.away_team
            chosen_relievers = self.result['away_chosen_relievers']
            starter_innings = self.result['away_starter_innings']
            reliever_innings_distribution = self.result['away_reliever_innings_distribution']
            logger.debug(f"Winning team (away): {winning_team.team_name}")

        # Log final game result
        logger.info(f"Game Day {self.day}: {self.away_team.team_name} {self.result['away_runs']} - "
                    f"{self.home_team.team_name} {self.result['home_runs']} "
                    f"(SP {self.away_team.team_name}: {away_pitcher.name}, SP {self.home_team.team_name}: {home_pitcher.name})")

        # Determine pitcher decision (win/loss for starters or relievers)
        winning_reliever, losing_reliever = self.determine_pitcher_decision(away_pitcher, home_pitcher)

        # Check if the game went into extra innings
        is_extra_innings = self.result.get('is_extra_innings', False)

        # Finally, check if a save can be awarded for the winning team
        self.determine_save_situation(
            winning_reliever=winning_reliever,
            chosen_relievers=chosen_relievers,
            is_extra_innings=is_extra_innings,
            starter_innings=starter_innings,
            reliever_innings_distribution=reliever_innings_distribution,
            winning_team=winning_team,
            home_runs=self.result['home_runs'],  # Pass home_runs
            away_runs=self.result['away_runs']   # Pass away_runs
        )


        # Step 8: Update last start day for both starting pitchers
        home_pitcher.last_start_day = current_day
        away_pitcher.last_start_day = current_day

        return self.result

class Team:
    def __init__(self, team_id, team_name, pitchers, players, unearned_runs_chart=None, stadium_value=0, home_field_advantage=0, weather_value=0, minors=0, budget=0, ballpark_name="", ballpark_capacity=0, ballpark_weather=""):
        self.team_id = team_id
        self.team_name = team_name
        self.pitchers = pitchers if pitchers else []
        self.current_rotation_index = 0  # Track the current pitcher in the rotation  
        self.players = players if players else []
        self.transactions = []
        self.injuries = []
        self.stadium_value = stadium_value  # Used in Park Effects
        self.home_field_advantage = home_field_advantage  # Used in Park Effects
        self.weather_value = weather_value  # Used in Weather Effects
        self.minors = minors  # minor league system rating
        self.budget = budget  # Budget for player acquisition
        self.current_day = 0  # Track days for pitcher rest
        self.unearned_runs_chart = unearned_runs_chart if unearned_runs_chart is not None else {str(i): 0 for i in range(3, 11)}
        logger.debug(f"Initialized unearned_runs_chart: {self.unearned_runs_chart}")

        # Instantiate Ballpark object for the team
        self.ballpark = Ballpark(ballpark_name, ballpark_capacity, ballpark_weather, stadium_value)

    def save_team_data(self, file_name=None):
        """Save the team's data to a JSON file."""
        if file_name is None:
            file_name = f'team_id_{self.team_id}_data.json'
        file_path = os.path.join(BASE_DIRECTORY, file_name)
        with open(file_path, 'w') as file:
            json.dump({
                'team_name': self.team_name,
                'players': [p.__dict__ for p in self.players],
                'pitchers': [p.__dict__ for p in self.pitchers],
                'transactions': self.transactions,
                'injuries': self.injuries
            }, file, indent=4)
    
    def load_team_data(self, file_path):
        """Load the team's data from a JSON file."""
        with open(file_path, 'r') as file:
            data = json.load(file)

        # Set other team attributes
        self.team_name = data['team_name']
        self.pitchers = [Pitcher(**p) for p in data['pitchers']]
        self.players = [Player(**p) for p in data['players']]
        self.transactions = data.get('transactions', [])
        self.injuries = data.get('injuries', [])

        # Explicitly set unearned_runs_chart
        self.unearned_runs_chart = data.get('unearned_runs_chart', {str(i): 0 for i in range(3, 11)})
        logger.debug(f"Loaded unearned_runs_chart: {self.unearned_runs_chart}")

    def select_starting_pitcher(self, current_day):
        # Ensure rotation index is constrained to starters only (1-5)
        num_starters = min(5, len(self.pitchers))  # In case a team has less than 5 starters
        
        # Stick to strict rotation, only selecting among the first 5 pitchers
        selected_pitcher = self.pitchers[self.current_rotation_index % num_starters]
        
        # Log the selected pitcher's details for debugging
        logger.debug(f"Checking pitcher: {selected_pitcher.name} for team {self.team_name}")
        logger.debug(f"current_day: {current_day}, last_start_day: {selected_pitcher.last_start_day}, rest: {selected_pitcher.rest}, start_value: {selected_pitcher.start_value}, endurance: {selected_pitcher.endurance}")
        
        # Update the rotation index (1-5 loop only)
        self.current_rotation_index = (self.current_rotation_index + 1) % num_starters
        
        logger.debug(f"{self.current_rotation_index} is the current rotation index")
        logger.debug(f"Selected starter: {selected_pitcher.name} for team {self.team_name}")
        
        return selected_pitcher

    def get_last_used_reliever(self, used_relievers):
        """
        Get the last used reliever from the list of used relievers.
        """
        if used_relievers:
            # Return the last reliever in the used_relievers list
            return used_relievers[-1]
        else:
            logger.error(f"No relievers have been used yet for {self.team_name}.")
            return None

    def get_available_relievers(self, current_day):
        available_relievers = []
        for pitcher in self.pitchers:
            if pitcher.type == 'Reliever':  # Only look at relievers
                logger.debug(f"Checking reliever: {pitcher.name}")
                logger.debug(f"current_day: {current_day}, last_relief_day: {pitcher.last_relief_day}, fatigue: {pitcher.fatigue}, relief_value: {pitcher.relief_value}")
                
                # Initialize last_relief_day if it's None
                if pitcher.last_relief_day is None:
                    pitcher.last_relief_day = 0  # Default to 0 if uninitialized
                    logger.debug(f"Reliever {pitcher.name} had an uninitialized last_relief_day. Set to 0.")
                
                # Check if reliever is available based on custom logic, e.g., not used for 3 consecutive days
                days_since_last_relief = current_day - pitcher.last_relief_day
                if days_since_last_relief > 0:  # Customize this condition as needed
                    available_relievers.append(pitcher)

        if not available_relievers:
            logger.debug(f"No rested relievers for team {self.team_name} on day {current_day}.")
        return available_relievers

    def get_batting_value(self, opponent_pitcher):
        """
        Calculate the team's batting value dynamically based on the handedness of the opponent pitcher.
        For each player: Batting Value = batting + eye (+ player-specific handedness modifier)
        """
        total_batting_value = 0
        
        for player in self.players:
            if player.role == 'Starter':  # Assuming only starters contribute to batting value
                # Calculate base batting value as batting + eye + a fraction of power
                player_bv = player.batting + player.eye + (player.power * 0.6)

                # Initialize default modifiers
                batter_modifier = 0
                pitcher_modifier = 0

                logger.debug(f"Line 1217 Opponent pitcher {opponent_pitcher.name} splits_L: {opponent_pitcher.splits_L}, splits_R: {opponent_pitcher.splits_R}")

                # Check handedness and apply split ratings based on the opponent pitcher
                if opponent_pitcher.throws == 'L':  # Facing a left-handed pitcher
                    if player.bats == 'L':
                        batter_modifier = player.splits_L  # Player's rating against left-handed pitchers
                        pitcher_modifier = opponent_pitcher.splits_L
                    elif player.bats == 'R':
                        batter_modifier = player.splits_L  # Player's rating against right-handed pitchers
                        pitcher_modifier = opponent_pitcher.splits_R
                    elif player.bats == 'S':
                        batter_modifier = 0  # Switch hitter gets no handedness adjustment
                        pitcher_modifier = 0
                elif opponent_pitcher.throws == 'R':  # Facing a right-handed pitcher
                    if player.bats == 'L':
                        batter_modifier = player.splits_R  # Player's rating against right-handed pitchers
                        pitcher_modifier = opponent_pitcher.splits_L
                    elif player.bats == 'R':
                        batter_modifier = player.splits_R  # Player's rating against left-handed pitchers
                        pitcher_modifier = opponent_pitcher.splits_R
                    elif player.bats == 'S':
                        batter_modifier = 0  # Switch hitter gets no handedness adjustment
                        pitcher_modifier = 0

                # Adjust player batting value by batter's split and pitcher's split modifier
                player_bv += batter_modifier - pitcher_modifier
                logger.debug(f"LINE 1239 Player {player.name} batting value: {player_bv}, Batter Modifier: {batter_modifier}, Pitcher Modifier: {pitcher_modifier}")

                # Clamp player_bv to a minimum of 0
                player_bv = max(0, player_bv)

                # Add player's final BV to the total batting value
                total_batting_value += player_bv

        return total_batting_value

    def get_lineup_position(self, dice_number):
        """Return the lineup position based on the two-digit dice roll."""
        dice_map = {
            range(11, 13): 1,   # 11-12
            range(13, 15): 2,   # 13-14
            range(15, 17): 3,   # 15-16
            range(21, 23): 4,   # 21-22
            range(23, 25): 5,   # 23-24
            range(25, 27): 6,   # 25-26
            range(31, 33): 7,   # 31-32
            range(33, 35): 8,   # 33-34
            range(35, 37): 9,   # 35-36
            range(41, 44): 10,  # 41-43
            range(44, 47): 11,  # 44-46
            range(51, 54): 12,  # 51-53
            range(54, 57): 13,  # 54-56
            range(61, 64): 14,  # 61-63
            range(64, 67): 15   # 64-66
        }
        
        for dice_range, position in dice_map.items():
            if dice_number in dice_range:
                return position
        raise ValueError(f"Invalid dice number: {dice_number}")

    def get_batter_for_extra_innings(self, dice_number):
        """Get the player based on the lineup position corresponding to the dice roll."""
        lineup_position = self.get_lineup_position(dice_number)
        return self.players[lineup_position - 1]  # assuming lineup positions are 1-based

    def get_unearned_runs(self, dice_sum):
        # Log the dice_sum and the current unearned_runs_chart
        logger.debug(f"get_unearned_runs called with dice_sum: {dice_sum}")
        logger.debug(f"Current unearned_runs_chart for {self.team_name}: {self.unearned_runs_chart}")
        
        # Ensure dice_sum is within the expected range
        if not (3 <= dice_sum <= 10):
            logger.debug(f"Warning: dice_sum {dice_sum} is outside the valid range (3-10). Returning 0.")
            return 0

        # Convert dice_sum to string for lookup and perform lookup in the chart
        unearned_runs = self.unearned_runs_chart.get(str(dice_sum), 0)

        # Log the result of the lookup
        logger.debug(f"Unearned runs for dice_sum {dice_sum}: {unearned_runs}")
        
        return unearned_runs

class Player:
    def __init__(self, role, name, batting=0, power=0, speed=0, fielding=0, position=None, sec_position=None, bats='R', clutch=0, injury=0, salary=0, eye=0, splits_L=0, splits_R=0):
        self.name = name
        self.role = role
        self.position = position
        self.sec_position = sec_position
        self.batting = batting
        self.power = power
        self.eye = eye
        self.splits_L = splits_L
        self.splits_R = splits_R
        self.speed = speed
        self.fielding = fielding
        self.bats = bats # R, L or B
        self.clutch = clutch
        self.injury = injury
        self.salary = salary

class Pitcher:
    def __init__(self, name, type, start_value, endurance, rest, relief_value, fatigue, cg_rating=666, sho_rating=666, throws='R', clutch=0, injury=0, salary=0, splits_L=0, splits_R=0):
        self.name = name
        self.throws = throws  # Handedness (R or L)
        self.type = type  # "SP" for starter or "RP" for reliever
        self.start_value = start_value  # Starting value (pitching quality)
        self.endurance = endurance  # How long they can pitch in a game
        self.rest = rest  # Days required between starts/appearances
        self.cg_rating = cg_rating
        self.sho_rating = sho_rating
        self.splits_L = splits_L
        self.splits_R = splits_R
        self.relief_value = relief_value  # Relief value
        self.fatigue = fatigue
        self.last_start_day = None  # Initialize to allow immediate start
        self.last_relief_day = None  # Initialize as None for relievers
        self.clutch = clutch
        self.injury = injury  # Injury status
        self.morale = 0
        self.salary = salary  # Salary

class ReliefPitching:
    def __init__(self, opponent_pitcher, team, dice, game, splits_L=0, splits_R=0, used_relievers=None):
        self.opponent_pitcher = opponent_pitcher
        self.team = team
        self.dice = dice  # The rolled dice values
        self.game = game
        self.splits_L = splits_L
        self.splits_R = splits_R
        self.fatigue_cache = {}
        
        # Keep track of relievers used in the game
        if used_relievers is None:
            self.used_relievers = []
        else:
            self.used_relievers = used_relievers

    def innings_pitched_by_bullpen(self):
        """Determine the number of innings pitched by the bullpen based on the starter's endurance and the white die."""
        white_die = self.dice[0]  # Assuming the dice are passed as a tuple (white, red, green)
        endurance = self.opponent_pitcher.endurance

        # Innings Pitched chart with grouped endurance values, dice read 6, 5, 4, 3, 2, 1
        innings_pitched_chart = {
            (0.5, 1.0): [3, 3.1, 3.2, 4, 4.1, 4.2],
            (1.5, 2.0): [2.2, 3, 3.1, 3.2, 4, 4.1],
            (2.5, 3.0): [2.1, 2.2, 3, 3.1, 3.2, 4],
            (3.5, 4.0): [2, 2.1, 2.2, 3, 3.1, 3.2],
            (4.5, 5.0): [1.2, 2, 2.1, 2.2, 3, 3.1],
            (5.5, 6.0): [1.1, 1.2, 2, 2.1, 2.2, 3],
            (6.5, 7.0): [1, 1.1, 1.2, 2, 2.1, 2.2],
            (7.5, 8.0): [0.2, 1, 1.1, 1.2, 2, 2.1]
        }

        # Find the corresponding innings pitched chart for the given endurance
        for endurance_range, innings_list in innings_pitched_chart.items():
            if endurance_range[0] <= endurance <= endurance_range[1]:
                # Reverse the white die roll: 6 -> 0, 5 -> 1, ..., 1 -> 5
                adjusted_white_die = 6 - white_die
                bullpen_innings = innings_list[adjusted_white_die]
                logger.debug(f"LINE 1250: Relief pitching: {bullpen_innings} innings pitched by the bullpen (Endurance: {endurance}, White die: {white_die})")
                return bullpen_innings

        logger.error(f"Invalid endurance value: {endurance}")
        return 0
        
    def update_last_relief_day(self, reliever, current_day):
        """Update the last relief day after a reliever is used."""
        reliever.last_relief_day = current_day

    def number_of_relievers_used(self, bullpen_innings):
        """Determine the number of relievers based on the bullpen innings and red die."""
        red_die = self.dice[1]
        
        # Relievers to Use chart (cross-referenced by bullpen innings and red die)
        relievers_chart = {
            4.2: [4, 4, 4, 4, 5, 5],
            4.1: [3, 4, 4, 4, 4, 5],
            4:   [3, 3, 4, 4, 4, 4],
            3.2: [3, 3, 3, 4, 4, 4],
            3.1: [2, 3, 3, 3, 4, 4],
            3:   [2, 2, 3, 3, 3, 4],
            2.2: [2, 2, 2, 3, 3, 3],
            2.1: [2, 2, 2, 2, 3, 3],
            2:   [1, 2, 2, 2, 2, 3],
            1.2: [1, 1, 2, 2, 2, 2],
            1.1: [1, 1, 1, 2, 2, 2],
            1:   [1, 1, 1, 1, 2, 2],
            0.2: [1, 1, 1, 1, 1, 2],
            0.1: [1, 1, 1, 1, 1, 1],
        }

        # Check if bullpen_innings exceeds chart, use 5 relievers if so
        if bullpen_innings >= 5.0:
            logger.debug(f"LINE 1282 Bullpen innings {bullpen_innings} exceed chart max, defaulting to 5 relievers.")
            return 5

        if bullpen_innings in relievers_chart:
            relievers_used = relievers_chart[bullpen_innings][red_die - 1]
            logger.debug(f"LINE 1287: Relief pitching: {relievers_used} relievers used (Bullpen innings: {bullpen_innings}, Red die: {red_die})")
            return relievers_used
        else:
            logger.error(f"Invalid bullpen innings: {bullpen_innings}")
            return 0

    def get_fatigue_multiplier(self, reliever, current_day, fatigue_cache):
        if reliever not in fatigue_cache:
            fatigue_cache[reliever] = self.apply_fatigue(reliever, current_day)
        return fatigue_cache[reliever]

    def calculate_relief_value(self, relievers_used, current_day, fatigue_cache):
        available_relievers = sorted(
            [p for p in self.team.pitchers if p.type == 'Reliever' and p not in self.used_relievers],
            key=lambda p: p.relief_value * self.get_fatigue_multiplier(p, current_day, fatigue_cache),
            reverse=True
        )

        chosen_relievers = available_relievers[:relievers_used]
        logger.debug(f"LINE 1308: Relief pitching: Chosen relievers: {[r.name for r in chosen_relievers]}")
        self.used_relievers.extend(chosen_relievers)

        # Output each reliever's relief value before summing
        individual_relief_values = {}
        for reliever in chosen_relievers:
            reliever_total_value = reliever.relief_value * fatigue_cache[reliever]
            individual_relief_values[reliever.name] = reliever_total_value
            reliever.total_relief_value = reliever_total_value
            logger.debug(f"Reliever {reliever.name} relief value: {reliever.relief_value}, "
                        f"fatigue multiplier: {fatigue_cache[reliever]}, "
                        f"total: {reliever_total_value}")

        total_relief_value = sum([r.relief_value * fatigue_cache[r] for r in chosen_relievers])
        logger.debug(f"LINE 1312: Relief pitching: Total relief value: {total_relief_value} for {relievers_used} relievers")

        for reliever in chosen_relievers:
            self.update_last_relief_day(reliever, current_day)

        fatigue_debug_info = {r.name: fatigue_cache[r] for r in chosen_relievers if r in fatigue_cache}
        logger.debug(f"LINE 1318: Relief pitching: Fatigue Cache: {fatigue_debug_info}")
        logger.debug(f"Chosen reliever total relief values: {individual_relief_values}")
        logger.debug(f"LINE 1320: Relief pitching: Total relief value after adjustments: {total_relief_value}")
        return total_relief_value, chosen_relievers

    def apply_fatigue(self, reliever, current_day):
        """Apply fatigue adjustment based on consecutive usage."""
        # If the reliever has never pitched, initialize last_relief_day to assume they are fully rested.
        if reliever.last_relief_day is None or reliever.last_relief_day == 0:
            reliever.last_relief_day = None  # Leave it as None or 0 to treat them as fully rested for the first game.
            days_since_last_relief = float('inf')  # Treat as infinitely rested if they've never pitched before.
        else:
            days_since_last_relief = current_day - reliever.last_relief_day
            reliever.last_relief_day = int(reliever.last_relief_day)  # Ensure it's an integer

        logger.debug(f"LINE 1332 Apply Fatigue: Days since last relief for {reliever.name}: {days_since_last_relief}")
        
        # Default multiplier assumes the pitcher is fully rested
        fatigue_multiplier = 1.0

        # Apply penalties based on consecutive days pitched (reverse the logic for the penalty)
        if days_since_last_relief == 0:
            # Pitched the previous day, apply full fatigue penalty (based on fatigue rating)
            fatigue_multiplier = (reliever.fatigue / 8) * 0.5  # Larger penalty
        elif days_since_last_relief == 1:
            # Pitched two consecutive days, moderate penalty
            fatigue_multiplier = (reliever.fatigue / 8) * 0.75
        elif days_since_last_relief == 2:
            # Pitched three consecutive days, small penalty
            fatigue_multiplier = reliever.fatigue / 8  # Lesser penalty

        logger.debug(f"LINE 1347 Apply Fatigue: Fatigue multiplier for {reliever.name}: {fatigue_multiplier}")

        # Return the multiplier to adjust relief value accordingly
        return float(fatigue_multiplier)

    def process_relief_pitching(self, current_day):
        # Determine bullpen innings pitched
        bullpen_innings = self.innings_pitched_by_bullpen()
        
        # Determine number of relievers used
        relievers_used = self.number_of_relievers_used(bullpen_innings)
        
        # Calculate total relief value and get chosen relievers
        total_relief_value, chosen_relievers = self.calculate_relief_value(relievers_used, current_day, self.fatigue_cache)
        
        # Update the used relievers list in the Game instance
        if self.team == self.game.home_team:
            self.game.used_relievers_home.extend(chosen_relievers)
        else:
            self.game.used_relievers_away.extend(chosen_relievers)
        
        return total_relief_value, chosen_relievers, self.fatigue_cache

    def distribute_runs_among_relievers(self, relievers, remaining_earned_runs, remaining_unearned_runs, current_day, fatigue_cache):
        # Adjust relief_value based on fatigue and calculate total relief strength
        total_relief_value = sum([self.get_fatigue_multiplier(r, current_day, fatigue_cache) for r in relievers])

        # Distribute earned runs based on each reliever's relative contribution to the total relief value
        earned_runs_distribution = {}
        unearned_runs_distribution = {}
        remaining_earned = remaining_earned_runs
        remaining_unearned = remaining_unearned_runs
        logger.debug(f"LINE 1379 Distributing {remaining_earned_runs} earned runs and {remaining_unearned_runs} unearned runs among relievers.")

        for i, reliever in enumerate(relievers):
            adjusted_value = self.get_fatigue_multiplier(reliever, current_day, fatigue_cache)

            # For the last reliever, assign all remaining earned and unearned runs to avoid rounding errors
            if i == len(relievers) - 1:
                reliever_earned_runs = remaining_earned
                reliever_unearned_runs = remaining_unearned
            else:
                reliever_earned_runs = round(remaining_earned * (adjusted_value / total_relief_value))
                reliever_unearned_runs = round(remaining_unearned * (adjusted_value / total_relief_value))

            # Distribute earned and unearned runs to relievers
            earned_runs_distribution[reliever.name] = reliever_earned_runs
            unearned_runs_distribution[reliever.name] = reliever_unearned_runs

            # Subtract assigned runs from remaining runs
            remaining_earned -= reliever_earned_runs
            remaining_unearned -= reliever_unearned_runs

        logger.debug(f"LINE 1400 Distributed earned runs among relievers: {earned_runs_distribution}")
        logger.debug(f"LINE 1401 Distributed unearned runs among relievers: {unearned_runs_distribution}")
    
        return earned_runs_distribution, unearned_runs_distribution


    def distribute_innings_among_relievers(self, relievers, total_innings, fatigue_cache):
        """Distribute innings among relievers using precomputed fatigue multipliers."""
        
        # Sum the total relief value using the cached fatigue multipliers
        total_relief_value = sum([fatigue_cache[r] for r in relievers])

        # Convert total innings into total outs
        total_outs = int(total_innings) * 3 + round((total_innings % 1) * 10)
        logger.debug(f"LINE 1414: Total outs to distribute: {total_outs} from {total_innings} innings")

        outs_distribution = {}
        remaining_outs = total_outs

        for i, reliever in enumerate(relievers):
            # Use the cached fatigue multiplier instead of recalculating it
            adjusted_value = fatigue_cache[reliever]

            # For the last reliever, assign all remaining outs to ensure total adds up correctly
            if i == len(relievers) - 1:
                reliever_outs = remaining_outs
            else:
                # Calculate reliever outs based on relative relief value
                reliever_outs = int(round(remaining_outs * (adjusted_value / total_relief_value)))

            # Convert outs into innings notation (1 out = 0.1 innings, 3 outs = 1.0 innings)
            whole_innings = reliever_outs // 3
            fractional_innings = reliever_outs % 3  # 0, 1, or 2 (0.0, 0.1, 0.2 innings)

            # Ensure correct baseball notation
            innings_pitched = f"{whole_innings}.{fractional_innings}"

            outs_distribution[reliever.name] = innings_pitched

            # Subtract assigned outs from remaining outs
            remaining_outs -= reliever_outs
            logger.debug(f"{reliever.name} has pitched {innings_pitched} innings (outs: {reliever_outs})")

        logger.debug(f"LINE 1443: Distributed innings: {outs_distribution}")
        return outs_distribution

class Dice:
    def __init__(self, sides=6):
        self.sides = sides

    def roll(self):
        return random.randint(1, self.sides)

class TeamStats:
    def __init__(self, team_name):
        self.team_name = team_name
        self.wins = 0
        self.losses = 0
        self.home_wins = 0  # Track home wins
        self.home_losses = 0  # Track home losses
        self.away_wins = 0  # Track away wins
        self.away_losses = 0  # Track away losses
        self.run_scored = 0  # Total runs
        self.run_allowed = 0  # Total runs allowed
        self.games_played = 0
        self.one_run_games = {'wins': 0, 'losses': 0}
        self.extra_innings_games = {'wins': 0, 'losses': 0}
        self.vs_rhp = {'wins': 0, 'losses': 0}
        self.vs_lhp = {'wins': 0, 'losses': 0}
        self.pyth_wins = 0  # Pythagorean wins
        self.pyth_losses = 0  # Pythagorean losses
        self.luck = 0  # Actual wins minus Pythagorean wins
        self.most_runs_in_a_game = 0  # Add this line to track the most runs in a single game
        self.most_runs_allowed_in_a_game = 0  # Track most runs allowed in a game

        # Streak tracking
        self.current_streak = 0  # Positive for winning streaks, negative for losing streaks
        self.longest_winning_streak = 0
        self.longest_losing_streak = 0

    def update_stats(self, runs_scored, runs_allowed, is_one_run_game=False, is_extra_innings=False, pitcher_throws=None, is_home_game=False):
        """Update the stats after a game."""
        self.run_scored += runs_scored
        self.run_allowed += runs_allowed
        self.games_played += 1

        # Update the most runs scored and allowed in a single game
        if runs_scored > self.most_runs_in_a_game:
            self.most_runs_in_a_game = runs_scored
        if runs_allowed > self.most_runs_allowed_in_a_game:
            self.most_runs_allowed_in_a_game = runs_allowed

        # Determine if the team won or lost
        if runs_scored > runs_allowed:
            self.wins += 1
            if is_home_game:
                self.home_wins += 1
            else:
                self.away_wins += 1
            self.update_streak(is_win=True)  # Update streak with a win
            if is_one_run_game:
                self.one_run_games['wins'] += 1
            if is_extra_innings:
                self.extra_innings_games['wins'] += 1

            # Track wins vs RHP/LHP using pitcher_throws
            if pitcher_throws == 'R':
                self.vs_rhp['wins'] += 1
            elif pitcher_throws == 'L':
                self.vs_lhp['wins'] += 1

        else:
            self.losses += 1
            if is_home_game:
                self.home_losses += 1
            else:
                self.away_losses += 1
            self.update_streak(is_win=False)  # Update streak with a loss
            if is_one_run_game:
                self.one_run_games['losses'] += 1
            if is_extra_innings:
                self.extra_innings_games['losses'] += 1

            # Track losses vs RHP/LHP using pitcher_throws
            if pitcher_throws == 'R':
                self.vs_rhp['losses'] += 1
            elif pitcher_throws == 'L':
                self.vs_lhp['losses'] += 1


        # Recalculate Pythagorean win-loss after each game
        self.calculate_pythagorean_wl()

    def update_streak(self, is_win):
        """Update the current streak and track the longest winning/losing streaks."""
        if is_win:
            if self.current_streak >= 0:
                self.current_streak += 1
            else:
                self.current_streak = 1  # Reset streak to a win streak

            # Check if this is the longest winning streak
            if self.current_streak > self.longest_winning_streak:
                self.longest_winning_streak = self.current_streak
        else:
            if self.current_streak <= 0:
                self.current_streak -= 1
            else:
                self.current_streak = -1  # Reset streak to a losing streak

            # Check if this is the longest losing streak
            if abs(self.current_streak) > self.longest_losing_streak:
                self.longest_losing_streak = abs(self.current_streak)

    def calculate_pythagorean_wl(self):
        """Calculate the Pythagorean win-loss record and update luck."""
        if self.run_scored == 0 and self.run_allowed == 0:
            self.pyth_wins = 0
            self.pyth_losses = 0
            self.luck = 0
            return
        
        # Pythagorean expectation formula
        pyth_wins_ratio = (self.run_scored ** 2) / ((self.run_scored ** 2) + (self.run_allowed ** 2))
        pyth_wins = pyth_wins_ratio * self.games_played
        self.pyth_wins = round(pyth_wins)
        self.pyth_losses = self.games_played - self.pyth_wins

        # Calculate the "luck" factor (actual wins - Pythagorean wins)
        self.luck = self.wins - self.pyth_wins

    def calculate_win_loss_percentage(self):
        """Calculate win-loss percentage."""
        if self.games_played == 0:
            return 0.0
        return round(self.wins / self.games_played, 3)
    
    def games_behind(self, leader_wins, leader_losses):
        """Calculate games behind the leader."""
        return round((leader_wins - self.wins) + (self.losses - leader_losses) / 2, 1)

    def display_team_stats(self):
        """Display the team stats with Pythagorean win-loss and luck."""
        logger.info(f"Team: {self.team_name}")
        logger.info(f"  Wins: {self.wins}, Losses: {self.losses}, Pythagorean W-L: {self.pyth_wins}-{self.pyth_losses}, Luck: {self.luck}")
        logger.info(f"  Runs Scored: {self.run_scored}, Runs Allowed: {self.run_allowed}")
        logger.info(f"  Home Record: {self.home_wins}-{self.home_losses}, Away Record: {self.away_wins}-{self.away_losses}")
        logger.info(f"  One-Run Games: {self.one_run_games['wins']}-{self.one_run_games['losses']}, Extra-Inning Games: {self.extra_innings_games['wins']}-{self.extra_innings_games['losses']}")
        logger.info(f"  Versus RHP: {self.vs_rhp['wins']}-{self.vs_rhp['losses']}, Versus LHP: {self.vs_lhp['wins']}-{self.vs_lhp['losses']}")
        logger.info(f"  Longest Winning Streak: {self.longest_winning_streak}, Longest Losing Streak: {self.longest_losing_streak}")

class SimulateStats:
    def __init__(self, total_innings=9):
        self.total_innings = total_innings

    # 1. Allocate innings pitched between starter and bullpen
    def assign_innings(self, starter_endurance):
        innings_pitched_starter = random.uniform(5.0, starter_endurance)  # Simulate variable performance
        innings_pitched_bullpen = self.total_innings - innings_pitched_starter
        return innings_pitched_starter, innings_pitched_bullpen
    
    # 2. Calculate hits allowed based on runs and pitcher rating
    def calculate_hits_allowed(self, runs, pitcher_rating):
        hit_multiplier = random.uniform(1.5, 2.0) if pitcher_rating > 3 else random.uniform(1.0, 1.5)
        return int(runs * hit_multiplier)

    # 3. Calculate earned runs by checking fielding
    def calculate_earned_runs(self, total_runs, team_fielding_value):
        unearned_runs = random.choices([0, 1, 2], weights=[team_fielding_value, 2, 1])[0]
        return total_runs - unearned_runs
    
    # 4. Calculate walks (BB) based on pitcher rating
    def calculate_walks(self, innings_pitched, pitcher_rating):
        walk_rate = 0.5 if pitcher_rating > 3 else 1.0
        return int(innings_pitched * walk_rate)
    
    # 5. Calculate strikeouts (K) based on pitcher rating
    def calculate_strikeouts(self, innings_pitched, pitcher_rating):
        strikeout_rate = 1.0 if pitcher_rating > 3 else 0.5
        return int(innings_pitched * strikeout_rate)
    
    # 6. Calculate home runs allowed (HR) based on runs allowed and pitcher rating
    def calculate_home_runs(self, runs, pitcher_rating):
        hr_chance = random.uniform(0.1, 0.3) if pitcher_rating > 3 else random.uniform(0.2, 0.5)
        return int(runs * hr_chance)

    # Simulate a full pitching performance for a game
    def simulate_pitching_stats(self, team_runs, opponent_batting_value, starter_rating, bullpen_rating):
        innings_starter, innings_bullpen = self.assign_innings(starter_rating)

        # Starter stats
        starter_hits = self.calculate_hits_allowed(team_runs, starter_rating)
        starter_er = self.calculate_earned_runs(team_runs, opponent_batting_value)
        starter_bb = self.calculate_walks(innings_starter, starter_rating)
        starter_ks = self.calculate_strikeouts(innings_starter, starter_rating)
        starter_hrs = self.calculate_home_runs(starter_er, starter_rating)
        
        # Bullpen stats
        bullpen_hits = self.calculate_hits_allowed(team_runs // 3, bullpen_rating)
        bullpen_er = self.calculate_earned_runs(team_runs // 3, opponent_batting_value)
        bullpen_bb = self.calculate_walks(innings_bullpen, bullpen_rating)
        bullpen_ks = self.calculate_strikeouts(innings_bullpen, bullpen_rating)
        bullpen_hrs = self.calculate_home_runs(bullpen_er, bullpen_rating)

        return {
            'starter': {
                'IP': innings_starter,
                'H': starter_hits,
                'ER': starter_er,
                'BB': starter_bb,
                'K': starter_ks,
                'HR': starter_hrs
            },
            'bullpen': {
                'IP': innings_bullpen,
                'H': bullpen_hits,
                'ER': bullpen_er,
                'BB': bullpen_bb,
                'K': bullpen_ks,
                'HR': bullpen_hrs
            }
        }

    # Simulate batting stats for a single game
    def generate_batting_stats(self, players, runs):
        stats = {player['name']: {'hits': 0, 'RBIs': 0, 'HRs': 0, 'doubles': 0} for player in players}
        for _ in range(runs):
            batter = random.choices(players, weights=[p['batting'] + p['power'] for p in players])[0]
            hit_type = random.choices(['single', 'double', 'home_run'], weights=[70, 20, batter['power'] * 10])[0]

            stats[batter['name']]['hits'] += 1
            stats[batter['name']]['RBIs'] += 1
            if hit_type == 'home_run':
                stats[batter['name']]['HRs'] += 1
            elif hit_type == 'double':
                stats[batter['name']]['doubles'] += 1

        return stats

    # Simulate a game and combine batting and pitching stats
    def simulate_game(self, team_runs, opponent_batting_value, starter_rating, bullpen_rating, players):
        batting_stats = self.generate_batting_stats(players, team_runs)
        pitching_stats = self.simulate_pitching_stats(team_runs, opponent_batting_value, starter_rating, bullpen_rating)
        return batting_stats, pitching_stats
    
    # Aggregate stats over a full season
    def simulate_season(self, players, schedule, opponent_batting_value, starter_rating, bullpen_rating):
        season_stats = {player['name']: {'hits': 0, 'RBIs': 0, 'HRs': 0, 'doubles': 0} for player in players}
        season_pitching_stats = {'starter': {}, 'bullpen': {}}
        
        for game in schedule:
            team_runs = game['runs']
            game_batting_stats, game_pitching_stats = self.simulate_game(team_runs, opponent_batting_value, starter_rating, bullpen_rating, players)

            # Accumulate batting stats
            for player, stats in game_batting_stats.items():
                for stat, value in stats.items():
                    season_stats[player][stat] += value
            
            # Accumulate pitching stats (simple accumulation here)
            for role in ['starter', 'bullpen']:
                if role not in season_pitching_stats:
                    season_pitching_stats[role] = {k: 0 for k in game_pitching_stats[role].keys()}
                for stat, value in game_pitching_stats[role].items():
                    season_pitching_stats[role][stat] += value

        return season_stats, season_pitching_stats

class Schedule:
    def __init__(self, schedule_file):
        self.schedule = self.read_schedule(schedule_file)

    def read_schedule(self, schedule_file):
        games = []
        with open(schedule_file, 'r') as file:
            for line in file:
                if "<Game" in line:
                    # Extract attributes from the XML-like structure
                    day = int(self.extract_attribute(line, 'day'))
                    time = self.extract_attribute(line, 'time')
                    away = int(self.extract_attribute(line, 'away'))
                    home = int(self.extract_attribute(line, 'home'))
                    games.append({'day': day, 'time': time, 'away': away, 'home': home})
        return games

    def extract_attribute(self, text, attr_name):
        """Extract the attribute value from the line."""
        start = text.find(f'{attr_name}="') + len(attr_name) + 2
        end = text.find('"', start)
        return text[start:end]

    def get_games_for_day(self, day):
        """Return all games scheduled for the given day."""
        return [game for game in self.schedule if game['day'] == day]

class BatterStats:
    def __init__(self, batter_stats_file):
        self.batter_stats = self.read_batter_stats(batter_stats_file)

class PitcherStats:
    def __init__(self):
        self.games_played = 0
        self.innings_pitched = 0.0
        self.runs_allowed = 0
        self.earned_runs = 0
        self.strikeouts = 0
        self.walks = 0
        self.hits_allowed = 0
        self.home_runs_allowed = 0
        self.wins = 0
        self.losses = 0
        self.saves = 0
        self.blown_saves = 0

    def update_stats(self, innings, runs, earned_runs, strikeouts, walks, hits, home_runs, decision=None):
        self.innings_pitched += innings
        self.runs_allowed += runs
        self.earned_runs += earned_runs
        self.strikeouts += strikeouts
        self.walks += walks
        self.hits_allowed += hits
        self.home_runs_allowed += home_runs
        
        if decision == 'W':
            self.wins += 1
        elif decision == 'L':
            self.losses += 1
        elif decision == 'S':
            self.saves += 1
        elif decision == 'BS':
            self.blown_saves += 1
        
    def calculate_era(self):
        return (self.earned_runs / self.innings_pitched) * 9 if self.innings_pitched > 0 else 0

    def calculate_whip(self):
        return (self.walks + self.hits_allowed) / self.innings_pitched if self.innings_pitched > 0 else 0

class Standings:
    def __init__(self, sub_leagues, team_lookup):
        self.teams_stats = {}  # Dictionary to store team stats keyed by team ID or name
        self.team_lookup = team_lookup  # Store the team lookup here
        """Initialize standings, storing data by sub-league and division."""
        self.standings = {}
        for sub_league in sub_leagues:
            league_name = sub_league['sub_league_name']
            self.standings[league_name] = {}
            for division in sub_league['divisions']:
                division_name = division['division_name']
                self.standings[league_name][division_name] = {team_id: {"wins": 0, "losses": 0} for team_id in division['teams']}
    
    def add_team(self, team_id, team_name):
        if team_id not in self.teams_stats:
            self.teams_stats[team_id] = {
                'team_name': team_name,
                'wins': 0,
                'losses': 0,
                'run_scored': 0,
                'run_allowed': 0,
                'one_run_games': {'wins': 0, 'losses': 0},
                'extra_innings_games': {'wins': 0, 'losses': 0},
                'vs_rhp': {'wins': 0, 'losses': 0},
                'vs_lhp': {'wins': 0, 'losses': 0},
                'pyth_wins': 0,  # Pythagorean wins
                'pyth_losses': 0,  # Pythagorean losses
                'luck': 0,  # Actual wins minus Pythagorean wins
                'home_record': {'wins': 0, 'losses': 0},  # Home record
                'away_record': {'wins': 0, 'losses': 0},  # Away record
                'longest_winning_streak': 0,  # Longest winning streak
                'longest_losing_streak': 0,  # Longest losing streak
                'current_streak': 0  # Track the current streak (positive for winning, negative for losing)
            }
        
    def update_team_stats(self, team_id, runs_scored, runs_allowed, is_one_run_game=False, is_extra_innings=False, pitcher_throws=None, team_lookup=None):
        """Update team stats within the proper league and division."""
        team_name = team_lookup[team_id].team_name
        for league_name, divisions in self.standings.items():
            for division_name, teams in divisions.items():
                if team_id in teams:
                    # Update wins/losses for the team
                    if runs_scored > runs_allowed:
                        teams[team_id]["wins"] += 1
                    else:
                        teams[team_id]["losses"] += 1
                    break

        """Update stats for the team after a game, using the team_lookup to get team info."""
        # Ensure team is added to standings if it doesn't exist
        if team_id not in self.teams_stats:
            if team_lookup is None:
                raise ValueError(f"team_lookup is required to add team {team_id} to standings")
            
            team_name = team_lookup[team_id].team_name  # Use the team_lookup to get the name
            self.add_team(team_id, team_name)

        # Fetch the team's stats
        team_stats = self.teams_stats[team_id]
        team_stats['run_scored'] += runs_scored
        team_stats['run_allowed'] += runs_allowed
        
        # Update wins/losses and specific game type stats
        if runs_scored > runs_allowed:
            team_stats['wins'] += 1
            if is_one_run_game:
                team_stats['one_run_games']['wins'] += 1
            if is_extra_innings:
                team_stats['extra_innings_games']['wins'] += 1
            # Track wins vs RHP/LHP using pitcher_throws
            if pitcher_throws == 'R':
                team_stats['vs_rhp']['wins'] += 1
            elif pitcher_throws == 'L':
                team_stats['vs_lhp']['wins'] += 1
        else:
            team_stats['losses'] += 1
            if is_one_run_game:
                team_stats['one_run_games']['losses'] += 1
            if is_extra_innings:
                team_stats['extra_innings_games']['losses'] += 1
            # Track losses vs RHP/LHP using pitcher_throws
            if pitcher_throws == 'R':
                team_stats['vs_rhp']['losses'] += 1
            elif pitcher_throws == 'L':
                team_stats['vs_lhp']['losses'] += 1

    def calculate_championship_probability(self):
        # Simulate the rest of the season multiple times (Monte Carlo)
        simulations = 10000
        playoff_wins = {team_id: 0 for team_id in self.teams_stats}

        for _ in range(simulations):
            simulated_standings = self.simulate_remaining_games()
            playoff_winners = self.get_playoff_teams(simulated_standings)
            for team_id in playoff_winners:
                playoff_wins[team_id] += 1
        
        # Update playoff probability for each team
        for team_id in self.teams_stats:
            self.teams_stats[team_id]['playoff_prob'] = playoff_wins[team_id] / simulations

    def calculate_cli(self, team_id, game_id):
        # Simulate two scenarios for CLI: win and loss for a specific game
        win_scenario = self.simulate_game_outcome(team_id, game_id, win=True)
        lose_scenario = self.simulate_game_outcome(team_id, game_id, win=False)

        win_prob = self.get_team_playoff_prob(team_id, win_scenario)
        lose_prob = self.get_team_playoff_prob(team_id, lose_scenario)

        # Return the Championship Leverage Index for this game
        return abs(win_prob - lose_prob)

    def simulate_remaining_games(self):
        # Randomly simulate outcomes of the remaining games for the season
        # Update standings based on random outcomes
        pass
    
    def simulate_game_outcome(self, team_id, game_id, win):
        # Simulate the season with a specific game outcome (win/loss)
        pass

    def get_playoff_teams(self, standings):
        # Determine which teams make the playoffs based on standings
        pass

    def get_team_playoff_prob(self, team_id, standings):
        # Get the probability of a specific team making playoffs from standings
        return standings[team_id]['playoff_prob']

    def save_standings(self, file_name='standings.json'):
        """Save the standings to a JSON file."""
        file_path = os.path.join(BASE_DIRECTORY, file_name)
        with open(file_path, 'w') as file:
            json.dump(self.teams_stats, file, indent=4)

    def load_standings(self, file_path='standings.json'):
        """Load standings from a JSON file."""
        with open(file_path, 'r') as file:
            self.teams_stats = json.load(file)
    
    def display_standings(self, team_stats_lookup):
        """Display the standings for each sub-league and division."""
        for league_name, divisions in self.standings.items():
            logger.info(f"\n{league_name} Standings")
            logger.info("=" * (len(league_name) + 10))
            for division_name, teams in divisions.items():
                logger.info(f"\n{division_name} Division")
                logger.info("-" * (len(division_name) + 10))
                logger.info(f"{'Team':<20} {'W':<5} {'L':<5} {'PCT':<6} {'GB':<5} {'RS':<5} {'RA':<5} {'Pyth W-L':<10} {'Luck':<5} {'Home':<10} {'Away':<10} {'1-Run':<10} {'Extra':<10} {'vs RHP':<10} {'vs LHP':<10} {'Win Streak':<13} {'Losing Streak':<13} {'Most Runs Scored':<18} {'Most Runs Allowed':<18}")

                # Get the stats for the teams and sort them by win percentage
                team_list = []
                for team_id, record in teams.items():
                    team_stats = team_stats_lookup[team_id]
                    win_pct = team_stats.calculate_win_loss_percentage()
                    team_list.append((team_id, record['wins'], record['losses'], win_pct, team_stats))
                
                # Sort the teams based on win percentage, descending
                team_list.sort(key=lambda x: x[3], reverse=True)

                # Determine the division leader
                leader_wins = team_list[0][1]
                leader_losses = team_list[0][2]

                # logger.debug the sorted teams with all stats
                for team_id, wins, losses, win_pct, team_stats in team_list:
                    games_behind = team_stats.games_behind(leader_wins, leader_losses)
                    home_record = f"{team_stats.home_wins}-{team_stats.home_losses}"
                    away_record = f"{team_stats.away_wins}-{team_stats.away_losses}"
                    one_run_record = f"{team_stats.one_run_games['wins']}-{team_stats.one_run_games['losses']}"
                    extra_innings_record = f"{team_stats.extra_innings_games['wins']}-{team_stats.extra_innings_games['losses']}"
                    vs_rhp_record = f"{team_stats.vs_rhp['wins']}-{team_stats.vs_rhp['losses']}"
                    vs_lhp_record = f"{team_stats.vs_lhp['wins']}-{team_stats.vs_lhp['losses']}"
                    most_runs_scored = team_stats.most_runs_in_a_game
                    most_runs_allowed = team_stats.most_runs_allowed_in_a_game
                    
                    logger.info(f"{team_stats.team_name:<20} {wins:<5} {losses:<5} {win_pct:<6} {games_behind:<5} {team_stats.run_scored:<5} {team_stats.run_allowed:<5} {team_stats.pyth_wins}-{team_stats.pyth_losses:<10} {team_stats.luck:<5} {home_record:<10} {away_record:<10} {one_run_record:<10} {extra_innings_record:<10} {vs_rhp_record:<10} {vs_lhp_record:<10} {team_stats.longest_winning_streak:<13} {team_stats.longest_losing_streak:<13} {most_runs_scored:<18} {most_runs_allowed:<18}")

class Playoffs:
    def __init__(self, standings, team_stats_lookup, power_chart, speed_bench_chart, relief_defense_chart):
        self.standings = standings
        self.team_stats_lookup = team_stats_lookup
        self.power_chart = power_chart
        self.speed_bench_chart = speed_bench_chart
        self.relief_defense_chart = relief_defense_chart

        # Initialize playoff teams, seeded by their regular season record
        self.playoff_teams = {
            'AL': {
                'division_winners': [],
                'wildcard': None
            },
            'NL': {
                'division_winners': [],
                'wildcard': None
            }
        }

    def initialize_pitcher_rest(self):
        """Ensure all pitchers have their last_start_day initialized properly for the playoffs."""
        for league in ['AL', 'NL']:
            for team_id in self.playoff_teams[league]['division_winners'] + [self.playoff_teams[league]['wildcard']]:
                team = self.standings.team_lookup[team_id]
                for pitcher in team.pitchers:
                    if pitcher.last_start_day is None:
                        pitcher.last_start_day = 0  # Default to 0 if None
                    if pitcher.rest is None:
                        pitcher.rest = 0  # Ensure rest is initialized properly
                    logger.debug(f"LINE 2209 Initialized pitcher: {pitcher.name}, last_start_day: {pitcher.last_start_day}, rest: {pitcher.rest}")

    def seed_teams(self):
        # Loop through both AL and NL leagues
        league_mapping = {
            "American League": "AL",
            "National League": "NL"
        }
        
        for league_name in ['American League', 'National League']:
            logger.debug(f"Seeding teams from league: {league_name}")
            
            # Get the sub-leagues from the standings
            league_abbr = league_mapping[league_name]  # Use 'AL' or 'NL'
            league_standings = self.standings.standings[league_name]
            division_winners = []
            wildcard_candidates = []

            # Collect teams from divisions in each league
            for division_name, teams in league_standings.items():
                # Sort teams within the division by wins and run differential (run_scored - run_allowed)
                sorted_teams = sorted(teams.items(), key=lambda x: (
                    x[1]['wins'],  # Primary sort by wins
                    x[1].get('run_scored', 0) - x[1].get('run_allowed', 0)  # Secondary sort by run differential
                ), reverse=True)

                # Get the division winner (the first team in the sorted list)
                division_winner = sorted_teams[0][0]
                division_winners.append(division_winner)

                # Add the remaining teams to the wildcard candidate pool
                wildcard_candidates.extend([team_id for team_id, _ in sorted_teams[1:]])

            # Add division winners to playoff teams
            self.playoff_teams[league_abbr]['division_winners'] = division_winners

            # Determine the wildcard team (team with most wins from wildcard candidates)
            wildcard_team = max(wildcard_candidates, key=lambda team_id: self.standings.teams_stats[team_id]['wins'])
            self.playoff_teams[league_abbr]['wildcard'] = wildcard_team

        logger.info(f"Playoff teams seeded: {self.playoff_teams}")


    def simulate_series(self, team1, team2, games=7):
        """Simulate a series between two teams in a 2-3-2 format."""
        team1_wins = 0
        team2_wins = 0
        home_games = [team1, team1, team2, team2, team2, team1, team1]

        # Track the results of each game
        series_results = []

        for i in range(games):
            if team1_wins == 4 or team2_wins == 4:
                break  # Series over

            home_team = home_games[i]
            away_team = team2 if home_team == team1 else team1

            # Ensure pitchers' last_start_day is valid before selecting them
            for pitcher in home_team.pitchers + away_team.pitchers:
                if pitcher.last_start_day is None:
                    pitcher.last_start_day = 0  # Safety check

            # Simulate a single game between home and away teams
            game = Game(home_team, away_team, self.current_day, power_chart=self.power_chart, speed_bench_chart=self.speed_bench_chart, relief_defense_chart=self.relief_defense_chart)

            result = game.play_game(self.current_day)

            # Record the result with correct formatting: home team on the right, away team on the left
            if result['home_runs'] > result['away_runs']:
                # Home team wins
                if home_team == team1:
                    team1_wins += 1
                else:
                    team2_wins += 1
                series_results.append(f"Game {i+1}: {away_team.team_name} {result['away_runs']} - {home_team.team_name} {result['home_runs']}")
            else:
                # Away team wins
                if away_team == team1:
                    team1_wins += 1
                else:
                    team2_wins += 1
                series_results.append(f"Game {i+1}: {away_team.team_name} {result['away_runs']} - {home_team.team_name} {result['home_runs']}")

            # Increment the current day after each game
            self.current_day += 1

        # After the series ends, logger.debug out the results
        logger.info(f"{team1.team_name} vs {team2.team_name} Series Results:")
        for result in series_results:
            logger.info(result)

        # Announce the series winner
        if team1_wins > team2_wins:
            logger.info(f"{team1.team_name} wins the series 4 games to {team2_wins}")
            return team1  # Team 1 wins the series
        else:
            logger.info(f"{team2.team_name} wins the series 4 games to {team1_wins}")
            return team2  # Team 2 wins the series

    def simulate_playoffs(self):
        """Simulate the entire playoffs."""
        self.seed_teams()

        # Set the playoff start day to be 3 days after the last regular season game
        playoff_start_day = 186 + 3  # Day 189
        self.current_day = playoff_start_day  # Ensure playoff games use the new start day
        logger.debug(f"Playoffs starting on day: {self.current_day}")
        
        self.initialize_pitcher_rest()

        # AL Playoffs
        al_wildcard_team_id = self.playoff_teams['AL']['wildcard']
        al_best_team_id = self.playoff_teams['AL']['division_winners'][0]

        # Access the actual team objects from team_lookup instead of team_stats_lookup
        al_wildcard_team = self.standings.team_lookup[al_wildcard_team_id]  # Use team_lookup for actual teams
        al_best_team = self.standings.team_lookup[al_best_team_id]

        al_series_1_winner = self.simulate_series(al_best_team, al_wildcard_team)

        # Get the second and third division winners
        al_second_team_id = self.playoff_teams['AL']['division_winners'][1]
        al_third_team_id = self.playoff_teams['AL']['division_winners'][2]

        al_second_team = self.standings.team_lookup[al_second_team_id]
        al_third_team = self.standings.team_lookup[al_third_team_id]

        al_series_2_winner = self.simulate_series(al_second_team, al_third_team)

        # AL Championship Series
        al_champion = self.simulate_series(al_series_1_winner, al_series_2_winner)

        # NL Playoffs
        nl_wildcard_team_id = self.playoff_teams['NL']['wildcard']
        nl_best_team_id = self.playoff_teams['NL']['division_winners'][0]

        nl_wildcard_team = self.standings.team_lookup[nl_wildcard_team_id]
        nl_best_team = self.standings.team_lookup[nl_best_team_id]

        nl_series_1_winner = self.simulate_series(nl_best_team, nl_wildcard_team)

        nl_second_team_id = self.playoff_teams['NL']['division_winners'][1]
        nl_third_team_id = self.playoff_teams['NL']['division_winners'][2]

        nl_second_team = self.standings.team_lookup[nl_second_team_id]
        nl_third_team = self.standings.team_lookup[nl_third_team_id]

        nl_series_2_winner = self.simulate_series(nl_second_team, nl_third_team)

        # NL Championship Series
        nl_champion = self.simulate_series(nl_series_1_winner, nl_series_2_winner)

        # World Series
        world_series_winner = self.simulate_series(al_champion, nl_champion)

        # Display the results
        # Convert team_id to integer before looking it up in team_lookup
        world_series_winner_team_id = int(world_series_winner.team_id)

        logger.debug(f"Available team IDs in team_lookup: {list(self.standings.team_lookup.keys())}")
        # Lookup the team name in team_lookup using the integer team_id
        logger.debug(f"World Series Champion: {self.standings.team_lookup[world_series_winner_team_id].team_name}")

        return world_series_winner

class Weather:
    def __init__(self, weather_data):
        self.weather_data = weather_data

class Ballpark:
    def __init__(self, ballpark_name, ballpark_capacity, ballpark_weather, stadium_value=0, home_field_advantage=0):
        self.ballpark_name = ballpark_name
        self.ballpark_capacity = ballpark_capacity
        self.ballpark_weather = ballpark_weather
        self.stadium_value = stadium_value
        self.home_field_advantage = home_field_advantage
        self.away_team_ballpark = None
        self.home_team_ballpark = None

class Injury:
    def __init__(self, team):
        self.team = team  # Store the team information for player selection

    def check_injury(self):
        # Roll to determine which player might get injured
        injured_player = self.roll_for_injured_player()

        # Roll three dice to calculate injury duration
        roll_dice = self.roll_dice()

        # Calculate injury days based on the dice rolls and injury modifier
        injury_days = self.calculate_injury_days(roll_dice, injured_player.injury)

        # Assign the injury to the player
        injured_player.injury_days = injury_days

        # Log the result
        logger.info(f"Player {injured_player.name} is injured for {injury_days if injury_days != 'Season' else 'the rest of the season'} days.")
        
        return injured_player

    def roll_dice(self):
        # Roll three dice and return the results
        return [random.randint(1, 6) for _ in range(3)]

    def roll_for_injured_player(self):
        # Randomly select a player from the team's roster using a d66 roll equivalent
        dice = Dice(6)
        player_index = dice.roll() - 1  # Adjusting for 1-based index
        return self.team.players[player_index]

    def calculate_injury_days(self, roll_dice, injury_modifier):
        # Sum the dice and multiply by 3 to calculate base injury days
        total_injury_days = sum(roll_dice) * 3
        
        # Apply injury modifier
        final_injury_days = max(0, total_injury_days + injury_modifier)

        # Check for season-ending or doubled injury if all dice are the same
        if roll_dice[0] == roll_dice[1] == roll_dice[2]:
            if roll_dice[0] % 2 == 1:  # Odd triad: season-ending injury
                final_injury_days = 'Season'
            elif roll_dice[0] % 2 == 0:  # Even triad: double the injury days
                final_injury_days *= 2
        
        return final_injury_days

class Minors:
    def __init__(self, minors_data):
        self.minors_data = minors_data

class Transactions:
    def __init__(self, transactions_data):
        self.transactions_data = transactions_data

class Manager:
    def __init__(self, manager_data):
        self.manager_data = manager_data

class General_Manager:
    def __init__(self, general_manager_data):
        self.general_manager_data = general_manager_data

def load_team_from_json(file_path):
    logger.debug(f"Loading team data from file: {file_path}")
    
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
    except Exception as e:
        logger.debug(f"Error reading JSON file: {file_path} - {e}")
        return None

    logger.debug(f"Team data loaded successfully: {data}")  # Check if JSON is being loaded correctly

    # Extract the team_id from the JSON (assume it's included in the JSON data)
    team_id = data.get('team_id')
    logger.debug(f"Team ID: {team_id}")

    # Create Pitcher objects
    pitchers = []
    for p in data.get('pitchers', []):
        try:
            logger.debug(f"Creating pitcher: {p}")  # Add debug
            pitcher = Pitcher(
                name=p['name'],
                type=p['type'],  # Use the type field to specify if SP or RP
                splits_L=p['splits_L'],
                splits_R=p['splits_R'],
                start_value=p['start_value'],
                relief_value=p['relief_value'],
                endurance=p['endurance'],
                rest=p['rest'],
                throws=p.get('throws', 'R'),  # Default to 'R' if not provided
                injury=p.get('injury', 0),
                salary=p.get('salary', 0),
                cg_rating=p.get('cg_rating', 666),  # Add this line
                sho_rating=p.get('sho_rating', 666),  # Add this line
                fatigue=p.get('fatigue', 0),  # Add this line
                clutch=p.get('clutch', 0)  # Add this line
            )
            # Ensure `last_start_day` is initialized
            pitcher.last_start_day = p.get('last_start_day', 0)  # Default to 0 if not available
            pitchers.append(pitcher)
        except Exception as e:
            logger.debug(f"Error creating pitcher: {p.get('name', 'Unknown')} - {e}")

    # Create Player objects with extra debugging
    players = []
    for pl in data.get('players', []):
        try:
            logger.debug(f"Creating player: {pl}")  # Debug: Show player data
            player = Player(
                name=pl['name'],
                role=pl['role'],
                batting=pl['batting'],
                power=pl['power'],
                splits_L=pl['splits_L'],
                splits_R=pl['splits_R'],
                speed=pl['speed'],
                fielding=pl['fielding'],
                clutch=pl['clutch'],
                position=pl.get('position', None),
                sec_position=pl.get('sec_position', None),
                bats=pl.get('bats', 'R'),  # Default to 'R' if not provided
                injury=pl.get('injury', 0),
                salary=pl.get('salary', 0),
                eye=pl.get('eye', 0)
            )
            players.append(player)
        except Exception as e:
            logger.debug(f"Error creating player: {pl.get('name', 'Unknown')} - {e}")
    
    logger.debug(f"Players created successfully for team {team_id}")

    # Create Team object
    try:
        team = Team(
            team_id=data['team_id'],
            team_name=data['team_name'],
            pitchers=pitchers,
            players=players,
            unearned_runs_chart=data.get('unearned_runs_chart', None),
            stadium_value=data.get('stadium_value', 0),
            weather_value=data.get('weather_value', 0),
            home_field_advantage=data.get('home_field_advantage', 0),
            minors=data.get('minors', 0),
            budget=data.get('budget', 0),
            ballpark_name=data.get('ballpark_name', ""),  # Add ballpark details
            ballpark_capacity=data.get('ballpark_capacity', 0),
            ballpark_weather=data.get('ballpark_weather', "")
        )
        logger.debug(f"Team {team.team_name} created successfully.")
        return team
    except Exception as e:
        logger.debug(f"Error creating team: {data.get('team_name', 'Unknown')} - {e}")
        return None

def main():
    # Define the path to league.json using the BASE_DIRECTORY
    league_file_path = os.path.join(BASE_DIRECTORY, 'league.json')

    # Load the league structure from league.json
    with open(league_file_path, 'r') as f:
        league_data = json.load(f)
    
    # Extract the league and division data
    league_name = league_data['league_name']
    sub_leagues = league_data['sub_leagues']
    
    # Dictionary to store all the loaded teams, using their team_id as the key
    team_lookup = {}
    # logger.debug(team_lookup)

    # Dictionary to store team stats for each team
    team_stats_lookup = {}

    # Loop through team IDs and load each team's data
    # Define the number of teams
    num_teams = 30
    for team_id in range(1, num_teams + 1):
        # Construct the full file path by joining the base directory with the team file name
        file_path = os.path.join(BASE_DIRECTORY, f'team_id_{team_id}.json')  # Assuming team files are named in this format
        logger.debug(f"Loading team data from: {file_path}")
        try:
            team = load_team_from_json(file_path)
            team_lookup[team_id] = team
            team_stats_lookup[team_id] = TeamStats(team.team_name)
            logger.debug(f"Loaded team {team_id}: {team.team_name}")
        except FileNotFoundError:
            logger.debug(f"File not found: {file_path}")
        except Exception as e:
            logger.debug(f"Error loading team {team_id}: {str(e)}")

    logger.debug(f"Loaded teams: {list(team_lookup.keys())}")

    # Pass team_lookup to Standings
    standings = Standings(sub_leagues, team_lookup)

    # Load the schedule file (assuming we use the schedule name from league.json)
    schedule = Schedule(os.path.join(BASE_DIRECTORY, league_data['schedule_name']))

    power_chart = {
        (1, 1): {1: "Spot 4", 2: "Bench 6", 3: "Bench 5", 4: "Spot 5", 5: "Spot 7", 6: "Spot 9"},
        (2, 2): {1: "Spot 3", 2: "Spot 4", 3: "Bench 1", 4: "Spot 2", 5: "Spot 6", 6: "Bench 2"},
        (3, 3): {1: "Bench 4", 2: "Spot 3", 3: "Spot 4", 4: "Spot 1", 5: "Spot 5", 6: "Bench 3"},
        (4, 4): {1: "Spot 5", 2: "Spot 2", 3: "Spot 3", 4: "Spot 4", 5: "Spot 1", 6: "Spot 6"},
        (5, 5): {1: "Spot 8", 2: "Spot 7", 3: "Spot 6", 4: "Spot 3", 5: "Spot 4", 6: "Spot 2"},
        (6, 6): {1: "Bench 2", 2: "Spot 8", 3: "Spot 5", 4: "Bench 1", 5: "Spot 3", 6: "Spot 4"}
    }

    speed_bench_chart = {
        (1, 1): {1: "Spot 5", 2: "Bench 1", 3: "Bench 2", 4: "Spot 3", 5: "Spot 6", 6: "Spot 2"},
        (2, 2): {1: "Spot 1", 2: "Spot 8", 3: "Spot 3", 4: "Spot 4", 5: "Spot 7", 6: "Bench 3"},
        (3, 3): {1: "Spot 1", 2: "Spot 1", 3: "Spot 1", 4: "Spot 9", 5: "Spot 1", 6: "Spot 1"},
        (4, 4): {1: "Spot 2", 2: "Bench 3", 3: "Bench 6", 4: "Spot 2", 5: "Spot 3", 6: "Bench 5"},
        (5, 5): {1: "Spot 6", 2: "Spot 9", 3: "Spot 8", 4: "Bench 4", 5: "Spot 2", 6: "Spot 1"},
        (6, 6): {1: "Spot 7", 2: "Bench 2", 3: "Spot 4", 4: "Bench 1", 5: "Spot 3", 6: "Spot 5"}
    }

    # Play the season
    for day in range(1, 187):
        games_today = schedule.get_games_for_day(day)
        for game_info in games_today:
            away_team_id = game_info['away']
            home_team_id = game_info['home']

            away_team = team_lookup[away_team_id]
            home_team = team_lookup[home_team_id]

            relief_defense_chart = Game.consult_relief_defense_chart
            game = Game(home_team, away_team, day, power_chart, speed_bench_chart, relief_defense_chart)
            result = game.play_game(day)

            # Update team stats and standings, passing pitcher handedness
            standings.update_team_stats(home_team_id, result['home_runs'], result['away_runs'], result.get('is_one_run', False), result.get('is_extra_innings', False), pitcher_throws=result['away_pitcher_throws'], team_lookup=team_lookup)
            standings.update_team_stats(away_team_id, result['away_runs'], result['home_runs'], result.get('is_one_run', False), result.get('is_extra_innings', False), pitcher_throws=result['home_pitcher_throws'], team_lookup=team_lookup)

            # Update each team's stats with home and away tracking, passing the pitcher handedness
            team_stats_lookup[home_team_id].update_stats(result['home_runs'], result['away_runs'], result.get('is_one_run', False), result.get('is_extra_innings', False), pitcher_throws=result['away_pitcher_throws'], is_home_game=True)
            team_stats_lookup[away_team_id].update_stats(result['away_runs'], result['home_runs'], result.get('is_one_run', False), result.get('is_extra_innings', False), pitcher_throws=result['home_pitcher_throws'], is_home_game=False)

            # Save team-specific data (pitcher rest, injuries, etc.)
            home_team.save_team_data()
            away_team.save_team_data()

        # At the end of each day, display standings and save them
        standings.display_standings(team_stats_lookup)
        standings.save_standings()

    # At the end of the season, display the final standings
    logger.info("\n=== Final Standings ===")
    standings.display_standings(team_stats_lookup)

    # After the regular season is complete, initiate the playoffs
    playoffs = Playoffs(standings, team_stats_lookup, power_chart, speed_bench_chart, relief_defense_chart)
    playoffs.simulate_playoffs()

# ----------------------------
# GUI using Pygame
# ----------------------------
class GUI:
    def __init__(self, game):
        self.game = game
        pygame.init()
        self.screen = pygame.display.set_mode((1600,900))
        pygame.display.set_caption("Pennant Race")
        self.font = pygame.font.SysFont("Arial", 20)
        self.large_font = pygame.font.SysFont("Arial", 30)
        self.clock = pygame.time.Clock()

    def draw(self):
        self.screen.fill((0, 128, 0))  # Background color
        # Left panel: Home team (400px wide)
        left_rect = pygame.Rect(0, 0, 300, 800)
        pygame.draw.rect(self.screen, (200, 200, 200), left_rect)
        self.draw_team(self.game.home_team, left_rect, "Home Team")

        # Right panel: Visiting team (400px wide)
        right_rect = pygame.Rect(900, 0, 300, 800)
        pygame.draw.rect(self.screen, (200, 200, 200), right_rect)
        self.draw_team(self.game.visiting_team, right_rect, "Visiting Team")

        # Middle panel: Scoreboard, Field, and Play-by-Play (400px wide)
        middle_rect = pygame.Rect(300, 0, 600, 800)
        pygame.draw.rect(self.screen, (50, 50, 50), middle_rect)

        # Scoreboard (top 200px)
        standings_rect = pygame.Rect(300, 0, 600, 100)
        self.draw_standings(standings_rect)

        # Field diagram (next 200px)
        field_rect = pygame.Rect(300, 100, 600, 400)
        self.draw_field(field_rect)
        
        # Play-by-Play and options (bottom 400px)
        pbp_rect = pygame.Rect(300, 500, 600, 300)
        self.draw_play_by_play(pbp_rect)
        pygame.display.flip()

    def draw_team(self, team, rect, title):
        pygame.draw.rect(self.screen, (150, 150, 150), rect, 2)
        title_text = self.large_font.render(title, True, (0, 0, 0))
        self.screen.blit(title_text, (rect.x + 10, rect.y + 10))
        y_offset = rect.y + 50
        for player in team.players:
            player_text = self.font.render(f"{player.name} ({player.position})", True, (0, 0, 0))
            self.screen.blit(player_text, (rect.x + 10, y_offset))
            y_offset += 30
        score_text = self.font.render("Score: " + str(team.score), True, (0, 0, 0))
        self.screen.blit(score_text, (rect.x + 10, y_offset))

    def draw_standings(self, rect):
        pygame.draw.rect(self.screen, (100, 100, 100), rect, 2)
        title = self.large_font.render("Scoreboard", True, (255, 255, 255))
        self.screen.blit(title, (rect.x + 10, rect.y + 10))
        info = f"Inning: {self.game.inning}   Outs: {self.game.outs}"
        info_text = self.font.render(info, True, (255, 255, 255))
        self.screen.blit(info_text, (rect.x + 10, rect.y + 50))

    def draw_field(self, rect):
        pygame.draw.rect(self.screen, (80, 80, 80), rect, 2)
        title = self.large_font.render("Field", True, (255, 255, 255))
        self.screen.blit(title, (rect.x + 10, rect.y + 10))
        # Draw a simple diamond: circles for bases
        center_x = rect.x + rect.width // 2
        center_y = rect.y + rect.height // 2
        pygame.draw.circle(self.screen, (255, 255, 255), (center_x, rect.y + rect.height - 30), 10)  # Home
        pygame.draw.circle(self.screen, (255, 255, 255), (rect.x + rect.width - 30, center_y), 10)  # First
        pygame.draw.circle(self.screen, (255, 255, 255), (center_x, rect.y + 30), 10)              # Second
        pygame.draw.circle(self.screen, (255, 255, 255), (rect.x + 30, center_y), 10)              # Third

    def draw_play_by_play(self, rect):
        pygame.draw.rect(self.screen, (0, 0, 0), rect)
        pygame.draw.rect(self.screen, (255, 255, 255), rect, 2)
        title = self.large_font.render("Play-by-Play", True, (255, 255, 255))
        self.screen.blit(title, (rect.x + 10, rect.y + 10))
        y_offset = rect.y + 50
        recent_events = self.game.play_by_play[-10:]
        for event in recent_events:
            event_text = self.font.render(event, True, (255, 255, 255))
            self.screen.blit(event_text, (rect.x + 10, y_offset))
            y_offset += 25

# ----------------------------
# Main Loop: Integrating Simulation and GUI
# ----------------------------
def main():
    mode = "human"  # "human" for human vs AI; "ai" for AI vs AI simulation
    game = Game(mode)
    gui = GUI(game)

    running = True
    last_update = pygame.time.get_ticks()
    update_interval = 2000  # milliseconds between at-bats for AI mode

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            # In human mode, use the SPACE key to simulate an at-bat.
            if game.mode == "human" and event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    batter = game.current_batting_team.players[game.current_batter_index]
                    outcome = game.at_bat(batter)
                    if outcome.get("out_occurred"):
                        game.outs += 1
                    else:
                        game.update_baserunners(outcome, batter)
                    game.next_batter()

        if game.mode == "ai":
            current_time = pygame.time.get_ticks()
            if current_time - last_update > update_interval:
                batter = game.current_batting_team.players[game.current_batter_index]
                outcome = game.at_bat(batter)
                if outcome.get("out_occurred"):
                    game.outs += 1
                else:
                    game.update_baserunners(outcome, batter)
                game.next_batter()
                last_update = current_time

        if game.outs >= 3:
            game.switch_sides()

        gui.draw()
        gui.clock.tick(30)

        if game.game_over():
            game.declare_winner()
            gui.draw()
            pygame.time.delay(5000)
            running = False

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()



