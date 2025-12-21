import pandas as pd
import json
import os
import sys
import numpy as np
import random
import unicodedata
import math
from pathlib import Path

# Add common folder to sys.path for shared modules
COMMON_PATH = Path.home() / "Documents/_code/common"
sys.path.insert(0, str(COMMON_PATH))

from data_paths_pennant_fever import (
    PENNANT_FEVER_DATA_DIR,
    PENNANT_FEVER_JSON_MLB_DIR,
    MLB_2023_FILE,
    HISTORICAL_DATA_DIR,
)

# generate more granular ratings (3 decimal points eg 0.456, 1.234 etc) these number will get added through the play resolution process in the main game and eventually we round off the runs anyway but granularity differentiates players more than the coarse ratings (qv the fictional generator for specific code)
# need to build in era/year adjustments - might be good to have a separate file with yearly calculation distributions for average, power, etc (there is a historical wOBA list on fangraphs)
# stadium value should be broken down into batting and pitching values (MLB only)
# incorporate injury data from fangraphs (at least for the 2023 sheet)
# need to change 'B' to 'S' in database for switch hitters
# do i need yearly stats to normalise ratings?
# usage penalties? does need to be set elsewhere in the game? also for splits, penalties or bonuses should be capped at certain amounts depending on ABs vs L or R. ie if you batted 3 for 7 that year against L, you wouldnt get a 3. you would need to exceed an AB threshold to get higher than 1, then another for 2, same for negative
# expand imported positions: P, PR, PH
# pitcher batter/fielding

'''
# 1980s db: splits for pitchers and batters
1) when i finish with rosters, i will need to account for the fact that w the fangraphs data, i have no split seasons for players - its just one entry. and baseball-ref rosters may have duplicates (ie same player on multiple teams)


need to redo team_x_hr chart to look like this:
    "X-HR_chart": {
      "3": 122,
      "2": 145,
      "1": 323,
      "0": 666
    },
its broken right now
'''

# need input function here for which year league to load, eg 1980MLB or 1994NPB
# then adjust rating gen according to year and league

def normalize_name(name):
    # Normalize the name to remove accents and diacritics
    name_normalized = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('ascii')
    
    # Remove any asterisks from the name
    name_cleaned = name_normalized.replace('*', '')
    
    return name_cleaned

# Total games played is constant (default for modern MLB)
total_games_played = 162

# Global DataFrames - will be loaded when process_team_roster is called
team_bat_df = None
batting_df = None
fielding_df = None
pitching_df = None
roster_df = None
manager_df = None
general_manager_df = None

# Function to split sections (players, batting, pitching, etc.) from relevant sheets
def split_sections(team_abbr):
    # Batting data filtered by team abbreviation
    team_batting = batting_df[batting_df['team'].str.contains(team_abbr, case=False)]
    
    # Fielding data filtered by team abbreviation
    team_fielding = fielding_df[fielding_df['team'].str.contains(team_abbr, case=False)]
    
    # Pitching data filtered by team abbreviation
    team_pitching = pitching_df[pitching_df['team'].str.contains(team_abbr, case=False)]
    
    return team_batting, team_fielding, team_pitching

'''
def calculate_bat_rating(avg):
    # Assuming you already know min and max values for batting average from your dataset:
    min_batting_avg = 0.125  # Adjust based on actual data
    max_batting_avg = 0.354  # Adjust based on actual data
    return max(0, min(8, (avg - min_batting_avg) / (max_batting_avg - min_batting_avg) * 8))

def calculate_power_rating(slg):
    # Assuming you already know min and max values for slugging percentage from your dataset:
    min_slugging = 0.168  # Adjust based on actual data
    max_slugging = 0.654  # Adjust based on actual data
    return max(0, min(8, (slg - min_slugging) / (max_slugging - min_slugging) * 8))

'''
def calculate_bat_rating(avg):
    if avg < .190:
        return 0
    elif avg <= .220:
        return 1
    elif avg <= .247:
        return 2
    elif avg <= .260:
        return 3
    elif avg <= .280:
        return 4
    elif avg <= .300:
        return 5
    elif avg <= .320:
        return 6
    elif avg <= .340:
        return 7
    elif avg > .340:
        return 8

def calculate_power_rating(slg):
    if slg < .330:
        return 0
    elif slg <= .340:
        return 1
    elif slg <= .363:
        return 2
    elif slg <= .413:
        return 3
    elif slg <= .430:
        return 4
    elif slg <= .473:
        return 5
    elif slg <= .550:
        return 6
    elif slg <= .600:
        return 7
    elif slg > .600:
        return 8

def calculate_speed_rating(sb):
    if sb == 0:
        return 0
    elif sb <= 5:
        return 1
    elif sb <= 10:
        return 2
    elif sb <= 20:
        return 3
    elif sb <= 30:
        return 4
    elif sb <= 50:
        return 5
    elif sb <= 70:
        return 6
    elif sb <= 90:
        return 7
    elif sb >= 91:
        return 8

def calculate_speed_score(data, year):
    """
    Calculate a player's Speed Score based on the updated Bill James Speed Score formula,
    applying custom weights to each factor to adjust the final score.
    
    Parameters:
    data (dict): A dictionary containing player stats (SB, CS, 3B, R, H, BB, GDP, etc.).
    year (int): The year of the season being calculated (used to adjust pre-1933 seasons).

    Returns:
    float: A normalized Speed Score (0 to 10).
    """

    if year < 1933:
        return calculate_speed_rating(data.get('SB', 0))
    
        # Factor 1: Stolen base percentage
    sb = data.get('SB', 0)
    cs = data.get('CS', 0)
    sb_attempts = sb + cs
    if sb_attempts > 0:
        f1 = (sb + 3) / (sb_attempts + 7)
        f1 = (f1 - 0.4) * 20
    else:
        f1 = 0

    # Factor 2: Stolen base attempts per (singles + BB + HBP)
    singles = data.get('H', 0) - data.get('2B', 0) - data.get('3B', 0) - data.get('HR', 0)
    bb = data.get('BB', 0)
    hbp = data.get('HBP', 0)
    on_base_without_hr = singles + bb + hbp
    if on_base_without_hr > 0:
        f2 = math.sqrt(sb_attempts / on_base_without_hr) / 0.07
    else:
        f2 = 0

    # Factor 3: Triples rate (per AB minus HR and K)
    ab = data.get('AB', 0)
    strikeouts = data.get('SO', 0)
    triples = data.get('3B', 0)
    ab_no_hr_k = ab - data.get('HR', 0) - strikeouts
    if ab_no_hr_k > 0:
        f3 = triples / ab_no_hr_k / 0.0016
    else:
        f3 = 0

    # Factor 4: Runs scored percentage (excluding HRs)
    runs = data.get('R', 0)
    home_runs = data.get('HR', 0)
    times_on_base = singles + bb + hbp
    if times_on_base > 0:
        f4 = (runs - home_runs) / times_on_base
        f4 = (f4 - 0.1) * 25
    else:
        f4 = 0

    # Factor 5: Grounded into double plays rate (per AB minus HR and K)
    gidp = data.get('GDP', 0)
    if ab_no_hr_k > 0:
        f5 = (0.063 - (gidp / ab_no_hr_k)) / 0.007
    else:
        f5 = 0

    # Factor 6: Defensive position and range
    position = data.get('position', None)
    po = data.get('PO', 0)  # Putouts
    a = data.get('A', 0)  # Assists
    g = data.get('G', 0)  # Games played
    if g > 0:
        range_factor = (po + a) / g
    else:
        range_factor = 0
    
    # Mapping the position to fielding score
    if position == "P":
        f6 = 0
    elif position == "C":
        f6 = 1
    elif position == "1B":
        f6 = 2
    elif position == "2B":
        f6 = ((range_factor / 4.8) * 6)
    elif position == "3B":
        f6 = ((range_factor / 2.65) * 4)
    elif position == "SS":
        f6 = ((range_factor / 4.6) * 7)
    elif position in ["LF", "CF", "RF", "OF"]:
        f6 = ((range_factor / 2.0) * 6)
    else:
        f6 = 0  # If position is unknown

    # Ensure each factor is between 0 and 10
    factors = [min(max(f, 0), 10) for f in [f1, f2, f3, f4, f5, f6]]

    # Weights for each factor (tweak as needed)
    weights = {
        'f1': 0.4,  # Stolen base percentage
        'f2': 0.18, # Stolen base attempts
        'f3': 0.15, # Triples
        'f4': 0.04,  # Runs scored
        'f5': 0.05, # GIDP
        'f6': 0.04  # Defensive range
    }

    # Calculate weighted speed score
    weighted_speed_score = (
        factors[0] * weights['f1'] +
        factors[1] * weights['f2'] +
        factors[2] * weights['f3'] +
        factors[3] * weights['f4'] +
        factors[4] * weights['f5'] +
        factors[5] * weights['f6']
    )

    # Normalize the final score to the 0-10 range
    return round(weighted_speed_score, 2)

def calculate_fielding_rating(rtot_yr):
    """
    Calculate the fielding rating for non-pitchers based on RTOT/YR.
    Average RTOT/YR = -1.61, StdDev = 15.42
    """

    avg_rtot_yr = -1.61  # Mean of RTOT/YR
    std_dev_rtot_yr = 15.42  # Standard deviation

    # Calculate the number of standard deviations away from the mean
    z_score = (rtot_yr - avg_rtot_yr) / std_dev_rtot_yr

    # Map Z-scores to fielding ratings:
    if z_score >= 1:  # 1 SD above mean (~top 16%)
        return 2  # Excellent fielder
    elif z_score >= 0.2:  # ~Top 50%
        return 1  # Above average fielder
    elif z_score >= -0.2:  # Middle range (~34% around the mean)
        return 0  # Average fielder
    elif z_score >= -1:  # ~Bottom 50%
        return -1  # Below average fielder
    else:  # More than 1 SD below mean (~bottom 16%)
        return -2  # Poor fielder

def calculate_batting_splits():
    pass

def calculate_pitcher_fielding_rating(rdrs_yr):
    """
    Calculate the fielding rating for pitchers based on RDRS/YR.
    Average RDRS/YR = -0.68, StdDev = 11.99
    """

    avg_rdrs_yr = -0.68  # Mean of RDRS/YR
    std_dev_rdrs_yr = 11.99  # Standard deviation

    # Calculate the number of standard deviations away from the mean
    z_score = (rdrs_yr - avg_rdrs_yr) / std_dev_rdrs_yr

    # Map Z-scores to pitcher fielding ratings:
    if z_score >= 1:  # 1 SD above mean (~top 16%)
        return 2  # Excellent fielding pitcher
    elif z_score >= 0.2:  # ~Top 50%
        return 1  # Above average fielding pitcher
    elif z_score >= -0.2:  # Middle range (~34% around the mean)
        return 0  # Average fielding pitcher
    elif z_score >= -1:  # ~Bottom 50%
        return -1  # Below average fielding pitcher
    else:  # More than 1 SD below mean (~bottom 16%)
        return -2  # Poor fielding pitcher

def calculate_player_x_hr(player_hr, team_hr, lineup_spot, total_games_played=162):
    """
    Calculate the extra home run (X-HR) range for a player.
    
    Parameters:
    player_hr (int): Total home runs for the player.
    team_hr (int): Total home runs for the team.
    lineup_spot (int or str): The player's lineup spot (1-9 or A-F for dugout players).
    total_games_played (int): Total games played in the season (default: 162).
    
    Returns:
    int: The number of possibilities for an extra HR in a scale of 11-66.
    """
    
    power_chart = {
        1: 2, 2: 3, 3: 5, 4: 6, 5: 4,
        6: 3, 7: 2, 8: 2, 9: 1,
        10: 0, 11: 0, 12: 0, 13: 0, 14: 0, 15: 0  # Bench players
    }

    # Step 1: Calculate the expected Power Bonus HRs for the team
    team_power_bonus = 54  # Assuming 162 games

    # Step 2: Calculate the team's remaining HRs after power bonus
    remaining_team_hr = team_hr - team_power_bonus

    # Step 3: Get the player's expected Power Bonus HRs based on lineup spot
    if lineup_spot not in power_chart:
        return 0  # Default for invalid lineup spots
    
    player_power_bonus = (power_chart[lineup_spot] * total_games_played) // 216

    # Step 4: Calculate the remaining HRs the player must get from X-HR system
    remaining_player_hr = player_hr - player_power_bonus

    if remaining_player_hr <= 0:
        return 0  # No extra HRs to allocate

    # Step 5: Calculate player's share of team HRs for X-HR calculation
    player_x_hr_percentage = remaining_player_hr / remaining_team_hr

    # Step 6: Scale player's X-HR percentage to a dice range of 11-66 (36 possibilities)
    x_hr_possibilities = round(player_x_hr_percentage * 36)

    return x_hr_possibilities
    
'''
def calculate_starter_value(xfip):
    if xfip <= 2.50:
        return 7.0
    elif xfip <= 2.75:
        return 6.5
    elif xfip <= 3.00:
        return 6.0
    elif xfip <= 3.25:
        return 5.5
    elif xfip <= 3.50:
        return 5.0
    elif xfip <= 3.75:
        return 4.5
    elif xfip <= 4.00:
        return 4.0
    elif xfip <= 4.25:
        return 3.5
    elif xfip <= 4.50:
        return 3.0
    elif xfip <= 4.75:
        return 2.5
    elif xfip <= 5.00:
        return 2.0
    elif xfip <= 5.25:
        return 1.5
    else:
        return 1.0
'''

    # Calculate start value based on ERA
def calculate_start_value(era, games_started):
    # If no games started, return 0
    if games_started < 2:
        return 0.5
    
    # Assign start value based on updated ERA thresholds
    if era <= 2.50:
        return 7.0
    elif era <= 3.00:
        return 6.5
    elif era <= 3.50:
        return 6.0
    elif era <= 4.00:
        return 5.5
    elif era <= 4.50:
        return 5.0
    elif era <= 5.00:
        return 4.5
    elif era <= 5.50:
        return 4.0
    elif era <= 6.00:
        return 3.5
    elif era <= 6.50:
        return 3.0
    elif era <= 7.00:
        return 2.5
    elif era <= 8.00:
        return 2.0
    elif era <= 9.00:
        return 1.5
    else:
        return 1.0

def calculate_endurance(ip, cg, gs):
    innings = ip - (9 * cg)
    games_not_completed = gs - cg
    if games_not_completed > 0:
        innings_per_game = (innings / games_not_completed)
    else:
        innings_per_game = 0  # or another appropriate default value

    if innings_per_game <= 4.16:
        return 0
    elif innings_per_game <= 4.50:
        return 1
    elif innings_per_game <= 4.83:
        return 2
    elif innings_per_game <= 5.16:
        return 3
    elif innings_per_game <= 5.50:
        return 4
    elif innings_per_game <= 5.83:
        return 5
    elif innings_per_game <= 6.16:
        return 6
    elif innings_per_game <= 6.50:
        return 7
    elif innings_per_game >= 6.51:
        return 8

def calculate_rest(gs):
    if gs >= 40:
        return 3
    elif gs >= 30:
        return 4
    elif gs >= 20:
        return 5
    elif gs >= 15:
        return 6
    elif gs >= 10:
        return 7
    elif gs <= 9:
        return 8

def calculate_cg_rating(cg, gs):
    if gs > 0:
        cg_percentage = (cg / gs) * 100  # Convert to percentage
    else:
        cg_percentage = 0  # Handle the case when there are no games started

    
    if cg_percentage >= 16.20:
        return 611
    elif cg_percentage >= 15.74:
        return 612
    elif cg_percentage >= 15.28:
        return 613
    elif cg_percentage >= 14.81:
        return 614
    elif cg_percentage >= 14.35:
        return 615
    elif cg_percentage >= 13.89:
        return 616
    elif cg_percentage >= 13.43:
        return 621
    elif cg_percentage >= 12.96:
        return 622
    elif cg_percentage >= 12.50:
        return 623
    elif cg_percentage >= 12.04:
        return 624
    elif cg_percentage >= 11.57:
        return 625
    elif cg_percentage >= 11.11:
        return 626
    elif cg_percentage >= 10.65:
        return 631
    elif cg_percentage >= 10.19:
        return 632
    elif cg_percentage >= 9.72:
        return 633
    elif cg_percentage >= 9.26:
        return 634
    elif cg_percentage >= 8.80:
        return 635
    elif cg_percentage >= 8.33:
        return 636
    elif cg_percentage >= 7.87:
        return 641
    elif cg_percentage >= 7.41:
        return 642
    elif cg_percentage >= 6.94:
        return 643
    elif cg_percentage >= 6.48:
        return 644
    elif cg_percentage >= 6.02:
        return 645
    elif cg_percentage >= 5.56:
        return 646
    elif cg_percentage >= 5.09:
        return 651
    elif cg_percentage >= 4.63:
        return 652
    elif cg_percentage >= 4.17:
        return 653
    elif cg_percentage >= 3.70:
        return 654
    elif cg_percentage >= 3.24:
        return 655
    elif cg_percentage >= 2.78:
        return 656
    elif cg_percentage >= 2.31:
        return 661
    elif cg_percentage >= 1.85:
        return 662
    elif cg_percentage >= 1.39:
        return 663
    elif cg_percentage >= 0.93:
        return 664
    elif cg_percentage >= 0.46:
        return 665
    else:
        return 666

def calculate_sho_rating(sho, gs):
    if gs > 0:
        sho_percentage = (sho / gs) * 100  # Convert to percentage
    else:
        sho_percentage = 0
    
    if sho_percentage >= 16.20:
        return 611
    elif sho_percentage >= 15.74:
        return 612
    elif sho_percentage >= 15.28:
        return 613
    elif sho_percentage >= 14.81:
        return 614
    elif sho_percentage >= 14.35:
        return 615
    elif sho_percentage >= 13.89:
        return 616
    elif sho_percentage >= 13.43:
        return 621
    elif sho_percentage >= 12.96:
        return 622
    elif sho_percentage >= 12.50:
        return 623
    elif sho_percentage >= 12.04:
        return 624
    elif sho_percentage >= 11.57:
        return 625
    elif sho_percentage >= 11.11:
        return 626
    elif sho_percentage >= 10.65:
        return 631
    elif sho_percentage >= 10.19:
        return 632
    elif sho_percentage >= 9.72:
        return 633
    elif sho_percentage >= 9.26:
        return 634
    elif sho_percentage >= 8.80:
        return 635
    elif sho_percentage >= 8.33:
        return 636
    elif sho_percentage >= 7.87:
        return 641
    elif sho_percentage >= 7.41:
        return 642
    elif sho_percentage >= 6.94:
        return 643
    elif sho_percentage >= 6.48:
        return 644
    elif sho_percentage >= 6.02:
        return 645
    elif sho_percentage >= 5.56:
        return 646
    elif sho_percentage >= 5.09:
        return 651
    elif sho_percentage >= 4.63:
        return 652
    elif sho_percentage >= 4.17:
        return 653
    elif sho_percentage >= 3.70:
        return 654
    elif sho_percentage >= 3.24:
        return 655
    elif sho_percentage >= 2.78:
        return 656
    elif sho_percentage >= 2.31:
        return 661
    elif sho_percentage >= 1.85:
        return 662
    elif sho_percentage >= 1.39:
        return 663
    elif sho_percentage >= 0.93:
        return 664
    elif sho_percentage >= 0.46:
        return 665
    else:
        return 666

'''
def calculate_relief_value(xfip):
    if xfip <= 2.17:
        return -5
    elif xfip <= 2.42:
        return -4
    elif xfip <= 2.67:
        return -3
    elif xfip <= 2.92:
        return -2
    elif xfip <= 3.17:
        return -1
    elif xfip <= 3.42:
        return 0
    elif xfip <= 3.75:
        return 1
    elif xfip <= 4.25:
        return 2
    elif xfip <= 4.75:
        return 3
    elif xfip <= 5.25:
        return 4
    elif xfip <= 6.00:
        return 5
    elif xfip <= 6.75:
        return 6
    else:
        return 7
'''

def calculate_relief_value(era):
    if era <= 2.17:
        return -5
    elif era <= 2.42:
        return -4
    elif era <= 2.67:
        return -3
    elif era <= 2.92:
        return -2
    elif era <= 3.17:
        return -1
    elif era <= 3.42:
        return 0
    elif era <= 3.75:
        return 1
    elif era <= 4.25:
        return 2
    elif era <= 4.75:
        return 3
    elif era <= 5.25:
        return 4
    elif era <= 6.00:
        return 5
    elif era <= 6.75:
        return 6
    else:
        return 7

def calculate_pitching_splits():
    pass

def calculate_fatigue(games_relieved):
    if games_relieved >= 60:
        return 1
    elif games_relieved >= 50:
        return 2
    elif games_relieved >= 40:
        return 3
    elif games_relieved >= 30:
        return 4   
    elif games_relieved <= 29:
        return 5

def calculate_injury_rating():
    # Generate a random float between 0 and 1
    random_number = random.random()
    
    # Adjust injury rating based on the random number
    if random_number <= 0.1:
        return -3
    elif random_number <= 0.25:
        return -2
    elif random_number <= 0.4:
        return -1
    elif random_number <= 0.5:
        return 0
    elif random_number <= 0.75:
        return 1
    elif random_number <= 0.95:
        return 2
    else:  # This covers random_number > 0.95 up to 1.0
        return 3

def apply_bat_ratings(batting_df):
    # Ensure 'BA' (batting average), 'SLG' (slugging percentage), and 'SB' (stolen bases) are numeric
    if 'BA' in batting_df.columns:
        batting_df['BA'] = pd.to_numeric(batting_df['BA'], errors='coerce')

    if 'SLG' in batting_df.columns:
        batting_df['SLG'] = pd.to_numeric(batting_df['SLG'], errors='coerce')

    if 'SB' in batting_df.columns:
        batting_df['SB'] = pd.to_numeric(batting_df['SB'], errors='coerce')

    # Apply ratings only if columns exist
    if 'BA' in batting_df.columns:
        batting_df['bat_rating'] = batting_df['BA'].apply(calculate_bat_rating)

    if 'SLG' in batting_df.columns:
        batting_df['power_rating'] = batting_df['SLG'].apply(calculate_power_rating)

    if 'SB' in batting_df.columns:
        batting_df['speed_rating'] = batting_df['SB'].apply(calculate_speed_rating)

    return batting_df

def apply_pitching_ratings(pitching_df):
    try:
        # Ensure relevant columns are numeric before applying calculations
        if 'ERA' in pitching_df.columns:
            pitching_df['ERA'] = pd.to_numeric(pitching_df['ERA'], errors='coerce')
        
        if 'IP' in pitching_df.columns:
            pitching_df['IP'] = pd.to_numeric(pitching_df['IP'], errors='coerce')
        
        if 'CG' in pitching_df.columns:
            pitching_df['CG'] = pd.to_numeric(pitching_df['CG'], errors='coerce')
        
        if 'GS' in pitching_df.columns:
            pitching_df['GS'] = pd.to_numeric(pitching_df['GS'], errors='coerce')
        
        if 'SHO' in pitching_df.columns:
            pitching_df['SHO'] = pd.to_numeric(pitching_df['SHO'], errors='coerce')

        # Apply ratings
        if 'ERA' in pitching_df.columns:
            pitching_df['start_value'] = pitching_df['ERA'].apply(calculate_start_value)

        # Debug and ensure all values are numeric and scalar before applying calculations
        if 'IP' in pitching_df.columns and 'CG' in pitching_df.columns and 'GS' in pitching_df.columns:
            pitching_df['endurance'] = pitching_df.apply(
                lambda row: (
                    print(f"Processing pitcher {row['player_id']} - IP: {row['IP']}, CG: {row['CG']}, GS: {row['GS']}"),  # Debug statement
                    calculate_endurance(
                        row['IP'] if pd.notnull(row['IP']) and not isinstance(row['IP'], pd.Series) else 0,
                        row['CG'] if pd.notnull(row['CG']) and not isinstance(row['CG'], pd.Series) else 0,
                        row['GS'] if pd.notnull(row['GS']) and not isinstance(row['GS'], pd.Series) else 0
                    )
                )[1], axis=1)  # Apply only the second part of the tuple (the calculation)

        if 'GS' in pitching_df.columns:
            pitching_df['rest'] = pitching_df['GS'].apply(
                lambda x: calculate_rest(x) if pd.notnull(x) and not isinstance(x, pd.Series) else 0
            )

        if 'CG' in pitching_df.columns and 'GS' in pitching_df.columns:
            pitching_df['CG_rating'] = pitching_df.apply(
                lambda row: calculate_cg_rating(
                    row['CG'] if pd.notnull(row['CG']) and not isinstance(row['CG'], pd.Series) else 0,
                    row['GS'] if pd.notnull(row['GS']) and not isinstance(row['GS'], pd.Series) else 0
                ), axis=1)

        if 'SHO' in pitching_df.columns and 'GS' in pitching_df.columns:
            pitching_df['SHO_rating'] = pitching_df.apply(
                lambda row: calculate_sho_rating(
                    row['SHO'] if pd.notnull(row['SHO']) and not isinstance(row['SHO'], pd.Series) else 0,
                    row['GS'] if pd.notnull(row['GS']) and not isinstance(row['GS'], pd.Series) else 0
                ), axis=1)

        if 'ERA' in pitching_df.columns:
            pitching_df['relief_value'] = pitching_df['ERA'].apply(calculate_relief_value)

        if 'G' in pitching_df.columns and 'GS' in pitching_df.columns:
            pitching_df['fatigue'] = pitching_df.apply(
                lambda row: calculate_fatigue(
                    row['G'] - row['GS'] if pd.notnull(row['G']) and pd.notnull(row['GS']) and not isinstance(row['G'], pd.Series) and not isinstance(row['GS'], pd.Series) else 0
                ), axis=1)

    except KeyError as e:
        print(f"Error applying pitching ratings: {e}")
    
    return pitching_df

def apply_fielding_ratings(fielding_df):
    try:
        # Ensure 'Rtot/yr' exists and is numeric before applying calculation
        if 'Rtot/yr' in fielding_df.columns:
            fielding_df['Rtot/yr'] = pd.to_numeric(fielding_df['Rtot/yr'], errors='coerce')
            
            # Apply fielding rating based on the 'Rtot/yr' field (previously 'tz_runs_total')
            fielding_df['fielding_rating'] = fielding_df['Rtot/yr'].apply(calculate_fielding_rating)
    
    except KeyError as e:
        print(f"Error applying fielding ratings: {e}")
    
    return fielding_df

def calculate_team_x_hr(total_hr, games_played):
    """
    Calculate the X-HR chart based on the total home runs and number of games played.
    Each team will have a unique distribution of dice possibilities based on their home runs.

    Parameters:
    total_hr (int): Total team home runs for the season.
    games_played (int): Total games played in the season (154 or 162).

    Returns:
    dict: X-HR chart where keys are the extra HR values and values are the dice ranges.
    """

    # Subtract the expected power bonus HRs
    if games_played == 162:
        hr_bonus = 54
    elif games_played == 154:
        hr_bonus = 51
    else:
        raise ValueError("Unsupported number of games. Only 154 or 162 games are allowed.")

    # Calculate remaining HRs after subtracting the bonus
    remaining_hr = total_hr - hr_bonus

    # Proportional scaling factor based on remaining HRs
    scaled_hr = round((remaining_hr / games_played) * 216)

    # Define the dice roll ranges for each HR category
    ranges = {
        "3": (111, 125),  # 11 possibilities for 3 HR
        "2": (126, 241),  # 44 possibilities for 2 HR
        "1": (242, 261),  # 12 possibilities for 1 HR
        "0": (262, 666)   # The rest, no HR
    }

    # Assign HR totals to the ranges
    x_hr_chart = {
        "3": min(scaled_hr, (ranges["3"][1] - ranges["3"][0] + 1) * 3),  # Mapping to 3 HR (33 possibilities)
        "2": min(max(scaled_hr - 33, 0), (ranges["2"][1] - ranges["2"][0] + 1) * 2),  # Mapping to 2 HR (88 possibilities)
        "1": min(max(scaled_hr - 33 - 88, 0), (ranges["1"][1] - ranges["1"][0] + 1) * 1),  # Mapping to 1 HR (12 possibilities)
        "0": (ranges["0"][1] - ranges["0"][0] + 1)  # Mapping to 0 HR (remaining possibilities)
    }

    return x_hr_chart

def calculate_unearned_runs_chart(total_unearned_runs, games_played):
    """
    Calculate the unearned runs allowed grid based on total unearned runs and games played.

    Parameters:
    total_unearned_runs (float): Total unearned runs allowed by the team during the season.
    games_played (int): Total games played by the team during the season.

    Returns:
    dict: Unearned runs allowed grid where keys are dice sums and values are the expected unearned runs for that roll.
    """
    # Step 1: Calculate average unearned runs per game
    avg_unearned_runs_per_game = total_unearned_runs / games_played
    
    # Define dice roll probability percentages for each dice sum (normalized)
    dice_distribution = {
        3: 0.5,  # Most rare roll (1, 1, 1)
        4: 1.4,
        5: 2.8,
        6: 4.6,
        7: 6.9,  # Most common roll
        8: 9.7,
        9: 11.6,
        10: 12.5  # High probability rolls (combos like 3, 3, 4, etc.)
    }

    # Step 2: Calculate total percentage sum for scaling
    total_percent = sum(dice_distribution.values())

    # Step 3: Calculate the total number of runs to distribute
    total_runs_to_distribute = int(round(avg_unearned_runs_per_game * games_played))

    # Step 4: Initialize the unearned runs grid with 0
    unearned_runs_grid = {dice_sum: 0 for dice_sum in dice_distribution.keys()}

    # **NEW**: Introduce a small random chance for zero unearned runs (prioritizing high-probability dice rolls)
    zero_run_chance = random.choice([7, 9, 10])  # Choose which dice sum will get a '0'

    # Step 5: Distribute runs according to the dice distribution probabilities
    runs_left = total_runs_to_distribute

    for dice_sum, percentage in dice_distribution.items():
        # If this dice sum was selected for a zero unearned run chance, skip the allocation
        if dice_sum == zero_run_chance:
            unearned_runs_grid[dice_sum] = 0
            continue

        # Calculate the portion of runs to allocate to this dice sum
        dice_run_allocation = round((percentage / total_percent) * total_runs_to_distribute)

        # Ensure we don't exceed the number of runs left to distribute
        if dice_run_allocation > runs_left:
            dice_run_allocation = runs_left

        # Cap the runs for any dice sum at 3 (as per game rule)
        dice_run_allocation = min(dice_run_allocation, 3)

        # Assign the runs to the grid
        unearned_runs_grid[dice_sum] = dice_run_allocation

        # Subtract the allocated runs from the total runs left
        runs_left -= dice_run_allocation

        # If no runs left to distribute, break the loop
        if runs_left <= 0:
            break

    return unearned_runs_grid

def calculate_eye_rating(bb_pct, k_pct):
    """
    Calculate the eye rating based on BB% and K%, using Z-scores.
    BB% should be high, and K% should be low for a good rating.
    
    Parameters:
    bb_pct (float): Walk percentage (BB%)
    k_pct (float): Strikeout percentage (K%)
    
    Returns:
    int: Eye rating as a modifier from -3 to +3
    """
    # League-wide average and standard deviation for BB% and K%
    league_avg_bb_pct = 0.0817  # Average BB%
    league_avg_k_pct = 0.2544  # Average K%
    stdev_bb_pct = 0.0308 # Standard deviation BB%
    stdev_k_pct = 0.0617  # Standard deviation K%
    
    # Ensure bb_pct and k_pct are floats (in case they are tuples or other types)
    if isinstance(bb_pct, tuple) or isinstance(k_pct, tuple):
        print(f"Error: bb_pct or k_pct is a tuple. bb_pct: {bb_pct}, k_pct: {k_pct}")
        return 0
    
    # Calculate Z-scores for BB% and K%
    bb_z = (bb_pct - league_avg_bb_pct) / stdev_bb_pct
    k_z = (k_pct - league_avg_k_pct) / stdev_k_pct
    
    # We want a high BB% and a low K%, so subtract K% Z-score from BB% Z-score
    combined_z = bb_z - k_z
    
    # Scale the combined Z-score to the range [-3, +3]
    # If the Z-score range is wide, scale it more conservatively.
    # For example, clip the Z-scores to a reasonable range (-2, 2) for better distribution.
    scaled_eye_rating = np.clip(combined_z / 2.0, -3, 3)  # Adjust scale if necessary
    
    return round(scaled_eye_rating)

def calculate_extra_innings_range():
    pass

def scale_rating(z_score, max_rating=2):
    """
    Scale a z-score into a range between -max_rating and +max_rating.
    
    Parameters:
    z_score (float): The calculated z-score based on the metric's average and standard deviation.
    max_rating (int): The maximum rating (default is 2).

    Returns:
    int: A rating between -max_rating and +max_rating.
    """
    if isinstance(z_score, pd.Series):  # Ensure it's scalar
        z_score = z_score.item()

    # Scale the z-score into -2 to +2 (or -3 to +3, depending on your scaling logic)
    if z_score >= 1:
        return 2
    elif z_score >= 0.5:
        return 1
    elif z_score >= -0.5:
        return 0
    elif z_score >= -1:
        return -1
    else:
        return -2

def calculate_manager_ratings(manager_info):
    """
    Calculate the manager's ratings based on team performance metrics.
    
    Parameters:
    manager_info (Series or DataFrame): The row(s) containing the manager's data.
    
    Returns:
    dict: Manager ratings for batting, pitching, defense, and bench.
    """
    # Check if the required fields are present
    if manager_info.empty:
        return {
            "manager_batting": 0,
            "manager_pitching": 0,
            "manager_defense": 0,
            "manager_bench": 0
        }

    # Now safely extract values, defaulting to 0 if not found
    ops = manager_info.get('OPS', 0)
    fip = manager_info.get('FIP', 0)
    rdrs = manager_info.get('rdrs', 0)
    ph_rbi = manager_info.get('PH_RBI', 0)
    ph_lev = manager_info.get('PH_LEV', 0)
    ph_ba = manager_info.get('PH_BA', 0)

    # Ensure all values are scalar
    ops = ops.item() if isinstance(ops, pd.Series) else ops
    fip = fip.item() if isinstance(fip, pd.Series) else fip
    rdrs = rdrs.item() if isinstance(rdrs, pd.Series) else rdrs
    ph_rbi = ph_rbi.item() if isinstance(ph_rbi, pd.Series) else ph_rbi
    ph_lev = ph_lev.item() if isinstance(ph_lev, pd.Series) else ph_lev
    ph_ba = ph_ba.item() if isinstance(ph_ba, pd.Series) else ph_ba

    # Calculate Z-scores for each metric
    ops_z_score = (ops - 0.734) / 0.038  # For OPS
    fip_z_score = (4.33 - fip) / 0.529   # For FIP (lower is better)
    rdrs_z_score = (rdrs - 9.1) / 36.78  # For RDRS
    ph_rbi_z_score = (ph_rbi - 15.9) / 7.53
    ph_lev_z_score = (ph_lev - 1.6) / 0.22
    ph_ba_z_score = (ph_ba - 0.2161) / 0.0408

    # Calculate ratings based on Z-scores
    manager_batting = scale_rating(ops_z_score)
    manager_pitching = scale_rating(fip_z_score)
    manager_defense = scale_rating(rdrs_z_score)
    
    # Combine pinch-hitting metrics into a single bench rating
    bench_combined_z_score = (ph_rbi_z_score + ph_lev_z_score + ph_ba_z_score) / 3
    manager_bench = scale_rating(bench_combined_z_score)

    return {
        "manager_batting": manager_batting,
        "manager_pitching": manager_pitching,
        "manager_defense": manager_defense,
        "manager_bench": manager_bench
    }

def calculate_gm_ratings(gm_info):
    """
    Calculate the GM's ratings based on team performance metrics (batting and pitching wins above average, and payroll).

    Parameters:
    gm_info (Series or DataFrame): The row(s) containing the GM's data.

    Returns:
    dict: GM ratings for batting and pitching.

    potential ideas for calcs:
    https://tht.fangraphs.com/general-manager-rankings/
    https://bleacherreport.com/articles/187779-beane-counting-how-to-grade-a-general-manager
    """
    # Constants for calculating Z-scores (mean and standard deviation)
    bat_waa_avg = 0.04
    pit_waa_avg = -0.006666667
    payroll_avg = 154941212.7
    bat_waa_std = 9.966931531
    pit_waa_std = 5.481878191
    payroll_std = 63054512.56
    
    # Extract GM metrics, default to 0 if not present
    bat_waa = gm_info.get('bat_waa', 0)
    pit_waa = gm_info.get('pit_waa', 0)
    payroll = gm_info.get('payroll', payroll_avg)

    # Calculate Z-scores
    bat_waa_z_score = (bat_waa - bat_waa_avg) / bat_waa_std
    pit_waa_z_score = (pit_waa - pit_waa_avg) / pit_waa_std
    payroll_z_score = (payroll - payroll_avg) / payroll_std

    # Weigh the WAA scores inversely by payroll Z-score (lower payroll = better weight)
    weighted_bat_waa_z_score = bat_waa_z_score - payroll_z_score * 0.1
    weighted_pit_waa_z_score = pit_waa_z_score - payroll_z_score * 0.1

    # Scale the Z-scores to ratings from -2 to +2
    gm_batting = scale_rating(weighted_bat_waa_z_score)
    gm_pitching = scale_rating(weighted_pit_waa_z_score)

    return {
        "gm_batting": gm_batting,
        "gm_pitching": gm_pitching
    }

def home_field_advantage(home_wins, home_losses, away_wins, away_losses):
    """
    Calculate the home field advantage based on the team's home and away win-loss records.
    
    Parameters:
    home_wins (int): Number of home wins.
    home_losses (int): Number of home losses.
    away_wins (int): Number of away wins.
    away_losses (int): Number of away losses.

    Returns:
    float: Home field advantage value mapped to a scale of +3 to -3.
    """
    # Calculate home and away win percentages
    home_win_percentage = home_wins / (home_wins + home_losses)
    away_win_percentage = away_wins / (away_wins + away_losses)
    
    # Calculate the raw home field advantage (difference between home and away percentages)
    raw_home_field_advantage = home_win_percentage - away_win_percentage

    # Normalize the raw home field advantage difference to a scale of -3 to +3
    # A difference of ±0.06 (e.g., 0.530 - 0.470) would correspond to ±3
    max_difference = 0.08  # +/- 0.06 is the max difference we'd expect
    normalized_advantage = (raw_home_field_advantage / max_difference) * 3
    
    # Clip the value to ensure it stays within the -3 to +3 range
    home_field_advantage_value = max(min(normalized_advantage, 3), -3)

    return home_field_advantage_value # Return the value rounded to 1 decimal place

def extract_team_splits(team_df):
    """
    Extract home and away win-loss records from the TEAM sheet DataFrame.
    
    Parameters:
    team_df (DataFrame): The DataFrame containing team data.

    Returns:
    dict: A dictionary with home and away win-loss records.
    """
    home_wins = int(team_df['home_w'].values[0])
    home_losses = int(team_df['home_l'].values[0])
    away_wins = int(team_df['away_w'].values[0])
    away_losses = int(team_df['away_l'].values[0])
    
    return {
        'home_wins': home_wins,
        'home_losses': home_losses,
        'away_wins': away_wins,
        'away_losses': away_losses
    }

def stadium_value_rating(batting_factor, pitching_factor):
    """
    Calculate a stadium rating based on the park factors (batting and pitching).
    The stadium_value is a tuple (batting_factor, pitching_factor).
    A neutral factor of 100 should correspond to 0, and values range from -3 to +3.
    """    
    # Average the batting and pitching park factors
    average_factor = (batting_factor + pitching_factor) / 2

    # Map the average factor to a range of -3 to +3 (0 is neutral for factor 100)
    if average_factor < 90:
        return -3  # Extreme Pitcher's Park
    elif 90 <= average_factor < 94:
        return -2  # Strong Pitcher's Park
    elif 94 <= average_factor < 97:
        return -1  # Mild Pitcher's Park
    elif 97 <= average_factor <= 103:
        return 0  # Neutral Park
    elif 103 < average_factor <= 106:
        return 1  # Mild Hitter's Park
    elif 106 < average_factor <= 110:
        return 2  # Strong Hitter's Park
    elif average_factor > 110:
        return 3  # Extreme Hitter's Park

def extract_park_factors(team_df):
    """
    Extract park factors (batting and pitching) from the TEAM sheet.
    
    Parameters:
    team_df (DataFrame): The DataFrame containing team data.
    
    Returns:
    tuple: A tuple of (batting_factor, pitching_factor).
    """
    batting_factor = int(team_df['pf_batting'].values[0])
    pitching_factor = int(team_df['pf_pitching'].values[0])

    return batting_factor, pitching_factor

def map_market_size_to_value(attendance_rank):
    """
    Map attendance rank (1 to 15) to a market size value ranging from -3 to +3.
    
    Parameters:
    attendance_rank (int): The rank of the team's attendance out of the total teams in the league.
    
    Returns:
    int: The market size value, where higher ranks correlate with larger market size.
    """
    if attendance_rank == 1:
        return 3
    elif 2 <= attendance_rank <= 4:
        return 2
    elif 5 <= attendance_rank <= 8:
        return 1
    elif attendance_rank == 9:
        return 0
    elif 10 <= attendance_rank <= 12:
        return -1
    elif 13 <= attendance_rank <= 14:
        return -2
    else:
        return -3

def extract_attendance_rank(team_df):
    """
    Extract the attendance rank from the TEAM sheet.

    Parameters:
    team_df (DataFrame): The DataFrame containing team data.

    Returns:
    int: The attendance rank for the team.
    """
    attendance_rank = int(team_df['rank'].values[0])
    return attendance_rank

def imperial_to_metric(height, weight):
    """
    Converts height in feet and inches to centimeters, and weight in pounds to kilograms.
    
    Parameters:
    height (str): Height in the format "6' 2\""
    weight (int): Weight in pounds (lbs)
    
    Returns:
    tuple: Height in centimeters (rounded) and weight in kilograms (rounded)
    """
    # Convert height from "6' 2\"" to feet and inches
    try:
        feet, inches = height.split("' ")
        feet = int(feet)
        inches = int(inches.replace("\"", ""))
        # Convert to centimeters
        height_cm = round((feet * 30.48) + (inches * 2.54))  # Rounded to whole number
    except Exception as e:
        print(f"Error converting height {height}: {e}")
        height_cm = None  # Handle invalid heights

    # Convert weight from pounds to kilograms
    weight_kg = round(weight * 0.453592)  # Rounded to whole number

    return height_cm, weight_kg

def create_player_json(player_row, ranker, starters_threshold, batting_df, fielding_df, team_bat_df, year):
    """
    Generate a JSON object for a player, using data from CSV files.
    
    Parameters:
    player_row (Series): The row from the roster DataFrame containing player information.
    ranker (int): The player's rank for determining starter/bench role.
    starters_threshold (int): The threshold for defining starters vs bench players.
    batting_df (DataFrame): The batting stats DataFrame.
    fielding_df (DataFrame): The fielding stats DataFrame.
    team_bat_df (DataFrame): The team batting stats DataFrame (for team HRs).
    year (int): The year of the player's season.
    
    Returns:
    dict: A JSON object representing the player's information.
    """
    
    # Player identification and basic info
    player_id = player_row['player_id']
    name = normalize_name(player_row['name'])
    team = player_row['team']
    games_played = 162  # Default to 162 games played

    # Look up additional player data from the roster DataFrame
    roster_row = roster_df[roster_df['player_id'] == player_id].squeeze()

    # Extract basic info from the roster
    age = roster_row.get('age', 0)
    origin = roster_row.get('birth', 'Unknown')
    bats = roster_row.get('bats', 'Unknown')
    height = roster_row.get('ht', 0)
    weight = roster_row.get('wt', 0)
    experience = roster_row.get('yrs', 0)
    
    # Ensure salary is numeric and round it
    salary = pd.to_numeric(roster_row.get('salary', 0), errors='coerce')
    salary = 0 if pd.isna(salary) else round(salary)
 
    # Determine role: Starter or Bench
    role = "Starter" if ranker <= starters_threshold else "Bench"

    fielder_row = fielding_df[fielding_df['player_id'] == player_id].squeeze()
    primary_position = fielder_row.get('position', 'Unknown')
    secondary_position = fielder_row.get('sec_position', None)
    secondary_position = "None" if pd.isna(secondary_position) else secondary_position

    # Extract batting stats for the player
    player_batting_stats = batting_df[batting_df['player_id'] == player_id].squeeze()
    player_hr = player_batting_stats.get('HR', 0)
    avg = player_batting_stats.get('BA', 0)
    slg = player_batting_stats.get('SLG', 0)
    bb_pct = player_batting_stats.get('BB%', 0)
    k_pct = player_batting_stats.get('K%', 0)
    sb = player_batting_stats.get('SB', 0)

    # Extract fielding stats for the player
    rtot_yr = fielder_row.get('rtot_yr', 0)

    # Speed rating calculation (adjust based on pre-1933 logic)
    if year < 1933:
        speed = calculate_speed_rating(sb)
    else:
        speed_data = {
            'SB': sb,
            'CS': player_batting_stats.get('CS', 0),
            'H': player_batting_stats.get('H', 0),
            '2B': player_batting_stats.get('2B', 0),
            '3B': player_batting_stats.get('3B', 0),
            'HR': player_batting_stats.get('HR', 0),
            'BB': player_batting_stats.get('BB', 0),
            'bb_pct': player_batting_stats.get('BB%', 0),
            'k_pct': player_batting_stats.get('K%', 0),
            'AB': player_batting_stats.get('AB', 0),
            'R': player_batting_stats.get('R', 0),
            'GDP': player_batting_stats.get('GDP', 0),
            'SO': player_batting_stats.get('SO', 0),
            'PO': fielder_row.get('PO', 0),
            'A': fielder_row.get('A', 0),
            'G': fielder_row.get('G', 0),
            'position': primary_position
        }
        speed = calculate_speed_score(speed_data, year)

    # Extract team HRs from TEAM_BAT sheet
    team_stats = team_bat_df[(team_bat_df['team'] == team) & (team_bat_df['year'] == year)].squeeze()
    team_hr = team_stats.get('HR', 0)
    games_played = team_stats.get('G', 162)

    # Convert height and weight
    height_cm, weight_kg = imperial_to_metric(height, weight)

    # Generate a random clutch rating within the range [-2, 2]
    clutch = max(min(int(np.random.normal(0, 1)), 2), -2)

    # Try to get splits data if available in the spreadsheet (fallback to 0)
    # These would come from columns like 'AVG_vs_L', 'AVG_vs_R', etc. if present
    splits_L = player_batting_stats.get('splits_L', 0)  # Fallback to 0
    splits_R = player_batting_stats.get('splits_R', 0)  # Fallback to 0

    # If splits columns don't exist, default to 0
    if pd.isna(splits_L):
        splits_L = 0
    if pd.isna(splits_R):
        splits_R = 0

    # Construct player JSON
    return {
        "player_id": player_id,
        "name": name,
        "age": age,
        "origin": origin,
        "bats": bats,
        "height": height_cm,
        "weight": weight_kg,
        "experience": experience,
        "role": role,
        "position": primary_position,
        "secondary_position": secondary_position,
        "batting": calculate_bat_rating(avg),
        "power": calculate_power_rating(slg),
        "eye": calculate_eye_rating(bb_pct, k_pct),
        "splits_L": int(splits_L),  # Splits vs left-handed pitchers
        "splits_R": int(splits_R),  # Splits vs right-handed pitchers
        "speed": speed,
        "fielding": calculate_fielding_rating(rtot_yr),
        "x_hr": calculate_player_x_hr(player_hr, team_hr, ranker, games_played),
        "clutch": clutch,  # Adding generated clutch rating
        "injury": calculate_injury_rating(),
        "morale": 0,
        "popularity": 0,
        "salary": salary
    }

def create_pitcher_json(player_row, pitching_df, fielding_df):
    """
    Generate a JSON object for a pitcher, using data from CSV files.

    Parameters:
    player_row (Series): The row from the roster DataFrame containing player information.
    pitching_df (DataFrame): The pitching stats DataFrame.
    fielding_df (DataFrame): The fielding stats DataFrame.

    Returns:
    dict: A JSON object representing the pitcher's information.
    """
    
    # Player identification and basic info
    player_id = player_row['player_id']  # Using 'player_id' for unique identification
    name = normalize_name(player_row['name'])

    roster_row = roster_df[roster_df['player_id'] == player_id].squeeze()
    # Extract basic info from the roster (these replace the "Unknown" fields)

    age = roster_row.get('age', 0)
    origin = roster_row.get('birth', 'Unknown')  # Country or birth data
    throws = roster_row.get('throws', 'Unknown')
    height = roster_row.get('ht', 0)
    weight = roster_row.get('wt', 0)
    experience = roster_row.get('yrs', 0)

    # Ensure salary is numeric and replace NaN with 0, then round to whole number
    salary = pd.to_numeric(roster_row.get('salary', 0), errors='coerce')
    salary = 0 if pd.isna(salary) else round(salary)

    fielder_row = fielding_df[fielding_df['player_id'] == player_id].squeeze()

    # Fetch pitching stats for the player
    player_pitching_stats = pitching_df[pitching_df['player_id'] == player_id].squeeze()
    ip = player_pitching_stats.get('IP', 0)  # Innings Pitched
    cg = player_pitching_stats.get('CG', 0)  # Complete Games
    sho = player_pitching_stats.get('SHO', 0)  # Shutouts
    gs = player_pitching_stats.get('GS', 0)  # Games Started
    g = player_pitching_stats.get('G', 0)  # Total Games Played
    era = player_pitching_stats.get('ERA', 0)  # Earned Run Average (ERA)

    # Extract fielding stats for the player
    rdrs_yr = fielder_row.get('rdrs_yr', 0)  # Defensive Runs Saved per year

    # Calculate games relieved (G - GS)
    games_relieved = g - gs

    # Determine pitcher type based on games started (SP or RP to match game expectations)
    pitcher_type = "SP" if gs > 3 else "RP"

    # Fetch fielding stats for the pitcher
    pitcher_fielding_stats = fielding_df[fielding_df['player_id'] == player_id].squeeze()
    rdrs_yr = pitcher_fielding_stats.get('rdrs_yr', 0)  # Defensive runs saved per year (Rtot_yr)

    # Convert height to cm and weight to kg
    height_cm, weight_kg = imperial_to_metric(height, weight)

    # Try to get splits data if available in the spreadsheet (fallback to 0)
    splits_L = player_pitching_stats.get('splits_L', 0)  # Fallback to 0
    splits_R = player_pitching_stats.get('splits_R', 0)  # Fallback to 0

    # If splits columns don't exist, default to 0
    if pd.isna(splits_L):
        splits_L = 0
    if pd.isna(splits_R):
        splits_R = 0

    # Generate clutch rating for pitcher (same logic as batters)
    clutch = max(min(int(np.random.normal(0, 1)), 2), -2)

    # Build the pitcher JSON object
    return {
        "player_id": player_id,
        "name": name,
        "age": age,
        "throws": throws,
        "type": pitcher_type,
        "origin": origin,
        "height": height_cm,
        "weight": weight_kg,
        "experience": experience,
        "start_value": calculate_start_value(era, gs),  # Calculate start value based on ERA
        "endurance": calculate_endurance(ip, cg, gs),  # Calculate endurance based on innings, CG, and GS
        "rest": calculate_rest(gs),  # Calculate rest based on GS
        "cg_rating": calculate_cg_rating(cg, gs),  # Complete games rating (lowercase to match game)
        "sho_rating": calculate_sho_rating(sho, gs),  # Shutouts rating (lowercase to match game)
        "splits_L": int(splits_L),  # Splits vs left-handed batters
        "splits_R": int(splits_R),  # Splits vs right-handed batters
        "relief_value": calculate_relief_value(era),  # Relief value calculation for relievers
        "fatigue": calculate_fatigue(games_relieved),  # Fatigue calculation for relievers
        "fielding": calculate_pitcher_fielding_rating(rdrs_yr),  # Fielding rating for pitchers
        "clutch": clutch,  # Clutch rating for pitcher
        "injury": calculate_injury_rating(),
        "morale": 0,  # Placeholder for morale rating
        "popularity": 0,  # Placeholder for popularity rating
        "salary": salary,  # Player's salary
    }

def create_personnel_json(manager_info, gm_info):
    # Extract manager ID and name from manager_info
    manager_id = manager_info.get('manager_id', 'Unknown')
    manager_name = manager_info.get('manager_name', 'Unknown')
    manager_age = manager_info.get('manager_age', 0)
    # Calculate the manager ratings based on performance metrics
    manager_ratings = calculate_manager_ratings(manager_info)

    gm_id = gm_info.get('gm_id', 'Unknown')
    gm_name = gm_info.get('gm_name', 'Unknown')
    gm_age = gm_info.get('gm_age', 0)
    gm_ratings = calculate_gm_ratings(gm_info)

    # Create the personnel JSON object, including manager ratings
    return {
        "gm_id": gm_id,
        "gm_name": gm_name,
        "gm_age": gm_age,
        "gm_batting": gm_ratings.get('gm_batting', 0),
        "gm_pitching": gm_ratings.get('gm_pitching', 0),
        "manager_id": manager_id,
        "manager_name": manager_name,
        "manager_age": manager_age,
        "manager_batting": manager_ratings.get('manager_batting', 0),  # Batting rating
        "manager_pitching": manager_ratings.get('manager_pitching', 0),  # Pitching rating
        "manager_defense": manager_ratings.get('manager_defense', 0),   # Defense rating
        "manager_bench": manager_ratings.get('manager_bench', 0),       # Bench rating
        "manager_salary": 0     # Placeholder for now
    }

def create_team_json(team_id, city, name, ballpark_name, stadium_value, market_size, team_x_hr, unearned_runs_chart, home_field_advantage, weather_value, players):
    """
    Create a JSON object for the team, including city, name, stadium values, and other metrics.

    Parameters:
    team_id (str): The unique ID for the team (constructed from team abbreviation and year).
    city (str): The city of the team.
    name (str): The full name of the team.
    players (list): List of player JSON objects.
    ballpark_name (str): The name of the team's ballpark.
    stadium_value (tuple): A tuple containing the batting and pitching factors for the stadium.
    market_size (int): The calculated market size based on attendance rank.
    team_x_hr (dict): The X-HR chart for the team.
    unearned_runs_chart (dict): The unearned runs chart for the team.
    home_field_advantage (float): Home field advantage value.

    Returns:
    dict: A JSON object representing the team.
    """
    return {
        "team_id": team_id,
        "team_city": city,
        "team_name": name,
        "ballpark_name": ballpark_name,
        "stadium_value": stadium_value,  # (batting_factor, pitching_factor)
        "weather_value": weather_value,  # Weather value
        "market_size": market_size,
        "team_x_hr": team_x_hr,  # X-HR chart
        "unearned_runs_chart": unearned_runs_chart,  # Unearned runs chart
        "home_field_advantage": home_field_advantage,  # Home field advantage value
        "players": players  # JSON data for players
    }

def convert_to_python_types(data):
    """
    Recursively convert NumPy, pandas, and tuple objects to native Python types.
    """
    if isinstance(data, dict):
        return {convert_to_python_types(key): convert_to_python_types(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [convert_to_python_types(item) for item in data]
    elif isinstance(data, tuple):
        return [convert_to_python_types(item) for item in data]  # Convert tuples to lists
    elif isinstance(data, (np.integer, int)):
        return int(data)
    elif isinstance(data, (np.floating, float)):
        return float(data)
    elif isinstance(data, (np.ndarray, pd.Series, pd.Index)):
        return convert_to_python_types(data.tolist())
    elif isinstance(data, pd.DataFrame):
        return data.to_dict(orient='records')  # Convert DataFrame to a list of dictionaries
    else:
        return data

def process_team_roster(excel_file, save_directory):
    # Declare globals so we can update them
    global team_bat_df, batting_df, fielding_df, pitching_df, roster_df, manager_df, general_manager_df

    # Load Excel sheets
    print("Loading Excel sheets...")
    team_df = pd.read_excel(excel_file, sheet_name='TEAM')
    team_bat_df = pd.read_excel(excel_file, sheet_name='TEAM_BAT')  # Set global
    batting_df = pd.read_excel(excel_file, sheet_name='BAT')  # Set global
    pitching_df = pd.read_excel(excel_file, sheet_name='PIT')  # Set global
    fielding_df = pd.read_excel(excel_file, sheet_name='FIELD')  # Set global
    fielding_df.columns = fielding_df.columns.str.lower()  # Normalize to lowercase
    roster_df = pd.read_excel(excel_file, sheet_name='ROSTER')  # Set global
    manager_df = pd.read_excel(excel_file, sheet_name='MANAGER')  # Set global
    gm_df = pd.read_excel(excel_file, sheet_name='GM')  # Load GM data
    general_manager_df = gm_df  # Set global

    team_pitching_df = pd.read_excel(excel_file, sheet_name='TEAM_PIT')

    # Remove duplicates based on 'player_id', keeping the last entry
    batting_df = batting_df.drop_duplicates(subset='player_id', keep='last')
    pitching_df = pitching_df.drop_duplicates(subset='player_id', keep='last')
    fielding_df = fielding_df.drop_duplicates(subset='player_id', keep='last')
    roster_df = roster_df.drop_duplicates(subset='player_id', keep='last')
    manager_df = manager_df.drop_duplicates(subset='manager_id', keep='last')
    gm_df = gm_df.drop_duplicates(subset='gm_id', keep='last')

    # Loop through each unique team in the BAT sheet
    for _, manager_row in manager_df.iterrows():
        team_abbr = manager_row['team']
        year = manager_row['year']
        print(f"Processing team: {team_abbr} for year {year}")

        # Extract relevant team metadata
        team_info = team_df[team_df['team'] == team_abbr].iloc[0]
        team_id = team_info['team_id']  # Use the 'team_id' field directly
        city = team_info['city']
        team_name = team_info['team_name']
        ballpark_name = team_info['ballpark']
        games_played = int(team_info['g'])
        attendance_rank = int(team_info['rank'])

        # Extract GM information for this team and year
        gm_info = gm_df[(gm_df['team'] == team_abbr) & (gm_df['year'] == year)]
        if gm_info.empty:
            print(f"Warning: No GM information found for team {team_abbr} in {year}.")
            gm_info = pd.Series()  # Empty series as a placeholder
        else:
            gm_info = gm_info.iloc[0]  # Extract the first matching row

        # Extract park factors (batting_factor, pitching_factor)
        batting_factor = team_info['pf_batting']
        pitching_factor = team_info['pf_pitching']

        # Calculate stadium value rating (pass the factors directly)
        stadium_value = stadium_value_rating(batting_factor, pitching_factor)

        weather_value = 0 # Default weather value

        # Calculate market size
        market_size = map_market_size_to_value(attendance_rank)

        # Calculate team home run stats
        team_hr = int(batting_df.loc[batting_df['team'] == team_abbr, 'HR'].sum())  # Summing all HRs for the team
        team_x_hr = calculate_team_x_hr(team_hr, games_played)

        # Extract team pitching data from the team pitching DataFrame (TEAM_PIT)
        team_pitching_stats = team_pitching_df[team_pitching_df['team'] == team_abbr].iloc[0]

        # Calculate unearned runs: Total Runs (R) - Earned Runs (ER)
        total_r = int(team_pitching_stats['R'])  # Team's total runs allowed
        total_er = int(team_pitching_stats['ER'])  # Team's total earned runs allowed
        total_unearned_runs = total_r - total_er

        # Debugging step: Print unearned runs per team
        print(f"Team: {team_abbr}, Total Runs: {total_r}, Earned Runs: {total_er}, Unearned Runs: {total_unearned_runs}")

        # Pass the total unearned runs to the calculation function
        unearned_runs_chart = calculate_unearned_runs_chart(total_unearned_runs, games_played)
        print(f"Team: {team_abbr}, Total Unearned Runs: {total_unearned_runs}, Games Played: {games_played}, Unearned Runs per Game: {unearned_runs_chart}")

        # Calculate home field advantage from the splits
        home_wins = int(team_info['home_w'])
        home_losses = int(team_info['home_l'])
        away_wins = int(team_info['away_w'])
        away_losses = int(team_info['away_l'])
        home_field_advantage_value = home_field_advantage(home_wins, home_losses, away_wins, away_losses)

        # Initialize lists for players and minors
        players_json = []
        pitchers_json = []
        minors_json = []

        # ----------- Process Batters: Starters (1-9), Bench (10-15), Minors (16-19) -----------
        starters_threshold = 9
        bench_threshold = 15
        minors_batters_threshold = 19

        # Process Batters: Starters (1-9), Bench (10-15)
        for _, player_row in batting_df[(batting_df['team'] == team_abbr) & (batting_df['rk'] <= bench_threshold)].iterrows():
            ranker = player_row['rk']
            position_summary = player_row['pos']
            is_pitcher = 'P' in position_summary
            
            try:
                if not is_pitcher:
                    player_json = create_player_json(player_row, ranker, starters_threshold, batting_df, fielding_df, team_bat_df, year=2023)
                    players_json.append(player_json)
            except Exception as e:
                print(f"Error processing player {player_row['player_id']}: {e}")

        # Process Minor League Batters (16-19)
        for _, player_row in batting_df[(batting_df['team'] == team_abbr) & (batting_df['rk'].between(bench_threshold + 1, minors_batters_threshold))].iterrows():
            try:
                player_json = create_player_json(player_row, player_row['rk'], starters_threshold, batting_df, fielding_df, team_bat_df, year=2023)
                minors_json.append(player_json)
            except Exception as e:
                print(f"Error processing minor league batter {player_row['player_id']}: {e}")

        # Process pitchers, limit to the first 10 pitchers ordered by 'rk'
        pitchers_count = 0  # Initialize a counter for pitchers
        max_pitchers = 10  # Limit to 10 pitchers
        minors_pitchers_start = 11
        minors_pitchers_end = 14

        # Process pitchers
        pitchers_count = 0
        for _, pitcher_row in pitching_df[(pitching_df['team'] == team_abbr) & (pitching_df['rk'] <= max_pitchers)].iterrows():
            try:
                pitcher_json = create_pitcher_json(pitcher_row, pitching_df, fielding_df)
                pitchers_json.append(pitcher_json)
                pitchers_count += 1
            except Exception as e:
                print(f"Error processing pitcher {pitcher_row['player_id']}: {e}")

        # Process Minor League Pitchers (11-14)
        for _, pitcher_row in pitching_df[(pitching_df['team'] == team_abbr) & (pitching_df['rk'].between(minors_pitchers_start, minors_pitchers_end))].iterrows():
            try:
                player_json = create_pitcher_json(pitcher_row, pitching_df, fielding_df)
                minors_json.append(player_json)
            except Exception as e:
                print(f"Error processing minor league pitcher {pitcher_row['player_id']}: {e}")

            try:    
                # Extract values needed for the calculations
                games_started = pitcher_row.get('GS', 0)
                complete_games = pitcher_row.get('CG', 0)
                innings = pitcher_row.get('IP', 0)  # Get innings pitched
                
                if games_started > 0:  # Starter
                    games_not_completed = max(games_started - complete_games, 1)  # Prevent divide by zero
                    innings_per_game = innings / games_not_completed if games_not_completed > 0 else 1
                    endurance = calculate_endurance(innings_per_game, complete_games, games_started)

                    # Handle starters: no fatigue, only endurance
                    player_json = create_pitcher_json(pitcher_row, pitching_df, fielding_df)  # Remove 'endurance' argument
                    player_json['endurance'] = endurance  # Add endurance to the player JSON

                else:  # Reliever
                    fatigue = calculate_fatigue(innings)  # Assuming some function exists for relievers
                    player_json = create_pitcher_json(pitcher_row, pitching_df, fielding_df)  # Remove 'fatigue' argument
                    player_json['fatigue'] = fatigue  # Add fatigue to the player JSON

                # Append player JSON to list
                players_json.append(player_json)

                pitchers_count += 1  # Increment the counter for pitchers
            
            except Exception as e:
                print(f"Error processing pitcher {pitcher_row['player_id']}: {e}")

        # Debugging step: Print manager ID and name
        print(f"Manager ID: {manager_row['manager_id']}, Manager Name: {manager_row['manager_name']}")
        
        # Calculate manager ratings
        manager_ratings = calculate_manager_ratings(manager_row)
        gm_ratings = calculate_gm_ratings(manager_row)

        # Create the personnel JSON for the manager
        personnel_json = create_personnel_json(manager_row, gm_info)
        personnel_json.update(manager_ratings)  # Add calculated ratings to the JSON

        # Create team JSON
        team_json = create_team_json(
            team_id=team_id,
            city=city,
            name=team_name,
            ballpark_name=ballpark_name,
            stadium_value=stadium_value,
            weather_value=weather_value,
            market_size=market_size,
            team_x_hr=team_x_hr,
            unearned_runs_chart=unearned_runs_chart,
            home_field_advantage=home_field_advantage_value,
            players=players_json
        )

        team_json["pitchers"] = pitchers_json
        team_json['minors'] = minors_json

        # Add personnel data (manager information)
        team_json['personnel'] = personnel_json

        # Print the JSON for debugging
        print(f"Personnel JSON: {personnel_json}")

        # Convert all data types in team_json to Python native types
        print(f"Types in team_json: {[type(value) for key, value in team_json.items()]}")
        team_json = convert_to_python_types(team_json)

        # Save team data to a JSON file in the specified directory (team_abbr_year.json)
        json_filename = os.path.join(save_directory, f"team_id_{team_id}.json")
        with open(json_filename, "w") as json_file:
            json.dump(team_json, json_file, indent=4)

        print(f"Team data saved to {json_filename}")

if __name__ == "__main__":
    # Use centralized paths from data_paths_pennant_fever
    excel_file = str(MLB_2023_FILE)
    save_directory = str(PENNANT_FEVER_JSON_MLB_DIR)

    # Ensure output directory exists
    os.makedirs(save_directory, exist_ok=True)

    print(f"Input file: {excel_file}")
    print(f"Output directory: {save_directory}")

    process_team_roster(excel_file, save_directory)
