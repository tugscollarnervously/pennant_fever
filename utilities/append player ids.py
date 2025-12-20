import pandas as pd

# Load the Excel file
file_path = r'C:\Users\vadim\Documents\Code\_pennant_race\1980s_MLB_v10.xlsx'  # Replace with your file path
excel_data = pd.ExcelFile(file_path)

# Load the relevant sheets into dataframes
roster_df = pd.read_excel(excel_data, sheet_name='ROSTER')
retro_bat_df = pd.read_excel(excel_data, sheet_name='RETRO_BAT')
retro_pit_df = pd.read_excel(excel_data, sheet_name='RETRO_PIT')
bat_df = pd.read_excel(excel_data, sheet_name='BAT')
pit_df = pd.read_excel(excel_data, sheet_name='PIT')
field_df = pd.read_excel(excel_data, sheet_name='FIELD')

# Update these dataframes with player_id (your logic for adding player_id goes here)
# Example: Assuming player_id_df is the sheet where you have player names and their ids
player_id_df = pd.read_excel(excel_data, sheet_name='PLAYER_ID')

# Define a function to add player_id to sheets
def append_player_id(player_name, player_id, sheet_df):
    mask = sheet_df['full_name'] == player_name
    sheet_df.loc[mask, 'player_id'] = player_id
    return sheet_df

# Loop through each player in PLAYER_ID sheet and update each DataFrame
for index, row in player_id_df.iterrows():
    player_name = row['full_name']
    player_id = row['player_id']
    
    # Update each sheet
    roster_df = append_player_id(player_name, player_id, roster_df)
    retro_bat_df = append_player_id(player_name, player_id, retro_bat_df)
    retro_pit_df = append_player_id(player_name, player_id, retro_pit_df)
    bat_df = append_player_id(player_name, player_id, bat_df)
    pit_df = append_player_id(player_name, player_id, pit_df)
    field_df = append_player_id(player_name, player_id, field_df)

# Save all updated sheets to new names
output_file = file_path  # Optionally, change this to a new file if desired
with pd.ExcelWriter(output_file, engine='openpyxl', mode='a') as writer:
    roster_df.to_excel(writer, sheet_name='ROSTER_UPDATED', index=False)
    retro_bat_df.to_excel(writer, sheet_name='RETRO_BAT_UPDATED', index=False)
    retro_pit_df.to_excel(writer, sheet_name='RETRO_PIT_UPDATED', index=False)
    bat_df.to_excel(writer, sheet_name='BAT_UPDATED', index=False)
    pit_df.to_excel(writer, sheet_name='PIT_UPDATED', index=False)
    field_df.to_excel(writer, sheet_name='FIELD_UPDATED', index=False)

print("All sheets updated with player IDs and saved to new sheet names.")
