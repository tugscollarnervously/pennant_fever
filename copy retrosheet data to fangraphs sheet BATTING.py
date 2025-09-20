import pandas as pd

# Load the Excel file
file_path = r'C:\Users\vadim\Documents\Code\_pennant_race\1980s_MLB_v10.xlsx'  # Replace with your file path
excel_data = pd.ExcelFile(file_path)

# Load the relevant sheets into dataframes
retro_df = pd.read_excel(excel_data, sheet_name='RETRO_BAT_UPDATED')  # RETRO_BAT contains split stats
bat_df = pd.read_excel(excel_data, sheet_name='BAT_UPDATED')  # BAT contains the composite stats for each player/year

# Define the columns to copy over from RETRO_BAT to BAT
retro_columns = [
    'player_id', 'year',  # Include both player_id and year for matching
    'AB_vs_LHP', 'H_vs_LHP', '2B_vs_LHP', '3B_vs_LHP', 'HR_vs_LHP', 'BB_vs_LHP', 'SO_vs_LHP', 'HBP_vs_LHP', 
    'RBI_vs_LHP', 'TB_vs_LHP', 'SH_vs_LHP', 'SF_vs_LHP', 'AB_vs_RHP', 'H_vs_RHP', '2B_vs_RHP', 
    '3B_vs_RHP', 'HR_vs_RHP', 'BB_vs_RHP', 'SO_vs_RHP', 'HBP_vs_RHP', 'RBI_vs_RHP', 'TB_vs_RHP', 
    'SH_vs_RHP', 'SF_vs_RHP', 'BA_vs_LHP', 'OBP_vs_LHP', 'SLG_vs_LHP', 'OPS_vs_LHP', 'ISO_vs_LHP', 
    'BA_vs_RHP', 'OBP_vs_RHP', 'SLG_vs_RHP', 'OPS_vs_RHP', 'ISO_vs_RHP'
]


# Ensure there are no duplicates for each player_id and year in RETRO_BAT
# This ensures that we don't have duplicate composite rows for the same player and year
retro_unique = retro_df.drop_duplicates(subset=['player_id', 'year'])[retro_columns]

# Merge RETRO columns into BAT based on both 'player_id' and 'year'
if 'player_id' in retro_unique.columns and 'year' in retro_unique.columns and 'player_id' in bat_df.columns and 'year' in bat_df.columns:
    # Merge on both player_id and year
    updated_bat_df = bat_df.merge(retro_unique, on=['player_id', 'year'], how='left')
else:
    raise ValueError("player_id or year column not found in one of the sheets")

# Save the updated BAT data to a new sheet
output_file = file_path  # Optionally, change this to a new file if desired
with pd.ExcelWriter(output_file, engine='openpyxl', mode='a') as writer:
    updated_bat_df.to_excel(writer, sheet_name='BAT_SPLITS', index=False)

print("Data from RETRO successfully appended to BAT based on both player_id and year.")
