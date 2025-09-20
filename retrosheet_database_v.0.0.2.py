import sqlite3
import pandas as pd
import os

# Define the directory where the roster files are located
roster_dir = r'C:\Users\vadim\Documents\Code\_pennant_race\retrosheet-sqlite3_v2022_02_15\rosters'

# List all files in the directory
roster_files = [f for f in os.listdir(roster_dir) if f.endswith('.ROS')]

# Limit the number of roster files for debugging
roster_files = roster_files[:1]  # Process only one file for now

# Step 1: Read .ROS file and parse player data
def parse_ros_file(ros_file_path):
    print(f"Processing file: {ros_file_path}")  # Added to check if files are processed
    player_data = []
    with open(ros_file_path, 'r', encoding='ISO-8859-1') as f:  # Specify encoding
        for line in f.readlines():
            parts = line.strip().split(',')
            player_id = parts[0]
            name = f"{parts[1]} {parts[2]}"
            bats = parts[3]
            throws = parts[4]
            team = parts[5]
            position = parts[6]
            player_data.append({
                'player_id': player_id,
                'name': name,
                'bats': bats,
                'throws': throws,
                'team': team,
                'pos': position
            })
    print(f"Players found in {ros_file_path}: {len(player_data)}")  # Check parsed players
    return player_data

def get_player_stats(player_id, year, db_conn):
    print(f"Getting stats for player {player_id} in {year}")  # Log player ID
    cursor = db_conn.cursor()

    # Modify the query to include PIT_HAND_CD for splits and base-running fields for SB/CS
    query = """
    SELECT BAT_ID, AB_FL, H_CD, EVENT_CD, SH_FL, SF_FL, RBI_CT, BAT_FATE_ID, BAT_EVENT_FL, PIT_HAND_CD, 
           BASE1_RUN_ID, BASE2_RUN_ID, BASE3_RUN_ID, RUN1_SB_FL, RUN2_SB_FL, RUN3_SB_FL, 
           RUN1_CS_FL, RUN2_CS_FL, RUN3_CS_FL
    FROM events
    WHERE BAT_ID = ? AND GAME_ID LIKE ?
    """
    
    cursor.execute(query, (player_id, f'%{year}%'))
    events = cursor.fetchall()
    
    # Log the events fetched
    print(f"Events fetched for {player_id}: {len(events)} events")

    # Initialize stats for total, vs LHP, and vs RHP
    stats = {
        "PA": 0, "AB": 0, "H": 0, "2B": 0, "3B": 0, "HR": 0, "BB": 0, "SO": 0, "HBP": 0,
        "SH": 0, "SF": 0, "RBI": 0, "R": 0, "SB": 0, "CS": 0, "TB": 0,
        "PA_vs_LHP": 0, "AB_vs_LHP": 0, "H_vs_LHP": 0, "2B_vs_LHP": 0, "3B_vs_LHP": 0, "HR_vs_LHP": 0,
        "BB_vs_LHP": 0, "SO_vs_LHP": 0, "HBP_vs_LHP": 0, "R_vs_LHP": 0, "RBI_vs_LHP": 0, "TB_vs_LHP": 0, "SH_vs_LHP": 0, "SF_vs_LHP": 0,
        "PA_vs_RHP": 0, "AB_vs_RHP": 0, "H_vs_RHP": 0, "2B_vs_RHP": 0, "3B_vs_RHP": 0, "HR_vs_RHP": 0,
        "BB_vs_RHP": 0, "SO_vs_RHP": 0, "HBP_vs_RHP": 0, "R_vs_RHP": 0, "RBI_vs_RHP": 0, "TB_vs_RHP": 0, "SH_vs_RHP": 0, "SF_vs_RHP": 0
    }
    
    for event in events:
        if len(event) >= 19:  # Ensure event has at least 19 fields
            ab_fl, h_cd, event_cd, sh_fl, sf_fl, rbi_ct, bat_fate_id, bat_event_fl, pit_hand_cd = event[1:10]
            base1_run_id, base2_run_id, base3_run_id = event[10:13]
            run1_sb_fl, run2_sb_fl, run3_sb_fl = event[13:16]
            run1_cs_fl, run2_cs_fl, run3_cs_fl = event[16:19]
            
            # Track total plate appearances (PA)
            if bat_event_fl == 'T':
                stats["PA"] += 1
            
            # Check pitcher hand (for LHP/RHP splits)
            if pit_hand_cd == 'L':
                stat_prefix = "LHP"
            elif pit_hand_cd == 'R':
                stat_prefix = "RHP"
            else:
                stat_prefix = None

            # If it's an at-bat
            if ab_fl == 'T':
                stats["AB"] += 1
                if stat_prefix:
                    stats[f"AB_vs_{stat_prefix}"] += 1
                if h_cd > 0:
                    stats["H"] += 1
                    if stat_prefix:
                        stats[f"H_vs_{stat_prefix}"] += 1
                if event_cd == 21:
                    stats["2B"] += 1
                    if stat_prefix:
                        stats[f"2B_vs_{stat_prefix}"] += 1
                    stats["TB"] += 2
                    if stat_prefix:
                        stats[f"TB_vs_{stat_prefix}"] += 2
                if event_cd == 22:
                    stats["3B"] += 1
                    if stat_prefix:
                        stats[f"3B_vs_{stat_prefix}"] += 1
                    stats["TB"] += 3
                    if stat_prefix:
                        stats[f"TB_vs_{stat_prefix}"] += 3
                if event_cd == 23:
                    stats["HR"] += 1
                    if stat_prefix:
                        stats[f"HR_vs_{stat_prefix}"] += 1
                    stats["TB"] += 4
                    if stat_prefix:
                        stats[f"TB_vs_{stat_prefix}"] += 4
                if h_cd == 1:
                    stats["TB"] += 1  # Add 1 for a single
                    if stat_prefix:
                        stats[f"TB_vs_{stat_prefix}"] += 1
                if event_cd == 3:
                    stats["SO"] += 1
                    if stat_prefix:
                        stats[f"SO_vs_{stat_prefix}"] += 1
            
            # Track walks (BB) and hit by pitch (HBP)
            if event_cd in [14, 15]:
                stats["BB"] += 1
                if stat_prefix:
                    stats[f"BB_vs_{stat_prefix}"] += 1
            if event_cd == 16:
                stats["HBP"] += 1
                if stat_prefix:
                    stats[f"HBP_vs_{stat_prefix}"] += 1
            
            # Track sacrifice hits (SH) and sacrifice flies (SF)
            if sh_fl == 'T':
                stats["SH"] += 1
                if stat_prefix:
                    stats[f"SH_vs_{stat_prefix}"] += 1
            if sf_fl == 'T':
                stats["SF"] += 1
                if stat_prefix:
                    stats[f"SF_vs_{stat_prefix}"] += 1
            
            # Track RBIs
            if rbi_ct > 0:
                stats["RBI"] += rbi_ct
                if stat_prefix:
                    stats[f"RBI_vs_{stat_prefix}"] += rbi_ct
            
            # Track runs (based on BAT_FATE_ID 4 = scored, 5 = unearned run, 6 = scored after error)
            if bat_fate_id in [4, 5, 6]:
                stats["R"] += 1
                if stat_prefix:
                    stats[f"R_vs_{stat_prefix}"] += 1

            # Convert player IDs to lowercase to avoid case-sensitivity issues
            if base1_run_id.strip().lower() == player_id.strip().lower() and run1_sb_fl == 'T':
                stats["SB"] += 1
            if base2_run_id.strip().lower() == player_id.strip().lower() and run2_sb_fl == 'T':
                stats["SB"] += 1
            if base3_run_id.strip().lower() == player_id.strip().lower() and run3_sb_fl == 'T':
                stats["SB"] += 1

            # Check caught stealing (CS)
            if base1_run_id.strip().lower() == player_id.strip().lower() and run1_cs_fl == 'T':
                stats["CS"] += 1
            if base2_run_id.strip().lower() == player_id.strip().lower() and run2_cs_fl == 'T':
                stats["CS"] += 1
            if base3_run_id.strip().lower() == player_id.strip().lower() and run3_cs_fl == 'T':
                stats["CS"] += 1

            '''
            # Add print statements here to debug SB/CS logic
            print(f"Player: {player_id}, Base1: {base1_run_id}, SB1: {run1_sb_fl}, CS1: {run1_cs_fl}")
            print(f"Player: {player_id}, Base2: {base2_run_id}, SB2: {run2_sb_fl}, CS2: {run2_cs_fl}")
            print(f"Player: {player_id}, Base3: {base3_run_id}, SB3: {run3_sb_fl}, CS3: {run3_cs_fl}")

            print(f"Comparing: player_id: {player_id.strip().lower()} with base1_run_id: {base1_run_id.strip().lower()}")
            print(f"Comparing: player_id: {player_id.strip().lower()} with base2_run_id: {base2_run_id.strip().lower()}")
            print(f"Comparing: player_id: {player_id.strip().lower()} with base3_run_id: {base3_run_id.strip().lower()}")
            '''

    # Calculate advanced metrics for total and splits
    def calc_metrics(stats_dict, prefix=""):
        ba = round(stats_dict[f"H{prefix}"] / stats_dict[f"AB{prefix}"], 3) if stats_dict[f"AB{prefix}"] > 0 else 0
        obp = round((stats_dict[f"H{prefix}"] + stats_dict[f"BB{prefix}"] + stats_dict[f"HBP{prefix}"]) / 
                    (stats_dict[f"AB{prefix}"] + stats_dict[f"BB{prefix}"] + stats_dict[f"HBP{prefix}"] + stats_dict[f"SF{prefix}"]), 3) if (stats_dict[f"AB{prefix}"] + stats_dict[f"BB{prefix}"] + stats_dict[f"HBP{prefix}"] + stats_dict[f"SF{prefix}"]) > 0 else 0
        slg = round(stats_dict[f"TB{prefix}"] / stats_dict[f"AB{prefix}"], 3) if stats_dict[f"AB{prefix}"] > 0 else 0
        ops = round(obp + slg, 3)
        iso = round(slg - ba, 3)
        return ba, obp, slg, ops, iso
    
    # Add metrics for total
    stats["BA"], stats["OBP"], stats["SLG"], stats["OPS"], stats["ISO"] = calc_metrics(stats)
    
    # Add metrics for LHP and RHP splits
    stats["BA_vs_LHP"], stats["OBP_vs_LHP"], stats["SLG_vs_LHP"], stats["OPS_vs_LHP"], stats["ISO_vs_LHP"] = calc_metrics(stats, "_vs_LHP")
    stats["BA_vs_RHP"], stats["OBP_vs_RHP"], stats["SLG_vs_RHP"], stats["OPS_vs_RHP"], stats["ISO_vs_RHP"] = calc_metrics(stats, "_vs_RHP")

    # Log the calculated stats and metrics
    print(f"Stats for {player_id}: {stats}")
    
    return stats

# Step 3: Merge Player Roster Data and Stats
def compile_team_stats(ros_files, db_conn):
    compiled_data = []
    for ros_file in ros_files:
        ros_file_path = os.path.join(roster_dir, ros_file)
        if os.path.exists(ros_file_path):
            team_roster = parse_ros_file(ros_file_path)
            for player in team_roster:
                year = ros_file[-8:-4]
                stats = get_player_stats(player['player_id'], year, db_conn)
                player_stats = {**player, **stats}
                compiled_data.append(player_stats)
        else:
            print(f"File not found: {ros_file_path}")
    return pd.DataFrame(compiled_data)

# Step 4: Output the final CSV
def save_to_csv(compiled_data, output_path):
    print(f"Saving compiled data to {output_path}")  # Added to check if saving
    compiled_data.to_csv(output_path, index=False)

retro_team_abbr = ['ATL', 'BAL', 'BOS', 'CAL', 'CHN', 'CHA', 'CIN', 'CLE', 'DET', 'HOU', 'KCA', 'LAN', 'MIL', 'MIN', 'MON', 'NYN', 'NYA', 'OAK', 'PHI', 'PIT', 'SDN', 'SEA', 'SFN', 'SLN', 'TEX', 'TOR']

def generate_roster_files():
    years = range(1980, 1990)  # 1980 to 1989
    return [f"{team}{year}.ROS" for team in retro_team_abbr for year in years]

# Example usage
ros_files = generate_roster_files()
db_path = r'C:\Users\vadim\Documents\Code\_pennant_race\retrosheet-sqlite3_v2022_02_15\retrosheet.db'
conn = sqlite3.connect(db_path)
compiled_data = compile_team_stats(ros_files, conn)
save_to_csv(compiled_data, r'C:\Users\vadim\Documents\Code\_pennant_race\retrosheet-sqlite3_v2022_02_15\retrosheet_db_1980_1989.csv')

'''
     event type.  There are 25 different numeric codes to describe
             the type of event.  They are:

          Code Meaning

          0    Unknown event
          1    No event
          2    Generic out
          3    Strikeout
          4    Stolen base
          5    Defensive indifference
          6    Caught stealing
          7    Pickoff error
          8    Pickoff
          9    Wild pitch
          10   Passed ball
          11   Balk
          12   Other advance
          13   Foul error
          14   Walk
          15   Intentional walk
          16   Hit by pitch
          17   Interference
          18   Error
          19   Fielder's choice
          20   Single
          21   Double
          22   Triple
          23   Home run
          24   Missing play
'''