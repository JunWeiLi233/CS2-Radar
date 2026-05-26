"""
HLTV.org scraper for CS2 events, matches, player stats, and teams.
Uses curl_cffi (Chrome TLS fingerprint) to bypass Cloudflare.

Data sources (all server-rendered HTML):
- /results?offset=N        → match results: teams, scores, event names, match IDs
- /matches/{id}/-          → player stats (totalstats tables) + event links + team logos
- /events/{id}/{slug}      → event metadata: dates, prize, location, logo, teams
"""

import re
import json
import hashlib
import functools
import threading

from curl_cffi import requests
from bs4 import BeautifulSoup

BASE = "https://www.hltv.org"

_HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def _stable_id(text: str, mod: int = 100000) -> int:
    return int(hashlib.md5(text.encode("utf-8")).hexdigest(), 16) % mod


@functools.lru_cache(maxsize=256)
def _get(url: str, timeout: int = 30) -> str:
    resp = requests.get(
        url, impersonate="chrome124", headers=_HEADERS, timeout=timeout
    )
    resp.raise_for_status()
    return resp.text


def _soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


def _extract_player_alias(cell_text: str) -> str:
    if not cell_text:
        return ""
    m = re.search(r"'([^']+)'", cell_text)
    if m:
        return m.group(1)
    words = cell_text.split()
    return words[-1] if words else cell_text


def _resolve_url(path: str | None) -> str:
    if not path:
        return ""
    return path if path.startswith("http") else f"{BASE}{path}"


# ---------------------------------------------------------------------------
# Event metadata — from /events/{id}/{slug} page
# ---------------------------------------------------------------------------

def _get_event_id_and_slug(match_id: int) -> tuple[int, str]:
    """Get the real event ID and slug from a match page.
    Uses frequency count: the event linked most often is the correct one.
    """
    try:
        html = _get(f"{BASE}/matches/{match_id}/-")
        soup = _soup(html)
        from collections import Counter
        counts: Counter = Counter()
        for a in soup.select('a[href*="/events/"]'):
            href = a.get("href", "")
            m = re.match(r"/events/(\d+)/([^#?]+)", href)
            if m and "archive" not in href:
                counts[(int(m.group(1)), m.group(2))] += 1
        if counts:
            return counts.most_common(1)[0][0]
    except Exception:
        pass
    return 0, ""


def _fetch_event_meta(event_id: int, slug: str) -> dict:
    """Fetch event metadata from its HLTV page."""
    meta = {"date_start": "", "date_end": "", "prize": "", "location": "", "logo_url": ""}
    if not event_id or not slug:
        return meta

    try:
        html = _get(f"{BASE}/events/{event_id}/{slug}")
        soup = _soup(html)

        # Logo from og:image
        og_img = soup.select_one('meta[property="og:image"]')
        if og_img:
            meta["logo_url"] = og_img.get("content", "")

        full_text = soup.get_text()

        # Date range
        date_m = re.search(
            r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}[a-z]*)\s*[-–]\s*"
            r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}[a-z]*)\s*,?\s*(\d{4})",
            full_text,
        )
        if date_m:
            clean = lambda s: s.replace("rd","").replace("th","").replace("st","").replace("nd","")
            meta["date_start"] = clean(date_m.group(1)) + " " + date_m.group(3)
            meta["date_end"] = clean(date_m.group(2)) + " " + date_m.group(3)

        # Prize pool
        prize_m = re.search(r'\$\d[\d,]+(?:\s*(?:million|M))?', full_text, re.IGNORECASE)
        if prize_m:
            meta["prize"] = prize_m.group(0)

        # Location (known cities)
        loc_cities = [
            "Shanghai", "Cologne", "Dallas", "Paris", "London", "Berlin", "Malta",
            "Stockholm", "Copenhagen", "Rio de Janeiro", "Bucharest", "Katowice",
            "Abu Dhabi", "Sydney", "Melbourne", "Singapore", "Lisbon", "Belgrade",
            "Vienna", "Atlanta", "New York", "Los Angeles", "Seattle", "Toronto",
            "Montreal", "Istanbul", "Dubai", "Doha", "Riyadh", "Mumbai", "Jakarta",
            "Manila", "Bangkok", "Seoul", "Tokyo", "Osaka", "Sao Paulo",
            "Buenos Aires", "Lima", "Mexico City", "Helsinki", "Oslo", "Warsaw",
            "Prague", "Budapest", "Athens", "Barcelona", "Madrid", "Rome", "Milan",
            "Amsterdam", "Brussels", "Zurich", "Recife", "Reykjavik", "Santiago",
            "Bogota", "Lagos", "Cairo", "Cape Town", "Nairobi", "Astana",
        ]
        loc_m = re.search(r"(" + "|".join(loc_cities) + r")", full_text, re.IGNORECASE)
        if loc_m:
            # Get the full location text (e.g., "Shanghai, China")
            start = loc_m.start()
            snippet = full_text[start:start + 60]
            end_m = re.match(r"([A-Z][a-z]+(?:\s+[a-z]+)*,?\s*(?:USA|Germany|France|UK|Brazil|"
                            r"Sweden|Denmark|Poland|Romania|Portugal|Spain|Italy|"
                            r"Netherlands|Belgium|Switzerland|Austria|Norway|Finland|Serbia|"
                            r"Turkey|UAE|Qatar|Saudi Arabia|India|Indonesia|Philippines|"
                            r"Thailand|South Korea|Japan|China|Australia|Canada|Mexico|"
                            r"Argentina|Peru|Chile|Colombia|Czech Republic|Hungary|"
                            r"Greece|Croatia|Slovakia|Slovenia|Estonia|Latvia|Lithuania|"
                            r"Ukraine|Georgia|Armenia|Kazakhstan|Uzbekistan|Nigeria|Egypt|"
                            r"South Africa|Kenya|Morocco|Algeria|Tunisia|Russia|Belarus|"
                            r"Moldova|Albania|Macedonia|Montenegro|Bosnia|Iceland|"
                            r"Luxembourg|Monaco|Liechtenstein|Andorra|San Marino|"
                            r"Vatican|Cyprus|Korea|Kingdom))", snippet)
            if end_m:
                # Try to include city + country
                city_country = re.match(r"^([A-Z][a-z]+(?:\s+(?:de\s+)?[A-Z][a-z]+)*"
                                        r"(?:,\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*"
                                        r"(?:\s+(?:USA|Germany|France|UK|Brazil|"
                                        r"Sweden|Denmark|Poland|Romania|Portugal|Spain|Italy|"
                                        r"Netherlands|Belgium|Switzerland|Austria|Norway|Finland|Serbia|"
                                        r"Turkey|UAE|Qatar|Saudi Arabia|India|Indonesia|Philippines|"
                                        r"Thailand|South Korea|Japan|China|Australia|Canada|Mexico|"
                                        r"Argentina|Peru|Chile|Colombia|Czech Republic|Hungary|"
                                        r"Greece|Croatia|Slovakia|Slovenia|Estonia|Latvia|Lithuania|"
                                        r"Ukraine|Georgia|Armenia|Kazakhstan|Uzbekistan|Nigeria|Egypt|"
                                        r"South Africa|Kenya|Morocco|Algeria|Tunisia|Russia|Belarus|"
                                        r"Moldova|Albania|Macedonia|Montenegro|Bosnia|Iceland|"
                                        r"Luxembourg|Monaco|Liechtenstein|Andorra|San Marino|"
                                        r"Vatican|Cyprus|Korea|Kingdom)))?)", snippet)
                if city_country:
                    meta["location"] = city_country.group(0).strip().rstrip(",")
                else:
                    meta["location"] = loc_m.group(0)
    except Exception:
        pass

    return meta


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

def get_events() -> list[dict]:
    """Fetch all events from HLTV results, enriched with metadata from event pages."""
    all_results = []
    for offset in range(0, 600, 100):
        try:
            html = _get(f"{BASE}/results?offset={offset}")
            soup = _soup(html)
            results = soup.select(".result-con")
            if not results:
                break
            all_results.extend(results)
        except Exception:
            break

    # Build event map
    events_map: dict[str, dict] = {}
    for rc in all_results:
        match_a = rc.select_one("a.a-reset[href*='/matches/']")
        if not match_a:
            continue
        mm = re.match(r"/matches/(\d+)/", match_a.get("href", ""))
        if not mm:
            continue
        match_id = int(mm.group(1))

        t1_el = rc.select_one(".team1")
        t2_el = rc.select_one(".team2")
        team1 = t1_el.get_text(strip=True) if t1_el else ""
        team2 = t2_el.get_text(strip=True) if t2_el else ""

        score1 = score2 = None
        score_cell = rc.select_one(".result-score")
        if score_cell:
            parts = score_cell.get_text(strip=True).split("-")
            if len(parts) == 2:
                try:
                    score1, score2 = int(parts[0]), int(parts[1])
                except ValueError:
                    pass

        event_el = rc.select_one(".event-name")
        event_name = event_el.get_text(strip=True) if event_el else ""
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
                "_first_match_id": match_id,
            }
        events_map[event_name]["_matches"].append({
            "id": match_id, "team1": team1, "team2": team2,
            "score1": score1, "score2": score2, "format": fmt,
        })

    # Build result
    events = []
    for name, data in sorted(events_map.items(), key=lambda x: -len(x[1]["_matches"])):
        matches = data.pop("_matches")
        first_match_id = data.pop("_first_match_id")
        if len(matches) < 2:
            continue

        # Enrich with event page metadata (uses match page to find real event ID)
        real_id, slug = _get_event_id_and_slug(first_match_id)
        if real_id:
            data["id"] = real_id
        meta = _fetch_event_meta(real_id or data["id"], slug) if slug else {}
        data.update({k: v for k, v in meta.items() if v})

        data["_match_ids"] = [m["id"] for m in matches]
        events.append(data)

    return events


# ---------------------------------------------------------------------------
# Event detail — matches
# ---------------------------------------------------------------------------

def get_event_matches(event_id: int) -> tuple[dict, list[dict]]:
    """Get event info and all its matches. Works with both real HLTV IDs and computed IDs."""
    all_results = []
    for offset in range(0, 900, 100):
        try:
            html = _get(f"{BASE}/results?offset={offset}")
            soup = _soup(html)
            results = soup.select(".result-con")
            if not results:
                break
            all_results.extend(results)
        except Exception:
            break

    event_name = ""
    matches = []
    seen_ids = set()
    event_meta = {}
    target_stable_id = None  # Lazily determined

    for rc in all_results:
        match_a = rc.select_one("a.a-reset[href*='/matches/']")
        if not match_a:
            continue
        mm = re.match(r"/matches/(\d+)/", match_a.get("href", ""))
        if not mm:
            continue
        match_id = int(mm.group(1))

        event_el = rc.select_one(".event-name")
        ev_name = event_el.get_text(strip=True) if event_el else ""

        # Matching logic: try real HLTV ID first, then fall back to stable ID
        if not event_name:
            # First candidate — fetch real ID from match page to verify
            real_id, slug = _get_event_id_and_slug(match_id)
            if real_id:
                # Use real HLTV ID for matching
                if real_id == event_id:
                    target_stable_id = _stable_id(ev_name)
                    event_name = ev_name
                    if slug:
                        event_meta = _fetch_event_meta(event_id, slug)
            elif _stable_id(ev_name) == event_id:
                # Fallback: match by computed stable ID
                target_stable_id = event_id
                event_name = ev_name
        elif target_stable_id is not None:
            # Match subsequent results by consistent stable ID
            if _stable_id(ev_name) != target_stable_id:
                continue
        else:
            continue
        event_meta = event_meta or {}

        if match_id in seen_ids:
            continue
        seen_ids.add(match_id)

        t1_el = rc.select_one(".team1")
        t2_el = rc.select_one(".team2")
        team1 = t1_el.get_text(strip=True) if t1_el else ""
        team2 = t2_el.get_text(strip=True) if t2_el else ""

        score1 = score2 = None
        score_cell = rc.select_one(".result-score")
        if score_cell:
            parts = score_cell.get_text(strip=True).split("-")
            if len(parts) == 2:
                try:
                    score1, score2 = int(parts[0]), int(parts[1])
                except ValueError:
                    pass

        fmt_el = rc.select_one(".map-text")
        fmt = fmt_el.get_text(strip=True) if fmt_el else ""

        matches.append({
            "id": match_id, "event_id": event_id, "event_name": event_name,
            "team1": {"id": _stable_id(team1, 10000), "name": team1, "logo_url": ""},
            "team2": {"id": _stable_id(team2, 10000), "name": team2, "logo_url": ""},
            "score1": score1, "score2": score2, "format": fmt,
            "status": "completed" if score1 is not None else "upcoming", "date": "",
        })

    if not event_name:
        event_name = f"Event #{event_id}"

    event = {
        "id": event_id, "name": event_name,
        "date_start": event_meta.get("date_start", ""),
        "date_end": event_meta.get("date_end", ""),
        "prize": event_meta.get("prize", ""),
        "location": event_meta.get("location", ""),
        "status": "completed", "logo_url": event_meta.get("logo_url", ""),
    }
    return event, matches


# ---------------------------------------------------------------------------
# Match player stats
# ---------------------------------------------------------------------------

def get_match_stats(match_id: int) -> dict:
    """Fetch match player stats from the match page."""
    html = _get(f"{BASE}/matches/{match_id}/-")
    soup = _soup(html)

    # Team names
    team1_name = team2_name = ""
    team_els = soup.select(".teamName")
    names = list(dict.fromkeys(t.get_text(strip=True) for t in team_els))
    if len(names) >= 2:
        team1_name, team2_name = names[0], names[1]
    elif names:
        team1_name = names[0]

    # Team logos
    team1_logo = team2_logo = ""
    for img in soup.select(".teamLogo img, img[src*='team']"):
        src = img.get("src", "")
        alt = img.get("alt", "")
        if team1_name and team1_name in (alt or ""):
            team1_logo = _resolve_url(src)
        elif team2_name and team2_name in (alt or ""):
            team2_logo = _resolve_url(src)

    # Scores
    score1 = score2 = None
    for s in soup.select(".results-team-score"):
        text = s.get_text(strip=True)
        if text.isdigit() and int(text) < 50:
            val = int(text)
            if score1 is None:
                score1 = val
            elif score2 is None:
                score2 = val

    # Event info
    event_id = 0
    event_name = ""
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.string or "")
            if isinstance(data, dict) and data.get("@type") == "SportsEvent":
                desc = data.get("description", "") or data.get("name", "")
                ev_match = re.search(r"at\s+(.+?)(?:!|$)", desc)
                if ev_match:
                    event_name = ev_match.group(1).strip()
                ev_id_match = re.search(r"/events/(\d+)/", html)
                if ev_id_match:
                    event_id = int(ev_id_match.group(1))
        except (json.JSONDecodeError, TypeError):
            pass

    # Date
    date = ""
    date_m = re.search(
        r"(\d{1,2}[a-z]{2}\s+of\s+(?:January|February|March|April|May|June|"
        r"July|August|September|October|November|December)[a-z]*\s+\d{4})",
        soup.get_text(),
    )
    if date_m:
        date = date_m.group(1)

    # Parse player stats
    team1_players = []
    team2_players = []
    current_team = 0

    for table in soup.select("table.totalstats")[:2]:
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

            if any(t in ("K-D", "ADR", "KAST", "Rating") for t in cell_texts):
                continue
            if len(cell_texts) < 6:
                continue
            if cell_texts[0] in (team1_name, team2_name):
                continue

            raw_name = cell_texts[0] if cell_texts else ""
            player_name = _extract_player_alias(raw_name)
            if not player_name or len(player_name) < 2:
                continue
            if player_name.replace(".", "").replace("-", "").isdigit():
                continue

            kills = deaths = 0
            adr = kast = rating = 0.0

            for cell in cells:
                classes = " ".join(cell.get("class", []))
                t = cell.get_text(strip=True)

                if "kd" in classes and "traditional-data" in classes:
                    kd_match = re.match(r"^(\d+)\s*-\s*(\d+)$", t)
                    if kd_match:
                        kills = int(kd_match.group(1))
                        deaths = int(kd_match.group(2))
                    continue
                if "adr" in classes and "traditional-data" in classes:
                    val = float(t) if re.match(r"^\d+(?:\.\d+)?$", t) else 0
                    if 30 <= val <= 200 and adr == 0:
                        adr = val
                    continue
                if "kast" in classes and "traditional-data" in classes:
                    val = float(t.replace("%", "")) if t.endswith("%") else 0
                    if 40 <= val <= 100 and kast == 0:
                        kast = val
                    continue
                if "rating" in classes:
                    val = float(t) if re.match(r"^\d+\.\d+$", t) else 0
                    if 0.3 <= val <= 3.0 and rating == 0:
                        rating = val
                    continue

            team_name = team1_name if current_team == 1 else team2_name
            player_data = {
                "player_id": _stable_id(f"{match_id}:{player_name}"),
                "player_name": player_name,
                "team_name": team_name,
                "rating": round(rating, 2),
                "kpr": 0, "dpr": 0,
                "adr": round(adr, 1),
                "kast": round(kast, 1),
                "impact": round(rating, 2),
                "kills": kills, "deaths": deaths,
                "plus_minus": kills - deaths,
                "hs_percent": 0,
            }
            if current_team == 1:
                team1_players.append(player_data)
            elif current_team == 2:
                team2_players.append(player_data)

    # Compute relative KPR/DPR
    for players in (team1_players, team2_players):
        if not players:
            continue
        tk = sum(p["kills"] for p in players) or 1
        td = sum(p["deaths"] for p in players) or 1
        for p in players:
            p["kpr"] = round(p["kills"] / tk * 4, 2)
            p["dpr"] = round(p["deaths"] / td * 4, 2)

    # Fallback split
    if not team2_players and team1_players and team2_name:
        t1_set = {p["player_name"] for p in team1_players if p["team_name"] == team1_name}
        t2_set = {p["player_name"] for p in team1_players if p["player_name"] not in t1_set}
        if t2_set:
            team2_players = [p for p in team1_players if p["player_name"] in t2_set]
            team1_players = [p for p in team1_players if p["player_name"] in t1_set]

    return {
        "match": {
            "id": match_id, "event_id": event_id, "event_name": event_name,
            "team1": {"id": _stable_id(team1_name, 10000), "name": team1_name, "logo_url": team1_logo},
            "team2": {"id": _stable_id(team2_name, 10000), "name": team2_name, "logo_url": team2_logo},
            "score1": score1, "score2": score2, "format": "",
            "status": "completed", "date": date,
        },
        "team1_players": team1_players,
        "team2_players": team2_players,
    }
