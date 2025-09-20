import pandas as pd
import matplotlib.pyplot as plt

# Read the Excel file (make sure to replace 'your_file.xlsx' with the actual file path)
file_path = r'C:\Users\vadim\Documents\Code\_pennant_race\league_files\league_rosters_2024-10-15_18-36-03.xlsx'

# Load the Batters and Pitchers sheets
batters_df = pd.read_excel(file_path, sheet_name='Batters')
pitchers_df = pd.read_excel(file_path, sheet_name='Pitchers')

# Define the archetypes in the required order for sorting
batter_archetypes = ['scrub', 'career minor leaguer', 'september callup', 'injury replacement', 'AAAA player', 'backup', 'platoon', 'regular starter', 'star', '5-tool']
starter_archetypes = ['journeyman', 'fringe starter', 'late bloomer', 'spot starter', 'quad-a arm', 'swingman', 'back of rotation', 'regular starter', 'top of rotation', 'ace']
reliever_archetypes = ['filler arm', 'taxi squad reliever', 'roster expansion reliever', 'bullpen patch', 'perpetual callup', 'specialist', 'long-relief', 'low-leverage', 'high-leverage', 'closer']

# Function to create plots
def create_visualization(df, title, archetypes):
    # Group the data by school_type and archetype
    grouped_df = df.groupby(['school_type', 'archetype']).size().reset_index(name='count')
    
    # Pivot the table for better visualization
    pivot_df = grouped_df.pivot(index='archetype', columns='school_type', values='count').fillna(0)
    
    # Ensure the order of archetypes is correct
    pivot_df = pivot_df.reindex(archetypes)
    
    # Plot the results
    pivot_df.plot(kind='bar', stacked=True, figsize=(10, 7))
    plt.title(f'Archetype Distribution: {title}')
    plt.ylabel('Count')
    plt.xlabel('Archetype')
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()

# Filter batters, starting pitchers, and relief pitchers from the pitchers sheet
starting_pitchers_df = pitchers_df[pitchers_df['position'] == 'SP']
relief_pitchers_df = pitchers_df[pitchers_df['position'] == 'RP']

# Create visualizations
create_visualization(batters_df, 'Batters', batter_archetypes)
create_visualization(starting_pitchers_df, 'Starting Pitchers', starter_archetypes)
create_visualization(relief_pitchers_df, 'Relief Pitchers', reliever_archetypes)
