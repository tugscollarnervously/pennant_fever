def play_game(self, current_day):
    # Ensure self.day (current_day) is not None
    if self.day is None:
        logger.debug(f"Warning: Game day (self.day) is None. Defaulting to day 0.")
        self.day = 0

    # Step 1: Initialize used relievers lists
    self.used_relievers_away = []
    self.used_relievers_home = []

    # Step 2: Select starting pitchers once and store them
    away_pitcher = self.away_team.select_starting_pitcher(self.day)
    home_pitcher = self.home_team.select_starting_pitcher(self.day)

    # Add pitchers' handedness (throws) to the result
    self.result['away_pitcher_throws'] = away_pitcher.throws
    self.result['home_pitcher_throws'] = home_pitcher.throws

    # Step 3: Resolve runs for visiting team and store runs and reliever stats
    away_runs, away_total_relief_value, away_starter_innings, away_reliever_innings_distribution, away_earned_runs_distribution, away_unearned_runs_distribution = self.resolve_team_runs(
        self.away_team, home_pitcher, current_day, is_visiting=True)
    self.result['away_runs'] = away_runs
    self.result['away_starter_innings'] = away_starter_innings
    self.result['away_reliever_innings_distribution'] = away_reliever_innings_distribution
    self.result['away_reliever_earned_runs'] = away_earned_runs_distribution
    self.result['away_reliever_unearned_runs'] = away_unearned_runs_distribution

    # Step 4: Resolve runs for home team and store runs and reliever stats
    home_runs, home_total_relief_value, home_starter_innings, home_reliever_innings_distribution, home_earned_runs_distribution, home_unearned_runs_distribution = self.resolve_team_runs(
        self.home_team, away_pitcher, current_day, is_visiting=False)
    self.result['home_runs'] = home_runs
    self.result['home_starter_innings'] = home_starter_innings
    self.result['home_reliever_innings_distribution'] = home_reliever_innings_distribution
    self.result['home_reliever_earned_runs'] = home_earned_runs_distribution
    self.result['home_reliever_unearned_runs'] = home_unearned_runs_distribution

    # Step 5: Determine pitcher decisions
    self.determine_pitcher_decision(away_pitcher, home_pitcher)

    # **Step 6: Update Stats**
    # - Starting Pitchers
    away_pitcher_stats = self.away_team.get_pitcher_stats(away_pitcher)
    home_pitcher_stats = self.home_team.get_pitcher_stats(home_pitcher)

    # Update starting pitchers' stats
    away_pitcher_stats.update_stats(
        innings=away_starter_innings,
        runs=away_runs,
        earned_runs=self.result['away_reliever_earned_runs'].get(away_pitcher.name, 0),
        strikeouts=away_pitcher.strikeouts,  # If tracked during game
        walks=away_pitcher.walks,  # If tracked
        hits=away_pitcher.hits_allowed,  # If tracked
        home_runs=away_pitcher.home_runs_allowed,  # If tracked
        decision=away_pitcher.decision
    )

    home_pitcher_stats.update_stats(
        innings=home_starter_innings,
        runs=home_runs,
        earned_runs=self.result['home_reliever_earned_runs'].get(home_pitcher.name, 0),
        strikeouts=home_pitcher.strikeouts,
        walks=home_pitcher.walks,
        hits=home_pitcher.hits_allowed,
        home_runs=home_pitcher.home_runs_allowed,
        decision=home_pitcher.decision
    )

    # - Relievers
    for reliever in self.used_relievers_away:
        reliever_stats = self.away_team.get_pitcher_stats(reliever)
        reliever_innings = float(self.result['away_reliever_innings_distribution'].get(reliever.name, 0))
        reliever_earned_runs = self.result['away_reliever_earned_runs'].get(reliever.name, 0)

        reliever_stats.update_stats(
            innings=reliever_innings,
            runs=reliever_earned_runs,
            earned_runs=reliever_earned_runs,
            strikeouts=reliever.strikeouts,  # If tracked
            walks=reliever.walks,  # If tracked
            hits=reliever.hits_allowed,  # If tracked
            home_runs=reliever.home_runs_allowed  # If tracked
        )

    for reliever in self.used_relievers_home:
        reliever_stats = self.home_team.get_pitcher_stats(reliever)
        reliever_innings = float(self.result['home_reliever_innings_distribution'].get(reliever.name, 0))
        reliever_earned_runs = self.result['home_reliever_earned_runs'].get(reliever.name, 0)

        reliever_stats.update_stats(
            innings=reliever_innings,
            runs=reliever_earned_runs,
            earned_runs=reliever_earned_runs,
            strikeouts=reliever.strikeouts,  # If tracked
            walks=reliever.walks,  # If tracked
            hits=reliever.hits_allowed,  # If tracked
            home_runs=reliever.home_runs_allowed  # If tracked
        )

    # Step 7: Final log, return result
    logger.info(f"Game Day {self.day}: {self.away_team.team_name} {self.result['away_runs']} - {self.home_team.team_name} {self.result['home_runs']}")
    return self.result

# stat tracking
'''
1. Update Stats and Write Back to JSON:
You can integrate the updated stats into your existing team JSON files. When each game is played, you'll update the PitcherStats or BatterStats object and then write these updated stats back into the corresponding team's JSON file.

2. Modifying Your Team Object:
You can modify your Team class to have methods that not only update the statistics of the players but also save the team data (including updated stats) back to the JSON file.

3. Extend the Save Team Data Logic:
You already have a save_team_data method (or similar) in your main loop. This method should be responsible for writing updated team stats back to the JSON file after each game.
'''

class Team:
    def __init__(self, team_id, team_name, pitchers, players, **kwargs):
        self.team_id = team_id
        self.team_name = team_name
        self.pitchers = pitchers
        self.players = players
        # Additional initialization
        self.pitcher_stats = {}  # Dictionary to track individual pitcher stats

    def get_pitcher_stats(self, pitcher):
        # If the pitcher doesn't have stats yet, initialize them
        if pitcher not in self.pitcher_stats:
            self.pitcher_stats[pitcher.name] = {
                "appearances": 0,
                "innings_pitched": 0.0,
                "earned_runs": 0,
                "runs": 0,
                "strikeouts": 0,
                "walks": 0,
                "wins": 0,
                "losses": 0
            }
        return self.pitcher_stats[pitcher.name]

    def save_team_data(self):
        """Save team data, including updated pitcher stats, back to the JSON file."""
        file_path = os.path.join(BASE_DIRECTORY, f'team_id_{self.team_id}.json')
        data = {
            "team_id": self.team_id,
            "team_name": self.team_name,
            # Include pitchers and players here, updating with any new stats.
            "pitchers": [{
                "name": pitcher.name,
                "type": pitcher.type,
                "start_value": pitcher.start_value,
                "relief_value": pitcher.relief_value,
                "endurance": pitcher.endurance,
                "rest": pitcher.rest,
                "throws": pitcher.throws,
                "injury": pitcher.injury,
                "cg_rating": pitcher.cg_rating,
                "sho_rating": pitcher.sho_rating,
                "fatigue": pitcher.fatigue,
                "last_start_day": pitcher.last_start_day,
                # Update the pitcher’s stats
                "stats": self.get_pitcher_stats(pitcher)  # Save the stats
            } for pitcher in self.pitchers],
            "players": [{
                "name": player.name,
                "role": player.role,
                "batting": player.batting,
                "power": player.power,
                "speed": player.speed,
                "fielding": player.fielding,
                "position": player.position,
                "sec_position": player.sec_position,
                "bats": player.bats,
                "injury": player.injury,
                "salary": player.salary,
                "eye": player.eye
            } for player in self.players]
        }

        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)
        logger.debug(f"Saved team data for {self.team_name} to {file_path}")

'''
Once your Team object updates the player stats after each game (in the play_game function), you can call save_team_data to save the updated data back into the corresponding JSON file. For example, in your main loop:
'''

# Play the game
result = game.play_game(day)

# Update team stats
team_stats_lookup[home_team_id].update_stats(result['home_runs'], result['away_runs'])
team_stats_lookup[away_team_id].update_stats(result['away_runs'], result['home_runs'])

# Save updated team data (including stats)
home_team.save_team_data()
away_team.save_team_data()

'''
If you want to separate stats from the team JSON file, you can create a dedicated file for stats. For example, each team could have a team_id_{id}_stats.json file that only contains the stats. This file would be loaded and saved similarly to how you handle the team file.

'''

def save_team_stats(self):
    """Save just the stats data to a separate file."""
    file_path = os.path.join(BASE_DIRECTORY, f'team_id_{self.team_id}_stats.json')
    stats_data = {
        "team_id": self.team_id,
        "pitcher_stats": self.pitcher_stats,  # Only save stats
    }
    with open(file_path, 'w') as f:
        json.dump(stats_data, f, indent=4)
    logger.debug(f"Saved stats for {self.team_name} to {file_path}")


# And call this after each game:
# Save updated team stats to a separate stats file
home_team.save_team_stats()
away_team.save_team_stats()
