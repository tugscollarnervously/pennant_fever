#!/usr/bin/env python3
"""
npb_csv_to_sqlite.py

Load NPB boxscore CSV files into a SQLite database.
Creates proper schema with foreign keys and indexes for efficient querying.

Usage:
    python npb_csv_to_sqlite.py --csv-dir npb_csv_output --db npb_boxscores.db
"""

import argparse
import csv
import sqlite3
from pathlib import Path
from typing import List, Dict, Any


# =============================================================================
# SCHEMA DEFINITIONS
# =============================================================================

SCHEMA = """
-- Games table: one row per game
CREATE TABLE IF NOT EXISTS games (
    game_id TEXT PRIMARY KEY,
    year INTEGER,
    month INTEGER,
    day INTEGER,
    date TEXT,
    game_number INTEGER,
    stadium TEXT,
    attendance INTEGER,
    away_team TEXT,
    home_team TEXT,
    away_team_raw TEXT,
    home_team_raw TEXT,
    away_runs INTEGER,
    home_runs INTEGER,
    away_hits INTEGER,
    home_hits INTEGER,
    away_errors INTEGER,
    home_errors INTEGER,
    innings_played INTEGER
);

-- Linescore table: one row per team per inning
CREATE TABLE IF NOT EXISTS linescore (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id TEXT NOT NULL,
    team_side TEXT NOT NULL,  -- 'away' or 'home'
    inning TEXT NOT NULL,
    runs INTEGER,
    FOREIGN KEY (game_id) REFERENCES games(game_id)
);

-- Batting table: one row per batter appearance
CREATE TABLE IF NOT EXISTS batting (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id TEXT NOT NULL,
    team_side TEXT NOT NULL,
    lineup_slot INTEGER,
    player_name_jp TEXT,
    position TEXT,
    is_starter INTEGER,
    sub_type TEXT,
    ab INTEGER,
    h INTEGER,
    r INTEGER,
    k INTEGER,
    bb INTEGER,
    sb INTEGER,
    e INTEGER,
    hr INTEGER,
    FOREIGN KEY (game_id) REFERENCES games(game_id)
);

-- Pitching table: one row per pitcher appearance
CREATE TABLE IF NOT EXISTS pitching (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id TEXT NOT NULL,
    team_side TEXT NOT NULL,
    pitch_order INTEGER,
    player_name_jp TEXT,
    decision TEXT,
    ip REAL,
    bf INTEGER,
    h INTEGER,
    k INTEGER,
    bb INTEGER,
    er INTEGER,
    e INTEGER,
    FOREIGN KEY (game_id) REFERENCES games(game_id)
);

-- Home runs table: one row per HR event
CREATE TABLE IF NOT EXISTS home_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id TEXT NOT NULL,
    team_side TEXT,
    team_raw TEXT,
    batter_name_jp TEXT,
    pitcher_name_jp TEXT,
    season_hr_number INTEGER,
    FOREIGN KEY (game_id) REFERENCES games(game_id)
);

-- Extra-base hits table: one row per 2B/3B event
CREATE TABLE IF NOT EXISTS extra_base_hits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id TEXT NOT NULL,
    team_side TEXT,
    hit_type TEXT,  -- '2B' or '3B'
    player_name_jp TEXT,
    FOREIGN KEY (game_id) REFERENCES games(game_id)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_games_year ON games(year);
CREATE INDEX IF NOT EXISTS idx_games_date ON games(date);
CREATE INDEX IF NOT EXISTS idx_games_teams ON games(away_team, home_team);
CREATE INDEX IF NOT EXISTS idx_linescore_game ON linescore(game_id);
CREATE INDEX IF NOT EXISTS idx_batting_game ON batting(game_id);
CREATE INDEX IF NOT EXISTS idx_batting_player ON batting(player_name_jp);
CREATE INDEX IF NOT EXISTS idx_pitching_game ON pitching(game_id);
CREATE INDEX IF NOT EXISTS idx_pitching_player ON pitching(player_name_jp);
CREATE INDEX IF NOT EXISTS idx_hr_game ON home_runs(game_id);
CREATE INDEX IF NOT EXISTS idx_hr_batter ON home_runs(batter_name_jp);
CREATE INDEX IF NOT EXISTS idx_xbh_game ON extra_base_hits(game_id);
CREATE INDEX IF NOT EXISTS idx_xbh_player ON extra_base_hits(player_name_jp);
"""


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def safe_int(value: str) -> int | None:
    """Convert string to int, return None if empty or invalid."""
    if not value or value.strip() == '':
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def safe_float(value: str) -> float | None:
    """Convert string to float, return None if empty or invalid."""
    if not value or value.strip() == '':
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def load_csv(path: Path) -> List[Dict[str, str]]:
    """Load CSV file into list of dicts."""
    with path.open('r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        return list(reader)


# =============================================================================
# DATABASE OPERATIONS
# =============================================================================

def create_database(db_path: Path) -> sqlite3.Connection:
    """Create database and schema."""
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def insert_games(conn: sqlite3.Connection, rows: List[Dict[str, str]]):
    """Insert games data."""
    cursor = conn.cursor()
    for row in rows:
        cursor.execute("""
            INSERT OR REPLACE INTO games
            (game_id, year, month, day, date, game_number, stadium, attendance,
             away_team, home_team, away_team_raw, home_team_raw,
             away_runs, home_runs, away_hits, home_hits, away_errors, home_errors,
             innings_played)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            row['game_id'],
            safe_int(row['year']),
            safe_int(row['month']),
            safe_int(row['day']),
            row['date'],
            safe_int(row['game_number']),
            row['stadium'],
            safe_int(row['attendance']),
            row['away_team'],
            row['home_team'],
            row['away_team_raw'],
            row['home_team_raw'],
            safe_int(row['away_runs']),
            safe_int(row['home_runs']),
            safe_int(row['away_hits']),
            safe_int(row['home_hits']),
            safe_int(row['away_errors']),
            safe_int(row['home_errors']),
            safe_int(row['innings_played']),
        ))
    conn.commit()
    print(f"  Inserted {len(rows)} games")


def insert_linescore(conn: sqlite3.Connection, rows: List[Dict[str, str]]):
    """Insert linescore data."""
    cursor = conn.cursor()
    # Clear existing data first (for re-imports)
    cursor.execute("DELETE FROM linescore")
    for row in rows:
        cursor.execute("""
            INSERT INTO linescore (game_id, team_side, inning, runs)
            VALUES (?, ?, ?, ?)
        """, (
            row['game_id'],
            row['team_side'],
            row['inning'],
            safe_int(row['runs']),
        ))
    conn.commit()
    print(f"  Inserted {len(rows)} linescore rows")


def insert_batting(conn: sqlite3.Connection, rows: List[Dict[str, str]]):
    """Insert batting data."""
    cursor = conn.cursor()
    cursor.execute("DELETE FROM batting")
    for row in rows:
        cursor.execute("""
            INSERT INTO batting
            (game_id, team_side, lineup_slot, player_name_jp, position,
             is_starter, sub_type, ab, h, r, k, bb, sb, e, hr)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            row['game_id'],
            row['team_side'],
            safe_int(row['lineup_slot']),
            row['player_name_jp'],
            row['position'],
            safe_int(row['is_starter']),
            row['sub_type'],
            safe_int(row['ab']),
            safe_int(row['h']),
            safe_int(row['r']),
            safe_int(row['k']),
            safe_int(row['bb']),
            safe_int(row['sb']),
            safe_int(row['e']),
            safe_int(row['hr']),
        ))
    conn.commit()
    print(f"  Inserted {len(rows)} batting rows")


def insert_pitching(conn: sqlite3.Connection, rows: List[Dict[str, str]]):
    """Insert pitching data."""
    cursor = conn.cursor()
    cursor.execute("DELETE FROM pitching")
    for row in rows:
        cursor.execute("""
            INSERT INTO pitching
            (game_id, team_side, pitch_order, player_name_jp, decision,
             ip, bf, h, k, bb, er, e)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            row['game_id'],
            row['team_side'],
            safe_int(row['pitch_order']),
            row['player_name_jp'],
            row['decision'],
            safe_float(row['ip']),
            safe_int(row['bf']),
            safe_int(row['h']),
            safe_int(row['k']),
            safe_int(row['bb']),
            safe_int(row['er']),
            safe_int(row['e']),
        ))
    conn.commit()
    print(f"  Inserted {len(rows)} pitching rows")


def insert_home_runs(conn: sqlite3.Connection, rows: List[Dict[str, str]]):
    """Insert home runs data."""
    cursor = conn.cursor()
    cursor.execute("DELETE FROM home_runs")
    for row in rows:
        cursor.execute("""
            INSERT INTO home_runs
            (game_id, team_side, team_raw, batter_name_jp, pitcher_name_jp, season_hr_number)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            row['game_id'],
            row['team_side'],
            row['team_raw'],
            row['batter_name_jp'],
            row['pitcher_name_jp'],
            safe_int(row['season_hr_number']),
        ))
    conn.commit()
    print(f"  Inserted {len(rows)} home run rows")


def insert_extra_base_hits(conn: sqlite3.Connection, rows: List[Dict[str, str]]):
    """Insert extra-base hits data."""
    cursor = conn.cursor()
    cursor.execute("DELETE FROM extra_base_hits")
    for row in rows:
        cursor.execute("""
            INSERT INTO extra_base_hits (game_id, team_side, hit_type, player_name_jp)
            VALUES (?, ?, ?, ?)
        """, (
            row['game_id'],
            row['team_side'],
            row['hit_type'],
            row['player_name_jp'],
        ))
    conn.commit()
    print(f"  Inserted {len(rows)} extra-base hit rows")


# =============================================================================
# SAMPLE QUERIES
# =============================================================================

def run_sample_queries(conn: sqlite3.Connection):
    """Run some sample queries to demonstrate the database."""
    print("\n" + "="*60)
    print("SAMPLE QUERIES")
    print("="*60)

    cursor = conn.cursor()

    # 1. Games summary by year
    print("\n1. Games by year:")
    cursor.execute("""
        SELECT year, COUNT(*) as games,
               SUM(away_runs + home_runs) as total_runs,
               ROUND(AVG(away_runs + home_runs), 1) as avg_runs_per_game
        FROM games
        GROUP BY year
        ORDER BY year
    """)
    for row in cursor.fetchall():
        print(f"   {row[0]}: {row[1]} games, {row[2]} total runs, {row[3]} avg/game")

    # 2. Top HR hitters
    print("\n2. Top home run hitters:")
    cursor.execute("""
        SELECT batter_name_jp, COUNT(*) as hr_count
        FROM home_runs
        GROUP BY batter_name_jp
        ORDER BY hr_count DESC
        LIMIT 5
    """)
    for row in cursor.fetchall():
        print(f"   {row[0]}: {row[1]} HR")

    # 3. Pitching leaders (by strikeouts)
    print("\n3. Top pitchers by strikeouts:")
    cursor.execute("""
        SELECT player_name_jp, SUM(k) as total_k,
               ROUND(SUM(ip), 1) as total_ip,
               COUNT(*) as appearances
        FROM pitching
        GROUP BY player_name_jp
        HAVING total_ip > 5
        ORDER BY total_k DESC
        LIMIT 5
    """)
    for row in cursor.fetchall():
        print(f"   {row[0]}: {row[1]} K in {row[2]} IP ({row[3]} appearances)")

    # 4. Batting averages (min 10 AB)
    print("\n4. Top batting averages (min 10 AB):")
    cursor.execute("""
        SELECT player_name_jp,
               SUM(h) as hits,
               SUM(ab) as at_bats,
               ROUND(CAST(SUM(h) AS FLOAT) / SUM(ab), 3) as avg
        FROM batting
        GROUP BY player_name_jp
        HAVING SUM(ab) >= 10
        ORDER BY avg DESC
        LIMIT 5
    """)
    for row in cursor.fetchall():
        print(f"   {row[0]}: {row[1]}/{row[2]} ({row[3]})")

    # 5. Extra-base hits leaders
    print("\n5. Extra-base hit leaders:")
    cursor.execute("""
        SELECT player_name_jp,
               SUM(CASE WHEN hit_type = '2B' THEN 1 ELSE 0 END) as doubles,
               SUM(CASE WHEN hit_type = '3B' THEN 1 ELSE 0 END) as triples,
               COUNT(*) as total_xbh
        FROM extra_base_hits
        GROUP BY player_name_jp
        ORDER BY total_xbh DESC
        LIMIT 5
    """)
    for row in cursor.fetchall():
        print(f"   {row[0]}: {row[1]} 2B, {row[2]} 3B ({row[3]} total)")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description='Load NPB CSV files into SQLite')
    parser.add_argument('--csv-dir', required=True, help='Directory containing CSV files')
    parser.add_argument('--db', required=True, help='Output SQLite database file')
    parser.add_argument('--no-sample-queries', action='store_true', help='Skip sample queries')
    args = parser.parse_args()

    csv_dir = Path(args.csv_dir)
    db_path = Path(args.db)

    print(f"Creating database: {db_path}")
    conn = create_database(db_path)

    print(f"Loading CSV files from: {csv_dir}")

    # Load each CSV
    csv_files = {
        'games.csv': insert_games,
        'linescore.csv': insert_linescore,
        'batting.csv': insert_batting,
        'pitching.csv': insert_pitching,
        'home_runs.csv': insert_home_runs,
        'extra_base_hits.csv': insert_extra_base_hits,
    }

    for filename, insert_func in csv_files.items():
        path = csv_dir / filename
        if path.exists():
            rows = load_csv(path)
            insert_func(conn, rows)
        else:
            print(f"  WARNING: {filename} not found")

    if not args.no_sample_queries:
        run_sample_queries(conn)

    conn.close()
    print(f"\nDatabase created: {db_path}")


if __name__ == '__main__':
    main()
