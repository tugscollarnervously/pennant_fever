import pandas as pd

# Load the Excel file
file_path = r'C:\Users\vadim\Documents\Code\_pennant_race\1980s_MLB_v10.xlsx'  # Replace with your file path
excel_data = pd.ExcelFile(file_path)

# Load the relevant sheets into dataframes
retro_df = pd.read_excel(excel_data, sheet_name='RETRO_PIT_UPDATED')
pit_df = pd.read_excel(excel_data, sheet_name='PIT_UPDATED')

# Extract the relevant columns from RETRO (columns I to AR)
retro_columns = [
    'player_id', 'year', # Include both player_id and year for matching
    'AB_vs_LHB', 'H_vs_LHB', '2B_vs_LHB', '3B_vs_LHB', 'HR_vs_LHB', 'BB_vs_LHB', 'SO_vs_LHB', 'HBP_vs_LHB', 
    'RBI_vs_LHB', 'TB_vs_LHB', 'SH_vs_LHB', 'SF_vs_LHB', 'AB_vs_RHB', 'H_vs_RHB', '2B_vs_RHB', 
    '3B_vs_RHB', 'HR_vs_RHB', 'BB_vs_RHB', 'SO_vs_RHB', 'HBP_vs_RHB', 'RBI_vs_RHB', 'TB_vs_RHB', 
    'SH_vs_RHB', 'SF_vs_RHB', 'BA_vs_LHB', 'OBP_vs_LHB', 'SLG_vs_LHB', 'OPS_vs_LHB', 'ISO_vs_LHB', 'BA_vs_RHB', 
    'OBP_vs_RHB', 'SLG_vs_RHB', 'OPS_vs_RHB', 'ISO_vs_RHB'
]

# Ensure there is no duplication in RETRO for 'player_id'
retro_unique = retro_df.drop_duplicates(subset=['player_id', 'year'])[retro_columns]

# Merge RETRO columns into PIT based on 'player_id'
if 'player_id' in retro_unique.columns and 'year' in retro_unique.columns and 'player_id' in pit_df.columns and 'year' in pit_df.columns:
    # Merge on both player_id and year
    updated_pit_df = pit_df.merge(retro_unique, on=['player_id', 'year'], how='left')
else:
    raise ValueError("player_id or year column not found in one of the sheets")

# Save the updated PIT data to a new sheet
output_file = file_path  # Optionally, change this to a new file if desired
with pd.ExcelWriter(output_file, engine='openpyxl', mode='a') as writer:
    updated_pit_df.to_excel(writer, sheet_name='PIT_SPLITS', index=False)

print("Data from RETRO successfully appended to PIT based on both player_id and year.")