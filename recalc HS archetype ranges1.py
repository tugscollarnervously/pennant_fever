import numpy as np
import pandas as pd

# Load the High School and College data from their respective sheets
file_path = r'C:\Users\vadim\Documents\Code\_pennant_race\schools_register.xlsx'  # Replace with your actual file path

# Load high school data from the relevant sheet
hs_sheet_name = 'HS State Counts'
hs_data = pd.read_excel(file_path, sheet_name=hs_sheet_name)

# Load college data from the relevant sheet
college_sheet_name = 'COL'
college_data = pd.read_excel(file_path, sheet_name=college_sheet_name)

### High School Adjustments (Same as before)

# Helper function to adjust high school probabilities based on school counts
def adjust_hs_probabilities(row, max_schools):
    base_probs = np.array([0.05, 0.1, 0.2, 0.3, 0.4, 0.55, 0.65, 0.8, 0.9, 0.97])
    multiplier = row['unique_school_count'] / max_schools  # Adjust based on school frequency
    adjusted_probs = np.clip(base_probs * multiplier, 0.01, 0.99)
    adjusted_probs[-1] = 0.99  # Ensure 5-tool stays rare
    adjusted_probs[-2] = 0.97  # Ensure star stays rare as well
    return pd.Series(adjusted_probs, index=[
        'scrub_prob', 'career_minor_leaguer_prob', 'sept_callup_prob', 'injury_replacement_prob', 
        'AAAA_player_prob', 'backup_prob', 'platoon_prob', 'regular_starter_prob', 'star_prob', 'five_tool_prob'
    ])

# Find the maximum school count for normalization
max_hs_schools = hs_data['unique_school_count'].max()

# Apply the adjustment to high school data
hs_data[['scrub_prob', 'career_minor_leaguer_prob', 'sept_callup_prob', 'injury_replacement_prob', 
         'AAAA_player_prob', 'backup_prob', 'platoon_prob', 'regular_starter_prob', 'star_prob', 'five_tool_prob']] = hs_data.apply(adjust_hs_probabilities, axis=1, max_schools=max_hs_schools)

# Helper function to assign college probabilities based on player counts
def assign_college_probabilities(row, max_schools):
    col_base_probs = np.array([0.05, 0.1, 0.2, 0.3, 0.4, 0.55, 0.65, 0.8, 0.9, 0.97])
    col_multiplier = row['players'] / max_schools  # Adjust based on school frequency
    col_adjusted_probs = np.clip(col_base_probs * col_multiplier, 0.01, 0.99)
    col_adjusted_probs[-1] = 0.99  # Ensure 5-tool stays rare
    col_adjusted_probs[-2] = 0.97  # Ensure star stays rare as well
    return pd.Series(col_adjusted_probs, index=[
        'scrub_prob', 'career_minor_leaguer_prob', 'sept_callup_prob', 'injury_replacement_prob', 
        'AAAA_player_prob', 'backup_prob', 'platoon_prob', 'regular_starter_prob', 'star_prob', 'five_tool_prob'
    ])

# Find the maximum school count for normalization
max_col_schools = college_data['players'].max()

# Apply the probability assignment to the college data
college_data[['grade1_prob', 'grade2_prob', 'grade3_prob', 'grade4_prob', 'grade5_prob', 'grade6_prob', 
              'grade7_prob', 'grade8_prob', 'grade9_prob', 'grade10_prob']] = college_data.apply(assign_college_probabilities, axis=1, max_schools=max_col_schools)

### Save Both Datasets into One Excel File with Different Sheets
output_file = r'C:\Users\vadim\Documents\Code\_pennant_race\adjusted_archetype_probabilities.xlsx'
with pd.ExcelWriter(output_file) as writer:
    hs_data.to_excel(writer, sheet_name='HS Probabilities', index=False)
    college_data.to_excel(writer, sheet_name='College Probabilities', index=False)

print(f"Adjusted probabilities for high schools and colleges saved to '{output_file}'.")