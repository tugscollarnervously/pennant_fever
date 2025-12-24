import requests
from bs4 import BeautifulSoup
from openpyxl import Workbook
import os
import re

def find_game_info(soup):
    # Try finding the game info with various class names used across different eras
    for class_name in ['data-pa', 'data-in', 'data-ce']:
        game_info_element = soup.find('p', class_=class_name)
        if game_info_element:
            return game_info_element.text.strip()

    # Check if game info is within a header tag, etc.
    header_element = soup.find('h1', string=re.compile('vs'))
    if header_element:
        return header_element.text.strip()

    # Return None if nothing is found
    return None


def find_linescore(soup):
    """Extract inning-by-inning linescore from the board1 table."""
    linescore = {'header': [], 'visitor': [], 'home': []}

    board = soup.find('table', class_='board1')
    if not board:
        return None

    rows = board.find_all('tr')
    for i, row in enumerate(rows):
        cells = row.find_all('td')
        row_data = []

        for cell in cells:
            # Check if cell contains an image (score value)
            img = cell.find('img')
            if img and img.get('src'):
                # Extract value from image filename (e.g., "../../score/2.gif" -> "2")
                src = img['src']
                if '/score/' in src:
                    # Get filename without extension
                    value = src.split('/')[-1].replace('.gif', '')
                    row_data.append(value)
                elif '/team/' in src:
                    # Team logo - get team name from cell class
                    team_class = cell.get('class', [''])[0] if cell.get('class') else ''
                    row_data.append(team_class.upper() if team_class else 'TEAM')
            else:
                # Regular text cell
                text = cell.text.strip()
                # Skip the "..." separator
                if text and text != '…':
                    row_data.append(text)

        if i == 0:
            linescore['header'] = row_data
        elif i == 1:
            linescore['visitor'] = row_data
        elif i == 2:
            linescore['home'] = row_data

    return linescore


def find_home_runs(soup):
    """Extract home run data from the homerun div section."""
    home_runs = []

    homerun_div = soup.find('div', id='homerun')
    if not homerun_div:
        return home_runs

    # Find all tables with class 'stat2' in the homerun div
    tables = homerun_div.find_all('table', class_='stat2')

    for table in tables:
        # Look for the table containing 本塁打 (home runs)
        if table.find(string=lambda t: t and '本塁打' in t):
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 2:
                    # First row has 3 cells: [本塁打, team, HRs]
                    # Second row has 2 cells: [team, HRs] (due to rowspan)
                    if len(cells) == 3:
                        # First row with 本塁打 label
                        team_name = cells[1].text.strip()
                        hr_details = cells[2].text.strip()
                    else:
                        # Second row (rowspan means no 本塁打 cell)
                        team_name = cells[0].text.strip()
                        hr_details = cells[1].text.strip()

                    # Skip if team name is the label itself
                    if team_name and team_name != '本塁打':
                        home_runs.append({
                            'team': team_name,
                            'details': hr_details
                        })

    return home_runs

def download_and_save_boxscore(url_suffix, filename, parent_url):
    # Use the parent URL directly to handle the base directory construction
    base_url = os.path.dirname(parent_url)

    # Check if the URL needs specific handling for 'inter/' URLs
    if 'inter/' in url_suffix:
        # If the suffix contains 'inter/', we do not need to append the year again
        boxscore_url = os.path.join(base_url, url_suffix)
    else:
        # Standard URL formation for other URLs
        boxscore_url = os.path.join(base_url, url_suffix)

    # Complete URL for the boxscore page
    boxscore_url = os.path.join(base_url, url_suffix)

    # Complete URL for the boxscore page
    # boxscore_url = os.path.join(os.path.dirname(parent_url), url_suffix)
    
    # Fetch the boxscore page
    boxscore_response = requests.get(boxscore_url)
    boxscore_response.encoding = 'Shift_JIS'
    print(f"Fetching URL: {boxscore_url}, Status: {boxscore_response.status_code}")

    if boxscore_response.status_code == 200:
        soup = BeautifulSoup(boxscore_response.text, 'lxml')
        
        # Create a workbook and select active worksheet
        wb = Workbook()
        ws = wb.active
        
        # Extract the game date and location
        # Inside your existing function where you parse the game info:
        game_info = find_game_info(soup)
        if game_info:
            ws.append(['Game Info', game_info])
        else:
            print(f"Game info not found for {boxscore_url}")

        # Extract and write linescore (inning-by-inning)
        linescore = find_linescore(soup)
        if linescore:
            ws.append([])  # Blank row
            ws.append(['Linescore'])
            ws.append(linescore['header'])
            ws.append(linescore['visitor'])
            ws.append(linescore['home'])

        # Batting headers
        batting_headers = ['Pos', 'Sub', 'Name', 'AB', 'H', 'R', 'K', 'BB', 'SB', 'E', 'AVG', 'HR']

        # Store extra-base hits for later
        extra_base_hits = {'vis': [], 'hom': []}

        # Process batting stats (top-level vis/hom divs, not inside pitching div)
        for team_type in ['vis', 'hom']:
            # Find divs that are NOT inside the pitching section
            all_divs = [d for d in soup.find_all('div', class_=team_type)
                        if not d.find_parent('div', class_='pitching')]

            for idx, div in enumerate(all_divs):
                table = div.find('table')
                if not table:
                    continue

                # First div (idx=0) is batting stats, second div (idx=1) is extra-base hits
                if idx == 0:
                    # Main batting table
                    ws.append([])  # Blank row for separation
                    team_label = 'Visitor Batting' if team_type == 'vis' else 'Home Batting'
                    ws.append([team_label])
                    ws.append(batting_headers)
                    rows = table.find_all('tr')
                    for i, row in enumerate(rows):
                        if i == 0:  # Skip team name row
                            continue
                        if i == 1:  # Skip Japanese header row
                            continue
                        stats = [td.text.strip() for td in row.find_all('td')]
                        first_cell = row.find('td')
                        if first_cell and first_cell.has_attr('colspan'):
                            colspan_count = int(first_cell['colspan'])
                            stats = [""] * (colspan_count - 1) + stats
                        ws.append(stats)
                else:
                    # Extra-base hits table (doubles/triples)
                    rows = table.find_all('tr')
                    for row in rows:
                        cells = [td.text.strip() for td in row.find_all('td')]
                        if len(cells) >= 2:
                            extra_base_hits[team_type].append({
                                'type': cells[0],  # 三塁打 or 二塁打
                                'players': cells[1]
                            })

        # Pitching headers
        pitching_headers = ['Dec', 'Name', 'IP', 'BF', 'H', 'K', 'BB', 'ER', 'E', 'W-L-S', 'ERA']

        # Process pitching stats (inside pitching div)
        pitching_div = soup.find('div', class_='pitching')
        if pitching_div:
            for team_type in ['vis', 'hom']:
                div = pitching_div.find('div', class_=team_type)
                if div:
                    ws.append([])  # Blank row for separation
                    team_label = 'Visitor Pitching' if team_type == 'vis' else 'Home Pitching'
                    ws.append([team_label])
                    ws.append(pitching_headers)
                    table = div.find('table')
                    if table:
                        rows = table.find_all('tr')
                        for i, row in enumerate(rows):
                            if i == 0:  # Skip Japanese header row
                                continue
                            stats = [td.text.strip() for td in row.find_all('td')]
                            first_cell = row.find('td')
                            if first_cell and first_cell.has_attr('colspan'):
                                colspan_count = int(first_cell['colspan'])
                                stats = [""] * (colspan_count - 1) + stats
                            ws.append(stats)

        # Extract and write home run data
        ws.append([])  # Blank row for separation
        ws.append(['Home Runs'])
        ws.append(['Team', 'Details'])
        home_runs = find_home_runs(soup)
        if home_runs:
            for hr in home_runs:
                ws.append([hr['team'], hr['details']])
        else:
            ws.append(['No home runs'])

        # Write extra-base hits (triples and doubles)
        ws.append([])  # Blank row for separation
        ws.append(['Extra-Base Hits'])
        ws.append(['Team', 'Type', 'Players'])
        has_extra_base = False
        for team_type, team_name in [('vis', 'Visitor'), ('hom', 'Home')]:
            for hit in extra_base_hits[team_type]:
                # Translate hit type
                hit_type = hit['type']
                if hit_type == '三塁打':
                    hit_type = '3B'
                elif hit_type == '二塁打':
                    hit_type = '2B'
                ws.append([team_name, hit_type, hit['players']])
                has_extra_base = True
        if not has_extra_base:
            ws.append(['No extra-base hits'])

        # Save the workbook
        wb.save(filename)
    else:
        print(f"Failed to fetch {boxscore_url}")

# Directory to save Excel files
directory = '/Users/sputnik69/Documents/npb_boxscores'
os.makedirs(directory, exist_ok=True)  # Ensure the directory exists

# Iterate over the seasons from 1950 to 2023
for year in range(1960, 1961):
    # URL of the parent page containing links to boxscores for each season
    parent_url = f'https://2689web.com/{year}/giants.html'
    
# Fetch and parse the parent HTML
    response = requests.get(parent_url)
    response.encoding = 'Shift_JIS'
    parent_soup = BeautifulSoup(response.text, 'lxml')
    
    # Find all tables, then filter those that contain boxscore links
    all_tables = parent_soup.find_all('table')
    result_tables = [table for table in all_tables if table.find('a', href=True)]
    
    # Process each boxscore link in every result table
    for table in result_tables:
        boxscore_links = table.find_all('a', href=True)
        for link in boxscore_links:
            if link.get('href').startswith('../ind/'):
                continue  # Skip individual player pages
            excel_filename = os.path.join(directory, f'giants_{year}_' + os.path.basename(link['href']).replace('.html', '.xlsx'))
            download_and_save_boxscore(link['href'], excel_filename, parent_url)

print("All boxscores have been processed and saved.")
