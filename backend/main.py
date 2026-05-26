"""
CS2 Radar — FastAPI backend
Always fetches fresh data from HLTV. Falls back to mock data only on failure.
"""

import asyncio
import random
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from scraper import get_events, get_event_matches, get_match_stats

_executor = ThreadPoolExecutor(max_workers=4)

# Mock data kept only as last-resort fallback when HLTV is unreachable
MOCK_EVENTS = [
    {
        "id": 1, "name": "IEM Dallas 2026", "date_start": "2026-05-19", "date_end": "2026-05-25",
        "prize": "$1,000,000", "location": "Dallas, USA", "status": "ongoing", "logo_url": "",
    },
    {
        "id": 2, "name": "BLAST.tv Paris Major 2026", "date_start": "2026-05-08", "date_end": "2026-05-18",
        "prize": "$1,250,000", "location": "Paris, France", "status": "completed", "logo_url": "",
    },
    {
        "id": 3, "name": "ESL Pro League S24", "date_start": "2026-04-22", "date_end": "2026-05-04",
        "prize": "$750,000", "location": "Malta", "status": "completed", "logo_url": "",
    },
    {
        "id": 4, "name": "PGL Bucharest 2026", "date_start": "2026-04-05", "date_end": "2026-04-13",
        "prize": "$1,000,000", "location": "Bucharest, Romania", "status": "completed", "logo_url": "",
    },
    {
        "id": 5, "name": "BLAST Open Spring 2026", "date_start": "2026-03-19", "date_end": "2026-03-30",
        "prize": "$425,000", "location": "Copenhagen, Denmark", "status": "completed", "logo_url": "",
    },
    {
        "id": 6, "name": "IEM Katowice 2026", "date_start": "2026-02-11", "date_end": "2026-02-23",
        "prize": "$1,000,000", "location": "Katowice, Poland", "status": "completed", "logo_url": "",
    },
]

PRO_PLAYER_NAMES = {
    "FaZe": ["karrigan", "broky", "frozen", "rain", "ropz"],
    "G2": ["huNter-", "NiKo", "m0NESY", "malbsMd", "HeavyGod"],
    "Vitality": ["apEX", "ZywOo", "flameZ", "Spinx", "mezii"],
    "NAVI": ["Aleksib", "b1t", "jL", "iM", "w0nderful"],
    "Spirit": ["chopper", "sh1ro", "donk", "zont1x", "magixx"],
    "MOUZ": ["Brollan", "xertioN", "torzsi", "Jimpphat", "JDC"],
    "Falcons": ["Snappi", "Magisk", "dupreeh", "maden", "SunPayus"],
    "Liquid": ["Twistzz", "NAF", "jks", "YEKINDAR", "ultimate"],
}

TEAM_POOL = list(PRO_PLAYER_NAMES.keys())


def _generate_player_stats(player_name: str, team_name: str) -> dict:
    base = hash(f"{team_name}:{player_name}") % 1000
    random.seed(base)
    rating = round(random.uniform(0.88, 1.35), 2)
    kpr = round(random.uniform(0.55, 0.85), 2)
    dpr = round(random.uniform(0.50, 0.75), 2)
    adr = round(random.uniform(62.0, 92.0), 1)
    kast = round(random.uniform(64.0, 78.0), 1)
    impact = round(random.uniform(0.75, 1.45), 2)
    kills = random.randint(12, 28)
    deaths = random.randint(10, 24)
    hs = random.randint(35, 68)
    return {
        "player_id": abs(hash(f"{team_name}:{player_name}")) % 100000,
        "player_name": player_name,
        "team_name": team_name,
        "rating": rating,
        "kpr": kpr,
        "dpr": dpr,
        "adr": adr,
        "kast": kast,
        "impact": impact,
        "kills": kills,
        "deaths": deaths,
        "plus_minus": kills - deaths,
        "hs_percent": hs,
    }


def _generate_mock_matches(event_id: int, event_name: str) -> list[dict]:
    random.seed(event_id)
    matches = []
    for i in range(random.randint(6, 16)):
        t1 = random.choice(TEAM_POOL)
        t2 = random.choice([t for t in TEAM_POOL if t != t1])
        s1 = random.randint(0, 2) if random.random() < 0.85 else None
        s2 = random.randint(0, 2) if s1 is not None else None
        if s1 == s2 and s1 is not None and random.random() < 0.4:
            s2 = (s1 + 1) % 3
        matches.append({
            "id": event_id * 1000 + i + 1,
            "event_id": event_id,
            "event_name": event_name,
            "team1": {"id": abs(hash(t1)) % 10000, "name": t1, "logo_url": ""},
            "team2": {"id": abs(hash(t2)) % 10000, "name": t2, "logo_url": ""},
            "score1": s1,
            "score2": s2,
            "format": random.choice(["bo1", "bo3", "bo5"]),
            "status": "completed",
            "date": f"2026-05-{random.randint(10, 24):02d}",
        })
    return matches


app = FastAPI(title="CS2 Radar API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/events")
async def api_events():
    """Get recent CS2 events. Always fetches fresh from HLTV."""
    try:
        events = await asyncio.get_event_loop().run_in_executor(_executor, get_events)
        if events:
            return events
    except Exception:
        pass
    return MOCK_EVENTS


@app.get("/api/events/{event_id}")
async def api_event_detail(event_id: int):
    """Get event details with matches. Always fetches fresh from HLTV."""
    try:
        event, matches = await asyncio.get_event_loop().run_in_executor(
            _executor, get_event_matches, event_id
        )
        if matches:
            return {"event": event, "matches": matches}
    except Exception:
        pass

    # Mock fallback
    event = next((e for e in MOCK_EVENTS if e["id"] == event_id), None)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    matches = _generate_mock_matches(event_id, event["name"])
    return {"event": event, "matches": matches}


@app.get("/api/matches/{match_id}")
async def api_match_detail(match_id: int):
    """Get match detail with player radar stats. Always fetches fresh from HLTV."""
    try:
        stats = await asyncio.get_event_loop().run_in_executor(
            _executor, get_match_stats, match_id
        )
        if stats["team1_players"] or stats["team2_players"]:
            return stats
    except Exception:
        pass

    # Mock fallback
    random.seed(match_id)
    event_id = match_id // 1000
    event = next((e for e in MOCK_EVENTS if e["id"] == event_id), None)
    event_name = event["name"] if event else "Unknown Event"

    t1 = TEAM_POOL[match_id % len(TEAM_POOL)]
    t2 = TEAM_POOL[(match_id + 3) % len(TEAM_POOL)]
    if t1 == t2:
        t2 = TEAM_POOL[(match_id + 1) % len(TEAM_POOL)]

    s1 = random.randint(0, 2)
    s2 = (s1 + 1) % 3 if random.random() < 0.6 else s1
    if s1 == s2:
        s2 = (s1 + 1) % 3

    return {
        "match": {
            "id": match_id,
            "event_id": event_id,
            "event_name": event_name,
            "team1": {"id": abs(hash(t1)) % 10000, "name": t1, "logo_url": ""},
            "team2": {"id": abs(hash(t2)) % 10000, "name": t2, "logo_url": ""},
            "score1": s1,
            "score2": s2,
            "format": random.choice(["bo1", "bo3"]),
            "status": "completed",
            "date": f"2026-05-{random.randint(15, 24):02d}",
        },
        "team1_players": [
            _generate_player_stats(name, t1) for name in PRO_PLAYER_NAMES.get(t1, [])
        ],
        "team2_players": [
            _generate_player_stats(name, t2) for name in PRO_PLAYER_NAMES.get(t2, [])
        ],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8765)
