
import os
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from openpyxl import Workbook


def find_game_info(soup: BeautifulSoup) -> str | None:
    """Best-effort extraction of game info header text."""
    el = soup.find("p", class_="data-pa")
    if el:
        return el.get_text(strip=True)

    el = soup.find("p", class_="data-in")
    if el:
        return el.get_text(strip=True)

    header = soup.find("h1", string=re.compile("vs"))
    if header:
        return header.get_text(strip=True)

    return None


def parse_homeruns(soup: BeautifulSoup) -> dict[str, int]:
    """
    Robust HR parser for 2689web pages across eras.

    Returns dict: { hitter_name: HR_in_game }

    IMPORTANT: Use BeautifulSoup callable search correctly (do NOT pass the callable
    as the 2nd positional arg to .find, which is interpreted as attrs).
    """
    hr_count: dict[str, int] = {}

    # Find a <tr> that contains 本塁打 somewhere in its text.
    tr = soup.find(lambda tag: getattr(tag, "name", None) == "tr" and "本塁打" in tag.get_text(strip=True))
    if tr is None:
        return hr_count

    table = tr.find_parent("table")
    if table is None:
        return hr_count

    # Example token: 王7号(今井)
    pat = re.compile(r"^(?P<hitter>.+?)(?P<num>\d+)号\((?P<pitcher>.+?)\)$")

    for row in table.find_all("tr"):
        tds = [td.get_text(strip=True) for td in row.find_all("td")]
        if len(tds) < 2:
            continue

        text = tds[-1]
        if not text or text == "なし":
            continue
        if "号" not in text or "(" not in text:
            continue

        tokens = [x.strip() for x in text.split("、") if x.strip()]
        for token in tokens:
            token = token.replace(" ", "").replace("\u3000", "")
            m = pat.match(token)
            if not m:
                continue
            hitter = m.group("hitter").strip()
            hr_count[hitter] = hr_count.get(hitter, 0) + 1

    return hr_count


def is_probable_batting_row(row_values: list[str]) -> bool:
    """
    Heuristic: batting rows are typically 12 columns and AB (index 3) is an integer.
    """
    if len(row_values) < 12:
        return False
    player = row_values[2].strip() if len(row_values) > 2 else ""
    ab = row_values[3].strip() if len(row_values) > 3 else ""
    return bool(player) and bool(re.fullmatch(r"-?\d+", ab))


def download_and_save_boxscore(url_suffix: str, filename: str, parent_url: str, debug: bool = False) -> None:
    boxscore_url = urljoin(parent_url, url_suffix)

    resp = requests.get(boxscore_url, timeout=30)
    resp.encoding = "Shift_JIS"
    print(f"Fetching URL: {boxscore_url}, Status: {resp.status_code}")

    if resp.status_code != 200:
        print(f"Failed to fetch {boxscore_url}")
        return

    soup = BeautifulSoup(resp.text, "lxml")

    hr_count_map = parse_homeruns(soup)
    if debug:
        print("HR MAP:", hr_count_map)

    wb = Workbook()
    ws = wb.active
    ws.title = "Boxscore"

    game_info = find_game_info(soup)
    ws.append(["Game Info", game_info or "NOT FOUND"])

    # Batting header (AVG is season-to-date; HR will be overwritten to GAME HR)
    ws.append([
        "Position", "Sub", "Player", "At Bats", "Hits", "Runs",
        "Strikeouts", "Walks", "Steals", "Errors",
        "Batting Average (Season)", "Home Runs (Game)"
    ])

    for team_type in ["vis", "hom"]:
        divs = soup.find_all("div", class_=team_type)
        for div in divs:
            ws.append([])  # separator

            table = div.find("table")
            if not table:
                continue

            rows = table.find_all("tr")
            for i, row in enumerate(rows):
                if i == 0:
                    continue  # skip header

                row_values = [td.get_text(strip=True) for td in row.find_all("td")]
                if not row_values:
                    continue

                # Handle colspan label rows
                first_cell = row.find("td")
                if first_cell and first_cell.has_attr("colspan"):
                    try:
                        colspan_count = int(first_cell["colspan"])
                        row_values = [""] * (colspan_count - 1) + row_values
                    except Exception:
                        pass

                # Overwrite HR for batting-shaped rows
                if is_probable_batting_row(row_values):
                    player = row_values[2].replace("\u3000", " ").strip()
                    row_values[11] = str(hr_count_map.get(player, 0))

                ws.append(row_values)

    os.makedirs(os.path.dirname(filename), exist_ok=True)
    wb.save(filename)


def main():
    # ---- USER CONFIG ----
    directory = "/Users/sputnik69/Documents/npb_boxscores"
    team_page_name = "orions.html"
    team_prefix = "orions"
    year_start = 1990
    year_end_inclusive = 1990
    debug = True
    # ---------------------

    for year in range(year_start, year_end_inclusive + 1):
        parent_url = f"https://2689web.com/{year}/{team_page_name}"

        response = requests.get(parent_url, timeout=30)
        response.encoding = "Shift_JIS"
        parent_soup = BeautifulSoup(response.text, "lxml")

        all_tables = parent_soup.find_all("table")
        result_tables = [t for t in all_tables if t.find("a", href=True)]

        for table in result_tables:
            boxscore_links = table.find_all("a", href=True)
            for link in boxscore_links:
                href = link.get("href", "")
                if href.startswith("../ind/"):
                    continue

                excel_filename = os.path.join(
                    directory,
                    f"{team_prefix}_{year}_" + os.path.basename(href).replace(".html", ".xlsx"),
                )
                download_and_save_boxscore(href, excel_filename, parent_url, debug=debug)

    print("All boxscores have been processed and saved.")


if __name__ == "__main__":
    main()
