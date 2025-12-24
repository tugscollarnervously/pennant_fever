# NPB Boxscore Data Pipeline

A three-stage pipeline for scraping, converting, and storing NPB (Nippon Professional Baseball) boxscore data from 2689web.com.

## Overview

```
┌─────────────────────┐     ┌─────────────────────┐     ┌─────────────────────┐
│  parse2689boxscores │     │ npb_boxscore_       │     │ npb_csv_to_sqlite   │
│       v6a.py        │ ──▶ │    converter.py     │ ──▶ │        .py          │
│                     │     │                     │     │                     │
│  HTML → XLSX        │     │  XLSX → CSV         │     │  CSV → SQLite       │
└─────────────────────┘     └─────────────────────┘     └─────────────────────┘
```

**Data Flow:**
1. **Scraper** fetches boxscores from 2689web.com → Excel files
2. **Converter** normalizes Excel data → standardized CSVs
3. **Loader** imports CSVs → queryable SQLite database

---

## Stage 1: Boxscore Scraper (`parse2689boxscoresv6a.py`)

### Purpose
Scrapes NPB boxscore HTML pages from 2689web.com and converts them to structured Excel files.

### Usage
```bash
python parse2689boxscoresv6a.py
```

Edit the script to configure:
- `BASE_URL` - the 2689web.com URL pattern
- `OUTPUT_DIR` - where to save Excel files
- Team/year range to scrape

### What It Extracts

| Section | Data |
|---------|------|
| **Game Info** | Date, game number, stadium, attendance |
| **Linescore** | Inning-by-inning scores (from image filenames) |
| **Batting** | Position, name, AB, H, R, K, BB, SB, E, AVG, HR |
| **Pitching** | Decision, name, IP, BF, H, K, BB, ER, E, W-L-S, ERA |
| **Home Runs** | Team, batter, pitcher, season HR number |
| **Extra-Base Hits** | Team side, hit type (2B/3B), player names |

### Key Technical Details

**Encoding:** Pages use Shift_JIS encoding (Japanese legacy encoding)

**HTML Structure:**
- Game info: `<div class="data-pa">` (Pacific League) or `<div class="data-ce">` (Central League)
- Linescore: Scores stored as image filenames (e.g., `score/2.gif` → 2 runs)
- Batting: First `<div class="vis">` and `<div class="hom">` at top level
- Pitching: Inside `<div class="pitching">`
- Extra-base hits: Second `<div class="vis">`/`<div class="hom">` pair
- Home runs: `<div id="homerun">`

**Rowspan Handling:** Home run table uses rowspan for team names - first row has 3 cells, second row has 2.

### Potential Issues

1. **Missing CSS classes:** Historical games may use different class names by league
   - Pacific League: `data-pa`
   - Central League: `data-ce`
   - Interleague: `data-in`

2. **Stadium name variations:** New stadiums may use keywords not in detection:
   - Currently supported: 球場, ドーム, スタジアム, フィールド, パーク

3. **Rate limiting:** Be respectful when scraping - add delays between requests

4. **Character encoding:** Some older pages may have encoding issues with special characters

### Potential Enhancements

- [ ] Add command-line arguments for team/year selection
- [ ] Parallel scraping with rate limiting
- [ ] Resume capability for interrupted scrapes
- [ ] Error logging to file
- [ ] Support for playoff/Japan Series games (different URL patterns)

---

## Stage 2: Boxscore Converter (`npb_boxscore_converter.py`)

### Purpose
Converts Excel boxscores to normalized CSV files suitable for database storage.

### Usage
```bash
python npb_boxscore_converter.py \
    --input-dir npb_boxscores_test \
    --output-dir npb_csv_output \
    --glob "*.xlsx"
```

### Output Files

| File | Description | Key Fields |
|------|-------------|------------|
| `games.csv` | One row per game | game_id, date, teams, final score, stadium |
| `linescore.csv` | One row per team per inning | game_id, team_side, inning, runs |
| `batting.csv` | One row per batter appearance | game_id, player, position, stats |
| `pitching.csv` | One row per pitcher appearance | game_id, player, decision, stats |
| `home_runs.csv` | One row per HR | game_id, batter, pitcher, season_hr_number |
| `extra_base_hits.csv` | One row per 2B/3B | game_id, hit_type, player |

### Standardization Mappings

**Positions (Japanese → Standard):**
```
投→P  捕→C  一→1B  二→2B  三→3B  遊→SS  左→LF  中→CF  右→RF  指→DH
```

**Decisions:**
```
勝→W  敗→L  Ｓ/S→SV  Ｈ/H→H
```

**Sub Types:**
```
打→PH (pinch hitter)  走→PR (pinch runner)  [position]→DEF-[position]
```

**Team Names:** Maps both URL-style names (RAKUTEN) and Japanese names (楽天) to franchise codes (EAG).

### Key Technical Details

**Game ID Format:** Derived from filename (e.g., `eagles_2023_EF1.xlsx` → `eagles_2023_EF1`)

**Extra-Base Hit Counts:** Player names like "山崎2" mean "Yamazaki hit 2 doubles" - these are expanded into separate rows.

**Team Side Matching:** For home runs, Japanese team names (楽天) are mapped to romanized versions (RAKUTEN) to match against linescore team names.

### Potential Issues

1. **Team name coverage:** Historical teams may not be in the mapping
   - Solution: Add to `TEAM_MAP` and `TEAM_JP_MAP` dictionaries

2. **Position variations:** Some compound positions may not parse correctly
   - Example: `走左` (pinch runner who moved to left field)

3. **IP format:** Innings pitched stored as decimal (5.1 = 5⅓ innings)
   - Note: This is display format, not mathematical (5.1 + 0.2 ≠ 5.3)

4. **Seasonal stats:** AVG, W-L-S, ERA columns are season-to-date, not game stats

### Potential Enhancements

- [ ] Add player ID generation/linking across games
- [ ] Parse pitcher handedness from name suffixes
- [ ] Extract game result (W/L/T) for each team
- [ ] Support innings pitched as proper fractions (5.1 → 5.333)
- [ ] Add RBI extraction (currently not in boxscore)
- [ ] Stolen base details (CS, caught stealing)

---

## Stage 3: SQLite Loader (`npb_csv_to_sqlite.py`)

### Purpose
Loads CSV files into a SQLite database with proper schema, foreign keys, and indexes.

### Usage
```bash
python npb_csv_to_sqlite.py \
    --csv-dir npb_csv_output \
    --db npb_boxscores.db

# Skip sample queries
python npb_csv_to_sqlite.py \
    --csv-dir npb_csv_output \
    --db npb_boxscores.db \
    --no-sample-queries
```

### Database Schema

```sql
games (game_id PK, year, month, day, date, stadium, attendance,
       away_team, home_team, away_runs, home_runs, ...)

linescore (id PK, game_id FK, team_side, inning, runs)

batting (id PK, game_id FK, team_side, lineup_slot, player_name_jp,
         position, is_starter, sub_type, ab, h, r, k, bb, sb, e, hr)

pitching (id PK, game_id FK, team_side, pitch_order, player_name_jp,
          decision, ip, bf, h, k, bb, er, e)

home_runs (id PK, game_id FK, team_side, batter_name_jp,
           pitcher_name_jp, season_hr_number)

extra_base_hits (id PK, game_id FK, team_side, hit_type, player_name_jp)
```

### Indexes
- `games`: year, date, teams
- `batting/pitching`: game_id, player_name_jp
- `home_runs`: game_id, batter_name_jp
- `extra_base_hits`: game_id, player_name_jp

### Sample Queries

**Games by year:**
```sql
SELECT year, COUNT(*) as games,
       ROUND(AVG(away_runs + home_runs), 1) as avg_runs_per_game
FROM games GROUP BY year;
```

**Home run leaders:**
```sql
SELECT batter_name_jp, COUNT(*) as hr_count
FROM home_runs
GROUP BY batter_name_jp
ORDER BY hr_count DESC LIMIT 10;
```

**Batting average leaders (min 50 AB):**
```sql
SELECT player_name_jp,
       SUM(h) as hits, SUM(ab) as at_bats,
       ROUND(CAST(SUM(h) AS FLOAT) / SUM(ab), 3) as avg
FROM batting
GROUP BY player_name_jp
HAVING SUM(ab) >= 50
ORDER BY avg DESC LIMIT 10;
```

**Team records:**
```sql
SELECT
    home_team as team,
    SUM(CASE WHEN home_runs > away_runs THEN 1 ELSE 0 END) as wins,
    SUM(CASE WHEN home_runs < away_runs THEN 1 ELSE 0 END) as losses
FROM games
GROUP BY home_team;
```

### Potential Issues

1. **Re-import behavior:** Currently deletes and re-inserts all data except games table
   - Games table uses `INSERT OR REPLACE` to preserve game_id

2. **Player name matching:** Same player may appear with different name formats
   - Example: 田中　将大 vs 田中将大 (with/without full-width space)

3. **No player master table:** Players identified only by Japanese name per game

### Potential Enhancements

- [ ] Create players master table with unique IDs
- [ ] Add team standings views
- [ ] Calculate advanced stats (OPS, WHIP, ERA)
- [ ] Add win probability / leverage index
- [ ] Support incremental updates (append new games only)
- [ ] Add data validation / integrity checks
- [ ] Export to other formats (Parquet, JSON)

---

## Quick Start

```bash
# 1. Scrape boxscores (edit script first to configure)
python parse2689boxscoresv6a.py

# 2. Convert to CSV
python npb_boxscore_converter.py \
    --input-dir npb_boxscores \
    --output-dir npb_csv_output

# 3. Load into SQLite
python npb_csv_to_sqlite.py \
    --csv-dir npb_csv_output \
    --db npb_boxscores.db

# 4. Query the database
sqlite3 npb_boxscores.db "SELECT * FROM games LIMIT 5;"
```

---

## File Naming Convention

Excel files should follow the pattern:
```
{team}_{year}_{series}{game_number}.xlsx
```

Examples:
- `eagles_2023_EF1.xlsx` - Eagles 2023, vs Fighters, game 1
- `giants_1960_GS3.xlsx` - Giants 1960, vs Swallows, game 3
- `lions_1980_LH2.xlsx` - Lions 1980, vs Hawks, game 2

---

## Dependencies

```bash
pip install openpyxl beautifulsoup4 requests
```

SQLite is included with Python standard library.

---

## Historical Team Reference

| Current Name | Historical Names | Code |
|--------------|------------------|------|
| Orix Buffaloes | BlueWave, Braves, Hankyu, Kintetsu | BUF/BRV |
| Fukuoka SoftBank Hawks | Daiei Hawks, Nankai Hawks | HAW |
| Saitama Seibu Lions | Nishitetsu Lions, Taiheiyo, Crown | LIO |
| Tohoku Rakuten Golden Eagles | (est. 2005) | EAG |
| Chiba Lotte Marines | Orions | MAR |
| Hokkaido Nippon-Ham Fighters | Toei Flyers, Nittaku | FIG |
| Yomiuri Giants | Kyojin | GIA |
| Hanshin Tigers | | TIG |
| Chunichi Dragons | | DRA |
| Yokohama DeNA BayStars | Whales, Taiyo | BAY |
| Tokyo Yakult Swallows | Kokutetsu (National Railway) | SWA |
| Hiroshima Toyo Carp | | CAR |
