import sqlite3
import pandas as pd
import os

# Define the directory where the roster files are located
roster_dir = r'C:\Users\vadim\Documents\Code\_pennant_race\retrosheet-sqlite3_v2022_02_15\rosters'

# List all files in the directory
roster_files = [f for f in os.listdir(roster_dir) if f.endswith('.ROS')]

# Limit the number of roster files for debugging
roster_files = roster_files[:1]  # Process only one file for now

# Step 1: Read .ROS file and parse player data, filtering for pitchers (pos == "P")
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
            
            # Only include players with position "P" (pitchers)
            if position == "P":
                player_data.append({
                    'player_id': player_id,
                    'name': name,
                    'bats': bats,
                    'throws': throws,
                    'team': team,
                    'pos': position
                })
    
    print(f"Pitchers found in {ros_file_path}: {len(player_data)}")  # Check parsed pitchers
    return player_data

def get_pitcher_stats_against_batters(pitcher_id, year, db_conn):
    print(f"Getting stats for pitcher {pitcher_id} in {year}")  # Log pitcher ID
    cursor = db_conn.cursor()

    # Query events where the pitcher was involved (PIT_ID is the pitcher)
    query = """
    SELECT PIT_ID, BAT_HAND_CD, AB_FL, H_CD, EVENT_CD, SH_FL, SF_FL, RBI_CT
    FROM events
    WHERE PIT_ID = ? AND GAME_ID LIKE ?
    """
    
    cursor.execute(query, (pitcher_id, f'%{year}%'))
    events = cursor.fetchall()
    
    # Log the events fetched
    print(f"Events fetched for {pitcher_id}: {len(events)} events")

    # Initialize stats allowed by the pitcher for total, vs LHB, and vs RHB
    stats = {
        "PA": 0, "AB": 0, "H": 0, "2B": 0, "3B": 0, "HR": 0, "BB": 0, "SO": 0, "HBP": 0, "SH": 0, "SF": 0, "RBI": 0, "TB": 0,
        "PA_vs_LHB": 0, "AB_vs_LHB": 0, "H_vs_LHB": 0, "2B_vs_LHB": 0, "3B_vs_LHB": 0, "HR_vs_LHB": 0,
        "BB_vs_LHB": 0, "SO_vs_LHB": 0, "HBP_vs_LHB": 0, "RBI_vs_LHB": 0, "TB_vs_LHB": 0, "SH_vs_LHB": 0, "SF_vs_LHB": 0,
        "PA_vs_RHB": 0, "AB_vs_RHB": 0, "H_vs_RHB": 0, "2B_vs_RHB": 0, "3B_vs_RHB": 0, "HR_vs_RHB": 0,
        "BB_vs_RHB": 0, "SO_vs_RHB": 0, "HBP_vs_RHB": 0, "RBI_vs_RHB": 0, "TB_vs_RHB": 0, "SH_vs_RHB": 0, "SF_vs_RHB": 0
    }
    
    for event in events:
        pit_id, bat_hand_cd, ab_fl, h_cd, event_cd, sh_fl, sf_fl, rbi_ct = event[:8]
        
        # Increment plate appearances (PA)
        stats["PA"] += 1
        if bat_hand_cd == 'L':
            stat_prefix = "_vs_LHB"
        elif bat_hand_cd == 'R':
            stat_prefix = "_vs_RHB"
        else:
            stat_prefix = None
        
        # If it's an at-bat
        if ab_fl == 'T':
            stats["AB"] += 1
            if stat_prefix:
                stats[f"AB{stat_prefix}"] += 1
            if h_cd > 0:
                stats["H"] += 1
                if stat_prefix:
                    stats[f"H{stat_prefix}"] += 1
            if event_cd == 21:  # Double
                stats["2B"] += 1
                stats["TB"] += 2
                if stat_prefix:
                    stats[f"2B{stat_prefix}"] += 1
                    stats[f"TB{stat_prefix}"] += 2
            if event_cd == 22:  # Triple
                stats["3B"] += 1
                stats["TB"] += 3
                if stat_prefix:
                    stats[f"3B{stat_prefix}"] += 1
                    stats[f"TB{stat_prefix}"] += 3
            if event_cd == 23:  # Home Run
                stats["HR"] += 1
                stats["TB"] += 4
                if stat_prefix:
                    stats[f"HR{stat_prefix}"] += 1
                    stats[f"TB{stat_prefix}"] += 4
            if h_cd == 1:  # Single (default hit)
                stats["TB"] += 1
                if stat_prefix:
                    stats[f"TB{stat_prefix}"] += 1
        
        # Track strikeouts (SO)
        if event_cd == 3:
            stats["SO"] += 1
            if stat_prefix:
                stats[f"SO{stat_prefix}"] += 1
        
        # Track walks (BB)
        if event_cd in [14, 15]:  # Walk or intentional walk
            stats["BB"] += 1
            if stat_prefix:
                stats[f"BB{stat_prefix}"] += 1
        
        # Track hit by pitch (HBP)
        if event_cd == 16:  # Hit by pitch
            stats["HBP"] += 1
            if stat_prefix:
                stats[f"HBP{stat_prefix}"] += 1
        
        # Track sacrifice hits (SH) and sacrifice flies (SF)
        if sh_fl == 'T':
            stats["SH"] += 1
            if stat_prefix:
                stats[f"SH{stat_prefix}"] += 1
        if sf_fl == 'T':
            stats["SF"] += 1
            if stat_prefix:
                stats[f"SF{stat_prefix}"] += 1
        
        # Track RBIs
        if rbi_ct > 0:
            stats["RBI"] += rbi_ct
            if stat_prefix:
                stats[f"RBI{stat_prefix}"] += rbi_ct

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
    stats["BA_vs_LHB"], stats["OBP_vs_LHB"], stats["SLG_vs_LHB"], stats["OPS_vs_LHB"], stats["ISO_vs_LHB"] = calc_metrics(stats, "_vs_LHB")
    stats["BA_vs_RHB"], stats["OBP_vs_RHB"], stats["SLG_vs_RHB"], stats["OPS_vs_RHB"], stats["ISO_vs_RHB"] = calc_metrics(stats, "_vs_RHB")

    # Log the calculated stats and metrics
    print(f"Stats for pitcher {pitcher_id}: {stats}")
    
    return stats

def compile_team_stats(ros_files, db_conn):
    compiled_data = []
    for ros_file in ros_files:
        ros_file_path = os.path.join(roster_dir, ros_file)
        if os.path.exists(ros_file_path):
            team_roster = parse_ros_file(ros_file_path)
            for player in team_roster:
                year = ros_file[-8:-4]
                stats = get_pitcher_stats_against_batters(player['player_id'], year, db_conn)
                player_stats = {**player, **stats}
                compiled_data.append(player_stats)
        else:
            print(f"File not found: {ros_file_path}")
    return pd.DataFrame(compiled_data)

# Step 4: Output the final CSV
def save_to_csv(compiled_data, output_path):
    print(f"Saving compiled data to {output_path}")  # Added to check if saving
    compiled_data.to_csv(output_path, index=False)

retro_team_abbr = ['ATL', 'BAL', 'BOS', 'CAL', 'CHN', 'CHA', 'CIN', 'CLE', 'DET', 'HOU', 'KCA', 'LAN', 'MIL', 'MIN', 'MON', 'NYN', 'NYA', 'OAK', 'PHI', 'PIT', 'SDN', 'SEA', 'SFN', 'SLN', 'TEX', 'TOR', 'WS2']

def generate_roster_files():
    years = range(1980, 1990)  # 1980 to 1989
    return [f"{team}{year}.ROS" for team in retro_team_abbr for year in years]

# Example usage
ros_files = generate_roster_files()
db_path = r'C:\Users\vadim\Documents\Code\_pennant_race\retrosheet-sqlite3_v2022_02_15\retrosheet.db'
conn = sqlite3.connect(db_path)
compiled_data = compile_team_stats(ros_files, conn)
save_to_csv(compiled_data, r'C:\Users\vadim\Documents\Code\_pennant_race\retrosheet-sqlite3_v2022_02_15\retrosheet_db_1980_1989_pitchers.csv')