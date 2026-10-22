import random
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from slot import PAYTABLE, spin, evaluate, analytics
from export_to_excel import export

BASE = Path(__file__).parent
app = FastAPI()

rng = random.Random()   # without a seed: every time the server is started, the game plays out differently
log = []                # session log
balance = 0            


class SpinRequest(BaseModel):
    bet: float = 1


@app.get("/")
def index():
    return FileResponse(BASE / "static" / "index.html")


@app.get("/api/info")
def api_info():
    a = analytics()
    return {"paytable": PAYTABLE, "rtp": a["RTP"], "hit_freq": a["hit_freq"]}


@app.post("/api/spin")
def api_spin(req: SpinRequest):
    global balance
    if req.bet <= 0:
        raise HTTPException(400, "The rate must be positive")
    symbols = spin(rng)
    win = evaluate(symbols, req.bet)
    balance += win - req.bet
    log.append({"spin": len(log) + 1, "r1": symbols[0], "r2": symbols[1], "r3": symbols[2],
                "bet": req.bet, "win": win, "balance": balance})
    return {"symbols": list(symbols), "win": win}


@app.get("/api/export")
def api_export():
    if not log:
        raise HTTPException(400, "Not a single spin has been played yet")
    path = BASE / "session_results.xlsx"
    export(log, str(path))
    return FileResponse(path, filename="slot_session.xlsx")