"""
HLTV.org scraper for CS2 events, matches, and player stats.
Uses curl_cffi (Chrome TLS fingerprint) to bypass Cloudflare.

Data sources:
- /results        → server-rendered match results (team names, scores, event names, match IDs)
- /matches/{id}/- → server-rendered player stats tables (K-D, ADR, KAST, Rating 3.0)
"""

import re
import json
import hashlib

from curl_cffi import requests
from bs4 import BeautifulSoup

BASE = "https://www.hltv.org"


def _stable_id(text: str, mod: int = 100000) -> int:
    """Deterministic integer ID from a string (Python hash() is randomized)."""
    digest = hashlib.md5(text.encode("utf-8")).hexdigest()
    return int(digest, 16) % mod

_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def _get(url: str, timeout: int = 25) -> str:
    resp = requests.get(
        url, impersonate="chrome124", headers=_HEADERS, timeout=timeout
    )
    resp.raise_for_status()
    return resp.text


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


# ---------------------------------------------------------------------------
# Events — extracted from /results page (server-rendered)
# ---------------------------------------------------------------------------

def get_events() -> list[dict]:
    """Fetch events from recent HLTV results. Each unique event becomes an entry."""
    # Fetch multiple pages of results to collect events
    all_results = []
    for offset in (0, 100):
        html = _get(f"{BASE}/results?offset={offset}")
        soup = _soup(html)
        all_results.extend(soup.select(".result-con"))

    # Group matches by event name
    events_map: dict[str, dict] = {}

    for rc in all_results:
        # Match ID
        match_a = rc.select_one("a.a-reset[href*='/matches/']")
        if not match_a:
            continue
        href = match_a.get("href", "")
        mm = re.match(r"/matches/(\d+)/", href)
        if not mm:
            continue
        match_id = int(mm.group(1))

        # Team names
        t1_el = rc.select_one(".team1")
        t2_el = rc.select_one(".team2")
        team1 = t1_el.get_text(strip=True) if t1_el else ""
        team2 = t2_el.get_text(strip=True) if t2_el else ""

        # Score
        score1 = score2 = None
        score_won = rc.select_one(".score-won")
        score_lost = rc.select_one(".score-lost")
        # Determine which team won
        if t1_el and "team-won" in " ".join(t1_el.parent.get("class", [])):
            if score_won:
                score1 = int(score_won.get_text(strip=True))
            if score_lost:
                score2 = int(score_lost.get_text(strip=True))
        elif t2_el and "team-won" in " ".join(t2_el.parent.get("class", [])):
            if score_lost:
                score1 = int(score_lost.get_text(strip=True))
            if score_won:
                score2 = int(score_won.get_text(strip=True))
        else:
            # Fallback: parse "1-2" format from result-score cell
            score_cell = rc.select_one(".result-score")
            if score_cell:
                score_text = score_cell.get_text(strip=True)
                parts = score_text.split("-")
                if len(parts) == 2:
                    try:
                        score1, score2 = int(parts[0]), int(parts[1])
                    except ValueError:
                        pass

        # Event name
        event_name_el = rc.select_one(".event-name")
        event_name = event_name_el.get_text(strip=True) if event_name_el else ""

        # Format
        fmt_el = rc.select_one(".map-text")
        fmt = fmt_el.get_text(strip=True) if fmt_el else ""

        if not event_name:
            continue

        if event_name not in events_map:
            events_map[event_name] = {
                "id": _stable_id(event_name),
                "name": event_name,
                "date_start": "",
                "date_end": "",
                "prize": "",
                "location": "",
                "status": "ongoing",
                "logo_url": "",
                "_matches": [],
            }

        events_map[event_name]["_matches"].append({
            "id": match_id,
            "team1": team1,
            "team2": team2,
            "score1": score1,
            "score2": score2,
            "format": fmt,
        })

    # Build final event list — sort by most matches first, remove the _matches key
    events = []
    for name, data in sorted(events_map.items(), key=lambda x: -len(x[1]["_matches"])):
        matches = data.pop("_matches")
        if len(matches) >= 2:  # Only events with 2+ matches
            data["_match_ids"] = [m["id"] for m in matches]
            events.append(data)

    return events


# ---------------------------------------------------------------------------
# Event detail — matches for a specific event
# ---------------------------------------------------------------------------

def get_event_matches(event_id: int) -> tuple[dict, list[dict]]:
    """Get event info and its matches by scraping results for this event."""
    # Fetch all results
    all_results = []
    for offset in (0, 100, 200):
        html = _get(f"{BASE}/results?offset={offset}")
        soup = _soup(html)
        all_results.extend(soup.select(".result-con"))

    event_name = ""
    matches = []
    seen_ids = set()

    for rc in all_results:
        # Match ID
        match_a = rc.select_one("a.a-reset[href*='/matches/']")
        if not match_a:
            continue
        href = match_a.get("href", "")
        mm = re.match(r"/matches/(\d+)/", href)
        if not mm:
            continue
        match_id = int(mm.group(1))

        # Event name
        event_el = rc.select_one(".event-name")
        ev_name = event_el.get_text(strip=True) if event_el else ""

        # Check if this match belongs to our event
        computed_id = _stable_id(ev_name)
        if computed_id != event_id:
            continue

        if not event_name:
            event_name = ev_name

        if match_id in seen_ids:
            continue
        seen_ids.add(match_id)

        # Team names
        t1_el = rc.select_one(".team1")
        t2_el = rc.select_one(".team2")
        team1 = t1_el.get_text(strip=True) if t1_el else ""
        team2 = t2_el.get_text(strip=True) if t2_el else ""

        # Score
        score1 = score2 = None
        score_cell = rc.select_one(".result-score")
        if score_cell:
            score_text = score_cell.get_text(strip=True)
            parts = score_text.split("-")
            if len(parts) == 2:
                try:
                    score1, score2 = int(parts[0]), int(parts[1])
                except ValueError:
                    pass

        # Format
        fmt_el = rc.select_one(".map-text")
        fmt = fmt_el.get_text(strip=True) if fmt_el else ""

        matches.append({
            "id": match_id,
            "event_id": event_id,
            "event_name": event_name,
            "team1": {"id": _stable_id(team1, 10000), "name": team1, "logo_url": ""},
            "team2": {"id": _stable_id(team2, 10000), "name": team2, "logo_url": ""},
            "score1": score1,
            "score2": score2,
            "format": fmt,
            "status": "completed" if score1 is not None else "upcoming",
            "date": "",
        })

    event = {
        "id": event_id,
        "name": event_name or f"Event #{event_id}",
        "date_start": "",
        "date_end": "",
        "prize": "",
        "location": "",
        "status": "completed",
        "logo_url": "",
    }

    return event, matches


# ---------------------------------------------------------------------------
# Match player stats — from /matches/{id}/- (server-rendered)
# ---------------------------------------------------------------------------

def _extract_player_alias(cell_text: str) -> str:
    """Extract alias from 'Real Namealias' format."""
    if not cell_text:
        return ""
    m = re.search(r"'([^']+)'", cell_text)
    if m:
        return m.group(1)
    # Fallback: last word
    words = cell_text.split()
    return words[-1] if words else cell_text


def get_match_stats(match_id: int) -> dict:
    """Fetch match player stats from the match page.
    Parses HLTV totalstats table: Player, K-D, eK-eD, Swing, ADR, eADR, KAST, eKAST, Rating 3.0
    """
    html = _get(f"{BASE}/matches/{match_id}/-")
    soup = _soup(html)

    # --- Team names ---
    team1_name = team2_name = ""
    team_els = soup.select(".teamName")
    names = [t.get_text(strip=True) for t in team_els]
    # Deduplicate
    unique_names = list(dict.fromkeys(names))
    if len(unique_names) >= 2:
        team1_name, team2_name = unique_names[0], unique_names[1]
    elif unique_names:
        team1_name = unique_names[0]

    # --- Scores (total rounds) ---
    score1 = score2 = None
    score_els = soup.select(".results-team-score")
    for s in score_els:
        text = s.get_text(strip=True)
        if text.isdigit():
            val = int(text)
            if val < 50:
                if score1 is None:
                    score1 = val
                elif score2 is None:
                    score2 = val

    # Estimate total rounds for KPR/DPR calculation
    total_rounds = 26  # default
    if score1 and score2:
        total_rounds = score1 + score2

    # --- Event info from JSON-LD ---
    event_id = 0
    event_name = ""
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.string or "")
            if isinstance(data, dict) and data.get("@type") == "SportsEvent":
                desc = data.get("description", "")
                name = data.get("name", "")
                ev_match = re.search(r"at\s+(.+?)(?:!|$)", desc or name)
                if ev_match:
                    event_name = ev_match.group(1).strip()
                ev_id_match = re.search(r"/events/(\d+)/", html)
                if ev_id_match:
                    event_id = int(ev_id_match.group(1))
        except (json.JSONDecodeError, TypeError):
            pass

    # --- Date ---
    date = ""
    date_m = re.search(
        r"(\d{1,2}[a-z]{2}\s+of\s+(?:January|February|March|April|May|June|"
        r"July|August|September|October|November|December)[a-z]*\s+\d{4})",
        soup.get_text(),
    )
    if date_m:
        date = date_m.group(1)

    # --- Parse player stats tables ---
    team1_players = []
    team2_players = []
    current_team = 0

    # Only use the first 2 totalstats tables (team 1 all-maps, team 2 all-maps)
    # HLTV has 6 tables: 2 all-maps + 2 CT-side + 2 T-side. We only want the all-maps totals.
    stats_tables = soup.select("table.totalstats")[:2]

    for table in stats_tables:
        # Determine which team from first row
        first_row = table.select_one("tr")
        if first_row:
            first_text = first_row.get_text(strip=True)
            if team1_name and team1_name in first_text:
                current_team = 1
            elif team2_name and team2_name in first_text:
                current_team = 2
            elif not team1_name and current_team == 0:
                team1_name = first_text.split()[0] if first_text else "Team 1"
                current_team = 1
            elif not team2_name and current_team == 1:
                team2_name = first_text.split()[0] if first_text else "Team 2"
                current_team = 2

        for row in table.select("tr"):
            cells = row.select("td, th")
            cell_texts = [c.get_text(strip=True) for c in cells]

            # Skip header rows
            if any(t in ("K-D", "ADR", "KAST", "Rating") for t in cell_texts):
                continue
            if len(cell_texts) < 6:
                continue
            if cell_texts[0] in (team1_name, team2_name):
                continue

            # Player alias from first column
            raw_name = cell_texts[0] if cell_texts else ""
            player_name = _extract_player_alias(raw_name)
            if not player_name or len(player_name) < 2:
                continue
            if player_name.replace(".", "").replace("-", "").isdigit():
                continue

            # Parse stats using known column classes/positions
            kills = deaths = 0
            adr = kast = rating = 0.0

            for i, cell in enumerate(cells):
                classes = " ".join(cell.get("class", []))
                t = cell.get_text(strip=True)

                if "kd" in classes and "traditional-data" in classes:
                    # K-D: "55-35"
                    kd_match = re.match(r"^(\d+)\s*-\s*(\d+)$", t)
                    if kd_match:
                        kills = int(kd_match.group(1))
                        deaths = int(kd_match.group(2))
                    continue

                if "adr" in classes and "traditional-data" in classes:
                    val = float(t) if re.match(r"^\d+(?:\.\d+)?$", t) else 0
                    if 30 <= val <= 200:
                        adr = val
                    continue

                if "kast" in classes and "traditional-data" in classes:
                    val = float(t.replace("%", "")) if t.endswith("%") else 0
                    if 40 <= val <= 100:
                        kast = val
                    continue

                if "rating" in classes:
                    val = float(t) if re.match(r"^\d+\.\d+$", t) else 0
                    if 0.3 <= val <= 3.0:
                        rating = val
                    continue

            # Calculate KPR/DPR from kills/deaths and estimated rounds
            kpr = round(kills / max(total_rounds, 1), 2)
            dpr = round(deaths / max(total_rounds, 1), 2)

            player_data = {
                "player_id": _stable_id(f"{match_id}:{player_name}"),
                "player_name": player_name,
                "team_name": team1_name if current_team == 1 else team2_name,
                "rating": rating,
                "kpr": kpr,
                "dpr": dpr,
                "adr": adr,
                "kast": kast,
                "impact": rating,  # Rating 3.0 as proxy; Impact not in this table
                "kills": kills,
                "deaths": deaths,
                "plus_minus": kills - deaths,
                "hs_percent": 0,  # Not in this table
            }

            if current_team == 1:
                team1_players.append(player_data)
            elif current_team == 2:
                team2_players.append(player_data)

    # --- Post-process: calculate relative KPR/DPR within each team ---
    # Uses fraction of team's total kills/deaths for better radar visualization
    for players in (team1_players, team2_players):
        if not players:
            continue
        total_kills = sum(p["kills"] for p in players) or 1
        total_deaths = sum(p["deaths"] for p in players) or 1
        for p in players:
            p["kpr"] = round(p["kills"] / total_kills * 4, 2)  # scale to ~0-1 range
            p["dpr"] = round(p["deaths"] / total_deaths * 4, 2)

    # If team2_players is empty, try splitting by team_name
    if not team2_players and team1_players and team2_name:
        t1_names = set()
        t2_names = set()
        for p in team1_players:
            if p["team_name"] == team1_name:
                t1_names.add(p["player_name"])
            else:
                t2_names.add(p["player_name"])
        if t2_names:
            team2_players = [p for p in team1_players if p["player_name"] in t2_names]
            team1_players = [p for p in team1_players if p["player_name"] in t1_names]

    return {
        "match": {
            "id": match_id,
            "event_id": event_id,
            "event_name": event_name,
            "team1": {"id": _stable_id(team1_name, 10000), "name": team1_name, "logo_url": ""},
            "team2": {"id": _stable_id(team2_name, 10000), "name": team2_name, "logo_url": ""},
            "score1": score1,
            "score2": score2,
            "format": "",
            "status": "completed",
            "date": date,
        },
        "team1_players": team1_players,
        "team2_players": team2_players,
    }
