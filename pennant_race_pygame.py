import random
import logging
import numpy as np
import math
import pygame
import json
import sys
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, joinedload
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

'''
# custom playbook designer (need to have reasonable amount of alterable variables that have impact in the game), ability to name play whatever you want
# play variables: formation, personnel, times used, success rate, yards gained, yards lost, time taken, fatigue cost, stamina cost, turnover rate, penalty rate

# get pbp method, probably when we start using indiv players, but still could be useful initially for broadcasting things like "its a counter right" or "its a screen left" and results of plays
# where/how to store pbp? in master db or external file (like json)

# qb audible (rating?) - if it works, can reveal defensive play/alignment and offense can select another play. negatives: broken plays, loss of yards, increase turnovers - audible can be its own method
# more qb ratings - audible, read coverage, pressure (extra ratings can help rebalance off vs def), awareness, decision making
# more rb/wr ratings - route running, catch in traffic, break tackle, elusiveness, vision, hands
# punting: length/accuracy/hang time (rather than just 1 rating), defense rating (ie if kicker is last line of defense)
# kickers: onside kicks, kickoffs, defense rating (ie if kicker is last line of defense)
# player health rating (in-game only) - small prob that player can sustain injuries (knocks) during game that reduce effectivness like stamina/fatigue system does. if a player reaches 0, he is injured for rest of game. players can recover health via teams medical staff (the medical tent). a player reaching 0 health has a prob of being injured for more games past the current one. do we need an injury rating?
# defenders: ratings for zone and man coverage?

# need kickoff method
# need specials teams (KR/PR)

# head coach profiles - where are we storing them, do we create them in the player gen along with the team then import rating here like the players?
# head coach profiles would be the situational tendencies: quarter/ahead or behind by X points (or tied), 4th downs, blowouts (losing or winning), run out clock. maybe we have "personalities" and have the tendencies under that? each personality would have all the situational tendencies (with diff settings obv), could potential model specific historical coaches here

# pass deflection as an outcome
'''

# Initialize Pygame
pygame.init()

# Global constants for colors, font, and screen dimensions
WIDTH, HEIGHT = 1200, 800
WHITE = (255, 255, 255)
GREEN = (34, 139, 34)
BLUE = (0, 0, 128)
RED = (128, 0, 0)
YELLOW = (255, 255, 0)
BLACK = (0, 0, 0)
FONT = pygame.font.Font(None, 36)

# Initialize the Base for the models
Base = declarative_base()

# Configure logging
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename = f"C:\\Users\\vadim\\Documents\\Code\\_football_game\\logs\\football_game_log_{timestamp}.txt"

# Create a logger
logger = logging.getLogger('FootballSimulation')
logger.setLevel(logging.DEBUG)  # Ensure logger is set to DEBUG

# Remove all handlers before re-adding (to avoid duplicates)
if logger.hasHandlers():
    logger.handlers.clear()

# File handler
file_handler = logging.FileHandler(log_filename, mode='w')
file_handler.setLevel(logging.DEBUG)  # Ensure file handler is set to DEBUG
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)  # For console, INFO level should be sufficient
console_handler.setFormatter(logging.Formatter('%(message)s'))

# Attach handlers to logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

logger.propagate = False  # To avoid duplicate logging entries

BASE_DIRECTORY = 'C:\\Users\\vadim\\Documents\\Code\\_football_game\\'

DATABASE_URL = "postgresql://vadim:bacon@localhost/football_league"
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

# Define create_session to return a new session
def create_session():
    return Session()

class GameSetup:
    def __init__(self):
        self.session = create_session()
        # Load playbooks from JSON files
        self.offensive_playbook = OffensivePlaybook('offensive_plays.json')
        self.defensive_playbook = DefensivePlaybook('defensive_plays.json')

    def select_random_teams(self):
        """Select two random teams from the database."""
        try:
            teams = self.session.query(TeamModel).all()
            if len(teams) < 2:
                logger.error("Not enough teams in the database.")
                return None
            selected_teams = random.sample(teams, 2)

            # Log the selected teams
            for team in selected_teams:
                logger.debug(f"Selected team: {team.name}, City: {team.city}, Conference: {team.conference_name}, Division: {team.division_name}")

            logger.debug("Randomly selected two teams from the database.")
            return selected_teams
        except Exception as e:
            logger.error(f"Error selecting random teams: {e}")
            return None

    def load_team_data(self, team_model):
        """Load team and player data from the database and return a Team object."""
        try:
            # Query players associated with the team
            players = self.session.query(Player).filter_by(team_id=team_model.id).all()

            # Initialize the Team object with playbooks and strategies
            loaded_team = Team(
                team_model=team_model,
                offense_strategy=PassHeavyOffensiveStrategy(),
                defense_strategy=BalancedDefensiveStrategy(),
                offensive_playbook=self.offensive_playbook,
                defensive_playbook=self.defensive_playbook
            )

            # Assign players and log details
            loaded_team.players = players  # Add all players at once
            for player in players:
                logger.debug(f"Loaded player {player.name}, Position: {player.position}")

            return loaded_team

        except Exception as e:
            logger.error(f"Error loading team data: {e}")
            return None


    def close_session(self):
        """Close the database session after the setup is complete."""
        self.session.close()

# Game Initialization function
def initialize_game(game_context):
    """
    Initialize the game by setting up teams, loading data, and starting the game.
    """
    setup = GameSetup()  # Initialize game setup
    logger.debug("LINE 156 Game initialization started.")
    try:
        # Select two random teams
        teams = setup.select_random_teams()
        if not teams:
            logger.debug("No teams available for selection.")
            return

        # Log team and player data for debugging
        for team in teams:
            logger.debug(f"LINE 166 Team: {team.name}, City: {team.city}, Conference: {team.conference_name}")
            for player in team.players:
                logger.debug(f"Player: {player.name}, Position: {player.position}")

        # Load team data, converting TeamModel instances into Team objects
        team1 = setup.load_team_data(teams[0])
        team2 = setup.load_team_data(teams[1])

        # Initialize teams in GameContext and start the game simulation
        game_context.initialize_teams(team1, team2, home_team=team1, away_team=team2)
        game_context.start_game()

    except Exception as e:
        logger.error(f"LINE 179 Error initializing game: {e}")
    
    finally:
        setup.close_session()  # Ensure the session is closed

# Define TeamModel, Player, and Personnel classes here as per the generation code
class TeamModel(Base):
    __tablename__ = 'teams'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    city = Column(String)
    state = Column(String)
    conference_name = Column(String)
    division_name = Column(String)
    league_name = Column(String)  # Add league name field

    players = relationship("Player", back_populates="team")
    personnel = relationship("Personnel", back_populates="team")

class Player(Base):
    __tablename__ = 'players'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    position = Column(String)
    team_id = Column(Integer, ForeignKey('teams.id'))
    speed = Column(Integer)
    strength = Column(Integer)
    athleticism = Column(Integer)
    explosiveness = Column(Integer)
    passing = Column(Integer)  # Example of rating fields
    scrambling = Column(Integer)
    pressure = Column(Integer)
    audible = Column(Integer)
    read_coverage = Column(Integer)
    rushing = Column(Integer)  # Example of rating fields
    receiving = Column(Integer)
    block_run = Column(Integer)
    block_pass = Column(Integer)
    tackling = Column(Integer)
    pass_rush = Column(Integer)
    pass_defense = Column(Integer)
    run_defense = Column(Integer)
    kick_returns = Column(Integer)
    punt_returns = Column(Integer)
    kicking_long = Column(Integer)
    kicking_accuracy = Column(Integer)
    kicking_kickoffs = Column(Integer)
    kicking_onside_kicks = Column(Integer)
    punting_long = Column(Integer)
    punting_accuracy = Column(Integer)
    punting_hang_time = Column(Integer)
    penalty = Column(Integer)
    turnover = Column(Integer)
    stamina = Column(Integer, default=7)  # Stamina rating, default 7
    max_stamina = 7  # Maximum stamina

    # Relationship to the TeamModel
    team = relationship('TeamModel', back_populates='players')

    def apply_fatigue(self, fatigue_cost):
        """Reduces stamina based on the fatigue cost of a play."""
        self.stamina = max(0, self.stamina - fatigue_cost)
        # logger.debug(f"{self.name} stamina reduced by {fatigue_cost}. Current stamina: {self.stamina}")

    def recover_stamina(self, recovery_points):
        """Recovers stamina based on rest between plays or at end of drive."""
        self.stamina = min(self.max_stamina, self.stamina + recovery_points)
        # logger.debug(f"{self.name} recovers {recovery_points} stamina points. Current stamina: {self.stamina}")

    def adjust_for_fatigue(self):
        """Adjust player ratings based on fatigue level."""
        fatigue_penalty = 1.0  # No penalty if stamina is full

        # Apply penalties based on stamina level
        if self.stamina <= 2:
            fatigue_penalty = 0.5  # Severe penalty at low stamina
        elif self.stamina <= 4:
            fatigue_penalty = 0.75  # Moderate penalty at mid stamina
        elif self.stamina <= 6:
            fatigue_penalty = 0.9  # Light penalty at higher stamina

        # Adjust all player ratings based on fatigue penalty
        adjusted_ratings = {
            'speed': self.speed * fatigue_penalty,
            'strength': self.strength * fatigue_penalty,
            'athleticism': self.athleticism * fatigue_penalty,
            'explosiveness': self.explosiveness * fatigue_penalty,
            'passing': self.passing * fatigue_penalty,
            'scrambling': self.scrambling * fatigue_penalty,
            'pressure': self.pressure * fatigue_penalty,
            'audible': self.audible,
            'read_coverage': self.read_coverage,
            'rushing': self.rushing * fatigue_penalty,
            'block_run': self.block_run * fatigue_penalty,
            'block_pass': self.block_pass * fatigue_penalty,
            'receiving': self.receiving * fatigue_penalty,
            'tackling': self.tackling * fatigue_penalty,
            'pass_rush': self.pass_rush * fatigue_penalty,
            'run_defense': self.run_defense * fatigue_penalty,
            'pass_defense': self.pass_defense * fatigue_penalty,
            'kick_returns': self.kick_returns * fatigue_penalty,
            'punt_returns': self.punt_returns * fatigue_penalty,
            'kicking_long': self.kicking_long,
            'kicking_accuracy': self.kicking_accuracy,
            'kicking_kickoffs': self.kicking_kickoffs,
            'kicking_onside_kicks': self.kicking_onside_kicks,
            'punting_long': self.punting_long,
            'punting_accuracy': self.punting_accuracy,
            'punting_hang_time': self.punting_hang_time,
            'penalty': self.penalty,  # No change on penalties
            'turnover': self.turnover  # No change on turnovers
        }

        return adjusted_ratings

class Personnel(Base):
    __tablename__ = 'personnel'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    team_id = Column(Integer, ForeignKey('teams.id'))
    team = relationship('TeamModel', back_populates='personnel')

class PlayLoader:
    """Handles loading of plays from JSON files."""

    @staticmethod
    def load_offensive_plays(play_file):
        with open(play_file, 'r') as file:
            plays_data = json.load(file)
        # Pass only the relevant keys
        return [
            OffensivePlay(
                name=play['name'],
                play_id=play['play_id'],
                play_type=play['play_type'],
                formation=play['formation'],
                key_player=play['key_player'],
                personnel=play['personnel'],
                description=play.get('description', ''),
                play_intent=play.get('play_intent', 'neutral'),  # Default to 'neutral' if not specified
                play_attributes=play['play_attributes']
            ) for play in plays_data
        ]

    @staticmethod
    def load_defensive_plays(play_file):
        with open(play_file, 'r') as file:
            plays_data = json.load(file)
        
        return [
            DefensivePlay(
                name=play['name'],
                play_id=play['play_id'],
                formation=play['formation'],
                linemen=play['linemen'],
                def_backs=play['def_backs'],
                personnel=play['personnel'],
                description=play.get('description', ''),
                play_intent=play.get('play_intent', 'neutral'),  # Default to 'neutral' if not specified
                play_attributes=play['play_attributes']  # Pass full play_attributes to handle nested items
            ) for play in plays_data
        ]

# Team class
class Team:
    def __init__(self, team_model, offensive_playbook, defensive_playbook, offense_strategy, defense_strategy):
        """
        Initialize the team using the loaded team_model (from DB), 
        offensive strategy, and defensive strategy.
        """
        self.name = team_model.name
        self.offense_strategy = offense_strategy
        self.defense_strategy = defense_strategy
        self.players = team_model.players  # Load actual player data from the DB
        self.ratings = self.initialize_ratings()

        # Add playbooks to the team
        self.offensive_playbook = offensive_playbook
        self.defensive_playbook = defensive_playbook

        # Assign kicker and punter
        self.kicker = max(self.players, key=lambda player: player.kicking_accuracy, default=None)
        self.punter = max(self.players, key=lambda player: player.punting_long, default=None)

        # Log assigned kicker and punter
        if self.kicker:
            logger.debug(f"Assigned kicker for {self.name}: {self.kicker.name} with accuracy {self.kicker.kicking_accuracy}")
        else:
            logger.warning(f"No kicker found for {self.name}!")

        if self.punter:
            logger.debug(f"Assigned punter for {self.name}: {self.punter.name} with punting {self.punter.punting_long}")
        else:
            logger.warning(f"No punter found for {self.name}!")

    def initialize_ratings(self):
        """
        Initializes team ratings by summing the relevant player ratings for
        passing, rushing, blocking, run defense, and pass defense.
        """
        ratings = {
            "speed": 0.0,
            "strength": 0.0,
            "athleticism": 0.0,
            "explosiveness": 0.0,
            "passing": 0.0,
            "scrambling": 0.0,
            "pressure": 0.0,
            "audible": 0.0,
            "read_coverage": 0.0,
            "rushing": 0.0,
            "receiving": 0.0,
            "block_run": 0.0,
            "block_pass": 0.0,
            "tackling": 0.0,
            "pass_rush": 0.0,
            "run_defense": 0.0,
            "pass_defense": 0.0,
            "kick_returns":  0.0,
            "punt_returns": 0.0,
            "kicking_long": 0.0,
            "kicking_accuracy": 0.0,
            "kicking_kickoffs": 0.0,
            "kicking_onside_kicks": 0.0,
            "punting_long": 0.0,
            "punting_accuracy": 0.0,
            "punting_hang_time": 0.0,
            "penalty": 0.0,
            "turnover": 0.0,
            "stamina": 0.0
        }

        # Collect and sum ratings for offensive and defensive players
        for player in self.players:
            if player.position == 'QB':  # Quarterback
                ratings["speed"] += player.speed
                ratings["strength"] += player.strength
                ratings["athleticism"] += player.athleticism
                ratings["explosiveness"] += player.explosiveness
                ratings["passing"] += player.passing
                ratings["scrambling"] += player.scrambling
                ratings["pressure"] += player.pressure
                ratings["audible"] += player.audible
                ratings["read_coverage"] += player.read_coverage
                ratings["penalty"] += player.penalty
                ratings["turnover"] += player.turnover
                ratings["stamina"] += player.stamina
            elif player.position in ['RB', 'FB']:  # Running back or Fullback
                ratings["speed"] += player.speed
                ratings["strength"] += player.strength
                ratings["athleticism"] += player.athleticism
                ratings["explosiveness"] += player.explosiveness
                ratings["rushing"] += player.rushing
                ratings["block_pass"] += player.block_pass if player.position == 'FB' else 0  # FB can block
                ratings["block_run"] += player.block_run if player.position == 'FB' else 0  # FB can block
                ratings["kick_returns"] += player.kick_returns
                ratings["punt_returns"] += player.punt_returns
                ratings["penalty"] += player.penalty
                ratings["turnover"] += player.turnover
                ratings["stamina"] += player.stamina
            elif player.position in ['WR', 'TE']:  # Wide Receiver or Tight End
                ratings["speed"] += player.speed
                ratings["strength"] += player.strength
                ratings["athleticism"] += player.athleticism
                ratings["explosiveness"] += player.explosiveness
                ratings["receiving"] += player.receiving
                ratings["block_pass"] += player.block_pass if player.position == 'TE' else 0  # TE can block
                ratings["block_run"] += player.block_run if player.position == 'TE' else 0  # TE can block
                ratings["kick_returns"] += player.kick_returns if player.position == 'WR' else 0  # WR can return kicks
                ratings["punt_returns"] += player.punt_returns if player.position == 'WR' else 0  # WR can return punts
                ratings["penalty"] += player.penalty
                ratings["turnover"] += player.turnover
                ratings["stamina"] += player.stamina
            elif player.position == 'OL':  # Offensive Linemen
                ratings["speed"] += player.speed
                ratings["strength"] += player.strength
                ratings["athleticism"] += player.athleticism
                ratings["explosiveness"] += player.explosiveness
                ratings["block_run"] += player.block_run
                ratings["block_pass"] += player.block_pass
                ratings["penalty"] += player.penalty
                ratings["turnover"] += player.turnover
                ratings["stamina"] += player.stamina
            elif player.position in ['DE', 'DT']:  # Defensive Ends and Tackles
                ratings["speed"] += player.speed
                ratings["strength"] += player.strength
                ratings["athleticism"] += player.athleticism
                ratings["explosiveness"] += player.explosiveness
                ratings["tackling"] += player.tackling
                ratings["pass_rush"] += player.pass_rush
                ratings["run_defense"] += player.run_defense
                ratings["penalty"] += player.penalty
                ratings["turnover"] += player.turnover
                ratings["stamina"] += player.stamina
            elif player.position == 'LB':  # Linebackers
                ratings["speed"] += player.speed
                ratings["strength"] += player.strength
                ratings["athleticism"] += player.athleticism
                ratings["explosiveness"] += player.explosiveness
                ratings["tackling"] += player.tackling
                ratings["pass_rush"] += player.pass_rush
                ratings["run_defense"] += player.run_defense
                ratings["pass_defense"] += player.pass_defense
                ratings["penalty"] += player.penalty
                ratings["turnover"] += player.turnover
                ratings["stamina"] += player.stamina
            elif player.position == 'DB':  # Defensive Backs
                ratings["speed"] += player.speed
                ratings["strength"] += player.strength
                ratings["athleticism"] += player.athleticism
                ratings["explosiveness"] += player.explosiveness
                ratings["tackling"] += player.tackling
                ratings["pass_rush"] += player.pass_rush
                ratings["pass_defense"] += player.pass_defense
                ratings["kick_returns"] += player.kick_returns
                ratings["punt_returns"] += player.punt_returns
                ratings["penalty"] += player.penalty
                ratings["turnover"] += player.turnover
                ratings["stamina"] += player.stamina
            elif player.position == 'K':  # Kicker
                ratings["speed"] += player.speed
                ratings["strength"] += player.strength
                ratings["athleticism"] += player.athleticism
                ratings["explosiveness"] += player.explosiveness
                ratings["kicking_long"] += player.kicking_long
                ratings["kicking_accuracy"] += player.kicking_accuracy
                ratings["kicking_kickoffs"] += player.kicking_kickoffs
                ratings["kicking_onside_kicks"] += player.kicking_onside_kicks
            elif player.position == 'P':  # Punter
                ratings["speed"] += player.speed
                ratings["strength"] += player.strength
                ratings["athleticism"] += player.athleticism
                ratings["explosiveness"] += player.explosiveness
                ratings["punting_long"] += player.punting_long
                ratings["punting_accuracy"] += player.punting_accuracy
                ratings["punting_hang_time"] += player.punting_hang_time
            elif player.position == 'KR':  # Kick Returner
                ratings["speed"] += player.speed
                ratings["strength"] += player.strength
                ratings["athleticism"] += player.athleticism
                ratings["explosiveness"] += player.explosiveness
                ratings["receiving"] += player.receiving
                ratings["block_pass"] += player.block_pass
                ratings["block_run"] += player.block_run
                ratings["kick_returns"] += player.kick_returns
                ratings["punt_returns"] += player.punt_returns
                ratings["penalty"] += player.penalty
                ratings["turnover"] += player.turnover
                ratings["stamina"] += player.stamina
            elif player.position == 'PR':  # Punt Returner
                ratings["speed"] += player.speed
                ratings["strength"] += player.strength
                ratings["athleticism"] += player.athleticism
                ratings["explosiveness"] += player.explosiveness
                ratings["receiving"] += player.receiving
                ratings["block_pass"] += player.block_pass
                ratings["block_run"] += player.block_run
                ratings["kick_returns"] += player.kick_returns
                ratings["punt_returns"] += player.punt_returns
                ratings["penalty"] += player.penalty
                ratings["turnover"] += player.turnover
                ratings["stamina"] += player.stamina

        # Log the summed team ratings for tracking and debugging
        logger.debug(
            f"{self.name} Team Ratings: "
            f"Speed={ratings['speed']}, "
            f"Strength={ratings['strength']}, "
            f"Athleticism={ratings['athleticism']}, "
            f"Explosiveness={ratings['explosiveness']}, "
            f"Passing={ratings['passing']}, "
            f"Scrambling={ratings['scrambling']}, "
            f"Pressure={ratings['pressure']}, "
            f"Audible={ratings['audible']}, "
            f"Read Coverage={ratings['read_coverage']}, "
            f"Rushing={ratings['rushing']}, "
            f"Block Run={ratings['block_run']}, "
            f"Block Pass={ratings['block_pass']}, "
            f"Receiving={ratings['receiving']}, "
            f"Tackling={ratings['tackling']}, "
            f"Pass Rush={ratings['pass_rush']}, "
            f"Run Defense={ratings['run_defense']}, "
            f"Pass Defense={ratings['pass_defense']}, "
            f"Kick Returns={ratings['kick_returns']}, "
            f"Punt Returns={ratings['punt_returns']}, "
            f"Kicking Long={ratings['kicking_long']}, "
            f"Kicking Accuracy={ratings['kicking_accuracy']}, "
            f"Kicking Kickoffs={ratings['kicking_kickoffs']}, "
            f"Kicking Onside Kicks={ratings['kicking_onside_kicks']}, "
            f"Punting Long={ratings['punting_long']}, "
            f"Punting Accuracy={ratings['punting_accuracy']}, "
            f"Punting Hang Time={ratings['punting_hang_time']}, "
            f"Penalty={ratings['penalty']}, "
            f"Turnover={ratings['turnover']}"
            f"Stamina={ratings['stamina']}"
        )
        return ratings

    def apply_fatigue_to_players(self, fatigue_cost):
        """Apply fatigue to all players based on their involvement in the play."""
        for player in self.players:
            player.apply_fatigue(fatigue_cost)

    def recover_players_stamina(self, recovery_points):
        """Recover stamina for all players after a rest period."""
        for player in self.players:
            player.recover_stamina(recovery_points)

    def select_players_for_run(self):
        """Select specific players for a run play based on positions."""
        qb = next(player for player in self.players if player.position == 'QB')
        rb = next(player for player in self.players if player.position == 'RB')
        fb = next(player for player in self.players if player.position == 'FB')
        ol = [player for player in self.players if player.position == 'OL'][:5]  # Take 5 OL
        te = next(player for player in self.players if player.position == 'TE')

        # Apply fatigue cost to players involved in the run play
        fatigue_cost = 1  # Base fatigue cost, can vary by play type
        self.apply_fatigue_to_players(fatigue_cost)

        # Adjust ratings based on fatigue
        qb_ratings = qb.adjust_for_fatigue()
        rb_ratings = rb.adjust_for_fatigue()
        fb_ratings = fb.adjust_for_fatigue()
        te_ratings = te.adjust_for_fatigue()
        ol_ratings = [ol_player.adjust_for_fatigue() for ol_player in ol]

        # Calculate total offensive ratings
        total_offense = (
            qb_ratings['rushing'] + qb_ratings['speed'] + qb_ratings['strength'] + qb_ratings['explosiveness'] +  # QB attributes
            rb_ratings['rushing'] + rb_ratings['strength'] + rb_ratings['speed'] + rb_ratings['athleticism'] + rb_ratings['explosiveness'] +  # RB attributes
            fb_ratings['rushing'] + fb_ratings['block_run'] + fb_ratings['strength'] + fb_ratings['athleticism'] + fb_ratings['explosiveness'] +  # FB attributes
            te_ratings['block_run'] + te_ratings['strength'] + te_ratings['athleticism'] + te_ratings['explosiveness'] +  # TE attributes
            sum(ol_player['block_run'] + ol_player['strength'] for ol_player in ol_ratings)  # OL attributes
        )

        logger.debug(f"Run Play Offense: {self.name} Total Offensive Run Rating: {total_offense}")
        return total_offense

    def select_players_for_pass(self):
        """Select specific players for a pass play based on positions."""
        qb = next(player for player in self.players if player.position == 'QB')
        wr = [player for player in self.players if player.position == 'WR'][:2]  # Take 2 WR
        ol = [player for player in self.players if player.position == 'OL'][:5]  # Take 5 OL
        te = next(player for player in self.players if player.position == 'TE')
        rb = next(player for player in self.players if player.position == 'RB')
        fb = next(player for player in self.players if player.position == 'FB')

        # Apply fatigue cost to players involved in the pass play
        fatigue_cost = 1  # Base fatigue cost, can vary by play type
        self.apply_fatigue_to_players(fatigue_cost)

        # Adjust ratings based on fatigue
        qb_ratings = qb.adjust_for_fatigue()
        wr_ratings = [wr_player.adjust_for_fatigue() for wr_player in wr]
        te_ratings = te.adjust_for_fatigue()
        rb_ratings = rb.adjust_for_fatigue()
        fb_ratings = fb.adjust_for_fatigue()
        ol_ratings = [ol_player.adjust_for_fatigue() for ol_player in ol]

        # Calculate total offensive ratings
        total_offense = (
            qb_ratings['passing'] * 5 + qb_ratings['scrambling'] + qb_ratings['pressure'] + qb_ratings['audible'] + qb_ratings['read_coverage'] + qb_ratings['speed'] + qb_ratings['athleticism'] + qb_ratings['explosiveness'] +  # QB attributes
            sum(wr_player['receiving'] + wr_player['speed'] + wr_player['athleticism'] + wr_player['explosiveness'] for wr_player in wr_ratings) +  # WR attributes
            te_ratings['receiving'] + te_ratings['block_pass'] + te_ratings['strength'] + te_ratings['athleticism'] + te_ratings['explosiveness'] +  # TE attributes
            rb_ratings['receiving'] + rb_ratings['speed'] + rb_ratings['athleticism'] + rb_ratings['explosiveness'] +  # RB attributes
            fb_ratings['block_pass'] + fb_ratings['receiving'] + fb_ratings['strength'] + fb_ratings['athleticism'] + fb_ratings['explosiveness'] +  # FB attributes
            sum(ol_player['block_pass'] + ol_player['strength'] for ol_player in ol_ratings)  # OL attributes
        )

        logger.debug(f"LIJNE 668 Pass Play Offense: {self.name} Total Offensive Pass Rating: {total_offense}")
        return total_offense

    def select_defense_for_run(self):
        """Select specific defensive players to counter a run play."""
        de = [player for player in self.players if player.position == 'DE'][:2]
        dt = [player for player in self.players if player.position == 'DT'][:2]
        lb = [player for player in self.players if player.position == 'LB'][:3]  # Take 3 LB

        total_defense = (
            sum(de_player.tackling + de_player.run_defense + de_player.strength + de_player.athleticism + de_player.explosiveness for de_player in de) +  # DE attributes
            sum(dt_player.tackling + dt_player.run_defense + dt_player.strength + dt_player.athleticism + dt_player.explosiveness for dt_player in dt) +  # DT attributes
            sum(lb_player.tackling + lb_player.run_defense + lb_player.strength + lb_player.speed + lb_player.athleticism + lb_player.explosiveness for lb_player in lb)  # LB attributes
        )

        logger.debug(f"LINE 687 Run Play Defense: {self.name} Total Defensive Run Rating: {total_defense}")
        return total_defense

    def select_defense_for_pass(self):
        """Select specific defensive players to counter a pass play."""
        de = [player for player in self.players if player.position == 'DE'][:2]
        dt = [player for player in self.players if player.position == 'DT'][:2]
        lb = [player for player in self.players if player.position == 'LB'][:3]
        db = [player for player in self.players if player.position == 'DB'][:4]

        total_defense = (
            sum(de_player.tackling + de_player.pass_rush + de_player.strength + de_player.explosiveness for de_player in de) +  # DE attributes
            sum(dt_player.tackling + dt_player.pass_rush + dt_player.strength + dt_player.explosiveness for dt_player in dt) +  # DT attributes
            sum(lb_player.tackling + lb_player.pass_rush + lb_player.pass_defense + lb_player.speed + lb_player.strength + lb_player.explosiveness for lb_player in lb) +  # LB attributes
            sum(db_player.pass_rush + db_player.pass_defense + db_player.speed + db_player.athleticism + db_player.explosiveness for db_player in db)  # DB attributes
        )

        logger.debug(f"LINE 704 Pass Play Defense: {self.name} Total Defensive Pass Rating: {total_defense}")
        return total_defense

    def get_defensive_play(self):
        """Select a defensive play from the playbook."""
        return self.defensive_playbook.select_defensive_play()

# Game context and flow management
class GameContext:
    def __init__(self):
        self.teams = []
        self.clock = Clock()
        self.offensive_playbook = OffensivePlaybook("offensive_plays.json")
        self.defensive_playbook = DefensivePlaybook("defensive_plays.json")
        self.game_state = GameState(self.clock, self.defensive_playbook)
        self.current_state = None
        self.observers = []
        self.scoreboard = {}
        self.possession_team = None  # Initialize possession_team
        self.opposing_team = None  # Initialize opposing_team
        self.is_game_running = True
        self.current_state = None
        self.home_team = None
        self.away_team = None

    def get_opposing_team(self):
            """Returns the team that does not currently have possession."""
            return self.teams[1] if self.possession_team == self.teams[0] else self.teams[0]

    def reset_drive_flags(self):
        """Resets drive-ending flags at the start of each new drive."""
        self.game_state.is_turnover = False
        self.game_state.is_scoring_play = False

    def monitor_game_state(self):
        if not self.is_game_over():
            if not self.clock.is_quarter_over():
                # Perform state updates only if quarter hasn't already ended in simulate_quarter
                simulate_quarter(game_context)
            else:
                logger.debug("Quarter has already advanced, waiting for next state.")
            
            self.notify_observers({
                "team_score": self.scoring.get_team_scores(),
                "time": self.clock.get_time_remaining(),
                "possession_team": game_context.possession_team.name,  # Optional enhancement
            })
        else:
            self.is_game_running = False
            self.notify_observers({"game_over": True})

    def start_game(self):
        logger.debug("LINE 752 Game Start")
        self.current_state = FirstQuarterState(self.clock, self.defensive_playbook)
        self.notify_observers("Game Start")
        while not self.is_game_over():
            self.current_state.handle(self)
        self.notify_observers("Game Over")

    def initialize_teams(self, team1, team2, home_team, away_team):
        self.teams = [team1, team2]
        self.home_team = home_team
        self.away_team = away_team
        logger.debug("LINE 763 Teams initialized: {} vs. {}".format(team1.name, team2.name))
        self.scoreboard = {team.name: 0 for team in self.teams}
        self.scoring = Scoring(team1, team2)  # Initialize Scoring with teams now available
        self.possession_team = team1  # Start with team1 having possession
        self.opposing_team = team2    # Set opposing team as team2

    def get_team_roster(self, team_type):
        """Retrieve the roster for the specified team ('home' or 'away')."""
        if team_type == "home":
            return self.home_team.players if self.home_team else []
        elif team_type == "away":
            return self.away_team.players if self.away_team else []
        return []

    def get_returner(self, return_type):
        """
        Retrieves the appropriate return specialist for kickoffs (KR) or punts (PR).
        Falls back to a player with the highest return rating if no specialist is available.
        """
        if return_type == "KR":
            return_type_attr = "kick_returns"
        elif return_type == "PR":
            return_type_attr = "punt_returns"
        else:
            raise ValueError("Invalid return type. Use 'KR' for kickoff returner or 'PR' for punt returner.")

        # Get the opposing team based on current possession
        opposing_team = self.get_opposing_team()

        # Check if the opposing team has a designated return specialist for the given type
        for player in opposing_team.players:
            if getattr(player, "position", "") == return_type:
                return player

        # If no designated specialist, find the player with the highest return rating
        return max(opposing_team.players, key=lambda p: getattr(p, return_type_attr, 0))

    def start_drive(self):
        # Reset drive-ending flags for new drive
        self.reset_drive_flags()

        logger.debug("LINE 664 - Starting drive")
        while not self.game_state.is_drive_over():
            self.execute_play()  # Execute plays until drive ends

        logger.debug("LINE 668 - Drive over")

        # Change possession only if a drive-ending condition (turnover, punt, score) is met
        if self.game_state.is_turnover or self.game_state.is_scoring_play:
            logger.debug("LINE 672 - Changing possession in Start Drive")
            self.change_possession()  # Change possession here only once

        # Notify observers (e.g., GameGUI) about drive-related updates
        self.notify_observers({
            "drive_over": True,
            "possession_team": self.possession_team.name,
            "ball_position": self.format_field_position(self.game_state.ball_position),
            "team_score": self.scoring.get_team_scores(),
            "time": self.clock.get_time_remaining(),
        })

    def execute_play(self):
        if self.game_state.down == 4:
            # Handle fourth down plays
            logger.debug("LINE 808 - Handling fourth down")
            self.game_state.handle_fourth_down(self)
            return  # Exit as fourth down is handled by special teams or turnover

        # For regular plays
        play_type = "run" if random.random() < 0.5 else "pass"
        offense_play = self.offensive_playbook.get_play(
            self,
            self.game_state.down,
            self.game_state.yards_to_go,
            self.game_state.ball_position
        )
        logger.debug(f"LINE 820 Offense Play: {offense_play}")

        # Select the defensive play for the current play type
        defensive_play = self.opposing_team.get_defensive_play()
        logger.debug(f"LINE 824 Defensive Play: {defensive_play}")

        # Ensure `offense_play` and `defensive_play` are valid
        if offense_play:
            self.log_play_start(offense_play, defensive_play)
            yardage_gained, offense_play = self.game_state.play_down(offense_play, play_type, self)
            self.log_play_end(yardage_gained, offense_play, offense_play.play_attributes['time_cost'])
        else:
            logger.error("No valid offensive or defensive play selected.")

    def format_field_position(self, field_position):
        """Converts the internal field position to readable format based on own/ opponent half logic."""
        if field_position <= 50:
            # Increasing yardage in own half
            return f"Own {field_position}"
        else:
            # Decreasing yardage in opponent's half
            return f"Opponent {100 - field_position}"

    def log_play_start(self, offense_play, defensive_play=None):
        """Logs the details before executing a play, including the defensive play if provided."""
        offensive_team = self.possession_team.name
        defensive_team = self.teams[1].name if self.possession_team == self.teams[0] else self.teams[0].name
        down = self.game_state.down
        yards_to_go = self.game_state.yards_to_go
        display_position = self.format_field_position(self.game_state.ball_position)
        time_remaining = self.format_time_remaining(self.clock.time_remaining)

        # Handle both string and OffensivePlay object cases
        play_name = offense_play if isinstance(offense_play, str) else offense_play.name
        defense_play_name = defensive_play.name if defensive_play else "Default Defense"

        try:
            offense_rating = self.possession_team.ratings
            defense_rating = (self.away_team if self.possession_team == self.home_team else self.home_team).ratings
        except AttributeError:
            offense_rating = defense_rating = None

        logger.info(f"Starting Play - Offense Play: {play_name}, Defense Play: {defense_play_name}, "
                    f"Offensive Team: {offensive_team}, Defensive Team: {defensive_team}, Down: {down}, "
                    f"Yards to Go: {yards_to_go}, Field Position: {display_position}, Time Remaining: {time_remaining}, "
                    f"Offense Rating: {offense_rating}, Defense Rating: {defense_rating}, "
                    f"{self.scoring.display_score()}")

    def log_play_end(self, yardage, offense_play, time_cost):
        """Logs the details after a play is completed."""
        down = self.game_state.down
        yards_to_go = self.game_state.yards_to_go
        display_position = self.format_field_position(self.game_state.ball_position)
        time_remaining = self.format_time_remaining(self.clock.time_remaining)
        
        # Handle both string and OffensivePlay object cases
        play_name = offense_play if isinstance(offense_play, str) else offense_play.name

        try:
            rating_difference = self.possession_team.ratings["total"] - (
                self.away_team.ratings["total"] if self.possession_team == self.home_team else self.home_team.ratings["total"]
            )
        except KeyError:
            rating_difference = "N/A"

        logger.debug(f"LINE 972 - Log Play End")
        logger.info(f"LINE 897 Play Result - Play: {play_name}, Yardage Gained: {yardage}, "
                    f"New Down: {down}, Yards to Go: {yards_to_go}, Field Position: {display_position}, "
                    f"Time Remaining: {time_remaining}, Time Elapsed: {time_cost} seconds, "
                    f"Rating Difference: {rating_difference}, Yardage: {yardage}, "
                    f"{self.scoring.display_score()}\n")

    def format_time_remaining(self, time_remaining):
        """Formats time remaining in minutes:seconds format."""
        minutes = math.floor(time_remaining / 60)
        seconds = time_remaining % 60
        return f"{minutes}:{int(seconds):02d}"

    def change_possession(self):
        # Swap possession
        self.possession_team = self.teams[1] if self.possession_team == self.teams[0] else self.teams[0]
        self.game_state.down = 1
        self.game_state.yards_to_go = 10

    def change_state(self, new_state):
        self.current_state = new_state

    def notify_observers(self, event):
        for observer in self.observers:
            observer.update(event)

    def is_game_over(self):
        return isinstance(self.current_state, EndGameState)

    def register_observer(self, observer):
        self.observers.append(observer)

# Offensive and Defensive Strategies
class OffensiveStrategy:
    def __init__(self):
        self.ratings = self.initialize_ratings()

    def initialize_ratings(self):
        return {
            "run_offense": random.uniform(0.1, 1.0),
            "pass_offense": random.uniform(0.1, 1.0)
        }

class PassHeavyOffensiveStrategy(OffensiveStrategy):
    def execute_drive(self, offense_team, defense_strategy, game_state):
        result = self.resolve_pass_offense(offense_team, defense_strategy, game_state)
        return result

    def resolve_pass_offense(self, offense_team, defense_strategy, game_state):
        net_passing = offense_team.ratings["passing"] + offense_team.ratings["blocking"] - defense_strategy.ratings["pass_defense"]
        # Use game_state to access calculate_yardage
        return game_state.calculate_yardage(net_passing)

class RunHeavyOffensiveStrategy(OffensiveStrategy):
    def execute_drive(self, offense_team, defense_strategy, game_state):
        result = self.resolve_run_offense(offense_team, defense_strategy, game_state)
        return result

    def resolve_run_offense(self, offense_team, defense_strategy, game_state):
        net_rushing = offense_team.ratings["rushing"] + offense_team.ratings["blocking"] - defense_strategy.ratings["run_defense"]
        # Use game_state to access calculate_yardage
        return game_state.calculate_yardage(net_rushing)

# Defensive Strategies
class DefensiveStrategy:
    def __init__(self):
        self.ratings = self.initialize_ratings()

    def initialize_ratings(self):
        return {
            "run_defense": random.uniform(0.1, 1.0),
            "pass_defense": random.uniform(0.1, 1.0)
        }

class BalancedDefensiveStrategy(DefensiveStrategy):
    pass

class BlitzDefenseStrategy(DefensiveStrategy):
    pass

class OffensivePlay:
    def __init__(self, name, play_id, play_type, formation, key_player, personnel, description, play_intent, play_attributes):
        self.name = name
        self.play_id = play_id
        self.play_type = play_type
        self.formation = formation
        self.key_player = key_player
        self.personnel = personnel
        self.description = description
        self.play_intent = play_intent
        self.play_attributes = play_attributes

        # Shortcut attributes for frequent use
        self.avg_yardage = play_attributes['avg_yardage']
        self.risk_factor = play_attributes['risk_factor']
        self.time_cost = play_attributes['time_cost']

    def execute(self):
        # Calculate potential yardage based on average and risk factor
        yardage = self.avg_yardage + random.uniform(-self.risk_factor, self.risk_factor)
        return max(0, yardage)  # Ensure yardage is non-negative

class OffensivePlaybook:
    def __init__(self, play_file):
        self.plays = {
            "run": [],
            "pass": []
        }
        self.load_plays(play_file)

    def load_plays(self, play_file):
        loaded_plays = PlayLoader.load_offensive_plays(play_file)
        for play in loaded_plays:
            self.plays[play.play_type].append(play)

    def get_play(self, game_context, down, yards_to_go, field_position):
        # For first, second, and third downs, return a normal play
        if down < 4:
            offensive_play_type = "run" if random.random() < 0.5 else "pass"
            logger.debug(f"LINE 1021 Selected Play Type: {offensive_play_type}")
            return random.choice(self.plays[offensive_play_type])
        # Fourth down handling happens in play_down or execute_play
        return None

class DefensivePlay:
    def __init__(self, name, play_id, formation, linemen, def_backs, personnel, description, play_intent, play_attributes):
        self.name = name
        self.play_id = play_id
        self.formation = formation
        self.linemen = linemen
        self.def_backs = def_backs
        self.personnel = personnel
        self.description = description
        self.play_intent = play_intent
        # Accessing blitz, double_team, key_focus, and safety_blitz from play_attributes
        self.blitz = play_attributes['blitz']
        self.double_team = play_attributes['double_team']
        self.key_focus = play_attributes['key_focus']
        self.safety_blitz = play_attributes['safety_blitz']
        self.coverage = play_attributes['coverage']
        self.play_attributes = play_attributes  # Store full play_attributes for additional needs
        self.risk_factor = play_attributes['risk_factor']

    def get_modifier(self, offensive_play_type):
        """
        Determine the modifier based on the defensive setup versus the offensive play type.
        """
        modifier = 0
        # Set base modifiers for defensive fronts
        if self.front == "4-3" and offensive_play_type == "run":
            modifier += 2  # Favorable against run
        elif self.front == "3-4" and offensive_play_type == "pass":
            modifier += 2  # Favorable against pass
        
        # Adjustments based on coverage and blitz
        if offensive_play_type == "pass":
            if self.coverage == "man" and self.blitz == "heavy":
                modifier += 3  # Higher risk-reward against pass with a blitz
            elif self.coverage == "zone" and self.blitz == "none":
                modifier += 1  # Safer coverage choice
            elif self.coverage == "prevent":
                modifier += 5  # Strong against deep passes, weak vs. short gains
        elif offensive_play_type == "run":
            if self.stunt == "slant":
                modifier += 2  # Effective at limiting run gaps
            elif self.blitz == "light":
                modifier += 1  # Light pressure can control the run

        return modifier

class DefensivePlaybook:
    def __init__(self, play_file):
        self.plays = []
        self.load_plays(play_file)

    def load_plays(self, play_file):
        self.plays = PlayLoader.load_defensive_plays(play_file)

    def select_defensive_play(self):
        """Randomly selects a defensive play from the playbook."""
        return random.choice(self.plays) if self.plays else None  # Handles empty playbook case

class Clock:
    def __init__(self, quarter_length=900):
        self.time_remaining = quarter_length  # Default is 900 seconds (15 mins)

    def reset_quarter(self):
        """Resets the clock for a new quarter (15 minutes)."""
        self.time_remaining = 900  # Reset to 15 minutes in seconds

    def is_quarter_over(self):
        """Check if the quarter has ended."""
        return self.time_remaining <= 0

    def run_play_clock(self, time_elapsed):
        """Reduce the time on the clock based on play duration."""
        self.time_remaining -= time_elapsed
        if self.time_remaining < 0:
            self.time_remaining = 0  # Ensure no negative time

    def get_time_remaining(self):
        minutes = self.time_remaining // 60
        seconds = self.time_remaining % 60
        return f"{minutes}:{seconds:02d}"

class Scoring:
    def __init__(self, team1, team2):
        self.scores = {
            team1.name: [0, 0, 0, 0, 0],  # Scores for quarters 1-4, followed by total
            team2.name: [0, 0, 0, 0, 0]
        }
        self.current_quarter = 0  # Track the current quarter index (0-3)

    def register_touchdown(self, team):
        # Update only the current quarter's score
        self.scores[team.name][self.current_quarter] += 6  
        # Update total separately
        self.scores[team.name][4] = sum(self.scores[team.name][:4])  
        logger.info(f"LINE 948 - {team.name} scores a touchdown! Current Score - {self.display_score()}, Current Quarter: {self.current_quarter + 1}")

    def display_score(self):
        # Displaying score dynamically
        return f"Score - {list(self.scores.keys())[0]}: {self.scores[list(self.scores.keys())[0]]}, {list(self.scores.keys())[1]}: {self.scores[list(self.scores.keys())[1]]}"

    def touchdown(self, team_name):
        """Adds 6 points for a touchdown and sets up for an extra point or two-point attempt."""
        self.scores[team_name] += 6
        # Set up the game context to allow for extra point or two-point attempt
        return "touchdown"

    def extra_point(self, team_name, success=True):
        if success:
            self.scores[team_name][self.current_quarter] += 1
            self.scores[team_name][4] += 1
        self.is_scoring_play = True

    def two_point_conversion(self, team_name, success=True):
        if success:
            self.scores[team_name][self.current_quarter] += 2
            self.scores[team_name][4] += 2
        self.is_scoring_play = True

    def field_goal(self, team_name, success=True):
        """Adds 3 points if a field goal kick is successful."""
        if success:
            self.scores[team_name] += 3
            self.is_scoring_play = True
            return "field_goal"
        else:
            return "turnover_on_downs"  # Turnover on downs if the field goal fails

    def get_max_field_goal_range(self, kicker):
        # Map kicking_long rating to max range
        # Example scale: 1 rating = 40 yards, 7 rating = 65 yards
        return 40 + (kicker.kicking_long - 1) * 5

    def calculate_field_goal_success(self, kicker, distance):
        # Example: reduce accuracy based on distance
        # Near the max range will have much lower probability
        base_accuracy = kicker.kicking_accuracy * 0.9
        distance_factor = max(0.5, 1 - ((distance - 30) / 40))
        return base_accuracy * distance_factor  # Returns success probability

    def register_field_goal(self, team):
        # Update only the current quarter's score
        self.scores[team.name][self.current_quarter] += 3  
        # Update total separately
        self.scores[team.name][4] = sum(self.scores[team.name][:4])
        self.is_scoring_play = True  
        logger.info(f"{team.name} scores a field goal! Current Score - {self.display_score()}")

    def safety(self, scoring_team, opposing_team):
        """Adds 2 points for a safety and initiates a kick-off from the 20-yard line."""
        self.scores[scoring_team] += 2
        # Implement possession change and kick-off at the 20-yard line
        return "safety"

    def get_score(self):
        """Returns the current score of the game."""
        return self.scores
    
    def next_quarter(self):
        """Move to the next quarter, up to the fourth quarter."""
        if self.current_quarter < 3:  # Only move if within quarters 1 to 4
            self.current_quarter += 1

    def get_team_scores(self):
        """Returns the quarter-by-quarter scores for each team."""
        return [[team, scores] for team, scores in self.scores.items()]

    def display_score(self):
        return f"{list(self.scores.keys())[0]}: {self.scores[list(self.scores.keys())[0]][4]}, {list(self.scores.keys())[1]}: {self.scores[list(self.scores.keys())[1]][4]}"

class GameState:
    def __init__(self, clock, defensive_playbook):
        self.down = 1
        self.yards_to_go = 10
        self.ball_position = 20  # Starting at 20-yard line
        self.possession = None
        self.possession_team = None
        self.opposing_team = None
        self.clock = clock  # Pass in an instance of Clock
        self.defensive_playbook = defensive_playbook
        self.is_scoring_play = False
    
    defense_threshold = 85

    def play_down(self, offense_play, offensive_play_type, game_context):
        self.is_turnover = False  # Clear turnover at the start of each play
        logger.debug(f"LINE 1207 Executing play_down - Down: {self.down}, Yards to go: {self.yards_to_go}")

        if self.down == 4:
            logger.debug("LINE 1210 Fourth down, calling handle_fourth_down")
            self.handle_fourth_down(game_context)
            return  # End the play immediately after handling fourth down

        # Proceed with normal play logic
        defensive_play = game_context.opposing_team.get_defensive_play()
        logger.debug(f"Selected Defensive Play: {defensive_play.name} - {defensive_play.formation} with {defensive_play.coverage} coverage")

        offense_rating = game_context.possession_team.select_players_for_run() if offensive_play_type == "run" \
                        else game_context.possession_team.select_players_for_pass()
        defense_rating = game_context.opposing_team.select_defense_for_run() if offensive_play_type == "run" \
                        else game_context.opposing_team.select_defense_for_pass()

        # Calculate and evaluate play outcome
        yardage_gained = self.evaluate_play(offense_play, offense_rating, defense_rating)

        self.clock.run_play_clock(offense_play.play_attributes['time_cost'])
        logger.debug(f"LINE 1224 Yardage gained: {yardage_gained}")

        # Handle scoring and downs
        if self.ball_position >= 100:
            logger.info(f"LINE 1228 Touchdown! {game_context.possession_team.name} scores.")
            game_context.scoring.register_touchdown(game_context.possession_team)
            self.reset_after_score()
            return yardage_gained, offense_play

        if self.yards_to_go <= 0:
            self.new_first_down()
        else:
            self.down += 1

        # Log the end of play
        game_context.log_play_end(yardage_gained, offense_play, offense_play.play_attributes['time_cost'])
        logger.debug(f"LINE 1240 End of play - Down: {self.down}, Yards to go: {self.yards_to_go}, Ball Position: {self.ball_position}")
        return yardage_gained, offense_play

    def evaluate_play(self, offensive_play, offense_ratings, defense_ratings):
        """Evaluate the outcome of a play based on offense and defense ratings and play attributes."""
        # Access attributes from offensive_play directly
        attack_side = offensive_play.play_attributes.get('attack_side', 'center')
        guard_pull = offensive_play.play_attributes.get('guard_pull', False)
        risk_factor = offensive_play.play_attributes['risk_factor']
        avg_yardage = offensive_play.play_attributes['avg_yardage']
        play_action = offensive_play.play_attributes.get('play_action', False)

        # Calculate offensive and defensive advantages
        offensive_advantage = self.calculate_offensive_advantage(offense_ratings, attack_side, guard_pull, risk_factor, play_action)
        logger.debug(f"LINE 1265 offensive_advantage: {offensive_advantage}")

        # Determine and calculate defensive advantage based on the play type
        if offensive_play.play_type == "run":
            defensive_play = game_context.opposing_team.select_defense_for_run()
        else:
            defensive_play = game_context.opposing_team.select_defense_for_pass()

        defensive_advantage = self.calculate_defensive_advantage(offensive_play, defense_ratings, defensive_play=defensive_play)
        logger.debug(f"LINE 1273 defensive_advantage: {defensive_advantage}")

        # Calculate the yardage based on advantages and average play yardage
        logger.debug(f"LINE 1278 )self.calculate_yardage) avg_yardage: {avg_yardage}")
        return self.calculate_yardage(offensive_advantage, defensive_advantage, avg_yardage)


    def calculate_offensive_advantage(self, offense_ratings, attack_side, guard_pull, risk_factor, play_action):
        """Calculate offensive advantage based on play specifics and player ratings."""
        # Check if offense_ratings is a float (single rating) or a dictionary (multiple ratings)
        if isinstance(offense_ratings, dict):
            base_advantage = sum(offense_ratings.values()) / len(offense_ratings)
        else:
            base_advantage = offense_ratings  # Directly use the float rating

        # Apply play-specific boosts
        if guard_pull:
            base_advantage += 2
        if attack_side == 'strong':
            base_advantage += 1
        if play_action:
            base_advantage += 1.5
        logger.debug(f"LINE 1285 Offensive Base advantage: {base_advantage}")
        return base_advantage

    def calculate_defensive_advantage(self, offensive_play, defense_ratings, defensive_play):
        """Calculate defensive advantage based on the play and player ratings."""
        if isinstance(defense_ratings, dict):
            base_advantage = sum(defense_ratings.values()) / len(defense_ratings)
        else:
            base_advantage = defense_ratings

        # Ensure defensive_play is a DefensivePlay object with play_attributes
        play_attrs = defensive_play.play_attributes if isinstance(defensive_play, DefensivePlay) else {}

        # Apply play-specific defensive boosts based on attributes
        if play_attrs.get('linemen_assignment') == 'pass_rush':
            base_advantage += 2
        if play_attrs.get('lb_focus') in ['guard inside run', 'guard outside run']:
            base_advantage += 1
        if play_attrs.get('coverage') == 'man to man' and sum(play_attrs.get('blitz', {}).values()) > 0:
            base_advantage += sum(play_attrs['blitz'].values()) * 0.5
        if play_attrs.get('key_focus') == offensive_play.key_player:
            base_advantage += 2
        logger.debug(f"LINE 1307 Defensive Base advantage: {base_advantage}")
        return base_advantage


    def calculate_yardage(self, offensive_advantage, defensive_advantage, avg_yardage):
        """Calculate yardage outcome based on the advantage differential and average play yardage,
        incorporating specific outcomes like turnovers, breakaways, or losses.
        """
        differential = offensive_advantage - defensive_advantage
        logger.debug(f"Offensive Advantage: {offensive_advantage}, Defensive Advantage: {defensive_advantage}, Differential: {differential}")
        
        # Outcome-based yardage adjustments
        if differential >= 75:
            yardage_result = random.randint(50, 60)  # Long yard gain (breakaway)
        elif 60 <= differential < 75:
            yardage_result = random.randint(20, 49)  # Medium-long gain
        elif 50 <= differential < 60:
            yardage_result = random.randint(10, 19)  # Medium gain
        elif 40 <= differential < 50:
            yardage_result = random.randint(3, 9)  # Short gain
        elif 10 <= differential < 40:
            yardage_result = 0  # Incomplete or no gain
        elif -10 <= differential < 10:
            yardage_result = random.choice([-2, 0, 2])  # Stuffed at line or short loss/gain
        elif -50 <= differential < -10:
            yardage_result = -random.randint(1, 10)  # Loss of yards or sack
        elif differential < -50:
            yardage_result = -random.randint(11, 20)  # Turnover or major loss
        else:
            yardage_result = 0  # Default safety if no match

        # Adding random variability within the average yardage’s risk factor
        yardage_result += random.uniform(-1 * avg_yardage * 0.3, avg_yardage * 0.3)  # Adjust randomness to add realism
        
        # Clamp yardage to a reasonable range, e.g., max loss/gain bounds
        yardage_result = max(-20, min(yardage_result, 60))  # Limiting range for sanity

        logger.debug(f"Final Yardage Result: {yardage_result}")
        return yardage_result



    def new_first_down(self):
        self.down = 1
        self.yards_to_go = 10
        logger.debug(f"First down achieved! Ball at {self.ball_position} yard line.")

    def turnover_on_downs(self):
        # Set new down and yards to go for the team taking over
        self.down = 1
        self.yards_to_go = 10

        # Check if current position is in opponent's half
        if self.ball_position > 50:
            # Calculate the new field position relative to the team taking over
            self.ball_position = 100 - self.ball_position
        self.is_turnover = True
        # Log the turnover event
        logger.debug("LINE 1124 - Turnover on downs! Possession changes. New field position: Own {}".format(self.ball_position))

    def is_drive_over(self):
        # Check for end of drive due to quarter, turnover, or scoring play
        return (
            self.clock.is_quarter_over() or
            self.is_turnover or
            self.is_scoring_play
        )

    def reset_after_score(self):
        """Resets field position and downs after a score."""
        self.down = 1
        self.yards_to_go = 10
        self.ball_position = 20  # Place the other team at their own 20-yard line
        self.is_scoring_play = True
        logger.debug("LINE 1358 - Resetting field position and downs after a score.")

    def handle_fourth_down(self, game_context):
        logger.debug(f"LINE 1364 Handling fourth down - Yards to go: {self.yards_to_go}, Field position: {self.ball_position}")
        team_on_offense = game_context.possession_team
        field_position = self.ball_position
        kicker = team_on_offense.kicker  # Ensure a kicker is assigned with necessary attributes

        # Decide based on field position
        if field_position < 50:  # Own half
            if self.yards_to_go > 2:  # More than 2 yards to go
                logger.debug("LINE 1372 Decision: Punt")
                self.punt(game_context)
            else:
                logger.debug("LINE 1375 Decision: Go for it")
                self.go_for_it(game_context)
        else:
            fg_distance = 100 - field_position + 17
            if fg_distance <= game_context.scoring.get_max_field_goal_range(kicker):
                success_prob = game_context.scoring.calculate_field_goal_success(kicker, fg_distance)
                if success_prob >= 0.7:
                    logger.debug(f"LINE 1382 Decision: Attempt field goal from {fg_distance} yards with success probability {success_prob}")
                    self.attempt_field_goal(game_context, fg_distance, success_prob)
                elif self.yards_to_go <= 2:
                    logger.debug("LINE 1385 Decision: Go for it (short distance)")
                    self.go_for_it(game_context)
            else:
                logger.debug("LINE 1388 Decision: Punt (no other option viable)")
                self.punt(game_context)

    def kickoff(self, game_context):
        # Set the initial kickoff position at the kicking team's 30-yard line
        self.ball_position = 30

        # Determine the kicker and kickoff distance based on kicker's rating
        kicker = game_context.possession_team.kicker
        kickoff_distance = max(50, min(75, round(kicker.kicking_kickoffs * 0.8)))  # Typical range for kickoffs

        # Update ball position based on kickoff distance
        self.ball_position += kickoff_distance
        logger.info(f"Kickoff from {game_context.possession_team.name} travels {kickoff_distance} yards to {self.ball_position} yard line.")

        # Adjust position for receiving team perspective
        if self.ball_position >= 100:
            # Touchback scenario
            self.ball_position = 20  # Receiving team starts at their own 20
            logger.info("Kickoff results in a touchback. Ball placed at the receiving team's own 20-yard line.")
        elif self.ball_position > 50:
            # Flip to receiving team’s perspective (Own half)
            self.ball_position = 100 - self.ball_position
            logger.info(f"Kickoff lands at the receiving team's own {self.ball_position} yard line.")

        # Handle the kickoff return
        self.handle_kickoff_return(game_context)

    def handle_kickoff_return(self, game_context):
        # Determine the kick returner based on the team's roster
        returner = game_context.get_returner("KR")

        # Calculate return distance based on returner's kick_return rating
        return_yards = max(10, min(50, round(returner.kick_returns * 0.5)))  # Typical return range

        # Update ball position based on the return distance
        self.ball_position += return_yards
        logger.info(f"LINE 1422 Kickoff return by {returner.name} for {return_yards} yards. Ball now at the {game_context.format_field_position(self.ball_position)} yard line.")

        # Finalize possession change to the receiving team after the return
        self.is_turnover = True  # Signal that possession has officially changed post-return

    def attempt_field_goal(self, game_context, distance, success_prob):
        if random.random() <= success_prob:
            # Successful field goal
            game_context.scoring.register_field_goal(game_context.possession_team)
            logger.info(f"Field goal successful from {distance} yards!")
            self.is_scoring_play = True  # Drive ends with a score

            # Trigger kickoff after successful field goal
            self.kickoff(game_context)  
            return "successful_field_goal"

        else:
            # Missed field goal logic
            if distance <= 20:
                # Ball is placed at the 20-yard line if the attempt was from 20 yards or closer
                self.ball_position = 20
            else:
                # Ball is placed at the spot of the kick if further than 20 yards
                self.ball_position = 100 - distance

            logger.info(f"Field goal missed from {distance} yards! Opponent takes possession at the {game_context.format_field_position(self.ball_position)} yard line.")
            self.is_turnover = True  # Mark as a turnover
            return "missed_field_goal"

    def punt(self, game_context):
        # Retrieve punter attributes
        punter = game_context.possession_team.punter
        punt_distance = max(30, min(50, round(punter.punting_long * 10)))  # Between 30 and 50 yards

        # Calculate the new field position based on punt distance
        new_position = self.ball_position + punt_distance
        logger.debug(f"LINE 1458 self.ball_position: {self.ball_position} + punt_distance: {punt_distance} = new_position: {new_position}")

        if new_position >= 100:
            # Punt reaches or exceeds the opponent’s end zone (touchback scenario)
            self.ball_position = 20  # Receiving team starts from their own 20-yard line
            logger.debug("LINE 1463 Punt results in a touchback. Ball placed at the opponent's own 20-yard line.")
        else:
            # Adjust field position to reflect the new team's own half after the punt
            opponent_position = 100 - new_position  # Translate to "opponent's own half"
            self.ball_position = opponent_position
            logger.debug(f"LINE 1468 Punt goes {punt_distance} yards to the opponent's {game_context.format_field_position(self.ball_position)} yard line.")

        self.is_turnover = True
        return "punt_executed"

    def go_for_it(self, game_context):
        # Execute a normal play; if successful, reset downs
        if self.yards_to_go <= 0:
            self.new_first_down()
            return "conversion_successful"
        else:
            # If unsuccessful, turn over possession
            self.turnover_on_downs()
            return "turnover_on_downs"

    def handle(self, game_context):
        pass

# MAINLY FOR THE GUI
class EndQuarterState(GameState):
    def handle(self, game_context):
        # Log the end of the quarter and advance the scoring to the next quarter
        logger.debug("End of Quarter")
        game_context.scoring.next_quarter()  # Move to the next quarter in scoring
        # Transition to the appropriate quarter state
        if game_context.scoring.current_quarter == 1:
            game_context.change_state(SecondQuarterState(game_context.clock, game_context.defensive_playbook))
        elif game_context.scoring.current_quarter == 2:
            game_context.change_state(ThirdQuarterState(game_context.clock, game_context.defensive_playbook))
        elif game_context.scoring.current_quarter == 3:
            game_context.change_state(FourthQuarterState(game_context.clock, game_context.defensive_playbook))
        elif game_context.scoring.current_quarter == 4:
            game_context.change_state(EndGameState())  # End game after 4 quarters

class FirstQuarterState(GameState):
    def __init__(self, clock, defensive_playbook):
        super().__init__(clock, defensive_playbook)

    def handle(self, game_context):
        logger.debug("First quarter is starting.")
        simulate_quarter(game_context)
        game_context.change_state(SecondQuarterState(game_context.clock, game_context.defensive_playbook))

class SecondQuarterState(GameState):
    def __init__(self, clock, defensive_playbook):
        super().__init__(clock, defensive_playbook)

    def handle(self, game_context):
        logger.debug("Second quarter is starting.")
        simulate_quarter(game_context)
        game_context.change_state(HalftimeState(game_context.clock, game_context.defensive_playbook))

class HalftimeState(GameState):
    def __init__(self, clock, defensive_playbook):
        super().__init__(clock, defensive_playbook)
        
    def handle(self, game_context):
        # Log or perform any halftime adjustments here, if desired
        logger.debug("Halftime: Teams are preparing for the second half.")
        game_context.change_state(ThirdQuarterState(game_context.clock, game_context.defensive_playbook))

class ThirdQuarterState(GameState):
    def __init__(self, clock, defensive_playbook):
        super().__init__(clock, defensive_playbook)

    def handle(self, game_context):
        logger.debug("Third quarter is starting.")
        simulate_quarter(game_context)
        game_context.change_state(FourthQuarterState(game_context.clock, game_context.defensive_playbook))

class FourthQuarterState(GameState):
    def __init__(self, clock, defensive_playbook):
        super().__init__(clock, defensive_playbook)

    def handle(self, game_context):
        logger.debug("Fourth quarter is starting.")
        simulate_quarter(game_context)
        game_context.change_state(EndGameState())

class EndGameState(GameState):
    def __init__(self):
        # Skip GameState init to avoid clock and defensive_playbook requirement
        self.down = None
        self.yards_to_go = None
        self.ball_position = None
        self.possession = None
        self.clock = None
        self.defensive_playbook = None

    def handle(self, game_context):
        # End game and notify observers without further state changes
        game_context.notify_observers("Game Over")

def simulate_quarter(game_context):
    game_context.clock.reset_quarter()  # Reset quarter clock

    while not game_context.clock.is_quarter_over():
        team = game_context.possession_team
        if team is None:
            logger.error("Error: possession_team is None during simulate_quarter.")
            break

        logger.debug(f"LINE 1314 Starting drive for {team.name}")
        game_context.start_drive()

        if game_context.clock.is_quarter_over():
            break

        logger.debug(f"LINE 1325 - {team.name} drive complete.")

    logger.debug("End of quarter")
    game_context.scoring.next_quarter()  # Move this to the end of the quarter (double check i may have already done it)


# Observers for UI and Stats
class Observer:
    def update(self, event):
        pass

class StatTracker(Observer):
    def update(self, event):
        if event == "Game Start":
            logger.debug("Stat Tracking: Game started")
        elif event == "Game Over":
            logger.debug("Stat Tracking: Game ended")

class UISystem(Observer):
    def update(self, event):
        logger.debug(f"UI Update: {event}")

# Command Pattern for strategy changes
class Command:
    def execute(self):
        pass

class ChangeOffenseStrategyCommand(Command):
    def __init__(self, team, new_strategy):
        self.team = team
        self.new_strategy = new_strategy

    def execute(self):
        self.team.change_offense_strategy(self.new_strategy)

class ChangeDefenseStrategyCommand(Command):
    def __init__(self, team, new_strategy):
        self.team = team
        self.new_strategy = new_strategy

    def execute(self):
        self.team.change_defense_strategy(self.new_strategy)

class Weather:
    def __init__(self, temperature, precipitation, wind_speed):
        self.temperature = temperature
        self.precipitation = precipitation
        self.wind_speed = wind_speed

# Define constants
MAIN_WINDOW_WIDTH = 1200  # Keep the main game area at 1200 pixels
SIDEBAR_WIDTH = MAIN_WINDOW_WIDTH // 3  # Sidebar width (400 pixels)
TOTAL_WIDTH = MAIN_WINDOW_WIDTH + SIDEBAR_WIDTH  # Total screen width with the sidebar (1600 pixels)
HEIGHT = 800  # Example height, adjust as needed

# Initialize the screen with TOTAL_WIDTH to accommodate the sidebar
screen = pygame.display.set_mode((TOTAL_WIDTH, HEIGHT))

class MainView:
    def __init__(self, screen):
        self.screen = screen
        try:
            self.font = pygame.font.Font("Calibri.ttf", 30)
        except FileNotFoundError:
            self.font = pygame.font.SysFont("Arial", 30)  # Fallback to Arial if custom font is not found

    def draw_scoreboard(self, game_data):
        # Draw scoreboard within the MAIN_WINDOW_WIDTH
        pygame.draw.rect(self.screen, BLUE, (0, 0, MAIN_WINDOW_WIDTH // 2, HEIGHT // 4))

        # Define the y-offset to push the scoreboard down
        y_offset = 25

        # Column x-positions for each quarter and total score
        column_positions = {
            "team": 20,
            "q1": 300,
            "q2": 350,
            "q3": 400,
            "q4": 450,
            "total": 500
        }

        # Draw headers for quarters
        headers = ["1", "2", "3", "4", "T"]
        for idx, header in enumerate(headers):
            header_text = self.font.render(header, True, WHITE)
            self.screen.blit(header_text, (column_positions["q1"] + idx * 50, 10 + y_offset))

        # Draw each team's name and their scores with fixed spacing
        team_scores = game_data.get("team_score", [])
        for i, (team, scores) in enumerate(team_scores):
            team_text = self.font.render(f"{team}", True, WHITE)
            self.screen.blit(team_text, (column_positions["team"], 40 + i * 40 + y_offset))
            
            for j in range(4):  # Render quarters 1 to 4
                score_text = self.font.render(str(scores[j]), True, WHITE)
                score_width = score_text.get_width()
                x_position = column_positions[f"q{j+1}"] + 20 - score_width
                self.screen.blit(score_text, (x_position, 40 + i * 40 + y_offset))
            
            total_text = self.font.render(str(scores[4]), True, WHITE)
            total_width = total_text.get_width()
            x_position_total = column_positions["total"] + 20 - total_width
            self.screen.blit(total_text, (x_position_total, 40 + i * 40 + y_offset))

    def draw_game_state(self, game_data):
        """Draws the game state box on the right within MAIN_WINDOW_WIDTH."""
        pygame.draw.rect(self.screen, (128, 0, 0), (MAIN_WINDOW_WIDTH // 2, 0, MAIN_WINDOW_WIDTH // 2, HEIGHT // 4))
        time_text = self.font.render(f"Time: {game_data.get('time', '00:00')}  Quarter: {game_data.get('quarter', 1)}", True, WHITE)
        down_text = self.font.render(f"Down: {game_data.get('down', 1)}  To Go: {game_data.get('to_go', 10)}", True, WHITE)
        ball_text = self.font.render(f"Ball on {game_data.get('ball_position', 'own 20 yard line')}", True, WHITE)

        self.screen.blit(time_text, (MAIN_WINDOW_WIDTH // 2 + 20, 20))
        self.screen.blit(down_text, (MAIN_WINDOW_WIDTH // 2 + 20, 60))
        self.screen.blit(ball_text, (MAIN_WINDOW_WIDTH // 2 + 20, 100))

    def draw_field(self):
        """Draws the field within MAIN_WINDOW_WIDTH, with end zones and yard lines."""
        field_top = HEIGHT // 4
        field_bottom = HEIGHT * 3 // 4
        field_height = field_bottom - field_top
        endzone_width = 100

        pygame.draw.rect(self.screen, GREEN, (0, field_top, MAIN_WINDOW_WIDTH, field_height))
        pygame.draw.rect(self.screen, BLUE, (0, field_top, endzone_width, field_height))
        pygame.draw.rect(self.screen, BLUE, (MAIN_WINDOW_WIDTH - endzone_width, field_top, endzone_width, field_height))

        # Add "TOUCHDOWN" text in each end zone
        touchdown_text = pygame.font.Font(None, 48).render("TOUCHDOWN", True, WHITE)
        self.screen.blit(pygame.transform.rotate(touchdown_text, 90), (40, field_top + field_height // 2 - 100))
        self.screen.blit(pygame.transform.rotate(touchdown_text, -90), (MAIN_WINDOW_WIDTH - 80, field_top + field_height // 2 - 100))

        # Draw yard lines starting at the 0-yard line
        for i in range(0, 101, 10):
            x_pos = endzone_width + (MAIN_WINDOW_WIDTH - 2 * endzone_width) * i / 100
            if i != 0 and i != 100:
                yard_text = self.font.render(f"{i if i <= 50 else 100 - i}", True, WHITE)
                self.screen.blit(yard_text, (x_pos - 15, field_top + 10))
                
            pygame.draw.line(self.screen, WHITE, (x_pos, field_top), (x_pos, field_bottom))

            # Draw hash marks within the field boundaries (between 0-50)
            if i < 100:
                for j in range(1, 10):  # Draw 10 hash marks between each major yard line
                    hash_x = x_pos + j * (WIDTH - 2 * endzone_width) / 100  # Adjust hash spacing
                    pygame.draw.line(self.screen, WHITE, (hash_x, field_top + field_height * 0.25),
                                    (hash_x, field_top + field_height * 0.30))  # Top row hash marks
                    pygame.draw.line(self.screen, WHITE, (hash_x, field_bottom - field_height * 0.30),
                                    (hash_x, field_bottom - field_height * 0.25))  # Bottom row hash marks

        # Draw the white border around the entire field (including end zones)
        pygame.draw.rect(self.screen, WHITE, (0, field_top, WIDTH, field_height), width=5)


    def draw_play_by_play(self):
        """Draws the play-by-play box at the bottom within MAIN_WINDOW_WIDTH."""
        pygame.draw.rect(self.screen, BLUE, (0, HEIGHT * 3 // 4, MAIN_WINDOW_WIDTH, HEIGHT // 8))
        play_text = self.font.render("Play-by-Play: 4-3 READ STANDARD ZONE", True, YELLOW)
        self.screen.blit(play_text, (20, HEIGHT * 3 // 4 + 10))

    def render(self, game_data):
        self.draw_scoreboard(game_data)
        self.draw_game_state(game_data)
        self.draw_field()
        self.draw_play_by_play()


class SidebarView:
    def __init__(self, screen, game_context):
        self.screen = screen
        self.game_context = game_context
        self.current_screen = "main"
        try:
            self.font = pygame.font.Font("Calibri.ttf", 20)
        except FileNotFoundError:
            self.font = pygame.font.SysFont("Arial", 20)  # Fallback to Arial if custom font is not found
        self.scroll_offset = 0  # Initialize scroll offset

    def set_screen(self, screen_name):
        self.current_screen = screen_name
        self.scroll_offset = 0  # Reset scroll position when screen changes

    def handle_scroll(self, direction):
        scroll_amount = 30  # Adjusted for smoother scrolling
        roster_size = len(self.get_roster()) * 30  # Total height needed for roster
        visible_area = HEIGHT - 120  # Visible area within the sidebar
        max_scroll = max(0, roster_size - visible_area)

        if direction == "down":
            self.scroll_offset = min(self.scroll_offset + scroll_amount, max_scroll)
        elif direction == "up":
            self.scroll_offset = max(self.scroll_offset - scroll_amount, 0)

    def get_roster(self):
        """Retrieve the roster for the current team."""
        if self.current_screen == "home roster":
            return self.game_context.get_team_roster("home")
        elif self.current_screen == "away roster":
            return self.game_context.get_team_roster("away")
        return []

    def draw_sidebar(self):
        sidebar_x = MAIN_WINDOW_WIDTH
        pygame.draw.rect(self.screen, (30, 30, 30), (sidebar_x, 0, SIDEBAR_WIDTH, HEIGHT))

        title_text = self.font.render(f"{self.current_screen.capitalize()} View", True, WHITE)
        self.screen.blit(title_text, (sidebar_x + 20, 20))

        if self.current_screen in ["home roster", "away roster"]:
            roster_text = self.font.render(f"{self.current_screen.capitalize()} Roster:", True, WHITE)
            self.screen.blit(roster_text, (sidebar_x + 20, 60))
            roster = self.get_roster()
            self._draw_roster(roster, sidebar_x)

        elif self.current_screen == "stats":
            stats_text = self.font.render("First Downs: 15 | 23", True, WHITE)
            self.screen.blit(stats_text, (sidebar_x + 20, 60))
        elif self.current_screen == "options":
            options_text = self.font.render("Game Options:", True, WHITE)
            self.screen.blit(options_text, (sidebar_x + 20, 60))
        elif self.current_screen == "out_of_town":
            scores_text = self.font.render("Out-of-Town Scores:", True, WHITE)
            self.screen.blit(scores_text, (sidebar_x + 20, 60))
        elif self.current_screen == "tactics":
            tactics_text = self.font.render("Tactical Options:", True, WHITE)
            self.screen.blit(tactics_text, (sidebar_x + 20, 60))
        elif self.current_screen == "playbook":
            play_calling_text = self.font.render("Playbook:", True, WHITE)
            self.screen.blit(play_calling_text, (sidebar_x + 20, 60))
        elif self.current_screen == "quit":
            quit_text = self.font.render("Press ESC to confirm quit.", True, RED)
            self.screen.blit(quit_text, (sidebar_x + 20, 60))

    def _draw_roster(self, roster, sidebar_x):
        start_y = 100
        line_height = 30
        visible_area_height = HEIGHT - start_y - 20  # Leave some padding at bottom

        # Determine the starting index based on scroll offset
        start_index = self.scroll_offset // line_height
        end_index = min(start_index + visible_area_height // line_height + 1, len(roster))

        # Only render the visible portion of the roster
        for idx in range(start_index, end_index):
            player = roster[idx]
            player_text = self.font.render(f"{player.position} - {player.name}", True, WHITE)
            y_position = start_y + (idx - start_index) * line_height
            self.screen.blit(player_text, (sidebar_x + 20, y_position))

    def render(self):
        self.draw_sidebar()


class GameGUI:
    """Main class for managing the game GUI, including main and sidebar views."""
    def __init__(self):
        # Initialize the screen with the full width, including sidebar
        self.screen = pygame.display.set_mode((TOTAL_WIDTH, HEIGHT))
        self.main_view = MainView(self.screen)
        self.sidebar_view = SidebarView(self.screen, game_context)
        self.running = True
        self.game_data = {}  # Store game state updates here
        self.game_over = False  # New flag to track if the game is over
        self.font = pygame.font.Font(None, 36)

    def update(self, event):
        """Observer method to receive updates from GameContext."""
        if isinstance(event, dict):
            if event.get("game_over"):  # Check if the game is over
                self.game_over = True
            self.game_data.update(event)  # Update the GUI data with new game state info

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key in SIDEBAR_KEYS:
                    self.sidebar_view.set_screen(SIDEBAR_KEYS[event.key])
                elif event.key == pygame.K_ESCAPE:
                    if self.game_over:
                        self.running = False
                    else:
                        self.sidebar_view.set_screen("main")
            elif event.type == pygame.MOUSEWHEEL:
                # Add mouse wheel scrolling
                if event.y > 0:
                    self.sidebar_view.handle_scroll("up")
                else:
                    self.sidebar_view.handle_scroll("down")


    def render(self):
        # Clear screen and draw main view components
        self.screen.fill(BLACK)
        self.main_view.render(self.game_data)
        
        # Draw the sidebar on the right, occupying 1/3 of the screen
        self.sidebar_view.render()

    def run(self, game_context):
        clock = pygame.time.Clock()

        while self.running:
            self.handle_events()

            # Only advance game state if the game is still running
            if not self.game_over:
                game_context.monitor_game_state()

            # Render regardless of game state to keep final screen visible
            self.render()

            # Cap the frame rate at 30 FPS
            pygame.display.flip()
            clock.tick(30)

# Key mappings for sidebar navigation
SIDEBAR_KEYS = {
    pygame.K_s: "stats",
    pygame.K_o: "options",
    pygame.K_b: "out_of_town",
    pygame.K_t: "tactics",
    pygame.K_h: "home roster",
    pygame.K_a: "away roster",
    pygame.K_p: "playbook",
    pygame.K_q: "quit"
}

# Main Game Execution Flow
if __name__ == "__main__":
    game_context = GameContext()
    stat_tracker = StatTracker()
    ui_system = UISystem()
    game_gui = GameGUI()  # Initialize the GUI

    # Register observers
    game_context.register_observer(stat_tracker)
    game_context.register_observer(ui_system)
    game_context.register_observer(game_gui)  # Register GameGUI as an observer

    initialize_game(game_context)  # This loads teams and starts the game simulation.
    game_gui.run(game_context)  # Run the GUI's Pygame loop in parallel
