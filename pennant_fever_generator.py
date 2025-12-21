import pandas as pd
import numpy as np
import random
import random as r
import scipy.stats as stats
from datetime import datetime
from geopy.distance import geodesic
import logging
import os
import sys
import json
import re
from pathlib import Path

# Add common folder to sys.path for shared modules
COMMON_PATH = Path.home() / "Documents/_code/common"
sys.path.insert(0, str(COMMON_PATH))

from data_paths_pennant_fever import (
    PENNANT_FEVER_LOGS_LEAGUE_GEN_DIR,
    CORPORATE_NAMES_FILE,
    LEAGUE_NAME_SOURCES_FILE,
    FIRST_NAMES_FILE,
    SURNAMES_FILE,
    SCHOOLS_REGISTER_FILE,
    TEAM_GENERATION_FILE,
    PENNANT_FEVER_LEAGUE_FILES_DIR,
    SCOUTING_REPORTS_FILE,
)
from common_logger import setup_logger

# need to skew specialists to be mostly LHP
# go to a universal 2-8 scale for all ratings (then maybe we can convert to 20-80 scale in the main game?)
# penalties for age (either too young or too old) may be a little too harsh, consider trebling down the amounts (maybe go to decimal points? so instead of 1 point per year its 0.1 or 0.25 etc, depending on quality of archetype)
# need to add league.json export
# L/R splits built in for players? so then we eliminate generic pen/bonus for L/R matchups here def get_batting_value in the main game; could do this via one general rating you would use that would be for each player and not a hard coded value depending on handedness like we have now. use our modifier system so we'd have -2 to 2 vs opposite handedness so this way you could occasionally have reverse splits guy. also can auto assign -2 or +2 to platoon archetype players (would need to alter handedness mod mechanic in actual game as well)
# markov chain league name gen - now that its setup, get in there and tweak how the markov chain works along with using our corp names and league name parts
# machine learning japanese corponames (alternate version of corp_name_gen3.5.py) - need training data
# name file: need chatbot to separate del and van surnames eg Delprado should be Del Prado, Vanhorne should be Van Horne etc (found: Jose Jaimesbenitez)
# when we generate personnel, we are using playerbio/NameGen and end up generating data we dont need/use, how to skip steps we dont need, for personnel
# we seem to be getting a low percentage of dominican players
# expand on scouting report text in json file for the scoutingreport generator. need better logic in terms of connecting sentences so theyre not all starting with. He has or He's etc
# instead of my markov process to generate league/division names, can we link (and/or) adapt my corponames gen to pull names from. can also use for stadium names, team names, owners etc

'''
generate more granular ratings (3 decimal points eg 0.456, 1.234 etc) these number will get added through the play resolution process in the main game and eventually we round off the runs anyway but granularity differentiates players more than the coarse ratings
class BatterProfile:
    #... other methods and initializations ...

    def generate_attribute(self, range_tuple, attribute_name, age_affected=True):
        """Generate a float rating with three decimal points based on a given range."""
        floor, ceiling = range_tuple

        # Generate a float rating within the range
        if self.archetype.name in ["star", "5-tool"]:
            # High-quality archetypes skew towards the ceiling
            rating = self.skewed_random(floor, ceiling, skew="high")
        elif self.archetype.name in ["scrub", "career minor leaguer", "september callup", "injury replacement"]:
            # Low-quality archetypes skew towards the floor
            rating = self.skewed_random(floor, ceiling, skew="low")
        else:
            # Neutral or moderate archetypes have a balanced distribution
            rating = np.random.uniform(floor, ceiling)

        # Clamp the values within the floor/ceiling bounds and round to 3 decimal places
        return round(np.clip(rating, floor, ceiling), 3)

******* for some reason some players are having multiple calls for assigned grade_prob: which changes from original to the one at the end
*********** so the multiple iterations are just the us going through each probability in the grades and seeing if its TRUE so here .254 is grade4, which is correct
2024-10-03 16:30:12,404 - DEBUG - LINE 1353 - Fetched archetype probabilities for Lorain Hs (type: HS): {'grade1_prob': 0.05, 'grade2_prob': 0.1, 'grade3_prob': 0.2, 'grade4_prob': 0.3, 'grade5_prob': 0.4, 'grade6_prob': 0.55, 'grade7_prob': 0.65, 'grade8_prob': 0.8, 'grade9_prob': 0.9, 'grade10_prob': 0.97}
2024-10-03 16:30:12,404 - DEBUG - LINE 1357 - Random Probability for Jim Jones: 0.2543732512701309
2024-10-03 16:30:12,404 - DEBUG - LINE 1367 - Jim Jones assigned grade_prob: grade1_prob for archetype mapping.
2024-10-03 16:30:12,404 - DEBUG - LINE 1367 - Jim Jones assigned grade_prob: grade1_prob for archetype mapping.
2024-10-03 16:30:12,404 - DEBUG - LINE 1367 - Jim Jones assigned grade_prob: grade1_prob for archetype mapping.
2024-10-03 16:30:12,404 - DEBUG - LINE 1363 - Jim Jones assigned grade_prob: grade4_prob for archetype mapping.
2024-10-03 16:30:12,404 - DEBUG - LINE 1390 - Jim Jones (Batter) Archetype: injury replacement
2024-10-03 16:30:12,404 - DEBUG - LINE 1395 - Generating ratings for Jim Jones
2024-10-03 16:30:12,404 - DEBUG - LINE 549 - Generating ratings for batter: Jim Jones, Archetype: injury replacement



******* ALSO for some reason we are generating a player, process stops, then we generate another player completely eg
2024-10-03 16:30:12,586 - DEBUG - LINE 1338 - Creating player for position: CF
2024-10-03 16:30:12,611 - DEBUG - LINE 150 - Generated player bio: Steve Yiapis, Race: white, Origin: USA
2024-10-03 16:30:12,611 - DEBUG - LINE 276 - Generated position for Steve Yiapis: Selected Position CF
2024-10-03 16:30:12,611 - DEBUG - LINE 369 - Generated age for Steve Yiapis (CF): 34
2024-10-03 16:30:12,612 - DEBUG - LINE 406: Generated School Name: San Diego State, School Type: COL
2024-10-03 16:30:12,612 - DEBUG - LINE 168 - Generated school for Steve Yiapis: School Name: San Diego State, School Type: COL
2024-10-03 16:30:12,612 - DEBUG - LINE 281 - Starting to generate secondary position for Steve Yiapis
2024-10-03 16:30:12,612 - DEBUG - LINE 314 - RNG for CF: 0.06107924006554821
2024-10-03 16:30:12,612 - DEBUG - LINE 321 - Possible positions for CF: ['LF', 'RF', 'OF', 'IF']
2024-10-03 16:30:12,612 - DEBUG - LINE 330 - STEP 3 possible positions: ['LF', 'RF', 'OF', 'IF'] and weights: [0.4, 0.3, 0.2, 0.1]
2024-10-03 16:30:12,612 - DEBUG - LINE 331 - Generated secondary position for CF: OF
2024-10-03 16:30:12,612 - DEBUG - LINE 332 - Finished generating secondary position for Steve Yiapis / P: CF / SP: OF


2024-10-03 16:30:12,619 - DEBUG - LINE 150 - Generated player bio: Kevin Timmons, Race: black, Origin: USA
2024-10-03 16:30:12,619 - DEBUG - LINE 276 - Generated position for Kevin Timmons: Selected Position CF
2024-10-03 16:30:12,619 - DEBUG - LINE 369 - Generated age for Kevin Timmons (CF): 33
2024-10-03 16:30:12,619 - DEBUG - LINE 406: Generated School Name: Michigan, School Type: COL
2024-10-03 16:30:12,619 - DEBUG - LINE 168 - Generated school for Kevin Timmons: School Name: Michigan, School Type: COL
2024-10-03 16:30:12,620 - DEBUG - LINE 281 - Starting to generate secondary position for Kevin Timmons
2024-10-03 16:30:12,620 - DEBUG - LINE 314 - RNG for CF: 0.7660348465089046
2024-10-03 16:30:12,620 - DEBUG - LINE 317 - No secondary generated for CF because RNG (0.7660348465089046) > chance (0.15).
2024-10-03 16:30:12,620 - DEBUG - Line 1657 - PlayerProfile - Position: CF, School Type: COL
2024-10-03 16:30:12,620 - DEBUG - LINE 1344 - Generated bio for Kevin Timmons - Position: CF, School: Michigan, Origin: USA
2024-10-03 16:30:12,620 - DEBUG - LINE 1349 - Player Kevin Timmons school: Michigan, School type: COL
2024-10-03 16:30:12,620 - DEBUG - LINE 444 - Entering get_archetype_probs - School: Michigan, Type: COL

'''
# LOGGERS

# Ensure log directory exists
PENNANT_FEVER_LOGS_LEAGUE_GEN_DIR.mkdir(parents=True, exist_ok=True)

# Configure logging using centralized setup
logger = setup_logger(
    name="FictionalGenerator",
    log_dir=PENNANT_FEVER_LOGS_LEAGUE_GEN_DIR,
    prefix="fic_gen",
    console_level=logging.INFO
)

# START LOADING DATA

# Load your corporate sponsor names and league name parts
corporate_names_df = pd.read_excel(CORPORATE_NAMES_FILE)
league_name_sources_df = pd.read_excel(LEAGUE_NAME_SOURCES_FILE)

# Assuming the columns in your Excel files are 'corporate_name' and 'league_name_part'
corporate_names = corporate_names_df['corporate_name'].tolist()
league_name_parts = league_name_sources_df['league_name_part'].tolist()


# Load the datasets once
first_names_df = pd.read_excel(FIRST_NAMES_FILE)
surnames_df = pd.read_excel(SURNAMES_FILE)
high_school_df = pd.read_excel(SCHOOLS_REGISTER_FILE, sheet_name='HS')
college_df = pd.read_excel(SCHOOLS_REGISTER_FILE, sheet_name='COL')

# Load city data from CITY sheet
city_data = pd.read_excel(TEAM_GENERATION_FILE, sheet_name='CITY')

# Load nickname data from NICKNAMES sheet
nickname_data = pd.read_excel(TEAM_GENERATION_FILE, sheet_name='NICKNAMES')

def sanitize_filename(name):
    """Sanitize the team name to create a valid filename for macOS."""
    # Replace any character that is not alphanumeric, underscore, or hyphen with an underscore
    sanitized = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
    
    # Ensure the filename doesn't start with a dot (hidden file in macOS)
    if sanitized.startswith('.'):
        sanitized = '_' + sanitized
    
    # Trim the filename if it's too long (macOS has a limit of 255 characters)
    return sanitized[:255]

def convert_numpy_types(obj):
    """Recursively convert NumPy types to native Python types."""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()  # Convert NumPy arrays to Python lists
    elif isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(i) for i in obj]
    elif isinstance(obj, Archetype):
        return {k: convert_numpy_types(v) for k, v in obj.__dict__.items()}
    else:
        return obj

class NameGen:
    def __init__(self):
        # Initialize fields to be populated
        self.first_name = None
        self.surname = None
        self.race = None
        self.age = None
        self.height = None
        self.weight = None
        self.origin = None
        self.school = None
        self.position = None
        self.secondary_position = None
        self.bats = None
        self.throws = None

    def generate_bio(self, position=None):
        # Generate first name and race
        first_name_row = first_names_df.sample(weights='scaled_weight').iloc[0]
        self.first_name = (first_name_row['name'] if pd.isna(first_name_row['diminutive']) or np.random.rand() >= 0.3 else first_name_row['diminutive']).title()
        self.race = self.generate_race(first_name_row, ['white', 'black', 'hispanic', 'asian', 'other'])

        # Generate surname based on race
        self.surname = self.generate_random_name_matching_race(surnames_df, self.race).title()

        self.origin = self.generate_origin(self.race)

        # Log key details about the generated player
        logger.debug(f"LINE 150 - Generated player bio: {self.first_name} {self.surname}, Race: {self.race}, Origin: {self.origin}")

        # Generate height, weight, and position together, but keep the provided primary position intact
        self.height, self.weight, generated_position = self.generate_height_weight_and_position(position)

        # Only use the generated position if no primary position was explicitly passed
        self.position = position if position is not None else generated_position

        # Generate bats/throws based on position
        self.bats, self.throws = self.generate_bats_throws()

        # Generate age based on position
        self.age = self.generate_age(self.position)

        # Generate school and assign school_name and school_type
        school_name, school_type = self.generate_school_with_type(self.origin)
        self.school = school_name  # Set the full school name for later use
        self.school_type = school_type  # Explicitly store the school type
        logger.debug(f"LINE 168 - Generated school for {self.first_name} {self.surname}: School Name: {self.school}, School Type: {self.school_type}")

        # Generate secondary position based on the final primary position
        self.secondary_position = self.generate_secondary_position(self.position)

        return {
            "name": f"{self.first_name} {self.surname}",
            "race": self.race.capitalize(),
            "age": self.age,
            "height": self.height,
            "weight": self.weight,
            "origin": self.origin,
            "school": self.school,
            "school_type": self.school_type,
            "position": self.position,  # This will be the correct primary position
            "secondary_position": self.secondary_position,
            "bats": self.bats,
            "throws": self.throws
        }

    def generate_race(self, row, race_columns):
        total_weight = row[race_columns].sum()
        if total_weight == 0:
            return 'other'
        normalized_weights = row[race_columns] / total_weight
        rnd = np.random.rand()
        cumulative_weight = 0
        for race, weight in normalized_weights.items():
            cumulative_weight += weight
            if rnd <= cumulative_weight:
                return race
        return race_columns[-1]

    def generate_random_name_matching_race(self, df, race):
        filtered_df = df[df[race] > 0]
        surname = filtered_df.sample(weights=filtered_df[race]).iloc[0]['name'] # surname should not be identical to first name
        return surname

    def generate_origin(self, race):
        countries = [
            ('USA', 8500, ['white', 'black', 'hispanic', 'asian', 'other']),
            ('Dominican Republic', 843, ['hispanic']),
            ('Venezuela', 451, ['hispanic']),
            ('Puerto Rico', 258, ['hispanic']),
            ('Mexico', 133, ['hispanic']),
            ('Cuba', 126, ['hispanic']),
            ('Canada', 123, ['white', 'black', 'hispanic', 'asian', 'other']),
            ('Japan', 73, ['asian']),
            ('Panama', 59, ['hispanic']),
            ('Australia', 32, ['white', 'black', 'hispanic', 'asian', 'other']),
            ('Colombia', 29, ['hispanic']),
            ('South Korea', 28, ['asian']),
            ('Taiwan', 16, ['asian']),
            ('Curacao', 16, ['black']),
            ('Nicaragua', 15, ['hispanic']),
            ('Virgin Islands', 10, ['black']),
            ('United Kingdom', 9, ['white', 'black', 'hispanic', 'asian']),
            ('Netherlands', 7, ['white']),
            ('Aruba', 6, ['black']),
            ('Bahamas', 6, ['black']),
            ('Brazil', 5, ['hispanic', 'black']),
            ('Jamaica', 4, ['black']),
            ('Honduras', 2, ['hispanic']),
            ('France', 1, ['white', 'black', 'hispanic', 'other']),
            ('Spain', 1, ['hispanic', 'white']),
            ('Germany', 1, ['white']),
            ('Italy', 1, ['white']),
        ]

        filtered_countries = [country for country in countries if race in country[2]]
        total_frequency = sum(country[1] for country in filtered_countries)
        rnd = np.random.randint(0, total_frequency)

        for country, frequency, _ in filtered_countries:
            if rnd < frequency:
                return country
            rnd -= frequency

            logger.debug(f"LINE 246 - Origin for {self.first_name} {self.surname}")
        return 'Other'

    def generate_height_weight_and_position(self, position=None):
        """Simultaneously generate height, weight, and position based on predefined ranges."""

        # If position is 'SP' or 'RP', treat it as a pitcher
        if position in ['SP', 'RP']:
            height = np.random.uniform(185, 200)  # Example range for pitcher height
            weight = np.random.uniform(90, 105)   # Example range for pitcher weight
            return round(height), round(weight), "P"  # Set position to "P" for pitchers

        # Position-dependent ranges for batters
        position_ranges = {
            'DH': (189, 200, 95, 110), 'LF': (180, 190, 85, 95), 'CF': (175, 185, 80, 90), 
            'RF': (180, 190, 85, 100), '3B': (180, 190, 85, 95), 'SS': (175, 185, 75, 85),
            '2B': (170, 180, 75, 85), '1B': (185, 200, 90, 110), 'C': (180, 190, 90, 100)
        }

        # If a primary position is provided, use it to get the height/weight range
        if position in position_ranges:
            min_height, max_height, min_weight, max_weight = position_ranges[position]
        else:
            # Randomly select a position if no specific position is provided
            position = random.choice(list(position_ranges.keys()))
            min_height, max_height, min_weight, max_weight = position_ranges[position]

        # Generate height and weight within the range
        height = np.random.uniform(min_height, max_height)
        weight = np.random.uniform(min_weight, max_weight)
        logger.debug(f"LINE 276 - Generated position for {self.first_name} {self.surname}: Selected Position {position}")

        return round(height), round(weight), position  # Return the selected position

    def generate_secondary_position(self, position):
        logger.debug(f"LINE 281 - Starting to generate secondary position for {self.first_name} {self.surname}")
        # Define the possible secondary positions for each primary position
        secondary_position_options = {
            'C': (['1B', 'LF', 'RF', 'IF'], [0.4, 0.3, 0.2, 0.1]),
            '1B': (['3B', 'IF', 'OF', 'C'], [0.4, 0.3, 0.2, 0.1]),
            '2B': (['SS', '3B', 'IF', 'OF'], [0.3, 0.3, 0.3, 0.1]),
            '3B': (['2B', 'SS', 'OF', 'IF'], [0.6, 0.2, 0.1, 0.1]),
            'SS': (['2B', '3B', 'IF', 'OF'], [0.5, 0.2, 0.2, 0.1]),
            'LF': (['CF', 'RF', 'OF', 'IF'], [0.4, 0.3, 0.2, 0.1]),
            'CF': (['LF', 'RF', 'OF', 'IF'], [0.4, 0.3, 0.2, 0.1]),
            'RF': (['LF', 'CF', 'OF', 'IF'], [0.4, 0.3, 0.2, 0.1]),
            'DH': (['1B', 'OF', '3B', 'C'], [0.6, 0.2, 0.1, 0.1])  # DH always gets a secondary
        }

        # Define the chance a player has a secondary position based on the primary position
        chance_of_secondary = {
            'C': 0.1,
            '1B': 0.18,
            '2B': 0.2,
            '3B': 0.18,
            'SS': 0.15,
            'LF': 0.3,
            'CF': 0.15,
            'RF': 0.3,
            'DH': 1.0  # DH always gets a secondary
        }

        # No secondary position for pitchers
        if position in ['P', 'SP', 'RP']:
            return None
        
        # Step 1: Generate an RNG and compare to the chance_of_secondary for the position
        rng = random.random()  # Generates a number between 0 and 1
        logger.debug(f"LINE 314 - RNG for {position}: {rng}")

        if rng > chance_of_secondary.get(position, 0.0):
            logger.debug(f"LINE 317 - No secondary generated for {position} because RNG ({rng}) > chance ({chance_of_secondary[position]}).")
            return None

        possible_positions, weights = secondary_position_options.get(position, ([], []))
        logger.debug(f"LINE 321 - Possible positions for {position}: {possible_positions}")

        # Check if there are any possible secondary positions
        if not possible_positions:
            logger.debug(f"LINE 325 - No possible secondary positions for {position}.")
            return None

        # Step 3: Ensure the secondary position is not the same as the primary position
        secondary_position = random.choices(possible_positions, weights=weights)[0]
        logger.debug(f"LINE 330 - STEP 3 possible positions: {possible_positions} and weights: {weights}")
        logger.debug(f"LINE 331 - Generated secondary position for {position}: {secondary_position}")
        logger.debug(f"LINE 332 - Finished generating secondary position for {self.first_name} {self.surname} / P: {position} / SP: {secondary_position}")
        return secondary_position

    def generate_bats_throws(self):
        handedness_probabilities = {
            'switch_hit_throw_left': 0.0026, 'bat_right_throw_left': 0.0251,
            'bat_left_throw_left': 0.1826, 'switch_hit_throw_right': 0.0299,
            'bat_left_throw_right': 0.1188, 'bat_right_throw_right': 0.6411
        }

        rnd = np.random.rand()
        cumulative_prob = 0
        for combo, prob in handedness_probabilities.items():
            cumulative_prob += prob
            if rnd <= cumulative_prob:
                if combo == 'switch_hit_throw_left':
                    return 'S', 'L'
                elif combo == 'bat_right_throw_left':
                    return 'R', 'L'
                elif combo == 'bat_left_throw_left':
                    return 'L', 'L'
                elif combo == 'switch_hit_throw_right':
                    return 'S', 'R'
                elif combo == 'bat_left_throw_right':
                    return 'L', 'R'
                elif combo == 'bat_right_throw_right':
                    return 'R', 'R'
        return 'R', 'R'

    def generate_age(self, position):
        age_distribution = {
            'Starting Pitcher': (27, 4), 'Relief Pitcher': (28, 4), 'Catcher': (29, 3),
            'First Baseman': (30, 3), 'Second Baseman': (28, 4), 'Shortstop': (27, 4),
            'Third Baseman': (28, 4), 'Outfielder': (28, 4), 'Designated Hitter': (31, 3)
        }
        mean_age, std_age = age_distribution.get(position, (28, 4))
        age = round(np.random.normal(mean_age, std_age))
        logger.debug(f"LINE 369 - Generated age for {self.first_name} {self.surname} ({position}): {age}")
        return max(18, min(age, 40))

    def generate_age_personnel(self):
        """Generate a skewed age distribution for personnel (managers, GMs) between 40 and 75, with a median around 50."""
        mean_age = 50
        std_dev = 8

        # Generate age using a skewed normal distribution, clipped between 40 and 75
        age = np.random.normal(mean_age, std_dev)
        
        # Cap the range at 40 and 75, and make higher ages rare
        age = np.clip(age, 40, 75)
        
        # If the age is 68 or higher, make them rarer by applying another filter
        if age >= 68:
            age = np.random.choice([age, np.random.uniform(40, 67)], p=[0.2, 0.8])

        return int(age)

    def generate_school_with_type(self, origin):
        """Generate a school name along with its type (HS or COL) based on the player's origin."""
        if origin != 'USA':
            return "International", "INT"  # Return both school name and type for international players

        probabilities = {'high_school': 0.47, 'college': 0.53}
        draft_origin = np.random.choice(list(probabilities.keys()), p=list(probabilities.values()))

        if draft_origin == 'high_school':
            school_row = high_school_df.sample(weights=high_school_df['players']).iloc[0]
            school_name = f"{school_row['school_name'].strip().title()}"
            school_type = 'HS'
        else:
            school_row = college_df.sample(weights=college_df['players']).iloc[0]
            school_name = school_row['school_name'].strip().title()
            school_type = 'COL'

        logger.debug(f"LINE 406 - Generated School Name: {school_name}, School Type: {school_type}")
        return school_name, school_type  # Return both name and type

class Archetype:
    def __init__(self, name, 
                 contact_range=None, power_range=None, eye_range=None, splits_range=None, speed_range=None, fielding_range=None, 
                 potential_range=None, 
                 start_value_range=None, endurance_range=None, rest_range=None, cg_rating_range=None, 
                 sho_rating_range=None, relief_value_range=None, fatigue_range=None,
                 dev_ceiling_age=25, decline_age=32):
        self.name = name
        
        # Batter-specific ranges
        self.contact_range = contact_range
        self.power_range = power_range
        self.eye_range = eye_range
        self.splits_range = splits_range
        self.speed_range = speed_range
        self.fielding_range = fielding_range
        self.potential_range = potential_range
        
        # Pitcher-specific ranges
        self.start_value_range = start_value_range
        self.endurance_range = endurance_range
        self.rest_range = rest_range
        self.cg_rating_range = cg_rating_range
        self.sho_rating_range = sho_rating_range
        self.relief_value_range = relief_value_range
        self.fatigue_range = fatigue_range
        
        # Development and decline
        self.dev_ceiling_age = dev_ceiling_age
        self.decline_age = decline_age

    @staticmethod
    def get_archetype_probs(school_name, school_type):
        logger.debug(f"LINE 444 - Entering get_archetype_probs - School: {school_name}, Type: {school_type}")
        
        # Handle international schools directly based on school_type
        if school_type == "INT":
            logger.debug(f"LINE 448 - International school detected. Using baseline probabilities.")
            return {
                'grade1_prob': 0.15, 'grade2_prob': 0.3, 'grade3_prob': 0.4,
                'grade4_prob': 0.5, 'grade5_prob': 0.6, 'grade6_prob': 0.7,
                'grade7_prob': 0.85, 'grade8_prob': 0.95, 'grade9_prob': 0.98,
                'grade10_prob': 0.99
            }

        # Determine if it's a high school or college (normalize the case)
        if school_type in ['HS', 'hs', 'high school', 'highschool']:
            school_df = high_school_df
        else:
            school_df = college_df
        logger.debug(f"LINE 458 - School type: {school_type}, School DataFrame: {school_df}")

        # Find matching rows after cleaning
        matching_rows = school_df[school_df['school_name'].str.strip().str.lower() == school_name.strip().lower()]
        logger.debug(f"LINE 462 - Matching rows for school '{school_name}' in {school_type}: {matching_rows} - School DataFrame: {school_df}")

        if matching_rows.empty:
            # If no matching school is found, use default probabilities
            logger.debug(f"LINE 466 - Warning: School '{school_name}' not found in {school_type}. Using default probabilities.")
            return {
                'grade1_prob': 0.15, 'grade2_prob': 0.3, 'grade3_prob': 0.4,
                'grade4_prob': 0.5, 'grade5_prob': 0.6, 'grade6_prob': 0.7,
                'grade7_prob': 0.85, 'grade8_prob': 0.95, 'grade9_prob': 0.98,
                'grade10_prob': 0.99
            }

        # Return the grade probabilities from the matching row
        school_row = matching_rows.iloc[0]
        logger.debug(f"LINE 476 - Found school '{school_name}' with probabilities: {school_row[['grade1_prob', 'grade10_prob']]}")
        return {
            'grade1_prob': school_row['grade1_prob'], 
            'grade2_prob': school_row['grade2_prob'],
            'grade3_prob': school_row['grade3_prob'], 
            'grade4_prob': school_row['grade4_prob'],
            'grade5_prob': school_row['grade5_prob'], 
            'grade6_prob': school_row['grade6_prob'],
            'grade7_prob': school_row['grade7_prob'], 
            'grade8_prob': school_row['grade8_prob'],
            'grade9_prob': school_row['grade9_prob'], 
            'grade10_prob': school_row['grade10_prob']
        }

class BatterProfile:
    def __init__(self, bio, archetype):
        self.bio = bio  # Link to bio data generated by NameGen
        self.archetype = archetype  # Use an archetype
        # Core player attributes
        self.name = bio['name']
        self.race = bio['race']
        self.age = bio['age']
        self.height = bio['height']
        self.weight = bio['weight']
        self.origin = bio['origin']
        self.school = bio['school']
        self.bats = bio['bats']
        self.throws = bio['throws']
        
        # Role and ratings
        self.draft = None 
        self.role = None  # Starter, Bench, etc.
        self.batting = 0
        self.contact = 0
        self.power = 0
        self.eye = 0
        self.splits_L = 0
        self.splits_R = 0
        self.speed = 0
        self.fielding = 0
        self.potential = 0
        self.clutch = 0
        self.injury = 0  # Injury rating
        
        # Initial morale, popularity, salary
        self.makeup = 0
        self.morale = 0
        self.popularity = 0
        self.contract = 0  # Contract length in years
        self.salary = 0
        self.service_time = 0

    batter_archetypes = [
        Archetype("scrub", 
            contact_range=(0, 0), power_range=(0, 0), eye_range=(-3, -2), speed_range=(0, 0), splits_range=(-3, -1), 
            fielding_range=(-3, -2), potential_range=(0, 0), 
            dev_ceiling_age=21, decline_age=28),
        
        Archetype("career minor leaguer", 
            contact_range=(0, 1), power_range=(0, 1), eye_range=(-3, -1), speed_range=(0, 2), splits_range=(-3, 0),
            fielding_range=(-3, 0), potential_range=(0, 0), 
            dev_ceiling_age=22, decline_age=29),
        
        Archetype("september callup", 
            contact_range=(0, 2), power_range=(0, 1), eye_range=(-1, 0), speed_range=(0, 3), splits_range=(-2, 0),
            fielding_range=(-2, 0), potential_range=(0, 1), 
            dev_ceiling_age=23, decline_age=29),
        
        Archetype("injury replacement", 
            contact_range=(1, 3), power_range=(0, 2), eye_range=(-1, 0), speed_range=(0, 4), splits_range=(-2, 1),
            fielding_range=(-2, 0), potential_range=(0, 1), 
            dev_ceiling_age=23, decline_age=29),
        
        Archetype("AAAA player", 
            contact_range=(1, 4), power_range=(0, 3), eye_range=(0, 0), speed_range=(0, 4), splits_range=(-1, 1),
            fielding_range=(-2, 1), potential_range=(0, 2), 
            dev_ceiling_age=24, decline_age=30),
        
        Archetype("backup", 
            contact_range=(2, 4), power_range=(0, 3), eye_range=(0, 1), speed_range=(0, 4), splits_range=(-1, 2),
            fielding_range=(-2, 1), potential_range=(0, 2), 
            dev_ceiling_age=25, decline_age=31),
        
        Archetype("platoon", 
            contact_range=(3, 4), power_range=(0, 4), eye_range=(0, 2), speed_range=(0, 5), splits_range=(-3, 3),
            fielding_range=(-1, 2), potential_range=(1, 3), 
            dev_ceiling_age=25, decline_age=32),
        
        Archetype("regular starter", 
            contact_range=(4, 6), power_range=(0, 5), eye_range=(0, 2), speed_range=(0, 6), splits_range=(0, 2),
            fielding_range=(-1, 3), potential_range=(1, 6), 
            dev_ceiling_age=25, decline_age=33),
        
        Archetype("star", 
            contact_range=(5, 7), power_range=(1, 7), eye_range=(1, 3), speed_range=(1, 7), splits_range=(1, 2),
            fielding_range=(0, 3), potential_range=(2, 7), 
            dev_ceiling_age=25, decline_age=34),
        
        Archetype("5-tool", 
            contact_range=(5, 8), power_range=(4, 8), eye_range=(2, 3), speed_range=(4, 8), splits_range=(1, 3), 
            fielding_range=(1, 3), potential_range=(3, 8), 
            dev_ceiling_age=25, decline_age=35)
    ]

    def generate_ratings(self):
        # Use archetype ranges to generate ratings
        logger.debug(f"LINE 549 - Generating ratings for batter: {self.name}, Archetype: {self.archetype.name}")
        self.contact = self.generate_attribute(self.archetype.contact_range, "batting")
        self.power = self.generate_attribute(self.archetype.power_range, "power")
        self.eye = self.generate_attribute(self.archetype.eye_range, "eye", age_affected=False)
        self.speed = self.generate_attribute(self.archetype.speed_range, "speed")
        self.fielding = self.generate_attribute(self.archetype.fielding_range, "fielding")
        self.potential = self.generate_attribute(self.archetype.potential_range, "potential", age_affected=False)

        logger.debug(f"LINE 549 - Ratings generated for {self.name}: Contact: {self.contact}, Power: {self.power}, Eye: {self.eye}, Speed: {self.speed}, Fielding: {self.fielding}, Potential: {self.potential}")

        # Generate splits (L vs R)
        self.splits_L, self.splits_R = self.generate_splits()

        # Generate random injury rating
        self.injury = max(min(int(np.random.normal(0, 1.5)), 3), -3)
        logger.debug(f"LINE 553 - Injury rating for {self.name}: {self.injury}")

        self.makeup = max(min(int(np.random.normal(0, 1)), 2), -2)

        self.clutch = max(min(int(np.random.normal(0, 1)), 2), -2)
        logger.debug(f"LINE 558 - Makeup: {self.makeup}, Clutch: {self.clutch}")
                      
        # Adjust ratings by age and log any changes
        logger.debug(f"LINE 561 - Adjusting ratings by age for {self.name}, Age: {self.age}")
        self.adjust_by_age()

        logger.debug(f"LINE 564 - Final adjusted ratings for {self.name}: Contact: {self.contact}, Power: {self.power}, Speed: {self.speed}, Fielding: {self.fielding}")
        
    def to_dict(self):
        # Return all attributes in dictionary format for JSON serialization
        return {
            "name": self.name,
            "race": self.race,
            "age": self.age,
            "height": self.height,
            "weight": self.weight,
            "origin": self.origin,
            "draft": self.draft,
            "school": self.school,
            "bats": self.bats,
            "throws": self.throws,
            "role": self.role,
            "batting": self.contact,
            "power": self.power,
            "eye": self.eye,
            "splits_L": self.splits_L,  # Added splits_L
            "splits_R": self.splits_R,  # Added splits_R
            "speed": self.speed,
            "fielding": self.fielding,
            "potential": self.potential,
            "clutch": self.clutch,
            "injury": self.injury,
            "makeup": self.makeup,
            "morale": self.morale,
            "popularity": self.popularity,
            "salary": self.salary,
            "contract": self.contract,
            "service_time": self.service_time,
        }

    def generate_splits(self):
        """Generate the splits_L and splits_R ratings based on the batter's handedness and archetype."""
        floor, ceiling = self.archetype.splits_range
        
        # Initialize splits_L and splits_R with default values
        splits_L = 0
        splits_R = 0

        # Special case for platoon players
        if self.archetype.name == "scrub":
            if self.bats == "L":
                splits_L = self.skewed_random(-3, -1, skew="low")  # Weaker against left-handed pitchers
                splits_R = self.skewed_random(-2, 0, skew="high")  # Stronger against right-handed pitchers
            elif self.bats == "R":
                splits_R = self.skewed_random(-3, -1, skew="low")  # Weaker against right-handed pitchers
                splits_L = self.skewed_random(-2, 0, skew="high")  # Stronger against left-handed pitchers
            else:  # Switch hitters
                splits_L = self.skewed_random(-2, 1, skew="neutral")  # Balanced vs. left-handed pitchers
                splits_R = self.skewed_random(-2, 1, skew="neutral")  # Balanced vs. right-handed pitchers

        if self.archetype.name == "career minor leaguer":
            if self.bats == "L":
                splits_L = self.skewed_random(-3, 0, skew="low")  # Weaker against left-handed pitchers
                splits_R = self.skewed_random(-2, 1, skew="high")  # Stronger against right-handed pitchers
            elif self.bats == "R":
                splits_R = self.skewed_random(-3, 0, skew="low")  # Weaker against right-handed pitchers
                splits_L = self.skewed_random(-2, 1, skew="high")  # Stronger against left-handed pitchers
            else:  # Switch hitters
                splits_L = self.skewed_random(-2, 1, skew="neutral")  # Balanced vs. left-handed pitchers
                splits_R = self.skewed_random(-2, 1, skew="neutral")  # Balanced vs. right-handed pitchers

        if self.archetype.name == "september callup":
            if self.bats == "L":
                splits_L = self.skewed_random(-2, 0, skew="low")  # Weaker against left-handed pitchers
                splits_R = self.skewed_random(-2, 1, skew="high")  # Stronger against right-handed pitchers
            elif self.bats == "R":
                splits_R = self.skewed_random(-2, 0, skew="low")  # Weaker against right-handed pitchers
                splits_L = self.skewed_random(-2, 1, skew="high")  # Stronger against left-handed pitchers
            else:  # Switch hitters
                splits_L = self.skewed_random(-2, 1, skew="neutral")  # Balanced vs. left-handed pitchers
                splits_R = self.skewed_random(-2, 1, skew="neutral")  # Balanced vs. right-handed pitchers

        if self.archetype.name == "injury replacement":
            if self.bats == "L":
                splits_L = self.skewed_random(-2, -1, skew="low")  # Weaker against left-handed pitchers
                splits_R = self.skewed_random(-1, 2, skew="high")  # Stronger against right-handed pitchers
            elif self.bats == "R":
                splits_R = self.skewed_random(-2, -1, skew="low")  # Weaker against right-handed pitchers
                splits_L = self.skewed_random(-1, 2, skew="high")  # Stronger against left-handed pitchers
            else:  # Switch hitters
                splits_L = self.skewed_random(-2, 1, skew="neutral")  # Balanced vs. left-handed pitchers
                splits_R = self.skewed_random(-2, 1, skew="neutral")  # Balanced vs. right-handed pitchers

        if self.archetype.name == "AAAA player":
            if self.bats == "L":
                splits_L = self.skewed_random(-1, 1, skew="low")  # Weaker against left-handed pitchers
                splits_R = self.skewed_random(-1, 2, skew="high")  # Stronger against right-handed pitchers
            elif self.bats == "R":
                splits_R = self.skewed_random(-1, 1, skew="low")  # Weaker against right-handed pitchers
                splits_L = self.skewed_random(-1, 2, skew="high")  # Stronger against left-handed pitchers
            else:  # Switch hitters
                splits_L = self.skewed_random(-2, 1, skew="neutral")  # Balanced vs. left-handed pitchers
                splits_R = self.skewed_random(-2, 1, skew="neutral")  # Balanced vs. right-handed pitchers

        if self.archetype.name == "backup":
            if self.bats == "L":
                splits_L = self.skewed_random(-1, 2, skew="low")  # Weaker against left-handed pitchers
                splits_R = self.skewed_random(0, 2, skew="high")  # Stronger against right-handed pitchers
            elif self.bats == "R":
                splits_R = self.skewed_random(-1, 2, skew="low")  # Weaker against right-handed pitchers
                splits_L = self.skewed_random(0, 2, skew="high")  # Stronger against left-handed pitchers
            else:  # Switch hitters
                splits_L = self.skewed_random(-2, 1, skew="neutral")  # Balanced vs. left-handed pitchers
                splits_R = self.skewed_random(-2, 1, skew="neutral")  # Balanced vs. right-handed pitchers

        if self.archetype.name == "platoon":
            if self.bats == "L":
                splits_L = self.skewed_random(-3, 0, skew="low")  # Weaker against left-handed pitchers
                splits_R = self.skewed_random(1, 3, skew="high")  # Stronger against right-handed pitchers
            elif self.bats == "R":
                splits_R = self.skewed_random(-3, 0, skew="low")  # Weaker against right-handed pitchers
                splits_L = self.skewed_random(1, 3, skew="high")  # Stronger against left-handed pitchers
            else:  # Switch hitters
                splits_L = self.skewed_random(-2, 1, skew="neutral")  # Balanced vs. left-handed pitchers
                splits_R = self.skewed_random(-2, 1, skew="neutral")  # Balanced vs. right-handed pitchers

        if self.archetype.name == "regular starter":
            if self.bats == "L":
                splits_L = self.skewed_random(0, 2, skew="low")  # Weaker against left-handed pitchers
                splits_R = self.skewed_random(0, 3, skew="high")  # Stronger against right-handed pitchers
            elif self.bats == "R":
                splits_R = self.skewed_random(0, 2, skew="low")  # Weaker against right-handed pitchers
                splits_L = self.skewed_random(0, 3, skew="high")  # Stronger against left-handed pitchers
            else:  # Switch hitters
                splits_L = self.skewed_random(-2, 1, skew="neutral")  # Balanced vs. left-handed pitchers
                splits_R = self.skewed_random(-2, 1, skew="neutral")  # Balanced vs. right-handed pitchers

        if self.archetype.name == "star":
            if self.bats == "L":
                splits_L = self.skewed_random(1, 2, skew="low")  # Weaker against left-handed pitchers
                splits_R = self.skewed_random(1, 3, skew="high")  # Stronger against right-handed pitchers
            elif self.bats == "R":
                splits_R = self.skewed_random(1, 2, skew="low")  # Weaker against right-handed pitchers
                splits_L = self.skewed_random(1, 3, skew="high")  # Stronger against left-handed pitchers
            else:  # Switch hitters
                splits_L = self.skewed_random(-2, 1, skew="neutral")  # Balanced vs. left-handed pitchers
                splits_R = self.skewed_random(-2, 1, skew="neutral")  # Balanced vs. right-handed pitchers

        if self.archetype.name == "5-tool":
            if self.bats == "L":
                splits_L = self.skewed_random(1, 3, skew="low")  # Weaker against left-handed pitchers
                splits_R = self.skewed_random(1, 3, skew="high")  # Stronger against right-handed pitchers
            elif self.bats == "R":
                splits_R = self.skewed_random(1, 3, skew="low")  # Weaker against right-handed pitchers
                splits_L = self.skewed_random(1, 3, skew="high")  # Stronger against left-handed pitchers
            else:  # Switch hitters
                splits_L = self.skewed_random(-2, 1, skew="neutral")  # Balanced vs. left-handed pitchers
                splits_R = self.skewed_random(-2, 1, skew="neutral")  # Balanced vs. right-handed pitchers

        return splits_L, splits_R

    def generate_attribute(self, range_tuple, attribute_name, age_affected=True):
        """Generate a rating based on a given range, skewed by archetype quality."""
        floor, ceiling = range_tuple
        
        # Skewed distribution depending on archetype quality
        if self.archetype.name in ["star", "5-tool"]:
            # High-quality archetypes skew towards the ceiling
            rating = self.skewed_random(floor, ceiling, skew="high")
        elif self.archetype.name in ["scrub", "career minor leaguer", "september callup", "injury replacement"]:
            # Low-quality archetypes skew towards the floor
            rating = self.skewed_random(floor, ceiling, skew="low")
        else:
            # Neutral or moderate archetypes have a balanced distribution
            rating = np.random.randint(floor, ceiling + 1)

        # Clamp the values within the floor/ceiling bounds
        return np.clip(rating, floor, ceiling)

    def skewed_random(self, floor, ceiling, skew="neutral"):
        """Generate a random number in the floor/ceiling range, skewed to high or low, with a chance for extremes."""
        
        # Introduce a small chance (e.g., 5%) of hitting the extreme values
        if np.random.rand() < 0.05:
            # 5% chance to return the exact floor or ceiling (depending on skew)
            if skew == "high":
                return ceiling
            elif skew == "low":
                return floor

        # Standard beta distribution logic
        if skew == "high":
            # Skew towards higher values (better performance against opposite-handedness)
            return int(np.random.beta(2, 5) * (ceiling - floor) + floor)
        elif skew == "low":
            # Skew towards lower values (worse performance against same-handedness)
            return int(np.random.beta(5, 2) * (ceiling - floor) + floor)
        else:
            # Neutral distribution for switch hitters
            return np.random.randint(floor, ceiling + 1)

    def adjust_by_age(self):
        """Adjust attributes based on player's age."""
        # dev difference should also be mitigated by potential rating (higher rating, less penalty)
        dev_diff = self.archetype.dev_ceiling_age - self.bio['age']
        decline_diff = self.bio['age'] - self.archetype.decline_age

        # Log development and decline calculations
        logger.debug(f"LINE 632 - Development difference: {dev_diff}, Decline difference: {decline_diff}")

        # List of top and second-tier archetypes
        top_tier_archetypes = ["5-tool"]
        second_tier_archetypes = ["star", "regular starter"]

        # Determine penalty adjustments based on archetype
        if self.archetype.name in top_tier_archetypes:
            adjusted_decline = max(0, decline_diff - 2)  # Reduce penalty by 2
        elif self.archetype.name in second_tier_archetypes:
            adjusted_decline = max(0, decline_diff - 1)  # Reduce penalty by 1
        else:
            adjusted_decline = decline_diff  # Apply regular penalty

        if self.bio['age'] < self.archetype.dev_ceiling_age:
            logger.debug(f"LINE 647 - {self.name} is under development ceiling. Reducing ratings by {dev_diff}")
            # Penalize for being underdeveloped
            self.contact -= dev_diff
            self.power -= dev_diff
            self.speed -= dev_diff
            self.fielding -= dev_diff
        elif self.bio['age'] > self.archetype.decline_age:
            logger.debug(f"LINE 654 - {self.name} is past decline age. Reducing ratings by {decline_diff}")
            # Penalize for being past decline, adjusted by archetype
            self.contact -= adjusted_decline
            self.power -= adjusted_decline
            self.speed -= adjusted_decline
            self.fielding -= adjusted_decline

        # Clamp the values within the min and max ranges for each attribute
        self.contact = max(0, self.contact)
        self.power = max(0, self.power)
        self.eye = max(-3, self.eye)  # Eye range is -3 to +3
        self.speed = max(0, self.speed)
        self.fielding = max(-3, self.fielding) # Fielding range is -3 to +3

        logger.debug(f"LINE 668 - Adjusted ratings for {self.name}: Contact: {self.contact}, Power: {self.power}, Speed: {self.speed}, Fielding: {self.fielding}")

class PitcherProfile:
    def __init__(self, bio, archetype):
        self.bio = bio  # Link to bio data generated by NameGen
        self.archetype = archetype  # Use the pitcher archetype
        # Core player attributes
        self.name = bio['name']
        self.race = bio['race']
        self.age = bio['age']
        self.height = bio['height']
        self.weight = bio['weight']
        self.origin = bio['origin']
        self.school = bio['school']
        self.position = bio['position']
        self.bats = bio['bats']
        self.throws = bio['throws']
        
        # Pitching-specific attributes
        self.draft = None
        self.type = None  # Starter or Reliever
        self.start_value = 0  # 0.5 to 7.0
        self.endurance = 0  # 0.5 to 8.0
        self.rest = 0  # 3 to 8
        self.cg_rating = 666  # 611 to 666
        self.sho_rating = 666  # 611 to 666
        self.splits_L = 0
        self.splits_R = 0
        self.relief_value = 0  # +7 to -5
        self.fatigue = 0  # 1 to 5
        self.potential = 0  # 0 to 8
        self.injury = 0  # Injury rating
        
        # Initialise morale, popularity, salary
        self.makeup = 0
        self.morale = 0
        self.popularity = 0
        self.salary = 0
        self.contract = 0
        self.service_time = 0

    starter_archetypes = [
        Archetype("journeyman", 
            start_value_range=(0.5, 1.0), endurance_range=(0.5, 1.0), rest_range=(7, 8), splits_range=(-3, -1),
            cg_rating_range=(666, 666), sho_rating_range=(666, 666), relief_value_range=(6, 6), 
            fatigue_range=(+5, +5), potential_range=(0, 0), dev_ceiling_age=21, decline_age=28),

        Archetype("fringe starter", 
            start_value_range=(0.5, 1.5), endurance_range=(0.5, 1.5), rest_range=(6, 8), splits_range=(-3, 0),
            cg_rating_range=(665, 666), sho_rating_range=(666, 666), relief_value_range=(6, 6), 
            fatigue_range=(+5, +5), potential_range=(0, 0), dev_ceiling_age=22, decline_age=29),

        Archetype("late bloomer", 
            start_value_range=(1.0, 1.5), endurance_range=(1.0, 1.5), rest_range=(6, 8), splits_range=(-2, 0),
            cg_rating_range=(664, 666), sho_rating_range=(666, 666), relief_value_range=(6, 6), 
            fatigue_range=(+5, +5), potential_range=(0, 1), dev_ceiling_age=23, decline_age=29),

        Archetype("spot starter", 
            start_value_range=(1.0, 2.0), endurance_range=(1.0, 2.0), rest_range=(5, 8), splits_range=(-2, 1),
            cg_rating_range=(666, 666), sho_rating_range=(666, 666), relief_value_range=(6, 6), 
            fatigue_range=(+5, +5), potential_range=(0, 1), dev_ceiling_age=23, decline_age=29),

        Archetype("quad-a arm", 
            start_value_range=(1.0, 2.5), endurance_range=(1.0, 2.5), rest_range=(5, 7), splits_range=(-1, 0),
            cg_rating_range=(665, 665), sho_rating_range=(665, 665), relief_value_range=(6, 6), 
            fatigue_range=(+5, +5), potential_range=(0, 2), dev_ceiling_age=24, decline_age=30),

        Archetype("swingman", 
            start_value_range=(1.5, 3.0), endurance_range=(1.5, 3.0), rest_range=(5, 6), splits_range=(-1, 1),
            cg_rating_range=(665, 665), sho_rating_range=(665, 665), relief_value_range=(5, 5), 
            fatigue_range=(4, 2), potential_range=(0, 2), dev_ceiling_age=25, decline_age=31),

        Archetype("back of rotation", 
            start_value_range=(2.0, 3.0), endurance_range=(2.0, 3.5), rest_range=(4, 6), splits_range=(-1, 2),
            cg_rating_range=(661, 666), sho_rating_range=(661, 661), relief_value_range=(5, 5), 
            fatigue_range=(+5, +5), potential_range=(1, 3), dev_ceiling_age=25, decline_age=32),

        Archetype("regular starter", 
            start_value_range=(2.5, 4.0), endurance_range=(2.5, 5.5), rest_range=(4, 5), splits_range=(0, 2),
            cg_rating_range=(661, 666), sho_rating_range=(656, 666), relief_value_range=(5, 5), 
            fatigue_range=(+5, +5), potential_range=(1, 5), dev_ceiling_age=25, decline_age=34),

        Archetype("top of rotation", 
            start_value_range=(3.0, 5.5), endurance_range=(3.5, 6.5), rest_range=(4, 5), splits_range=(1, 2),
            cg_rating_range=(641, 666), sho_rating_range=(651, 666), relief_value_range=(5, 5), 
            fatigue_range=(+5, +5), potential_range=(3, 7), dev_ceiling_age=25, decline_age=34),

        Archetype("ace", 
            start_value_range=(5.0, 7.0), endurance_range=(4.0, 8.0), rest_range=(4, 4), splits_range=(1, 3),
            cg_rating_range=(611, 666), sho_rating_range=(611, 666), relief_value_range=(4, 4), 
            fatigue_range=(+4, +4), potential_range=(4, 8), dev_ceiling_age=25, decline_age=35)
    ]

    reliever_archetypes = [
        Archetype("filler arm", 
            start_value_range=(0.5, 0.5), endurance_range=(0.5, 0.5), rest_range=(8, 8), splits_range=(-3, -1),
            cg_rating_range=(666, 666), sho_rating_range=(666, 666), relief_value_range=(7, 6), 
            fatigue_range=(4, 4), potential_range=(0, 0), dev_ceiling_age=21, decline_age=28),

        Archetype("taxi squad reliever", 
            start_value_range=(0.5, 0.5), endurance_range=(0.5, 0.5), rest_range=(7, 8), splits_range=(-2, -1),
            cg_rating_range=(665, 666), sho_rating_range=(666, 666), relief_value_range=(7, 5), 
            fatigue_range=(4, 4), potential_range=(0, 0), dev_ceiling_age=22, decline_age=29),

        Archetype("roster expansion reliever", 
            start_value_range=(0.5, 0.5), endurance_range=(0.5, 0.5), rest_range=(7, 8), splits_range=(-2, 0),
            cg_rating_range=(664, 666), sho_rating_range=(666, 666), relief_value_range=(6, 5), 
            fatigue_range=(4, 4), potential_range=(0, 1), dev_ceiling_age=23, decline_age=29),

        Archetype("bullpen patch", 
            start_value_range=(0.5, 0.5), endurance_range=(0.5, 0.5), rest_range=(8, 8), splits_range=(-1, 0),
            cg_rating_range=(666, 666), sho_rating_range=(666, 666), relief_value_range=(6, 4), 
            fatigue_range=(4, 3), potential_range=(0, 1), dev_ceiling_age=23, decline_age=29),

        Archetype("perpetual callup", 
            start_value_range=(0.5, 0.5), endurance_range=(0.5, 0.5), rest_range=(8, 8), splits_range=(-1, 1),
            cg_rating_range=(666, 666), sho_rating_range=(666, 666), relief_value_range=(5, 4), 
            fatigue_range=(4, 2), potential_range=(0, 2), dev_ceiling_age=24, decline_age=30),

        Archetype("specialist", 
            start_value_range=(0.5, 0.5), endurance_range=(0.5, 0.5), rest_range=(7, 7), splits_range=(-3, 3),
            cg_rating_range=(666, 666), sho_rating_range=(666, 666), relief_value_range=(5, 3), 
            fatigue_range=(4, 3), potential_range=(0, 3), dev_ceiling_age=25, decline_age=30),

        Archetype("long-relief", 
            start_value_range=(1.0, 1.5), endurance_range=(0.5, 1.0), rest_range=(5, 7), splits_range=(0, 1),
            cg_rating_range=(665, 666), sho_rating_range=(665, 666), relief_value_range=(4, 2), 
            fatigue_range=(2, 1), potential_range=(1, 3), dev_ceiling_age=25, decline_age=31),

        Archetype("low-leverage", 
            start_value_range=(0.5, 0.5), endurance_range=(0.5, 0.5), rest_range=(8, 8), splits_range=(0, 2),
            cg_rating_range=(666, 666), sho_rating_range=(666, 666), relief_value_range=(3, 0), 
            fatigue_range=(3, 1), potential_range=(1, 5), dev_ceiling_age=25, decline_age=32),

        Archetype("high-leverage", 
            start_value_range=(0.5, 0.5), endurance_range=(0.5, 0.5), rest_range=(8, 8), splits_range=(1, 2),
            cg_rating_range=(666, 666), sho_rating_range=(666, 666), relief_value_range=(0, -3), 
            fatigue_range=(2, 1), potential_range=(2, 7), dev_ceiling_age=25, decline_age=34),

        Archetype("closer", 
            start_value_range=(0.5, 0.5), endurance_range=(0.5, 0.5), rest_range=(8, 8), splits_range=(1, 3),
            cg_rating_range=(666, 666), sho_rating_range=(666, 666), relief_value_range=(-4, -5), 
            fatigue_range=(1, 1), potential_range=(3, 8), dev_ceiling_age=25, decline_age=35)
    ]

    def generate_ratings(self):
        # Generate ratings based on archetype
        self.start_value = self.generate_attribute(self.archetype.start_value_range, "start_value")
        self.endurance = self.generate_attribute(self.archetype.endurance_range, "endurance")
        self.rest = self.generate_attribute(self.archetype.rest_range, "rest")
        self.cg_rating = self.generate_attribute(self.archetype.cg_rating_range, "cg_rating")
        self.sho_rating = self.generate_attribute(self.archetype.sho_rating_range, "sho_rating")
        self.relief_value = self.generate_attribute(self.archetype.relief_value_range, "relief_value", reverse=True)
        self.fatigue = self.generate_attribute(self.archetype.fatigue_range, "fatigue", reverse=True)
        self.potential = self.generate_attribute(self.archetype.potential_range, "potential", age_affected=False)

        logger.debug(f"LINE 1051 - Ratings generated for {self.name}: Start Value: {self.start_value}, Endurance: {self.endurance}, Rest: {self.rest}, CG Rating: {self.cg_rating}, SHO Rating: {self.sho_rating}, Relief Value: {self.relief_value}, Fatigue: {self.fatigue}, Potential: {self.potential}")

        # Generate splits for L vs R batters
        self.splits_L, self.splits_R = self.generate_splits()

        # Generate random injury rating
        self.injury = max(min(int(np.random.normal(0, 1.5)), 3), -3)
        logger.debug(f"LINE 1058 - Injury rating for {self.name}: {self.injury}")

        # Adjust ratings by age
        logger.debug(f"LINE 1061 - Adjusting ratings by age for {self.name}, Age: {self.age}")
        self.adjust_by_age()
        
        self.makeup = self.generate_makeup()

        logger.debug(f"LINE 1066 - Final adjusted ratings for {self.name}: Start Value: {self.start_value}, Endurance: {self.endurance}, Rest: {self.rest}, CG Rating: {self.cg_rating}, SHO Rating: {self.sho_rating}, Relief Value: {self.relief_value}, Fatigue: {self.fatigue}, Potential: {self.potential}")
        

    def generate_makeup(self):
        """Generate a makeup rating centered around 0 with a limited range from -2 to 2."""
        # Normal distribution centered at 0, with a standard deviation of 1
        # Clamped between -2 and 2
        makeup = max(min(int(np.random.normal(0, 1)), 2), -2)
        return makeup

    def to_dict(self):
        # Return all attributes in dictionary format for JSON serialization
        return {
            "name": self.name,
            "race": self.race,
            "age": self.age,
            "height": self.height,
            "weight": self.weight,
            "origin": self.origin,
            "draft": self.draft,
            "school": self.school,
            "position": self.position,
            "bats": self.bats,
            "throws": self.throws,
            "type": self.type,
            "start_value": self.start_value,
            "endurance": self.endurance,
            "rest": self.rest,
            "cg_rating": self.cg_rating,
            "sho_rating": self.sho_rating,
            "splits_L": self.splits_L,
            "splits_R": self.splits_R,
            "relief_value": self.relief_value,
            "fatigue": self.fatigue,
            "potential": self.potential,
            "injury": self.injury,
            "makeup": self.makeup,
            "morale": self.morale,
            "popularity": self.popularity,
            "salary": self.salary,
            "contract": self.contract,
            "service_time": self.service_time,
        }

    def generate_splits(self):
        """Generate the splits_L and splits_R ratings based on the pitcher's throwing hand and archetype."""
        floor, ceiling = self.archetype.splits_range
        
        # Initialize splits_L and splits_R
        splits_L = 0
        splits_R = 0

        # STARTING PITCHERS

        if self.archetype.name == "journeyman":
            if self.throws == "L":
                splits_L = self.skewed_random(-3, -1, skew="low")  # Stronger splits against same-handed hitters
                splits_R = self.skewed_random(-3, -2, skew="high")  # Weaker splits against opposite-handed hitters
            elif self.throws == "R":
                splits_R = self.skewed_random(-3, -1, skew="low")  # Stronger splits against same-handed hitters
                splits_L = self.skewed_random(-3, -2, skew="high")  # Weaker against opposite-handed hitters

        if self.archetype.name == "fringe starter":
            if self.throws == "L":
                splits_L = self.skewed_random(-3, 0, skew="low")  # Stronger splits against same-handed hitters
                splits_R = self.skewed_random(-3, -1, skew="high")  # Weaker against opposite-handed hitters
            elif self.throws == "R":
                splits_R = self.skewed_random(-3, 0, skew="low")  # Stronger splits against same-handed hitters
                splits_L = self.skewed_random(-3, -1, skew="high")  # Weaker against opposite-handed hitters

        if self.archetype.name == "late bloomer":
            if self.throws == "L":
                splits_L = self.skewed_random(-2, 0, skew="low")  # Stronger splits against same-handed hitters
                splits_R = self.skewed_random(-2, -1, skew="high")  # Weaker against opposite-handed hitters
            elif self.throws == "R":
                splits_R = self.skewed_random(-2, 0, skew="low")  # Stronger splits against same-handed hitters
                splits_L = self.skewed_random(-2, -1, skew="high")  # Weaker against opposite-handed hitters

        if self.archetype.name == "spot starter":
            if self.throws == "L":
                splits_L = self.skewed_random(-2, 1, skew="low")  # Stronger splits against same-handed hitters
                splits_R = self.skewed_random(-2, 0, skew="high")  # Weaker against opposite-handed hitters
            elif self.throws == "R":
                splits_R = self.skewed_random(-2, 1, skew="low")  # Stronger splits against same-handed hitters
                splits_L = self.skewed_random(-2, 0, skew="high")  # Weaker against opposite-handed hitters

        if self.archetype.name == "quad-a arm":
            if self.throws == "L":
                splits_L = self.skewed_random(-1, 0, skew="low")  # Stronger splits against same-handed hitters
                splits_R = self.skewed_random(-2, 0, skew="high")  # Weaker against opposite-handed hitters
            elif self.throws == "R":
                splits_R = self.skewed_random(-1, 0, skew="low")  # Stronger splits against same-handed hitters
                splits_L = self.skewed_random(-2, 0, skew="high")  # Weaker against opposite-handed hitters

        if self.archetype.name == "swingman":
            if self.throws == "L":
                splits_L = self.skewed_random(-1, 1, skew="low")  # Stronger splits against same-handed hitters
                splits_R = self.skewed_random(-2, 0, skew="high")  # Weaker against opposite-handed hitters
            elif self.throws == "R":
                splits_R = self.skewed_random(-1, 1, skew="low")  # Stronger splits against same-handed hitters
                splits_L = self.skewed_random(-2, 0, skew="high")  # Weaker against opposite-handed hitters

        if self.archetype.name == "back of rotation":
            if self.throws == "L":
                splits_L = self.skewed_random(-1, 2, skew="low")  # Stronger splits against same-handed hitters
                splits_R = self.skewed_random(-1, 1, skew="high")  # Weaker against opposite-handed hitters
            elif self.throws == "R":
                splits_R = self.skewed_random(-1, 2, skew="low")  # Stronger splits against same-handed hitters
                splits_L = self.skewed_random(-1, 1, skew="high")  # Weaker against opposite-handed hitters

        if self.archetype.name == "regular starter":
            if self.throws == "L":
                splits_L = self.skewed_random(0, 2, skew="low")  # Stronger splits against same-handed hitters
                splits_R = self.skewed_random(0, 1, skew="high")  # Weaker against opposite-handed hitters
            elif self.throws == "R":
                splits_R = self.skewed_random(0, 2, skew="low")  # Stronger splits against same-handed hitters
                splits_L = self.skewed_random(0, 1, skew="high")  # Weaker against opposite-handed hitters

        if self.archetype.name == "top of rotation":
            if self.throws == "L":
                splits_L = self.skewed_random(1, 2, skew="low")  # Stronger splits against same-handed hitters
                splits_R = self.skewed_random(0, 2, skew="high")  # Weaker against opposite-handed hitters
            elif self.throws == "R":
                splits_R = self.skewed_random(1, 2, skew="low")  # Stronger splits against same-handed hitters
                splits_L = self.skewed_random(0, 2, skew="high")  # Weaker against opposite-handed hitters

        if self.archetype.name == "ace":
            if self.throws == "L":
                splits_L = self.skewed_random(1, 3, skew="low")  # Stronger splits against same-handed hitters
                splits_R = self.skewed_random(1, 2, skew="high")  # Weaker against opposite-handed hitters
            elif self.throws == "R":
                splits_R = self.skewed_random(1, 3, skew="low")  # Stronger splits against same-handed hitters
                splits_L = self.skewed_random(1, 2, skew="high")  # Weaker against opposite-handed hitters

        # RELIEF PITCHERS

        if self.archetype.name == "filler arm":
            if self.throws == "L":
                splits_L = self.skewed_random(-3, -1, skew="low")  # Strong splits against same-handed hitters
                splits_R = self.skewed_random(-3, -2, skew="high")  # Weaker against opposite-handed hitters
            elif self.throws == "R":
                splits_R = self.skewed_random(-3, -1, skew="low")  # Strong splits against same-handed hitters
                splits_L = self.skewed_random(-3, -2, skew="high")  # Weaker against opposite-handed hitters

        if self.archetype.name == "taxi squad reliever":
            if self.throws == "L":
                splits_L = self.skewed_random(-2, -1, skew="low")  # Strong splits against same-handed hitters
                splits_R = self.skewed_random(-3, -1, skew="high")  # Weaker against opposite-handed hitters
            elif self.throws == "R":
                splits_R = self.skewed_random(-2, -1, skew="low")  # Strong splits against same-handed hitters
                splits_L = self.skewed_random(-3, -1, skew="high")  # Weaker against opposite-handed hitters

        if self.archetype.name == "roster expansion reliever":
            if self.throws == "L":
                splits_L = self.skewed_random(-2, 0, skew="low")  # Strong splits against same-handed hitters
                splits_R = self.skewed_random(-2, -1, skew="high")  # Weaker against opposite-handed hitters
            elif self.throws == "R":
                splits_R = self.skewed_random(-2, 0, skew="low")  # Strong splits against same-handed hitters
                splits_L = self.skewed_random(-2, -1, skew="high")  # Weaker against opposite-handed hitters

        if self.archetype.name == "bullpen patch":
            if self.throws == "L":
                splits_L = self.skewed_random(-1, 0, skew="low")  # Strong splits against same-handed hitters
                splits_R = self.skewed_random(-2, 0, skew="high")  # Weaker against opposite-handed hitters
            elif self.throws == "R":
                splits_R = self.skewed_random(-1, 0, skew="low")  # Strong splits against same-handed hitters
                splits_L = self.skewed_random(-2, 0, skew="high")  # Weaker against opposite-handed hitters

        if self.archetype.name == "perpetual callup":
            if self.throws == "L":
                splits_L = self.skewed_random(-1, 1, skew="low")  # Strong splits against same-handed hitters
                splits_R = self.skewed_random(-2, 0, skew="high")  # Weaker against opposite-handed hitters
            elif self.throws == "R":
                splits_R = self.skewed_random(-1, 1, skew="low")  # Strong splits against same-handed hitters
                splits_L = self.skewed_random(-2, 0, skew="high")  # Weaker against opposite-handed hitters

        if self.archetype.name == "specialist":
            if self.throws == "L":
                splits_L = self.skewed_random(2, 3, skew="low")  # Stronger splits against same-handed hitters
                splits_R = self.skewed_random(-3, -2, skew="high")  # Weaker against opposite-handed hitters
            elif self.throws == "R":
                splits_R = self.skewed_random(2, 3, skew="low")  # Stronger splits against same-handed hitters
                splits_L = self.skewed_random(-3, -2, skew="high")  # Weaker against opposite-handed hitters

        if self.archetype.name == "long-relief":
            if self.throws == "L":
                splits_L = self.skewed_random(0, 1, skew="low")  # Strong splits against same-handed hitters
                splits_R = self.skewed_random(-1, 1, skew="high")  # Weaker against opposite-handed hitters
            elif self.throws == "R":
                splits_R = self.skewed_random(0, 1, skew="low")  # Strong splits against same-handed hitters
                splits_L = self.skewed_random(-1, 1, skew="high")  # Weaker against opposite-handed hitters

        if self.archetype.name == "low-leverage":
            if self.throws == "L":
                splits_L = self.skewed_random(0, 2, skew="low")  # Strong splits against same-handed hitters
                splits_R = self.skewed_random(0, 1, skew="high")  # Weaker against opposite-handed hitters
            elif self.throws == "R":
                splits_R = self.skewed_random(0, 2, skew="low")  # Strong splits against same-handed hitters
                splits_L = self.skewed_random(0, 1, skew="high")  # Weaker against opposite-handed hitters

        if self.archetype.name == "high-leverage":
            if self.throws == "L":
                splits_L = self.skewed_random(1, 2, skew="low")  # Strong splits against same-handed hitters
                splits_R = self.skewed_random(0, 2, skew="high")  # Weaker against opposite-handed hitters
            elif self.throws == "R":
                splits_R = self.skewed_random(1, 2, skew="low")  # Strong splits against same-handed hitters
                splits_L = self.skewed_random(0, 2, skew="high")  # Weaker against opposite-handed hitters

        if self.archetype.name == "closer":
            if self.throws == "L":
                splits_L = self.skewed_random(1, 3, skew="low")  # Strong splits against same-handed hitters
                splits_R = self.skewed_random(0, 3, skew="high")  # Weaker against opposite-handed hitters
            elif self.throws == "R":
                splits_R = self.skewed_random(1, 3, skew="low")  # Strong splits against same-handed hitters
                splits_L = self.skewed_random(0, 3, skew="high")  # Weaker against opposite-handed hitters

        return splits_L, splits_R

    def generate_attribute(self, range_tuple, attribute_name, age_affected=True, reverse=False):
        """Generate a rating based on a given range, with support for reversed scales."""
        floor, ceiling = range_tuple
        
        # Handle reversed ranges where lower values are better
        if reverse:
            # Skew distribution depending on archetype quality, but in reversed order
            if self.archetype.name in ["ace", "top of rotation", "closer", "high-leverage"]:
                rating = self.skewed_random(ceiling, floor, skew="low")  # Reversed, lower is better
            elif self.archetype.name in ["journeyman", "fringe starter", "filler arm", "taxi squad reliever"]:
                rating = self.skewed_random(ceiling, floor, skew="high")  # Reversed, lower is better
            else:
                rating = np.random.randint(ceiling, floor + 1)  # Generate within reversed range
        else:
            # Skew distribution for normal ranges
            if self.archetype.name in ["ace", "top of rotation", "closer", "high-leverage"]:
                rating = self.skewed_random(floor, ceiling, skew="high")
            elif self.archetype.name in ["journeyman", "fringe starter", "filler arm", "taxi squad reliever"]:
                rating = self.skewed_random(floor, ceiling, skew="low")
            else:
                rating = np.random.randint(floor, ceiling + 1)
        
        # Clamp the values within the floor/ceiling bounds
        return np.clip(rating, min(floor, ceiling), max(floor, ceiling))


    def skewed_random(self, floor, ceiling, skew="neutral"):
        """Generate a random number in the floor/ceiling range, skewed to high or low, with a chance for extremes."""
        
        # Introduce a small chance (e.g., 5%) of hitting the extreme values
        if np.random.rand() < 0.05:
            # 5% chance to return the exact floor or ceiling (depending on skew)
            if skew == "high":
                return ceiling
            elif skew == "low":
                return floor

        # Standard beta distribution logic
        if skew == "high":
            # Skew towards higher values (better performance against opposite-handedness)
            return int(np.random.beta(2, 5) * (ceiling - floor) + floor)
        elif skew == "low":
            # Skew towards lower values (worse performance against same-handedness)
            return int(np.random.beta(5, 2) * (ceiling - floor) + floor)
        else:
            # Neutral distribution for switch hitters
            return np.random.randint(floor, ceiling + 1)

    def adjust_by_age(self):
        """Adjust ratings based on the player's age (penalties or bonuses)."""
        dev_diff = self.archetype.dev_ceiling_age - self.bio['age']
        decline_diff = self.bio['age'] - self.archetype.decline_age

        # List of top and second-tier archetypes
        top_tier_archetypes = ["ace", "closer"]
        second_tier_archetypes = ["top of rotation", "high-leverage"]

        # Determine penalty adjustments based on archetype
        if self.archetype.name in top_tier_archetypes:
            adjusted_decline = max(0, decline_diff - 2)  # Reduce penalty by 2
        elif self.archetype.name in second_tier_archetypes:
            adjusted_decline = max(0, decline_diff - 1)  # Reduce penalty by 1
        else:
            adjusted_decline = decline_diff  # Apply regular penalty

        # If under dev_ceiling_age, reduce ratings based on years away from dev_ceiling_age
        if self.bio['age'] < self.archetype.dev_ceiling_age:
            self.start_value -= dev_diff
            self.endurance -= dev_diff
            self.cg_rating += dev_diff * 10  # CG/SHO rating needs larger adjustments
            self.sho_rating += dev_diff * 10
            self.relief_value -= dev_diff  # Adjust for relievers
        elif self.bio['age'] > self.archetype.decline_age:
            # If over decline_age, apply decline penalties
            self.start_value -= adjusted_decline
            self.endurance -= adjusted_decline
            self.cg_rating += adjusted_decline * 10
            self.sho_rating += adjusted_decline * 10
            self.relief_value += adjusted_decline  # Adjust for relievers

        # Clamp the values to stay within valid ranges
        self.start_value = np.clip(self.start_value, 0.5, 7.0)
        self.endurance = np.clip(self.endurance, 0.5, 8.0)
        self.rest = np.clip(self.rest, 4, 8)
        self.cg_rating = np.clip(self.cg_rating, 611, 666)
        self.sho_rating = np.clip(self.sho_rating, 611, 666)
        self.relief_value = np.clip(self.relief_value, -5, 7)
        self.fatigue = np.clip(self.fatigue, 1, 5)

class ManagerProfile:
    def __init__(self):
        self.bio = NameGen().generate_bio()  # Generate bio data (name, age, etc.)
        self.bio['age'] = NameGen().generate_age_personnel()  # Overwrite age with proper personnel age distribution
        self.role = "Manager"

        # these ratings will ultimately be added to the team totals for each game, leadership may be for team morale modifier
        self.manager_leadership = 0 # -3 to +3
        self.manager_hitting = 0 # -3 to +3
        self.manager_pitching = 0 # -3 to +3
        self.manager_fielding = 0 # -3 to +3
        self.manager_bench = 0 # -3 to +3
        self.manager_potential = 0 # 0 to 8 (will dynamically adjust other ratings season to season based on this rating, age and team results)
        # do we need teach/develop ratings (ie manager_teach_pitching)? that would dynamically adjust player ratings during season? in general manager represents entire coaching staff
        self.manager_salary = 0

    def generate_ratings(self): # most of these should be clustered around zero
        self.manager_leadership = min(max(int(np.random.normal(0, 1.5)), -3), 3)
        self.manager_hitting = min(max(int(np.random.normal(0, 1.5)), -3), 3)
        self.manager_pitching = min(max(int(np.random.normal(0, 1.5)), -3), 3)
        self.manager_fielding = min(max(int(np.random.normal(0, 1.5)), -3), 3)
        self.manager_bench = min(max(int(np.random.normal(0, 1.5)), -3), 3)
        self.manager_potential = min(max(int(np.random.normal(4, 1.5)), 0), 8)

    '''
    do we generate manager archetypes (smallball, sabermetric etc) for managers to help dictate lineup, rotation, bullpen gen? but those mostly represent in-game tactics/decisions. we need archetypes for macro-management
    -lineup persistence: how often manager tinkers with lineup (maybe L/R, platoon stuff here) and how long he sticks with it when club is or isnt performing according to certain guidelines (maybe winning pct, runs scored/allowed etc)
    -lineup philosophy: speed, power, batting, eye, defense etc
    -rotation: should be fairly straightforward except maybe decisions to intentionally short-rest or start highest rested based on the opponent, schedule, record, point in season
    -bullpen: can we have any logic here that would let us dynamically altered numbers of relievers used chart? would represent managers with quick hooks for example
    '''

    def generate_lineup(self):
        pass

    def generate_rotation(self):
        pass

    def generate_bullpen(self):
        pass

    def to_dict(self):
        return {
            "manager_name": self.bio['name'],
            "manager_race": self.bio['race'],
            "manager_origin": self.bio['origin'],
            "manager_age": self.bio['age'],
            "manager_leadership": self.manager_leadership,
            "manager_hitting": self.manager_hitting,
            "manager_pitching": self.manager_pitching,
            "manager_fielding": self.manager_fielding,
            "manager_bench": self.manager_bench,
            "manager_potential": self.manager_potential,
            "manager_salary": self.manager_salary
        }

class GMProfile:
    def __init__(self):
        self.bio = NameGen().generate_bio()  # Generate bio data (name, age, etc.)
        self.bio['age'] = NameGen().generate_age_personnel()  # Overwrite age with proper personnel age distribution
        self.role = "GM"
        self.gm_trading = 0 # -3 to +3
        self.gm_free_agents = 0 # -3 to +3
        self.gm_player_development = 0 # -3 to +3
        self.gm_scouting = 0 # -3 to +3
        self.gm_potential = 0 # 0 to 8
        self.gm_salary = 0

    def generate_ratings(self):
        self.gm_trading = min(max(int(np.random.normal(0, 1.5)), -3), 3)
        self.gm_free_agents = min(max(int(np.random.normal(0, 1.5)), -3), 3)
        self.gm_player_development = min(max(int(np.random.normal(0, 1.5)), -3), 3)
        self.gm_scouting = min(max(int(np.random.normal(0, 1.5)), -3), 3)
        self.gm_potential = min(max(int(np.random.normal(4, 1.5)), 0), 8)

    def to_dict(self):
        return {
            "gm_name": self.bio['name'],
            "gm_race": self.bio['race'],
            "gm_origin": self.bio['origin'],
            "gm_age": self.bio['age'],
            "gm_trading": self.gm_trading,
            "gm_free_agents": self.gm_free_agents,
            "gm_player_development": self.gm_player_development,
            "gm_scouting": self.gm_scouting,
            "gm_potential": self.gm_potential,
            "gm_salary": self.gm_salary
        }

class OwnerProfile:
    def __init__(self):
        self.bio = NameGen().generate_bio()  # Generate bio data (name, age, etc.)
        self.bio['age'] = NameGen().generate_age_personnel()  # Overwrite age with proper personnel age distribution
        self.role = "Owner"
        self.owner_budget = 0 # monetary amount OR 0 to 8 and have rating represent range of money available
        self.owner_resources = 0 # 0 to 8
        self.owner_patience = 0 # 0 to 8

    def generate_ratings(self):
        self.owner_budget = min(max(int(np.random.normal(100000000, 10000000)), 0), 1000000000)
        self.owner_resources = min(max(int(np.random.normal(100000000, 10000000)), 0), 1000000000)
        self.owner_patience = min(max(int(np.random.normal(5, 1.5)), 0), 10)
    
    def to_dict(self):
        return {
            "owner_name": self.bio['name'],
            "owner_race": self.bio['race'],
            "owner_origin": self.bio['origin'],
            "owner_age": self.bio['age'],
            "owner_budget": self.owner_budget,
            "owner_resources": self.owner_resources,
            "owner_patience": self.owner_patience
        }

class ScoutingProfile:
    def __init__(self):
        self.bio = NameGen().generate_bio()  # Generate bio data (name, age, etc.)
        self.bio['age'] = NameGen().generate_age_personnel()  # Overwrite age with proper personnel age distribution
        self.role = "Scouting"
        self.scouting_accuracy = 0 # 0 to 8 
        self.scouting_resources = 0 # 0 to 8
        self.scouting_amateurs = 0 # 0 to 8
        self.scouting_pros = 0 # 0 to 8
        self.scouting_potential = 0 # 0 to 8
        self.scouting_international = 0 # 0 to 8

class AgentProfile:
    def __init__(self):
        self.bio = NameGen().generate_bio()  # Generate bio data (name, age, etc.)
        self.bio['age'] = NameGen().generate_age_personnel()  # Overwrite age with proper personnel age distribution
        self.role = "Agent"
        self.agent_experience = 0 # in years
        self.agent_reputation = 0 # 0 to 8 (boras corp would be 8)
        self.agent_negotiating = 0 # 0 to 8

    def generate_ratings(self):
        self.agent_experience = min(max(int(np.random.normal(10, 1.5)), 0), 15)
        self.agent_reputation = min(max(int(np.random.normal(5, 1.5)), 0), 8)
        self.agent_negotiating = min(max(int(np.random.normal(5, 1.5)), 0), 8)
    
    def to_dict(self):
        return {
            "agent_name": self.bio['name'],
            "agent_race": self.bio['race'],
            "agent_origin": self.bio['origin'],
            "agent_age": self.bio['age'],
            "agent_experience": self.agent_experience,
            "agent_reputation": self.agent_reputation,
            "agent_negotiating": self.agent_negotiating
        } 

class ScoutingReport:
    def __init__(self, player_data):
        self.player_data = player_data  # All attributes from player generation
        self.report_sections = []       # Stores the dynamically generated report sections
        self.templates = self.load_templates()  # Load the JSON templates for all ratings and attributes

    def load_templates(self):
        # Load JSON files that contain text templates for ratings, archetypes, and other attributes
        with open(SCOUTING_REPORTS_FILE, 'r') as f:
            return json.load(f)

    def generate_report(self):
        # Check if player is a pitcher or batter based on position
        if self.player_data['position'] in ['SP', 'RP']:
            # Generate the pitcher's report
            self.add_demographics(batter=False)
            self.add_archetype_description(batter=False)
            self.add_pitcher_skills_analysis()
            self.add_potential_and_outlook(batter=False)
            self.add_summary(batter=False)
        else:
            # Generate the batter's report
            self.add_demographics(batter=True)
            self.add_archetype_description(batter=True)
            self.add_batter_skills_analysis()
            self.add_potential_and_outlook(batter=True)
            self.add_summary(batter=True)

        # Join the sections with a space, replace curly apostrophes with straight ones
        final_report = " ".join(self.report_sections)  # Use a space instead of '\n' for a continuous paragraph
        final_report = final_report.replace("\u00e2\u20ac\u2122", "'")  # Replace curly apostrophes with straight ones
        return final_report


    def add_demographics(self, batter=True):
        # Differentiate between batters and pitchers for demographic information
        if batter:
            demographics = (
                f"{self.player_data['name']} is a {self.player_data['age']}-year-old "
                f"{self.player_data['bats']} handed batter who plays {self.player_data['position']}."
            )
        else:
            demographics = (
                f"{self.player_data['name']} is a {self.player_data['age']}-year-old "
                f"{self.player_data['throws']} handed pitcher."
            )
        self.report_sections.append(demographics)

    def add_archetype_description(self, batter=True):
        # Use batting or pitching archetype from JSON
        archetype_key = 'batting_archetype' if batter else 'pitching_archetype'
        archetype = self.player_data['archetype']
        if archetype in self.templates[archetype_key]:
            description = self.templates[archetype_key][archetype]
            self.report_sections.append(description)

    def add_batter_skills_analysis(self):
        # Only include batter-specific ratings
        ratings = ['batting', 'power', 'eye', 'speed', 'fielding']
        for rating in ratings:
            self.add_attribute_analysis(rating)

    def add_pitcher_skills_analysis(self):
        # Only include pitcher-specific ratings
        ratings = ['start_value', 'endurance', 'rest', 'cg_rating', 'sho_rating', 'relief_value', 'fatigue']
        for rating in ratings:
            self.add_attribute_analysis(rating)

    def add_attribute_analysis(self, attribute):
        # Get player rating for the attribute
        player_value = self.player_data[attribute]
        # Get the relevant template phrases for this attribute
        if attribute in self.templates:
            phrases = self.templates[attribute]
            # Filter by conditions (min/max)
            valid_phrases = [
                phrase['text'] for phrase in phrases
                if phrase['min'] <= player_value <= phrase['max']
            ]
            # Pick one phrase, weighted by the 'weight' value
            if valid_phrases:
                # Filter both valid phrases and their weights based on min/max
                valid_phrases_with_weights = [(phrase['text'], phrase['weight']) for phrase in phrases if phrase['min'] <= player_value <= phrase['max']]

                # Separate valid phrases and their respective weights
                if valid_phrases_with_weights:
                    valid_phrases, weights = zip(*valid_phrases_with_weights)  # Unzip into separate lists
                    selected_phrase = random.choices(valid_phrases, weights=weights)[0]  # Use the correct matching weights
                    self.report_sections.append(selected_phrase)


    def add_potential_and_outlook(self, batter=True):
        # Use batter or pitcher potential from JSON
        # age is crticial here, as it will determine how much potential is left if any
        potential_key = 'batting_potential' if batter else 'pitching_potential'
        potential = self.player_data['potential']
        if potential in self.templates[potential_key]:
            outlook = self.templates[potential_key][potential]
            self.report_sections.append(outlook)

    def add_summary(self, batter=True):
        # Differentiate the summary for batters and pitchers
        if batter:
            summary = (
                f"In summary, {self.player_data['name']} has shown "
                f"promise with {self.player_data['power']} power and {self.player_data['speed']} speed. "
                "He is expected to be a key player in the future."
            )
        else:
            summary = (
                f"In summary, {self.player_data['name']} has demonstrated "
                f"strong endurance with a starting value of {self.player_data['start_value']} and "
                f"reliable relief value of {self.player_data['relief_value']}. "
                "He is expected to be a key contributor in the pitching staff."
            )
        self.report_sections.append(summary)


# Assuming msa_data is already loaded from the external source with 'City', 'Population', 'Latitude', 'Longitude', and 'State' columns.
msa_data = pd.read_excel(TEAM_GENERATION_FILE)

class Team:
    """Class for representing a team with a roster of players."""
    def __init__(self, team_id, name, city, state, league_name, division_name):
        self.team_id = team_id
        self.name = name
        self.city = city
        self.state = state
        self.team_colors = self.generate_team_colors()
        self.ballpark = self.generate_ballpark()
        self.league_name = league_name
        self.division_name = division_name
        self.roster = self.generate_roster()  # Generate roster during team creation
        self.manager = ManagerProfile()  # Generate manager
        self.gm = GMProfile()  # Generate GM
        self.manager.generate_ratings()
        self.gm.generate_ratings()

        # Track fielding ratings for starters
        self.team_fielding_ratings, self.key_positions = self.compile_fielding_ratings()
        
        # Generate unearned runs chart based on fielding
        self.unearned_runs_chart = self.generate_unearned_runs_chart(self.team_fielding_ratings, self.key_positions)

    def compile_fielding_ratings(self):
        """
        Compile the fielding ratings for the team, focusing on key positions like SS and CF.
        Returns a list of total fielding ratings and a dictionary for key positions.
        """
        # Extract fielding ratings from the starting 9
        fielding_ratings = []
        key_positions = {}

        for player in self.roster['Starting 9']:
            position = player['position']
            fielding_rating = player['fielding']  # Assuming 'fielding' is a player attribute

            # Track the fielding rating for all starters
            fielding_ratings.append(fielding_rating)

            # Track key positions (SS and CF) separately
            if position == 'SS' or position == 'CF':
                key_positions[position] = fielding_rating

        return fielding_ratings, key_positions

    def generate_ballpark(self):
        """Generate ballpark information for the team."""
        # Placeholder for ballpark name (you can enhance this later with a name generator)
        ballpark_name = self.generate_ballpark_name()

        # Generate random home field advantage and stadium value (use a normal distribution for random values)
        home_field_advantage = max(min(int(np.random.normal(0, 1.5)), 3), -3)  # Range: -3 to +3
        stadium_value = max(min(int(np.random.normal(0, 1.5)), 3), -3)  # Range: -3 to +3

        return {
            "ballpark_name": ballpark_name,
            "home_field_advantage": home_field_advantage,
            "stadium_value": stadium_value
        }

    def generate_ballpark_name(self):
        """Generate a random ballpark name (placeholder)."""
        # This is a placeholder logic; you can replace it with a name generation mechanism later
        sample_names = ["Memorial Field", "Liberty Stadium", "Sunshine Park", "Riverfront Stadium"]
        return r.choice(sample_names)

    def generate_team_colors(self):
        """Generate random primary color in hex and its complementary color."""
        # Generate a random primary hex color
        primary_color = '#' + ''.join([r.choice('0123456789ABCDEF') for _ in range(6)])

        # Calculate the complementary color
        complementary_color = self.complementary_color(primary_color)

        return {"primary": primary_color, "complementary": complementary_color}

    def complementary_color(self, my_hex):
        """Returns the complementary hex color."""
        # Remove the '#' symbol if it's there
        if my_hex[0] == '#':
            my_hex = my_hex[1:]
        
        # Ensure the hex is 6 characters
        if len(my_hex) != 6:
            raise ValueError("Input must be a 6 character hex color code.")

        # Split hex into RGB components
        rgb = (my_hex[0:2], my_hex[2:4], my_hex[4:6])

        # Calculate the complementary color
        comp = ['%02X' % (255 - int(a, 16)) for a in rgb]

        # Return the complementary color in hex format
        return '#' + ''.join(comp)

    def generate_unearned_runs_chart(self, team_fielding_ratings, key_positions):
        """
        Generate an unearned runs allowed chart based on team fielding ratings and key defensive positions.
        :param team_fielding_ratings: A list of fielding ratings for the starting players (-3 to +3).
        :param key_positions: A dictionary with key positions (like SS and CF) and their fielding ratings.
        :return: A dictionary representing the unearned runs chart.
        """
        dice_roll_totals = [3, 4, 5, 6, 7, 8, 9, 10]
        dice_roll_probabilities = [0.5, 1.4, 2.8, 4.6, 6.9, 9.7, 11.6, 12.5]
        
        total_fielding = sum(team_fielding_ratings)
        base_unearned_runs = 0.57  # Based on MLB averages
        avg_fielding = total_fielding / len(team_fielding_ratings)
        
        fielding_adjustment = np.clip(avg_fielding, -3, 3) * 0.1
        adjusted_unearned_runs = base_unearned_runs + fielding_adjustment
        
        total_unearned_runs = round(adjusted_unearned_runs * 10)  # Scale to a season-like number
        
        unearned_runs_chart = {total: 0 for total in dice_roll_totals}
        
        for i, dice_total in enumerate(dice_roll_totals):
            prob = dice_roll_probabilities[i] / sum(dice_roll_probabilities)
            unearned_runs_chart[dice_total] = round(prob * total_unearned_runs)
        
        for position, rating in key_positions.items():
            if rating > 0:
                dice_total_to_zero = np.random.choice(dice_roll_totals, size=rating, replace=False)
                for dt in dice_total_to_zero:
                    unearned_runs_chart[dt] = 0
            elif rating < 0:
                dice_total_to_add = np.random.choice(dice_roll_totals, size=-rating, replace=False)
                for dt in dice_total_to_add:
                    unearned_runs_chart[dt] += 1

        for total in unearned_runs_chart:
            unearned_runs_chart[total] = min(unearned_runs_chart[total], 3)
        
        return unearned_runs_chart

    def generate_roster(self):
        logger.debug(f"LINE 1237 - Generating roster for team: {self.name}")
        """Generate a team roster with players for each role."""
        roster = {
            'Starting 9': self.generate_starting_9(),
            'Bench': self.generate_bench(),
            'Pitchers': self.generate_pitching_staff()
        }

        # Pass the roster to LineupManager for reordering
        lineup_manager = LineupManager(roster)
        
        # Reorder the batting lineup
        reordered_lineup = lineup_manager.construct_lineup()
        roster['Starting 9'] = reordered_lineup
        
        # Reorder the pitching staff (this reorders pitchers in place)
        lineup_manager.reorder_pitchers()

        # Assign roles: Starter for first 9 players, Bench for the next 6
        logger.debug(f"LINE 1246 - Assigning roles for {self.name}. Starter for the first 9, Bench for the next 6")
        for i, player in enumerate(roster['Starting 9']):
            player['role'] = 'Starter'  # Assign "Starter" to the first 9 players
            logger.debug(f"LINE 1249 - {player['name']} assigned role: Starter")

            # Instantiate the ScoutingReport for the player
            scouting_report = ScoutingReport(player)  # Pass the player object to ScoutingReport
            player['scouting_report'] = scouting_report.generate_report()  # Generate and attach the report

        for i, player in enumerate(roster['Bench']):
            player['role'] = 'Bench'  # Assign "Bench" to the bench players
            logger.debug(f"LINE 1253 - {player['name']} assigned role: Bench")

            # Instantiate the ScoutingReport for the player
            scouting_report = ScoutingReport(player)  # Pass the player object to ScoutingReport
            player['scouting_report'] = scouting_report.generate_report()  # Generate and attach the report

        # For pitchers, assign their scouting reports too
        for pitcher in roster['Pitchers']:
            scouting_report = ScoutingReport(pitcher)  # Pass the pitcher object to ScoutingReport
            pitcher['scouting_report'] = scouting_report.generate_report()  # Generate and attach the report

        return roster

    def generate_starting_9(self):
        """Generate the starting 9 players for the team."""

        positions = ['C', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF', 'DH']  # All required positions
        starting_9 = []
        for position in positions:
            player = self.create_player(position)
            player['role'] = 'Starter'  # Assign the "Starter" role
            starting_9.append(player)

        return starting_9

    def generate_bench(self):
        """Generate 6 bench players: 2 OF, 2 IF, 1 C, and 1 additional utility player."""
        bench_positions = ['OF', 'OF', 'IF', 'IF', 'C', 'Utility']
        bench = []
        for position in bench_positions:
            if position == 'OF':
                position = np.random.choice(['LF', 'CF', 'RF'])
            elif position == 'IF':
                position = np.random.choice(['1B', '2B', '3B', 'SS'])
            elif position == 'Utility':
                position = np.random.choice(['C', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF'])

            player = self.create_player(position)
            player['role'] = 'Bench'  # Assign the "Bench" role
            bench.append(player)
        return bench

    def generate_pitching_staff(self):
        """Generate the pitching staff: 5 starters and 5 relievers."""
        starters = [self.create_player('SP') for _ in range(5)]
        relievers = [self.create_player('RP') for _ in range(5)]

        # Ensure each pitcher has the correct type set in their profile
        for starter in starters:
            starter['type'] = 'Starter'
        for reliever in relievers:
            reliever['type'] = 'Reliever'

        return starters + relievers

    def assign_pitcher_type(self, position):
        """Assign pitcher type as 'Starter' or 'Reliever' based on the position."""
        if position == 'SP':
            return 'Starter'
        elif position == 'RP':
            return 'Reliever'
        
    def generate_farm_system(self):
        """Generate the farm system for the team. 10 players, 5 bat, 5 pitch, 18 to 23 yo, we still generate bio as normal, including archetype and age related penalties apply"""
        pass

    def generate_minor_leaguer(self):
        """Generate a minor league player for the farm system."""
        pass

    # Utility function to map grade_prob to the actual archetype
    def map_grade_prob_to_archetype(self, grade_prob, player_type):
        """Map gradeX_prob to the corresponding archetype based on player type (batter, starter, reliever)."""
        batter_archetypes = {
            'grade1_prob': 'scrub', 'grade2_prob': 'career minor leaguer', 'grade3_prob': 'september callup',
            'grade4_prob': 'injury replacement', 'grade5_prob': 'AAAA player', 'grade6_prob': 'backup',
            'grade7_prob': 'platoon', 'grade8_prob': 'regular starter', 'grade9_prob': 'star', 'grade10_prob': '5-tool'
        }
        
        starter_archetypes = {
            'grade1_prob': 'journeyman', 'grade2_prob': 'fringe starter', 'grade3_prob': 'late bloomer',
            'grade4_prob': 'spot starter', 'grade5_prob': 'quad-a arm', 'grade6_prob': 'swingman',
            'grade7_prob': 'back of rotation', 'grade8_prob': 'regular starter', 'grade9_prob': 'top of rotation', 'grade10_prob': 'ace'
        }
        
        reliever_archetypes = {
            'grade1_prob': 'filler arm', 'grade2_prob': 'taxi squad reliever', 'grade3_prob': 'roster expansion reliever',
            'grade4_prob': 'bullpen patch', 'grade5_prob': 'perpetual callup', 'grade6_prob': 'specialist',
            'grade7_prob': 'long-relief', 'grade8_prob': 'low-leverage', 'grade9_prob': 'high-leverage', 'grade10_prob': 'closer'
        }
        
        if player_type == 'batter':
            return batter_archetypes[grade_prob]
        elif player_type == 'starter':
            return starter_archetypes[grade_prob]
        elif player_type == 'reliever':
            return reliever_archetypes[grade_prob]
        else:
            raise ValueError("Invalid player type for archetype mapping.")

    def create_player(self, position):
        logger.debug(f"LINE 1338 - Creating player for position: {position}")
        bio = NameGen().generate_bio(position)

        # Now pass school_type from the bio
        player_profile = PlayerProfile(position)
        # Log the bio after generation
        logger.debug(f"LINE 1344 - Generated bio for {player_profile.bio['name']} - Position: {player_profile.bio['position']}, School: {player_profile.bio['school']}, Origin: {player_profile.bio['origin']}")

        # Generate school and determine the school type (HS or College)
        school_name = player_profile.bio['school']
        school_type = player_profile.school_type
        logger.debug(f"LINE 1349 - Player {player_profile.bio['name']} school: {school_name}, School type: {school_type}")

        # Fetch the appropriate grade probabilities from the school data in the Excel sheet
        school_probs = Archetype.get_archetype_probs(school_name, school_type)
        logger.debug(f"LINE 1353 - Fetched archetype probabilities for {school_name} (type: {school_type}): {school_probs}")
        
        # Random probability for archetype
        rand_prob = random.random()
        logger.debug(f"LINE 1357 - Random Probability for {player_profile.bio['name']}: {rand_prob}")

        # Map to the correct archetype
        for col, threshold in school_probs.items():
            if rand_prob <= threshold:
                grade_prob = col
                logger.debug(f"LINE 1363 - {player_profile.bio['name']} assigned grade_prob: {grade_prob} for archetype mapping.")
                break
            else:
                grade_prob = 'grade1_prob'
                logger.debug(f"LINE 1367 - {player_profile.bio['name']} assigned grade_prob: {grade_prob} for archetype mapping.")
            
        # Determine player type and map to archetype
        if position == 'SP':  # Starter
            archetype_name = self.map_grade_prob_to_archetype(grade_prob, 'starter')
            logger.debug(f"LINE 1373 - {player_profile.bio['name']} (Starter) Archetype: {archetype_name}")
            archetype = next(a for a in PitcherProfile.starter_archetypes if a.name == archetype_name)
            player_profile.profile = PitcherProfile(player_profile.bio, archetype)
            player_profile.profile.type = 'Starter'
        elif position == 'RP':  # Reliever
            archetype_name = self.map_grade_prob_to_archetype(grade_prob, 'reliever')
            logger.debug(f"LINE 1379 - {player_profile.bio['name']} (Reliever) Archetype: {archetype_name}")
            archetype = next(a for a in PitcherProfile.reliever_archetypes if a.name == archetype_name)
            player_profile.profile = PitcherProfile(player_profile.bio, archetype)
            player_profile.profile.type = 'Reliever'
        else:  # Batter
            valid_batter_positions = ['C', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF', 'DH']
            if position not in valid_batter_positions:
                position = random.choice(valid_batter_positions)
            player_profile.bio['position'] = position

            archetype_name = self.map_grade_prob_to_archetype(grade_prob, 'batter')
            logger.debug(f"LINE 1390 - {player_profile.bio['name']} (Batter) Archetype: {archetype_name}")
            archetype = next(a for a in BatterProfile.batter_archetypes if a.name == archetype_name)
            player_profile.profile = BatterProfile(player_profile.bio, archetype)

        # Log before generating ratings
        logger.debug(f"LINE 1395 - Generating ratings for {player_profile.bio['name']}")
        player_profile.generate_ratings()  

        return player_profile.to_dict()  # Return player data as a dictionary


    def to_dict(self):
        """Convert the team and roster information to a dictionary format for JSON output."""
        team_data = {
            "team_id": self.team_id,
            "team_city": self.city,
            "team_name": self.name,
            "team_colors": self.team_colors,
            "ballpark_name": self.ballpark["ballpark_name"],
            "home_field_advantage": self.ballpark["home_field_advantage"],
            "stadium_value": self.ballpark["stadium_value"],
            "league_name": self.league_name,
            "division_name": self.division_name,
            "unearned_runs_chart": self.unearned_runs_chart,
            "players": self.roster['Starting 9'] + self.roster['Bench'],
            "pitchers": self.roster['Pitchers'],
            "personnel": {
                "gm": self.gm.to_dict(),
                "manager": self.manager.to_dict()
            }
        }
        return team_data

    def __repr__(self):
        return f"Team({self.city} {self.name})"

class LineupManager:
    def __init__(self, roster):
        self.roster = roster
        self.lineup = []  # Initialize the lineup as an empty list
        self.reordered_starters = []
        self.reordered_relievers = []

    def construct_lineup(self):
        """Rearranges the team's batting lineup based on archetypes and ratings."""
        starters = self.roster['Starting 9']
        
        lineup = [None] * 9
        # Assign each lineup spot based on the key ratings (batting, power, eye, speed, etc.) and archetype priority
        lineup[0] = self.get_best_player(starters, primary="eye", secondary="batting", tertiary="speed")  # Leadoff
        self.lineup.append(lineup[0])

        lineup[1] = self.get_best_player(starters, primary="batting", secondary="eye", tertiary="power")  # #2 Hitter
        self.lineup.append(lineup[1])

        lineup[2] = self.get_best_player(starters, primary="batting", secondary="power", tertiary="eye")  # #3 Hitter
        self.lineup.append(lineup[2])

        lineup[3] = self.get_best_player(starters, primary="power")  # Cleanup
        self.lineup.append(lineup[3])

        lineup[4] = self.get_best_player(starters, primary="power")  # #5 Hitter
        self.lineup.append(lineup[4])

        logger.debug("Starting lineup construction")
        
        # Fill positions 6-9 with best of the rest, considering fielding as a factor
        for i in range(5, 9):
            lineup[i] = self.get_best_player(starters, primary="batting", secondary="power", fielding_priority=True)
            self.lineup.append(lineup[i])

        return lineup

    def get_best_player(self, players, primary, secondary=None, tertiary=None, fielding_priority=False):
        """Return the player with the highest rating based on the given criteria and archetype."""
        # Filter out already used players from the pool
        available_players = [p for p in players if p not in self.lineup]  # Exclude players already in the lineup

        # Sort by archetype priority first
        sorted_players = sorted(available_players, key=lambda x: self.get_archetype_priority(x), reverse=True)

        # Further sort by primary, secondary, tertiary criteria, or fielding priority within the same archetype tier
        sorted_players = sorted(sorted_players, key=lambda x: x[primary], reverse=True)

        if secondary:
            sorted_players = sorted(sorted_players, key=lambda x: x[secondary], reverse=True)
        if tertiary:
            sorted_players = sorted(sorted_players, key=lambda x: x[tertiary], reverse=True)
        if fielding_priority:
            sorted_players = sorted(sorted_players, key=lambda x: x['fielding'] if x['fielding'] >= 2 else 0, reverse=True)

        # Return the top player (archetype + ratings considered)
        return sorted_players[0]


    def reorder_pitchers(self):
        """Reorder the pitching staff based on the type ('Starter' or 'Reliever') and other criteria."""
        pitchers = self.roster['Pitchers']  # This is a flat list of all pitchers

        # Separate starters and relievers based on their 'type' attribute
        starters = [p for p in pitchers if p['type'] == 'Starter']
        relievers = [p for p in pitchers if p['type'] == 'Reliever']

        # Sort starters by archetype priority and start value
        reordered_starters = sorted(starters, key=lambda p: (self.get_archetype_priority(p), p['start_value']), reverse=True)

        # Sort relievers by archetype priority and relief value
        reordered_relievers = sorted(relievers, key=lambda p: (self.get_archetype_priority(p), p['relief_value']), reverse=True)

        # Combine starters and relievers back into the original pitcher list
        self.roster['Pitchers'] = reordered_starters + reordered_relievers

    def get_archetype_priority(self, player):
        """Get the archetype priority for a player. Higher numbers mean higher priority."""
        
        # Define the archetype priority for batters
        batter_priority = {
            'scrub': 1,
            'career minor leaguer': 2,
            'september callup': 3,
            'injury replacement': 4,
            'aaaa player': 5,
            'backup': 6,
            'platoon': 7,
            'regular starter': 8,
            'star': 9,
            '5-tool': 10
        }

        # Define the archetype priority for starters
        starter_priority = {
            'journeyman': 1,
            'fringe starter': 2,
            'late bloomer': 3,
            'spot starter': 4,
            'quad-a arm': 5,
            'swingman': 6,
            'back of rotation': 7,
            'regular starter': 8,
            'top of rotation': 9,
            'ace': 10
        }

        # Define the archetype priority for relievers
        reliever_priority = {
            'filler arm': 1,
            'taxi squad reliever': 2,
            'roster expansion reliever': 3,
            'bullpen patch': 4,
            'perpetual callup': 5,
            'specialist': 6,
            'long-relief': 7,
            'low-leverage': 8,
            'high-leverage': 9,
            'closer': 10
        }

        # Determine the player's archetype and type, and return the appropriate priority
        archetype = player.get('archetype', '').lower()
        player_type = player.get('type', '').lower()

        if player_type == 'batter':
            return batter_priority.get(archetype, 0)  # Batter archetype priority
        elif player_type == 'starter':
            return starter_priority.get(archetype, 0)  # Starter archetype priority
        elif player_type == 'reliever':
            return reliever_priority.get(archetype, 0)  # Reliever archetype priority
        else:
            return 0  # Fallback if type not found or archetype is not recognized


class MarkovChain:
    def __init__(self, data):
        self.data = data
        self.chain = self.build_chain()

    def build_chain(self):
        chain = {}
        for name in self.data:
            for i in range(len(name) - 1):
                if name[i] not in chain:
                    chain[name[i]] = []
                chain[name[i]].append(name[i + 1])
        return chain

    def generate_name(self, length=15):
        name = random.choice(list(self.chain.keys()))
        while len(name) < length:
            name += random.choice(self.chain[name[-1]])
        return name
    
# Load the msa data from Excel
msa_data = pd.read_excel(TEAM_GENERATION_FILE, sheet_name='CITY')

# Clean column names by stripping extra spaces
msa_data.columns = msa_data.columns.str.strip()

# Now try to access the 'msa' column
city_names = msa_data['msa'].tolist()
markov_chain = MarkovChain(city_names)

class League:
    def __init__(self, num_teams, num_divisions, msa_data, nickname_data):
        self.num_teams = num_teams
        self.num_divisions = num_divisions
        self.msa_data = msa_data
        self.nickname_data = nickname_data
        self.selected_cities = {}
        self.used_nicknames = set()  # Track used nicknames
        self.teams = self.generate_league()

    # Create an instance of MarkovChain for league name parts
    markov_chain = MarkovChain(league_name_parts)

    # Generate a random league name with or without a sponsor
    def generate_league_name(self):
        corporate_name = random.choice(corporate_names)  # Randomly pick a corporate name
        league_name = markov_chain.generate_name()  # Generate a league name
        
        # Decide randomly whether to use the corporate name or a combination
        naming_style = random.choice(['affix', 'full_corp', 'full_name'])
        
        if naming_style == 'affix':
            # Append or prepend the corporate name to the league name
            if random.choice(['prefix', 'suffix']) == 'prefix':
                return f"{corporate_name} {league_name} League"
            else:
                return f"{league_name} {corporate_name} League"
        elif naming_style == 'full_corp':
            # Use the corporate name alone
            return f"{corporate_name} League"
        else:
            # Use a pure league name
            return f"{league_name} League"

    def select_nickname(self):
        """Select a unique nickname from the nickname_data."""
        available_nicknames = self.nickname_data[~self.nickname_data['nickname'].isin(self.used_nicknames)]
        if available_nicknames.empty:
            raise ValueError("No nicknames left to assign.")
        nickname_row = available_nicknames.sample(n=1).iloc[0]
        self.used_nicknames.add(nickname_row['nickname'])  # Add to used set
        return nickname_row['nickname']

    def generate_team_name(self, city_name):
        """Generate a team name using the city name and a unique nickname."""
        nickname = self.select_nickname()
        return f"{nickname.title()}" 

    def get_city_weight(self, row):
        """Calculate a combined weight for a city based on its population and GDP rank."""
        population_weight = row['population'] / self.msa_data['population'].max()
        gdp_weight = 1 / row['gdp_rank']  # Inverse of the rank, lower rank is better
        return population_weight * gdp_weight

    def generate_league(self):
        teams = []
        league_name = self.generate_league_name()  # Generate league name once for all teams
        for team_id in range(1, self.num_teams + 1):
            try:
                city = self.select_city(teams)
            except ValueError as e:
                logger.debug(f"LINE 1517 - DEBUG: Error selecting city: {e}")
                continue  # Skip or retry city selection if it fails

            # Generate team name using only the nickname, city used separately
            team_name = self.generate_team_name(city)

            # Pass the generated team_id, league name, and other details when creating the team
            new_team = Team(team_id, team_name, city, state="", league_name=league_name, division_name="Some Division")
            teams.append(new_team)

        return teams

    def select_city(self, existing_teams):
        """Select a city from the available MSA data, ensuring no more than 2 teams in the same MSA."""
        # Copy the MSA data
        valid_cities = self.msa_data.copy()

        # Create the 'msa_base' column by extracting the first city from the 'msa' field
        if 'msa_base' not in valid_cities.columns:
            valid_cities['msa_base'] = valid_cities['msa'].apply(lambda x: x.split('-')[0].strip())

        # Extract the city names from existing teams
        selected_msa_counts = pd.Series([team.city for team in existing_teams]).apply(
            lambda x: valid_cities[valid_cities['msa'].str.contains(x)]['msa_base'].values[0] if not valid_cities[valid_cities['msa'].str.contains(x)].empty else None
        ).value_counts()

        # Exclude MSAs that already have 2 teams
        msas_to_exclude = selected_msa_counts[selected_msa_counts >= 2].index.tolist()
        valid_cities = valid_cities[~valid_cities['msa_base'].isin(msas_to_exclude)]

        # Debugging: Log excluded MSAs and the remaining valid cities
        # print(f"DEBUG: Excluded MSAs: {msas_to_exclude}")
        # print(f"DEBUG: Remaining valid MSAs: {valid_cities[['msa', 'msa_base']]}")

        # If no valid cities remain after exclusions
        if valid_cities.empty:
            raise ValueError("Unable to select a valid city from MSA.")

        # Calculate weights for remaining cities
        valid_cities['weight'] = valid_cities.apply(self.get_city_weight, axis=1)

        # Select a city randomly, weighted by population and GDP rank
        city_row = valid_cities.sample(n=1, weights=valid_cities['weight']).iloc[0]

        # Handle the case where multiple cities are in the same MSA
        msa = city_row['msa'].split('-')
        for city_name in msa:
            city_name = city_name.strip()
            if city_name not in self.selected_cities.get(city_row['msa_base'], []):
                # If this city is not already selected, use it
                self.selected_cities.setdefault(city_row['msa_base'], []).append(city_name)
                return city_name

        raise ValueError("Unable to select a valid city from MSA.")

    def get_coordinates(self, city_name):
        city_row = self.msa_data[self.msa_data['City'] == city_name].iloc[0]
        return (city_row['Latitude'], city_row['Longitude'])

    def generate_divisions(self):
        divisions = {f'Division {i+1}': [] for i in range(self.num_divisions)}
        teams_per_division = self.num_teams // self.num_divisions
        for i, team in enumerate(self.teams):
            division = f'Division {(i // teams_per_division) + 1}'
            divisions[division].append(team)
        return divisions

    def generate_amateur_player_pool(self):
        """generate a list of amateur players. generate players as normal except only ages 18-22. we print this to its own separate list (json/excel) to store for main game. ratings structure will be same except we add signability and bonus demand"""
        amateur_players = []
        pass

    def save_teams_to_json(self):
        """Save each team's roster to a separate JSON file."""
        # Use centralized folder path
        folder_path = PENNANT_FEVER_LEAGUE_FILES_DIR

        # Ensure the directory exists
        folder_path.mkdir(parents=True, exist_ok=True)

        for team in self.teams:
            team_data = team.to_dict()
            team_data = convert_numpy_types(team_data)  # Convert NumPy types to Python types
            
            # Sanitize city and team name for the filename
            sanitized_city = sanitize_filename(team.city)
            sanitized_name = sanitize_filename(team.name)
            
            file_name = f"team_id_{team.team_id}.json"
            file_path = folder_path / file_name

            with open(file_path, 'w') as f:
                json.dump(team_data, f, indent=4)
            logger.debug(f"LINE 1610 - Saved team {team.city} {team.name} to {file_path}")

    def print_teams_and_rosters(self):
        """Print the generated teams and their rosters to an Excel file."""
        batters_data = []
        pitchers_data = []

        for team in self.teams:
            # Collecting batter data (starting 9 and bench)
            for player in team.roster['Starting 9'] + team.roster['Bench']:
                # Add the team information to each player for context
                player_data = player.copy()
                player_data['team'] = f"{team.city} {team.name}"
                batters_data.append(player_data)

            # Collecting pitcher data
            for player in team.roster['Pitchers']:
                # Add the team information to each pitcher for context
                player_data = player.copy()
                player_data['team'] = f"{team.city} {team.name}"
                pitchers_data.append(player_data)

        # Convert the data into DataFrames for easier export
        batters_df = pd.DataFrame(batters_data)
        pitchers_df = pd.DataFrame(pitchers_data)

        # Get the current timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        # Specify the Excel file path with the timestamp using centralized paths
        file_path = PENNANT_FEVER_LEAGUE_FILES_DIR / f"league_rosters_{timestamp}.xlsx"

        # Ensure the directory exists
        PENNANT_FEVER_LEAGUE_FILES_DIR.mkdir(parents=True, exist_ok=True)

        # Use ExcelWriter to create an Excel file with two sheets
        with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
            batters_df.to_excel(writer, sheet_name='Batters', index=False)
            pitchers_df.to_excel(writer, sheet_name='Pitchers', index=False)

        logger.debug(f"LINE 1650 - Rosters saved to {file_path}")

class PlayerProfile:
    """PlayerProfile class for batter and pitcher profiles."""
    def __init__(self, position):
        self.position = position
        name_gen = NameGen()
        self.bio = name_gen.generate_bio(position)
        self.school_type = self.bio.get('school_type')  # Directly use the generated school_type
        logger.debug(f"Line 1657 - PlayerProfile - Position: {self.position}, School Type: {self.school_type}")

    def generate_ratings(self):
        """Generate player ratings based on position."""
        if self.position in ['SP', 'RP']:
            # The profile should already be assigned in create_player, no need to recreate it
            self.profile.generate_ratings()
        else:
            # Similarly for batters, use the profile already created in create_player
            self.profile.generate_ratings()

    def to_dict(self):
        """Return combined bio and ratings in a single, flattened dictionary with bio information first."""
        bio_dict = self.bio.copy()  # Start with bio data
        profile_dict = self.profile.__dict__.copy()  # Get ratings data
        if 'bio' in profile_dict:
            del profile_dict['bio']  # Remove nested bio if it exists
        if 'archetype' in profile_dict:
            profile_dict['archetype'] = profile_dict['archetype'].name  # Only keep the archetype name

        # Change the key from 'contact' to 'batting'
        if 'contact' in profile_dict:
            profile_dict['batting'] = profile_dict.pop('contact')  # Rename 'contact' to 'batting'

        combined_dict = {**bio_dict, **profile_dict}  # Merge bio and profile data, bio first
        return combined_dict

# Example usage
num_teams = 30
num_divisions = 6
league = League(num_teams, num_divisions, msa_data, nickname_data)

# Generate league name and divisions
league_name = league.generate_league_name()
divisions = league.generate_divisions()
league.print_teams_and_rosters()
league.save_teams_to_json()

print("League Name:", league_name)
print("Divisions:", divisions)



