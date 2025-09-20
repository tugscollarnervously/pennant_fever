from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# Define your PostgreSQL database URL
DATABASE_URL = "postgresql://postgres:bacon@localhost:5432/pennant_race"

# Set up SQLAlchemy base and engine
Base = declarative_base()
engine = create_engine(DATABASE_URL)

# Session maker for handling database sessions
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Example Player model (table) definition
class Player(Base):
    __tablename__ = "players"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    position = Column(String)
    team_id = Column(Integer, ForeignKey("teams.id"))

# Example Team model (table) definition
class Team(Base):
    __tablename__ = "teams"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    city = Column(String)
    players = relationship("Player", back_populates="team")

Player.team = relationship("Team", back_populates="players")

# Create the database tables (initial setup)
def create_database():
    Base.metadata.create_all(bind=engine)

# Function to drop tables (for maintenance purposes)
def drop_database():
    Base.metadata.drop_all(bind=engine)

# Example of adding a player to the database
def add_player(session, name, position, team):
    new_player = Player(name=name, position=position, team=team)
    session.add(new_player)
    session.commit()

# Example of modifying a player (changing their team)
def modify_player_team(session, player_id, new_team_id):
    player = session.query(Player).filter(Player.id == player_id).first()
    if player:
        player.team_id = new_team_id
        session.commit()

# Example usage of the script for adding a team and players
def main():
    # Create tables
    create_database()

    # Create a session
    session = SessionLocal()

    # Example: Add a team
    team = Team(name="Eagles", city="Philadelphia")
    session.add(team)
    session.commit()

    # Example: Add players
    add_player(session, name="John Doe", position="Quarterback", team=team)
    add_player(session, name="Mike Smith", position="Running Back", team=team)

    # Modify a player's team
    modify_player_team(session, player_id=1, new_team_id=2)

    # Close the session
    session.close()

if __name__ == "__main__":
    main()
