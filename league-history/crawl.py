#!/usr/bin/env python3
"""Crawl a Sleeper dynasty league (all seasons) into one history.json.

Usage:  python crawl.py LEAGUE_ID [output_path]
        (or set the LEAGUE_ID env var)
Needs:  pip install requests
"""
import json, os, sys, time
from datetime import datetime, timezone

import requests

BASE = "https://api.sleeper.app/v1"
session = requests.Session()


def get(path):
    """GET a Sleeper endpoint with light retry. Returns None on 404."""
    for attempt in range(4):
        try:
            r = session.get(BASE + path, timeout=60)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 404:
                return None
        except requests.RequestException:
            pass
        time.sleep(1 + attempt)
    raise RuntimeError(f"Failed to fetch {path}")


def crawl_league(league_id, out):
    """Walk this league and every previous season via previous_league_id."""
    while league_id and league_id != "0":
        lg = get(f"/league/{league_id}")
        if not lg:
            break
        season = str(lg["season"])
        print(f"Season {season} ({league_id})")

        # roster_id -> team name (only stable within a season)
        users = {u["user_id"]: u for u in get(f"/league/{league_id}/users") or []}
        teams = {}
        for r in get(f"/league/{league_id}/rosters") or []:
            u = users.get(r.get("owner_id"), {})
            name = (u.get("metadata") or {}).get("team_name") or u.get("display_name") or f"Team {r['roster_id']}"
            teams[str(r["roster_id"])] = {"name": name, "owner_id": r.get("owner_id"), "avatar": u.get("avatar")}
        out["teams"][season] = teams

        for u in users.values():
            uid = u.get("user_id")
            if uid:
                out["users"][uid] = {"name": u.get("display_name") or uid, "avatar": u.get("avatar")}
        # Newest league only: who owns every traded future pick right now
        if out["current"] is None:
            out["current"] = {"season": season, "league_id": league_id,
                              "rounds": int((lg.get("settings") or {}).get("draft_rounds") or 4)}
            for tp in get(f"/league/{league_id}/traded_picks") or []:
                out["pick_owners"][f"{tp['season']}-{tp['round']}-{tp['roster_id']}"] = tp["owner_id"]

        # Every completed transaction (trades, waivers, free agents, commish moves)
        seen = set()
        for week in range(0, 19):
            for t in get(f"/league/{league_id}/transactions/{week}") or []:
                tid = t["transaction_id"]
                if tid in seen or t.get("status") != "complete":
                    continue
                seen.add(tid)
                out["transactions"].append({
                    "id": tid,
                    "type": t["type"],
                    "season": season,
                    "week": week,
                    "created": t["created"],
                    "adds": t.get("adds") or {},    # {player_id: roster_id that received}
                    "drops": t.get("drops") or {},  # {player_id: roster_id that sent/dropped}
                    "picks": [
                        {
                            "season": str(p["season"]),
                            "round": int(p["round"]),
                            "roster_id": p["roster_id"],        # original owner
                            "from": p["previous_owner_id"],
                            "to": p["owner_id"],
                        }
                        for p in t.get("draft_picks") or []
                    ],
                    "faab": [
                        {"from": w["sender"], "to": w["receiver"], "amount": w["amount"]}
                        for w in t.get("waiver_budget") or []
                    ],
                })

        # Weekly points per player + matchup pairings
        for week in range(1, 19):
            by_mid = {}
            for m in get(f"/league/{league_id}/matchups/{week}") or []:
                vals = {pid: round(v, 1) for pid, v in (m.get("players_points") or {}).items() if v}
                if vals:
                    out["points"][f"{season}-{week}-{m['roster_id']}"] = vals
                mid = m.get("matchup_id")
                if mid:
                    by_mid.setdefault(mid, []).append({"rid": str(m["roster_id"]), "pts": round(float(m.get("points") or 0), 2)})
            for pairs in by_mid.values():
                if len(pairs) == 2:
                    out["matchups"].append({"s": season, "w": week, "p": pairs})

        # Drafts: link each pick slot back to its original owner
        for d in get(f"/league/{league_id}/drafts") or []:
            slots = d.get("slot_to_roster_id")
            if not slots:
                slots = (get(f"/draft/{d['draft_id']}") or {}).get("slot_to_roster_id") or {}
            draft_time = d.get("last_picked") or d.get("start_time") or int(
                datetime(int(d["season"]), 8, 1, tzinfo=timezone.utc).timestamp() * 1000)
            for p in get(f"/draft/{d['draft_id']}/picks") or []:
                if not p.get("player_id"):
                    continue
                original = slots.get(str(p.get("draft_slot")), p.get("roster_id"))
                key = f"{d['season']}-{int(p['round'])}-{original}"
                out["draft_results"][key] = {
                    "player_id": p["player_id"],
                    "round": int(p["round"]),
                    "pick_no": p.get("pick_no"),
                    "by": p.get("roster_id"),        # roster that actually made the pick
                    "season": str(d["season"]),
                    "league_season": season,         # which season's team names to use
                    "time": draft_time,
                }

        league_id = lg.get("previous_league_id")


def attach_players(out):
    """Add names for only the player IDs the league has actually touched."""
    ids = set()
    for t in out["transactions"]:
        ids.update(t["adds"])
        ids.update(t["drops"])
    ids.update(d["player_id"] for d in out["draft_results"].values())
    print(f"Fetching player names for {len(ids)} players")
    everyone = get("/players/nfl") or {}
    for pid in ids:
        p = everyone.get(pid) or {}
        name = p.get("full_name") or " ".join(filter(None, [p.get("first_name"), p.get("last_name")])) or pid
        out["players"][pid] = {"name": name, "pos": p.get("position"), "team": p.get("team")}


def main():
    league_id = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("LEAGUE_ID")
    if not league_id:
        sys.exit("Usage: python crawl.py LEAGUE_ID [output_path]")
    out_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join("site", "history.json")

    out = {"generated": datetime.now(timezone.utc).isoformat(), "teams": {},
           "transactions": [], "draft_results": {}, "players": {},
           "points": {}, "pick_owners": {}, "current": None, "matchups": [], "users": {}}
    crawl_league(league_id, out)
    attach_players(out)
    out["transactions"].sort(key=lambda t: t["created"])

    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(out, f, separators=(",", ":"))
    trades = sum(1 for t in out["transactions"] if t["type"] == "trade")
    print(f"Wrote {out_path}: {trades} trades, {len(out['transactions'])} transactions, "
          f"{len(out['draft_results'])} drafted picks")


if __name__ == "__main__":
    main()
