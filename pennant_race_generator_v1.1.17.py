import pandas as pd
import numpy as np
import random
import random as r
import scipy.stats as stats
import datetime
from geopy.distance import geodesic
import os
import json
import re

# Load the datasets once
first_names_df = pd.read_excel(r'C:\Users\vadim\Documents\Code\_pennant_race\first_names_weighted_v2.xlsx')
surnames_df = pd.read_excel(r'C:\Users\vadim\Documents\Code\_pennant_race\surnames_weighted_v4.xlsx')
high_school_df = pd.read_excel(r'C:\Users\vadim\Documents\Code\_pennant_race\schools_register.xlsx', sheet_name='HS')
college_df = pd.read_excel(r'C:\Users\vadim\Documents\Code\_pennant_race\schools_register.xlsx', sheet_name='COL')

# Load city data from CITY sheet
city_data = pd.read_excel(r'C:\Users\vadim\Documents\Code\_pennant_race\team_generation.xlsx', sheet_name='CITY')

# Load nickname data from NICKNAMES sheet
nickname_data = pd.read_excel(r'C:\Users\vadim\Documents\Code\_pennant_race\team_generation.xlsx', sheet_name='NICKNAMES')

def sanitize_filename(name):
    """Sanitize the team name to create a valid filename."""
    # Replace any character that is not alphanumeric or underscore with an underscore
    return re.sub(r'[^a-zA-Z0-9_]', '_', name)

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

        # Generate height, weight, and position together, but keep the provided primary position intact
        self.height, self.weight, generated_position = self.generate_height_weight_and_position(position)

        # Only use the generated position if no primary position was explicitly passed
        self.position = position if position is not None else generated_position

        # Generate bats/throws based on position
        self.bats, self.throws = self.generate_bats_throws()

        # Generate age based on position
        self.age = self.generate_age(self.position)

        self.school = self.generate_school(self.origin)

        # Generate secondary position based on the final primary position
        self.secondary_position = self.generate_secondary_position(self.position)

        print(f"Line 85 Secondary Position: {self.secondary_position} for {self.first_name} {self.surname}")

        return {
            "name": f"{self.first_name} {self.surname}",
            "race": self.race.capitalize(),
            "age": self.age,
            "height": self.height,
            "weight": self.weight,
            "origin": self.origin,
            "school": self.school,
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
        print(f"Generated position for {self.first_name} {self.surname}: Selected Position {position}")

        return round(height), round(weight), position  # Return the selected position

    def generate_secondary_position(self, position):
        print(f"Starting to generate secondary position for {self.first_name} {self.surname}")
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
        print(f"RNG for {position}: {rng}")

        if rng > chance_of_secondary.get(position, 0.0):
            print(f"No secondary generated for {position} because RNG ({rng}) > chance ({chance_of_secondary[position]}).")
            return None

        possible_positions, weights = secondary_position_options.get(position, ([], []))
        print(f"Possible positions for {position}: {possible_positions}")

        # Check if there are any possible secondary positions
        if not possible_positions:
            print(f"No possible secondary positions for {position}.")
            return None

        # Step 3: Ensure the secondary position is not the same as the primary position
        secondary_position = random.choices(possible_positions, weights=weights)[0]
        print(f"STEP 3 possible positions: {possible_positions} and weights: {weights}")
        print(f"Generated secondary position for {position}: {secondary_position}")
        print(f"Finished generating secondary position for {self.first_name} {self.surname} / P: {position} / SP: {secondary_position}")
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

    def generate_school(self, origin):
        """Generate school based on origin (USA or International)."""
        if origin != 'USA':
            # If the player is international, we directly assign "International"
            return "International"

        # If the player is from the USA, use adjusted probabilities for high school and college
        probabilities = {'high_school': 0.47, 'college': 0.53}  # Proportionally adjusted
        
        draft_origin = np.random.choice(list(probabilities.keys()), p=list(probabilities.values()))

        if draft_origin == 'high_school':
            # Use the 'players' column as weights for school selection in high_school_df
            high_school_weights = high_school_df['players'] / high_school_df['players'].sum()
            school_row = high_school_df.sample(weights=high_school_weights).iloc[0]  # Get the row for school info

            school_name = school_row['school_name'].strip().title()  # Capitalize the school name properly
            city = school_row['city'].strip().title()
            state = school_row['state'].strip().upper()

            # Ensure "hs" is in uppercase (e.g., from "high school" or "hs" to "HS")
            if "Hs" in school_name:
                school_name = school_name.replace("Hs", "HS")
            elif "High School" in school_name:
                school_name = school_name.replace("High School", "HS")

            # Add city and state for high school output
            return f"{school_name} ({city}, {state})"

        elif draft_origin == 'college':
            # Use the 'players' column as weights for school selection in college_df
            college_weights = college_df['players'] / college_df['players'].sum()
            college_name = college_df.sample(weights=college_weights)['school_name'].values[0].strip()

            # Ensure proper title casing for college names
            return college_name.title()

        # Fallback case (shouldn't happen under normal conditions)
        return "International"


class Archetype:
    def __init__(self, name, 
                 contact_range=None, power_range=None, eye_range=None, speed_range=None, fielding_range=None, 
                 x_inning_range=None, potential_range=None, 
                 start_value_range=None, endurance_range=None, rest_range=None, cg_rating_range=None, 
                 sho_rating_range=None, relief_value_range=None, fatigue_range=None,
                 dev_ceiling_age=25, decline_age=32):
        self.name = name
        
        # Batter-specific ranges
        self.contact_range = contact_range
        self.power_range = power_range
        self.eye_range = eye_range
        self.speed_range = speed_range
        self.fielding_range = fielding_range
        self.x_inning_range = x_inning_range
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
        """Fetch archetype probabilities based on the player's school."""
        # Clean up the school name to remove any extra spaces or case mismatches
        cleaned_school_name = school_name.strip().lower()

        # Ensure the dataframes are also clean and lowercase
        high_school_df['school_name'] = high_school_df['school_name'].str.strip().str.lower()
        college_df['school_name'] = college_df['school_name'].str.strip().str.lower()

        # Check if it's an international school
        if cleaned_school_name == "international":
            # If it's an international school, return baseline probabilities
            return {
                'grade1_prob': 0.15, 'grade2_prob': 0.3, 'grade3_prob': 0.4,
                'grade4_prob': 0.5, 'grade5_prob': 0.6, 'grade6_prob': 0.7,
                'grade7_prob': 0.85, 'grade8_prob': 0.95, 'grade9_prob': 0.98,
                'grade10_prob': 0.99
            }

        # Determine if it's a high school or college
        if school_type == 'HS':
            school_df = high_school_df
        else:
            school_df = college_df

        # Find matching rows after cleaning
        matching_rows = school_df[school_df['school_name'] == cleaned_school_name]

        if matching_rows.empty:
            # If no matching school is found, use default probabilities
            print(f"Warning: School '{school_name}' not found in {school_type}. Using default probabilities.")
            return {
                'grade1_prob': 0.15, 'grade2_prob': 0.3, 'grade3_prob': 0.4,
                'grade4_prob': 0.5, 'grade5_prob': 0.6, 'grade6_prob': 0.7,
                'grade7_prob': 0.85, 'grade8_prob': 0.95, 'grade9_prob': 0.98,
                'grade10_prob': 0.99
            }

        # Fetch the first matching row
        school_row = matching_rows.iloc[0]

        return {
            'grade1_prob': school_row['grade1_prob'], 'grade2_prob': school_row['grade2_prob'],
            'grade3_prob': school_row['grade3_prob'], 'grade4_prob': school_row['grade4_prob'],
            'grade5_prob': school_row['grade5_prob'], 'grade6_prob': school_row['grade6_prob'],
            'grade7_prob': school_row['grade7_prob'], 'grade8_prob': school_row['grade8_prob'],
            'grade9_prob': school_row['grade9_prob'], 'grade10_prob': school_row['grade10_prob']
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
        self.contact = 0
        self.power = 0
        self.eye = 0
        self.speed = 0
        self.fielding = 0
        self.x_inning = 0
        self.potential = 0
        self.injury = 0  # Injury rating
        
        # Initial morale, popularity, salary
        self.makeup = 0
        self.morale = 0
        self.popularity = 0
        self.contract = 0  # Contract length in years
        self.salary = 0
        self.service_time = 0

    batter_archetypes = [
        Archetype("scrub", (0, 0), (0, 0), (-3, -2), (0, 0), (-3, -2), (-1, 0), (0, 0), dev_ceiling_age=21, decline_age=28),
        Archetype("career minor leaguer", (0, 1), (0, 1), (-3, -1), (0, 2), (-3, 0), (-1, 1), (0, 0), dev_ceiling_age=22, decline_age=29),
        Archetype("september callup", (0, 2), (0, 1), (-1, 0), (0, 3), (-2, 0), (-1, 1), (0, 1), dev_ceiling_age=23, decline_age=29),
        Archetype("injury replacement", (1, 3), (0, 2), (-1, 0), (0, 4), (-2, 0), (-1, 1), (0, 1), dev_ceiling_age=23, decline_age=29),
        Archetype("AAAA player", (1, 4), (0, 3), (0, 0), (0, 4), (-2, 1), (-1, 1), (0, 2), dev_ceiling_age=24, decline_age=30),
        Archetype("backup", (2, 4), (0, 3), (0, 1), (0, 4), (-2, 1), (-1, 1), (0, 2), dev_ceiling_age=25, decline_age=31),
        Archetype("platoon", (3, 4), (0, 4), (0, 2), (0, 5), (-1, 2), (-1, 1), (1, 3), dev_ceiling_age=25, decline_age=32),
        Archetype("regular starter", (4, 6), (0, 5), (0, 2), (0, 6), (-1, 3), (-1, 1), (1, 6), dev_ceiling_age=25, decline_age=33),
        Archetype("star", (5, 7), (1, 7), (1, 3), (1, 7), (0, 3), (-1, 1), (2, 7), dev_ceiling_age=25, decline_age=34),
        Archetype("5-tool", (5, 8), (4, 8), (2, 3), (4, 8), (1, 3), (0, 1), (3, 8), dev_ceiling_age=25, decline_age=35)
    ]

    def generate_ratings(self):
        # Use archetype ranges to generate ratings
        self.contact = self.generate_attribute(self.archetype.contact_range, "contact")
        self.power = self.generate_attribute(self.archetype.power_range, "power")
        self.eye = self.generate_attribute(self.archetype.eye_range, "eye", age_affected=False)
        self.speed = self.generate_attribute(self.archetype.speed_range, "speed")
        self.fielding = self.generate_attribute(self.archetype.fielding_range, "fielding")
        self.x_inning = self.generate_attribute(self.archetype.x_inning_range, "x_inning", age_affected=False)
        self.potential = self.generate_attribute(self.archetype.potential_range, "potential", age_affected=False)

        # Generate random injury rating
        self.injury = max(min(int(np.random.normal(0, 1.5)), 3), -3)

        self.makeup = max(min(int(np.random.normal(0, 1)), 2), -2)
                      
        # Adjust ratings by age
        self.adjust_by_age()

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
            "contact": self.contact,
            "power": self.power,
            "eye": self.eye,
            "speed": self.speed,
            "fielding": self.fielding,
            "x_inning": self.x_inning,
            "potential": self.potential,
            "injury": self.injury,
            "makeup": self.makeup,
            "morale": self.morale,
            "popularity": self.popularity,
            "salary": self.salary,
            "contract": self.contract,
            "service_time": self.service_time,
        }

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
        """Generate a random number in the floor/ceiling range, skewed to high or low."""
        if skew == "high":
            # Right skew: high-quality archetype (higher chance of values near ceiling)
            return int(np.random.beta(2, 5) * (ceiling - floor) + floor)
        elif skew == "low":
            # Left skew: low-quality archetype (higher chance of values near floor)
            return int(np.random.beta(5, 2) * (ceiling - floor) + floor)
        else:
            # Neutral distribution, equal chance across the range
            return np.random.randint(floor, ceiling + 1)

    def adjust_by_age(self):
        """Adjust attributes based on player's age."""
        dev_diff = self.archetype.dev_ceiling_age - self.bio['age']
        decline_diff = self.bio['age'] - self.archetype.decline_age

        # List of top and second-tier archetypes
        top_tier_archetypes = ["5-tool"]
        second_tier_archetypes = ["star"]

        # Determine penalty adjustments based on archetype
        if self.archetype.name in top_tier_archetypes:
            adjusted_decline = max(0, decline_diff - 2)  # Reduce penalty by 2
        elif self.archetype.name in second_tier_archetypes:
            adjusted_decline = max(0, decline_diff - 1)  # Reduce penalty by 1
        else:
            adjusted_decline = decline_diff  # Apply regular penalty

        if self.bio['age'] < self.archetype.dev_ceiling_age:
            # Penalize for being underdeveloped
            self.contact -= dev_diff
            self.power -= dev_diff
            self.speed -= dev_diff
            self.fielding -= dev_diff
        elif self.bio['age'] > self.archetype.decline_age:
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
        self.fielding = max(-3, self.fielding)

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
            start_value_range=(0.5, 1.0), endurance_range=(0.5, 1.0), rest_range=(7, 8), 
            cg_rating_range=(666, 666), sho_rating_range=(666, 666), relief_value_range=(6, 6), 
            fatigue_range=(+5, +5), potential_range=(0, 0), dev_ceiling_age=21, decline_age=28),

        Archetype("fringe starter", 
            start_value_range=(0.5, 1.5), endurance_range=(0.5, 1.5), rest_range=(6, 8), 
            cg_rating_range=(665, 666), sho_rating_range=(666, 666), relief_value_range=(6, 6), 
            fatigue_range=(+5, +5), potential_range=(0, 0), dev_ceiling_age=22, decline_age=29),

        Archetype("late bloomer", 
            start_value_range=(1.0, 1.5), endurance_range=(1.0, 1.5), rest_range=(6, 8), 
            cg_rating_range=(664, 666), sho_rating_range=(666, 666), relief_value_range=(6, 6), 
            fatigue_range=(+5, +5), potential_range=(0, 1), dev_ceiling_age=23, decline_age=29),

        Archetype("spot starter", 
            start_value_range=(1.0, 2.0), endurance_range=(1.0, 2.0), rest_range=(5, 8), 
            cg_rating_range=(666, 666), sho_rating_range=(666, 666), relief_value_range=(6, 6), 
            fatigue_range=(+5, +5), potential_range=(0, 1), dev_ceiling_age=23, decline_age=29),

        Archetype("quad-a arm", 
            start_value_range=(1.0, 2.5), endurance_range=(1.0, 2.5), rest_range=(5, 7), 
            cg_rating_range=(665, 665), sho_rating_range=(665, 665), relief_value_range=(6, 6), 
            fatigue_range=(+5, +5), potential_range=(0, 2), dev_ceiling_age=24, decline_age=30),

        Archetype("emergency starter", 
            start_value_range=(1.5, 3.0), endurance_range=(1.5, 3.0), rest_range=(5, 6), 
            cg_rating_range=(665, 665), sho_rating_range=(665, 665), relief_value_range=(5, 5), 
            fatigue_range=(+5, +5), potential_range=(0, 2), dev_ceiling_age=25, decline_age=31),

        Archetype("back of rotation", 
            start_value_range=(2.0, 3.0), endurance_range=(2.0, 3.5), rest_range=(4, 6), 
            cg_rating_range=(661, 666), sho_rating_range=(661, 661), relief_value_range=(5, 5), 
            fatigue_range=(+5, +5), potential_range=(1, 3), dev_ceiling_age=25, decline_age=32),

        Archetype("regular starter", 
            start_value_range=(2.5, 4.0), endurance_range=(2.5, 5.5), rest_range=(4, 5), 
            cg_rating_range=(661, 666), sho_rating_range=(656, 666), relief_value_range=(5, 5), 
            fatigue_range=(+5, +5), potential_range=(1, 5), dev_ceiling_age=25, decline_age=34),

        Archetype("top of rotation", 
            start_value_range=(3.0, 5.5), endurance_range=(3.5, 6.5), rest_range=(4, 5), 
            cg_rating_range=(641, 666), sho_rating_range=(651, 666), relief_value_range=(5, 5), 
            fatigue_range=(+5, +5), potential_range=(3, 7), dev_ceiling_age=25, decline_age=34),

        Archetype("ace", 
            start_value_range=(5.0, 7.0), endurance_range=(4.0, 8.0), rest_range=(4, 4), 
            cg_rating_range=(611, 666), sho_rating_range=(611, 666), relief_value_range=(4, 4), 
            fatigue_range=(+4, +4), potential_range=(4, 8), dev_ceiling_age=25, decline_age=35)
    ]

    reliever_archetypes = [
        Archetype("filler arm", 
            start_value_range=(0.5, 0.5), endurance_range=(0.5, 0.5), rest_range=(8, 8), 
            cg_rating_range=(666, 666), sho_rating_range=(666, 666), relief_value_range=(7, 6), 
            fatigue_range=(4, 4), potential_range=(0, 0), dev_ceiling_age=21, decline_age=28),

        Archetype("taxi squad reliever", 
            start_value_range=(0.5, 0.5), endurance_range=(0.5, 0.5), rest_range=(7, 8), 
            cg_rating_range=(665, 666), sho_rating_range=(666, 666), relief_value_range=(7, 5), 
            fatigue_range=(4, 4), potential_range=(0, 0), dev_ceiling_age=22, decline_age=29),

        Archetype("roster expansion reliever", 
            start_value_range=(0.5, 0.5), endurance_range=(0.5, 0.5), rest_range=(7, 8), 
            cg_rating_range=(664, 666), sho_rating_range=(666, 666), relief_value_range=(6, 5), 
            fatigue_range=(4, 4), potential_range=(0, 1), dev_ceiling_age=23, decline_age=29),

        Archetype("bullpen patch", 
            start_value_range=(0.5, 0.5), endurance_range=(0.5, 0.5), rest_range=(8, 8), 
            cg_rating_range=(666, 666), sho_rating_range=(666, 666), relief_value_range=(6, 4), 
            fatigue_range=(4, 3), potential_range=(0, 1), dev_ceiling_age=23, decline_age=29),

        Archetype("perpetual callup", 
            start_value_range=(0.5, 0.5), endurance_range=(0.5, 0.5), rest_range=(8, 8), 
            cg_rating_range=(666, 666), sho_rating_range=(666, 666), relief_value_range=(5, 4), 
            fatigue_range=(4, 2), potential_range=(0, 2), dev_ceiling_age=24, decline_age=30),

        Archetype("mop-up", 
            start_value_range=(0.5, 0.5), endurance_range=(0.5, 0.5), rest_range=(7, 7), 
            cg_rating_range=(666, 666), sho_rating_range=(666, 666), relief_value_range=(5, 3), 
            fatigue_range=(4, 1), potential_range=(0, 2), dev_ceiling_age=25, decline_age=30),

        Archetype("swingman", 
            start_value_range=(1.0, 1.5), endurance_range=(0.5, 1.0), rest_range=(5, 7), 
            cg_rating_range=(665, 666), sho_rating_range=(665, 666), relief_value_range=(4, 2), 
            fatigue_range=(4, 1), potential_range=(1, 3), dev_ceiling_age=25, decline_age=31),

        Archetype("low-leverage", 
            start_value_range=(0.5, 0.5), endurance_range=(0.5, 0.5), rest_range=(8, 8), 
            cg_rating_range=(666, 666), sho_rating_range=(666, 666), relief_value_range=(3, 0), 
            fatigue_range=(3, 1), potential_range=(1, 5), dev_ceiling_age=25, decline_age=32),

        Archetype("high-leverage", 
            start_value_range=(0.5, 0.5), endurance_range=(0.5, 0.5), rest_range=(8, 8), 
            cg_rating_range=(666, 666), sho_rating_range=(666, 666), relief_value_range=(0, -3), 
            fatigue_range=(2, 1), potential_range=(2, 7), dev_ceiling_age=25, decline_age=34),

        Archetype("closer", 
            start_value_range=(0.5, 0.5), endurance_range=(0.5, 0.5), rest_range=(8, 8), 
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

        # Potential is not age-dependent, generated once
        self.potential = self.generate_attribute(self.archetype.potential_range, "potential", age_affected=False)

        # Generate random injury rating
        self.injury = max(min(int(np.random.normal(0, 1.5)), 3), -3)

        # Adjust ratings by age
        self.adjust_by_age()

        self.makeup = self.generate_makeup()

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
        """Generate a random number skewed towards either the floor or ceiling."""
        if skew == "high":
            return int(np.random.beta(2, 5) * (ceiling - floor) + floor)
        elif skew == "low":
            return int(np.random.beta(5, 2) * (ceiling - floor) + floor)
        else:
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
        self.manager_leadership = 0 # -3 to +3
        self.manager_hitting = 0 # -3 to +3
        self.manager_pitching = 0 # -3 to +3
        self.manager_fielding = 0 # -3 to +3
        self.manager_bench = 0 # -3 to +3
        self.manager_potential = 0 # 0 to 8
        self.manager_salary = 0

    def generate_ratings(self):
        self.manager_leadership = min(max(int(np.random.normal(0, 1.5)), -3), 3)
        self.manager_hitting = min(max(int(np.random.normal(0, 1.5)), -3), 3)
        self.manager_pitching = min(max(int(np.random.normal(0, 1.5)), -3), 3)
        self.manager_fielding = min(max(int(np.random.normal(0, 1.5)), -3), 3)
        self.manager_bench = min(max(int(np.random.normal(0, 1.5)), -3), 3)
        self.manager_potential = min(max(int(np.random.normal(4, 1.5)), 0), 8)

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

# Assuming msa_data is already loaded from the external source with 'City', 'Population', 'Latitude', 'Longitude', and 'State' columns.
msa_data = pd.read_excel(r'C:\Users\vadim\Documents\Code\_pennant_race\team_generation.xlsx')

class Team:
    """Class for representing a team with a roster of players."""
    def __init__(self, name, city, state, league_name, division_name):
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

    def generate_roster(self):
        """Generate a team roster with players for each role."""
        roster = {
            'Starting 9': self.generate_starting_9(),
            'Bench': self.generate_bench(),
            'Pitchers': self.generate_pitching_staff()
        }
        return roster

    def generate_starting_9(self):
        """Generate the starting 9 players for the team."""
        # These positions should be fixed for the starting lineup
        positions = ['C', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF', 'DH']  # All required positions
        
        starting_9 = []
        for position in positions:
            starting_9.append(self.create_player(position))
        
        return starting_9

    def generate_bench(self):
        """Generate 6 bench players: 2 OF, 2 IF, 1 C, and 1 additional utility player."""
        # Define the positions for bench players
        bench_positions = ['OF', 'OF', 'IF', 'IF', 'C', 'Utility']
        bench = []
        
        for position in bench_positions:
            if position == 'OF':
                # Randomly choose between LF, CF, or RF for outfield positions
                position = np.random.choice(['LF', 'CF', 'RF'])
            elif position == 'IF':
                # Randomly choose between 1B, 2B, 3B, or SS for infield positions
                position = np.random.choice(['1B', '2B', '3B', 'SS'])
            elif position == 'Utility':
                # Randomly choose any field position for the utility player (either infield or outfield)
                position = np.random.choice(['C', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF'])

            # Create the player with the determined position
            bench.append(self.create_player(position))
    
        return bench

    def generate_pitching_staff(self):
        """Generate the pitching staff: 5 starters and 5 relievers."""
        starters = [self.create_player('SP') for _ in range(5)]
        relievers = [self.create_player('RP') for _ in range(5)]
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
            'grade4_prob': 'spot starter', 'grade5_prob': 'quad-a arm', 'grade6_prob': 'emergency starter',
            'grade7_prob': 'back of rotation', 'grade8_prob': 'regular starter', 'grade9_prob': 'top of rotation', 'grade10_prob': 'ace'
        }
        
        reliever_archetypes = {
            'grade1_prob': 'filler arm', 'grade2_prob': 'taxi squad reliever', 'grade3_prob': 'roster expansion reliever',
            'grade4_prob': 'bullpen patch', 'grade5_prob': 'perpetual callup', 'grade6_prob': 'mop-up',
            'grade7_prob': 'swingman', 'grade8_prob': 'low-leverage', 'grade9_prob': 'high-leverage', 'grade10_prob': 'closer'
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
        """Create a player for a specific position, ensuring correct archetype and role assignment."""
        player_profile = PlayerProfile(position)

        # Generate school and determine the school type (HS or College)
        school_name = player_profile.bio['school']
        school_type = 'HS' if school_name in high_school_df['school_name'].values else 'COL'

        # Fetch the appropriate grade probabilities from the school data in the Excel sheet
        school_probs = Archetype.get_archetype_probs(school_name, school_type)
        print(f"School: {school_name}, Type: {school_type}, Archetype Probabilities: {school_probs}")

        # Generate a random probability (0.0 to 1.0)
        rand_prob = random.random()
        print(f"Random Probability Generated: {rand_prob}")

        # Loop through each grade and check if the random probability falls below the threshold
        for col, threshold in school_probs.items():
            print(f"Checking {col}: Threshold: {threshold}, Random Probability: {rand_prob}")
            if rand_prob <= threshold:
                grade_prob = col
                print(f"Selected Archetype: {grade_prob}")
                break
        else:
            grade_prob = 'grade1_prob'  # Default to grade1_prob if no match
            print(f"Defaulted to Grade 1 Archetype")

        # Determine the player type (batter, starter, reliever) and map the gradeX_prob to the correct archetype
        if position == 'SP':  # Starter
            archetype_name = self.map_grade_prob_to_archetype(grade_prob, 'starter')
            archetype = next(a for a in PitcherProfile.starter_archetypes if a.name == archetype_name)
            player_profile.profile = PitcherProfile(player_profile.bio, archetype)
            player_profile.profile.type = 'Starter'
        elif position == 'RP':  # Reliever
            archetype_name = self.map_grade_prob_to_archetype(grade_prob, 'reliever')
            archetype = next(a for a in PitcherProfile.reliever_archetypes if a.name == archetype_name)
            player_profile.profile = PitcherProfile(player_profile.bio, archetype)
            player_profile.profile.type = 'Reliever'
        else:  # Batter roles
            # Ensure valid batter positions are assigned
            valid_batter_positions = ['C', '1B', '2B', '3B', 'SS', 'LF', 'CF', 'RF', 'DH']
            if position not in valid_batter_positions:
                position = random.choice(valid_batter_positions)
            player_profile.bio['position'] = position

            # Map the gradeX_prob to a batter archetype
            archetype_name = self.map_grade_prob_to_archetype(grade_prob, 'batter')
            print(f"Mapped Grade Prob: {grade_prob} to Archetype: {archetype_name}")
            archetype = next(a for a in BatterProfile.batter_archetypes if a.name == archetype_name)

            # Now pass both bio and archetype when creating the BatterProfile
            player_profile.profile = BatterProfile(player_profile.bio, archetype)
            print(f"Player Profile: {player_profile.bio}")

        player_profile.generate_ratings()  # Generate ratings based on the archetype

        return player_profile.to_dict()  # Return player data as a dictionary

    def to_dict(self):
        """Convert the team and roster information to a dictionary format for JSON output."""
        team_data = {
            "team_city": self.city,
            "team_name": self.name,
            "team_colors": self.team_colors,
            "ballpark": self.ballpark,
            "league_name": self.league_name,
            "division_name": self.division_name,
            "players": self.roster['Starting 9'] + self.roster['Bench'] + self.roster['Pitchers'],
            "personnel": {
                "gm": self.gm.to_dict(),
                "manager": self.manager.to_dict()
            }
        }
        return team_data

    def __repr__(self):
        return f"Team({self.city} {self.name})"

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
msa_data = pd.read_excel(r'C:\Users\vadim\Documents\Code\_pennant_race\team_generation.xlsx', sheet_name='CITY')

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

    def generate_league_name(self):
        return f"{markov_chain.generate_name()} League"

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
        return f"{city_name} {nickname}"

    def get_city_weight(self, row):
        """Calculate a combined weight for a city based on its population and GDP rank."""
        population_weight = row['population'] / self.msa_data['population'].max()
        gdp_weight = 1 / row['gdp_rank']  # Inverse of the rank, lower rank is better
        return population_weight * gdp_weight

    def generate_league(self):
        teams = []
        for _ in range(self.num_teams):
            try:
                city = self.select_city(teams)
            except ValueError as e:
                print(f"DEBUG: Error selecting city: {e}")
                continue  # Skip or retry city selection if it fails

            team_name = self.generate_team_name(city)
            
            # Create the full team object and append it to the list
            new_team = Team(team_name, city, state="", league_name="Some League", division_name="Some Division")
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
        # Use your specified folder path
        folder_path = r'C:\\Users\\vadim\\Documents\\Code\\_pennant_race\\league_files'
        
        # Ensure the directory exists
        os.makedirs(folder_path, exist_ok=True)

        for team in self.teams:
            team_data = team.to_dict()
            team_data = convert_numpy_types(team_data)  # Convert NumPy types to Python types
            
            # Sanitize city and team name for the filename
            sanitized_city = sanitize_filename(team.city)
            sanitized_name = sanitize_filename(team.name)
            
            file_name = f"{sanitized_city}_{sanitized_name}.json"
            file_path = os.path.join(folder_path, file_name)

            with open(file_path, 'w') as f:
                json.dump(team_data, f, indent=4)
            print(f"Saved team {team.city} {team.name} to {file_path}")

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
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

        # Specify the Excel file path with the timestamp
        file_path = rf'C:\\Users\\vadim\\Documents\\Code\\_pennant_race\\league_files\\league_rosters_{timestamp}.xlsx'

        # Use ExcelWriter to create an Excel file with two sheets
        with pd.ExcelWriter(file_path, engine='xlsxwriter') as writer:
            batters_df.to_excel(writer, sheet_name='Batters', index=False)
            pitchers_df.to_excel(writer, sheet_name='Pitchers', index=False)

        print(f"Rosters saved to {file_path}")

class PlayerProfile:
    """PlayerProfile class for batter and pitcher profiles."""
    def __init__(self, position):
        self.position = position
        self.bio = NameGen().generate_bio(position)  # Pass position directly to handle "P" correctly

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
        combined_dict = {**bio_dict, **profile_dict}  # Merge bio and profile data, bio first
        return combined_dict

class Player:
    """Represents a player with their profile and attributes."""
    def __init__(self, name, position, profile):
        self.name = name
        self.position = position
        self.profile = profile

    def __repr__(self):
        return f"{self.name} ({self.position})"

# Example usage
num_teams = 32
num_divisions = 4
league = League(num_teams, num_divisions, msa_data, nickname_data)

# Generate league name and divisions
league_name = league.generate_league_name()
divisions = league.generate_divisions()
league.print_teams_and_rosters()
league.save_teams_to_json()

print("League Name:", league_name)
print("Divisions:", divisions)



