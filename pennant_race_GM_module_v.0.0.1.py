import json

def manage_roster(team_id, action, player_id=None, target_team_id=None):
    """
    Allows the GM to manage the roster: 
    - `action`: 'add', 'remove', 'trade'
    - `player_id`: Player involved in the action
    - `target_team_id`: Target team for a trade
    """
    if action == 'add':
        # Logic to add a player to the roster
    elif action == 'remove':
        # Logic to remove a player from the roster
    elif action == 'trade':
        # Logic to trade player between teams

def set_team_strategy(team_id, strategy):
    """
    Allows the GM to set an overall strategy for the team.
    - `strategy`: e.g., 'aggressive', 'balanced', 'defensive'
    """
    # Update team data with the chosen strategy
    with open(f"team_{team_id}.json", 'r+') as file:
        team_data = json.load(file)
        team_data['strategy'] = strategy
        file.seek(0)
        json.dump(team_data, file)
        file.truncate()

def update_pitcher_stats(pitcher, result):
    # Update pitcher's season stats
    pitcher.stats['wins'] += result['wins']
    pitcher.stats['losses'] += result['losses']
    pitcher.stats['saves'] += result['saves']
    # ... and other stats like ERA, strikeouts, etc.
