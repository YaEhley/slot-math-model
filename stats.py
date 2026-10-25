"""Statistics: exact analytics, paytable tuning, validation against Monte Carlo, PAR sheet."""
import math
from collections import Counter
from itertools import product

import pandas as pd

from config import REELS, PAYTABLE, SHARES, JACKPOT, TARGET_RTP
from game import evaluate
from simulate import simulate_fast


# ---------- exact analytics ----------
def symbol_probs(reels=REELS):
    """P(three of a kind) for every symbol (strips may differ per reel)."""
    counts = [Counter(r) for r in reels]
    symbols = dict.fromkeys(s for r in reels for s in r)      # keeps order of appearance
    return {s: math.prod(c[s] / len(r) for c, r in zip(counts, reels)) for s in symbols}


def analytics(reels=REELS, pay=PAYTABLE):
    """Exact RTP, hit frequency, std and max win by closed-form formulas."""
    p = symbol_probs(reels)
    reachable = [s for s in p if p[s] > 0]
    missing = [s for s in reachable if s not in pay]
    if missing:
        raise KeyError(f"no payout defined for symbols on the reels: {missing}")

    rtp = sum(p[s] * pay[s] for s in reachable)
    var = sum(p[s] * pay[s] ** 2 for s in reachable) - rtp ** 2
    max_win = max(pay[s] for s in reachable)
    top = [s for s in reachable if pay[s] == max_win]          # all symbols tied for the max win
    return {"RTP": rtp,
            "hit_freq": sum(p[s] for s in reachable if pay[s] > 0),
            "std": math.sqrt(max(var, 0.0)),
            "max_win": max_win,
            "max_win_symbols": top,
            "max_win_prob": sum(p[s] for s in top)}


def enumerate_stats(reels=REELS, pay=PAYTABLE):
    """Reference: brute force over all stop combinations using the real round logic."""
    n = math.prod(len(r) for r in reels)
    total = hits = sq = 0
    for combo in product(*reels):
        w = evaluate(combo, 1, pay)
        total += w
        sq += w * w
        hits += w > 0
    rtp = total / n
    return {"combinations": n, "RTP": rtp, "hit_freq": hits / n,
            "std": math.sqrt(max(sq / n - rtp ** 2, 0.0))}


# ---------- tuning ----------
def tune_paytable(reels, target_rtp, shares, jackpot):
    """Integer paytable with RTP = target_rtp (up to rounding of the jackpot payout)."""
    if sum(shares.values()) >= 1:
        raise ValueError("shares of non-jackpot symbols must leave room for the jackpot")
    p = symbol_probs(reels)
    pay = {s: round(target_rtp * share / p[s]) for s, share in shares.items()}
    rest = sum(p[s] * pay[s] for s in pay)
    pay[jackpot] = round((target_rtp - rest) / p[jackpot])
    return {s: pay[s] for s in p}


# ---------- validation ----------
def validate(n_spins=100_000_000, seed=42, workers=4):
    """Compares Monte Carlo with the exact values: RTP, hit frequency, wins per symbol."""
    st = analytics()
    sim = simulate_fast(n_spins, seed=seed, workers=workers)
    dev = (sim["RTP"] - st["RTP"]) / sim["std_error"]
    print(f"{n_spins:,} spins, {workers} workers")
    print(f"RTP: exact {st['RTP']:.5f}, simulated {sim['RTP']:.5f} "
          f"({dev:+.2f} std errors, std error = {sim['std_error']:.5f})")
    print(f"Hit frequency: exact {st['hit_freq']:.6f}, simulated {sim['hit_freq']:.6f}")
    p = symbol_probs()
    print(f"\n{'symbol':>8} {'observed':>12} {'expected':>14} {'z':>6}")
    for s in PAYTABLE:
        exp = n_spins * p[s]
        obs = sim["wins_by_symbol"][s]
        z = (obs - exp) / math.sqrt(exp * (1 - p[s]))
        print(f"{s:>8} {obs:>12,} {exp:>14,.0f} {z:>+6.2f}")


# ---------- PAR sheet ----------
def build_par(reels=REELS, pay=PAYTABLE, sim_spins=10_000_000, seed=42):
    if sim_spins <= 0:
        raise ValueError("sim_spins must be positive")
    st = analytics(reels, pay)
    if st["RTP"] <= 0:
        raise ValueError("RTP must be positive")
    exact = enumerate_stats(reels, pay)                        # independent cross-check
    assert abs(st["RTP"] - exact["RTP"]) < 1e-9, "closed-form RTP != enumerated RTP"

    counts = [Counter(r) for r in reels]
    p = symbol_probs(reels)
    symbols = pd.DataFrame([{
        "Symbol": s,
        **{f"Count reel {i + 1}": c[s] for i, c in enumerate(counts)},
        "Combinations": math.prod(c[s] for c in counts),
        "Probability": p[s],
        "1 in": 1 / p[s] if p[s] else None,
        "Pay (x bet)": pay.get(s, 0),
        "RTP contribution": p[s] * pay.get(s, 0),
        "Share of RTP": p[s] * pay.get(s, 0) / st["RTP"],
    } for s in p])

    sim = simulate_fast(sim_spins, seed=seed, reels=reels, pay=pay)
    summary = pd.DataFrame([
        ("Reels", len(reels)),
        ("Stops per reel", ", ".join(str(len(r)) for r in reels)),
        ("Total combinations", exact["combinations"]),
        ("RTP (theory)", st["RTP"]),
        ("Hit frequency", st["hit_freq"]),
        ("Hit frequency, 1 in", 1 / st["hit_freq"]),
        ("Std dev of payout (x bet)", st["std"]),
        ("Max win (x bet)", st["max_win"]),
        ("Max win probability, 1 in", 1 / st["max_win_prob"]),
        ("Spins for ±1 pp RTP accuracy (95%)", (1.96 * st["std"] / 0.01) ** 2),
        ("Simulation: spins", sim_spins),
        ("Simulation: RTP", sim["RTP"]),
        ("Simulation: deviation (in std errors)", (sim["RTP"] - st["RTP"]) / sim["std_error"]),
        ("Simulation: 95% interval half-width", 1.96 * sim["std_error"]),
    ], columns=["Metric", "Value"])
    summary["Value"] = summary["Value"].map(lambda v: round(v, 6) if isinstance(v, float) else v)
    return symbols, summary


def export_par(reels=REELS, pay=PAYTABLE, path="par_sheet.xlsx", sim_spins=10_000_000, seed=42):
    symbols, summary = build_par(reels, pay, sim_spins=sim_spins, seed=seed)
    fmt = {"Probability": "0.0000%", "RTP contribution": "0.0000%",
           "Share of RTP": "0.0%", "1 in": "#,##0.0"}

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        summary.to_excel(writer, sheet_name="Summary", index=False)
        symbols.to_excel(writer, sheet_name="Symbols", index=False)

        ws = writer.sheets["Symbols"]
        for col in ws.iter_cols(min_row=1, max_row=ws.max_row):
            if col[0].value in fmt:
                for cell in col[1:]:
                    cell.number_format = fmt[col[0].value]

        for ws in writer.sheets.values():
            ws.freeze_panes = "A2"
            for col in ws.iter_cols(max_row=ws.max_row):
                width = max(len(str(c.value)) for c in col if c.value is not None)
                ws.column_dimensions[col[0].column_letter].width = min(width + 2, 55)

    print(f"Saved: {path}")


if __name__ == "__main__":
    print("Tuned paytable for target RTP:", tune_paytable(REELS, TARGET_RTP, SHARES, JACKPOT), "\n")
    validate()
    export_par()