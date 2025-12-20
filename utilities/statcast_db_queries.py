
import sqlite3
import pandas as pd
from datetime import datetime
from memory_profiler import profile

@profile
def process_data():
    # Connect to the SQLite database with the correct path
    conn = sqlite3.connect('/Users/sputnik3/Documents/The Chase/totalbaseballstatcast.db')

    # Query to select required columns
    query = """
    SELECT pitch_name, release_speed, release_spin_rate, zone, description, events, bb_type, hit_distance_sc, 
           hit_location, launch_speed, launch_angle, launch_speed_angle, hc_x, hc_y 
    FROM events;
    """
    df = pd.read_sql_query(query, conn)

    event_mappings = {
        'hit_into_play': [
            'single', 'double', 'triple', 'home_run', 'field_error'
        ],
        'field_out': [
            'field_out', 'sac_fly', 'force_out', 'double_play', 'sac_fly_double_play', 
            'grounded_into_double_play', 'fielders_choice', 'fielders_choice_out', 'sac_bunt'
        ],
        'strike': [
            'called_strike', 'swinging_strike', 'swinging_strike_blocked', 'foul_tip', 
            'missed_bunt', 'foul_bunt', 'bunt_foul_tip', 'foul_pitchout'
        ],
        'ball': [
            'ball', 'blocked_ball', 'pitchout', 'passed_ball', 'wild_pitch'
        ],
        'exclusion_events': [
            'pickoff_1b', 'caught_stealing_2b', 'runner_double_play', 'caught_stealing_home',
            'other_out', 'caught_stealing_3b', 'pickoff_2b', 'game_advisory'
        ],
        'description': [
            'hit_into_play', 'ball', 'called_strike', 'swinging_strike', 'swinging_strike_blocked', 'foul_tip', 'missed_bunt', 'foul_bunt', 'blocked_ball', 'pitchout', 'foul', 'hit_by_pitch', 'bunt_foul_tip', 'foul_pitchout'
        ],
        'bb_type': [
            'ground_ball', 'fly_ball', 'line_drive', 'popup'
        ],
        'pitch_name': [
            '4-Seam Fastball', 'Sinker', 'Cutter', 'Changeup', 'Curveball', 'Slider', 'Knuckle Curve', 'Splitter', 'Screwball', 'Eephus', 'Slow Curve', 'Forkball', 'Knuckleball', 'Pitchout', 'Slurve', 'Sweeper', 'Other'
        ]
    }

    # Filter out unwanted events
    df = df[~df['events'].isin(event_mappings['exclusion_events'])]

    # Map descriptions to simplified categories
    description_mapping = {
        'hit_into_play': 'hit_into_play',
        'ball': 'ball',
        'called_strike': 'called_strike',
        'swinging_strike': 'swinging_strike',
        'swinging_strike_blocked': 'swinging_strike',
        'foul_tip': 'swinging_strike',
        'missed_bunt': 'called_strike',
        'foul_bunt': 'swinging_strike',
        'blocked_ball': 'ball',
        'pitchout': 'ball',
        'foul': 'swinging_strike',
        'hit_by_pitch': 'hit_by_pitch',
        'bunt_foul_tip': 'swinging_strike',
        'foul_pitchout': 'swinging_strike',
        'passed_ball': 'ball',
        'wild_pitch': 'ball'
    }

    df['simplified_description'] = df['description'].map(description_mapping)

    # Map events to simplified categories
    event_mapping = {
        'field_out': 'field_out',
        'double': 'hit_into_play',
        'triple': 'hit_into_play',
        'single': 'hit_into_play',
        'sac_fly': 'field_out',
        'field_error': 'hit_into_play',
        'force_out': 'field_out',
        'double_play': 'field_out',
        'sac_fly_double_play': 'field_out',
        'grounded_into_double_play': 'field_out',
        'strikeout_double_play': 'strike_out',
        'fielders_choice': 'field_out',
        'fielders_choice_out': 'field_out',
        'sac_bunt': 'field_out',
        'home_run': 'hit_into_play',
        'catcher_interf': 'hit_into_play'
    }

    df['simplified_event'] = df['events'].map(event_mapping)

    # Generate timestamp for the file name
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Path for exporting the Excel file
    export_path = f'/Users/sputnik3/Documents/_totalbaseball/baseball_strategy/pitch_type_results_{timestamp}.xlsx'

    # Aggregate data by pitch type and export to Excel with each type on a different sheet
    with pd.ExcelWriter(export_path) as writer:
        for pitch_type in df['pitch_name'].unique():
            pitch_data = df[df['pitch_name'] == pitch_type]
            
            # Aggregate pitch data
            pitch_agg = pitch_data.groupby(['pitch_name', 'release_speed', 'release_spin_rate', 'zone', 'simplified_description']).size().reset_index(name='count')
            
            # Aggregate hit data
            hit_agg = pitch_data[pitch_data['simplified_event'] == 'hit_into_play'].groupby(['pitch_name', 'bb_type', 'hit_distance_sc', 'hit_location', 'launch_speed', 'launch_angle', 'launch_speed_angle', 'hc_x', 'hc_y']).size().reset_index(name='count')
            
            # Merge pitch and hit data
            merged_data = pd.merge(pitch_agg, hit_agg, on='pitch_name', how='left')
            
            # Export to Excel sheet
            merged_data.to_excel(writer, sheet_name=pitch_type, index=False)

    print(f"Data exported successfully to {export_path}")

# Run the process_data function
process_data()