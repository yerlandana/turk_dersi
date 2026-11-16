"""Kelime Oyunu by yerlandana: Turkish A2 vocabulary game with a shared leaderboard."""
import json
import re
import sqlite3
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

HERE = Path(__file__).parent
DB_PATH = HERE / "leaderboard.db"
MODES = {"tr2ru", "ru2tr", "listen", "write", "match", "letters", "blitz", "cards"}
UID_RE = re.compile(r"^[A-Za-z0-9_-]{6,40}$")

st.set_page_config(page_title="Kelime Oyunu by yerlandana", page_icon="🇹🇷", layout="centered")

st.markdown(
    """
    <style>
      header[data-testid="stHeader"], footer, #MainMenu {visibility:hidden;height:0}
      .block-container {padding:0.5rem 0.5rem 2rem; max-width: 600px}
      iframe {border:0}
    </style>
    """,
    unsafe_allow_html=True,
)

_game = components.declare_component("kelime_game", path=str(HERE / "frontend"))


def _conn():
    con = sqlite3.connect(DB_PATH, timeout=10)
    con.execute(
        "CREATE TABLE IF NOT EXISTS players ("
        "uid TEXT PRIMARY KEY, name TEXT NOT NULL, xp INTEGER NOT NULL, "
        "best TEXT NOT NULL, played INTEGER NOT NULL, updated REAL NOT NULL)"
    )
    return con


def load_rows(limit: int = 200):
    with _conn() as con:
        cur = con.execute("SELECT uid, name, xp, best FROM players ORDER BY xp DESC LIMIT ?", (limit,))
        return [{"id": u, "name": n, "xp": x, "best": json.loads(b)} for u, n, x, b in cur.fetchall()]


def upsert(v: dict) -> None:
    uid = str(v.get("uid", ""))
    if not UID_RE.match(uid):
        return
    name = re.sub(r"\s+", " ", str(v.get("name", ""))).strip()[:20] or "Игрок"
    xp = max(0, min(int(v.get("xp", 0) or 0), 1_000_000))
    played = max(0, min(int(v.get("played", 0) or 0), 100_000))
    best = {}
    raw = v.get("best") if isinstance(v.get("best"), dict) else {}
    for k, val in raw.items():
        if k in MODES:
            try:
                best[k] = max(0, min(int(val), 10_000))
            except (TypeError, ValueError):
                pass
    import time

    with _conn() as con:
        row = con.execute("SELECT xp, best, played FROM players WHERE uid=?", (uid,)).fetchone()
        if row:
            old_best = json.loads(row[1])
            for k, val in old_best.items():
                best[k] = max(best.get(k, 0), val)
            xp = max(xp, row[0])
            played = max(played, row[2])
        con.execute(
            "INSERT INTO players(uid,name,xp,best,played,updated) VALUES(?,?,?,?,?,?) "
            "ON CONFLICT(uid) DO UPDATE SET name=excluded.name, xp=excluded.xp, "
            "best=excluded.best, played=excluded.played, updated=excluded.updated",
            (uid, name, xp, json.dumps(best), played, time.time()),
        )


value = _game(rows=load_rows(), key="game", default=None)
if isinstance(value, dict) and value.get("nonce") != st.session_state.get("last_nonce"):
    st.session_state["last_nonce"] = value.get("nonce")
    upsert(value)
    st.rerun()
