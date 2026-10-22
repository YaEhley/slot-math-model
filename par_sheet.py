from collections import Counter
from math import prod

import pandas as pd

from slot import REELS, PAYTABLE, analytics, simulate
from tuning import symbol_probs, stats


def build_par(reels, pay, sim_spins=1_000_000, seed=42):
    if sim_spins <= 0:
        raise ValueError("sim_spins must be positive")
    counts = [Counter(r) for r in reels]
    n_comb = prod(len(r) for r in reels)
    p = symbol_probs(reels)
    st = stats(reels, pay)

    exact = analytics(reels, pay)
    assert abs(st["RTP"] - exact["RTP"]) < 1e-9, "closed-form RTP != enumerated RTP"

    rows = []
    for s in p:
        rows.append({
            "Symbol": s,
            **{f"Count reel {i + 1}": c[s] for i, c in enumerate(counts)},
            "Combinations": prod(c[s] for c in counts),
            "Probability": p[s],
            "1 in": 1 / p[s],
            "Pay (x bet)": pay[s],
            "RTP contribution": p[s] * pay[s],
            "Share of RTP": p[s] * pay[s] / st["RTP"],
        })
    symbols = pd.DataFrame(rows)

    sim = simulate(sim_spins, seed=seed, reels=reels, pay=pay)
    se = st["std"] / sim_spins ** 0.5          # standard error of simulated RTP
    summary = pd.DataFrame([
        ("Reels", len(reels)),
        ("Stops per reel", ", ".join(str(len(r)) for r in reels)),
        ("Total combinations", n_comb),
        ("RTP (theory)", st["RTP"]),
        ("Hit frequency", st["hit_freq"]),
        ("Hit frequency, 1 in", 1 / st["hit_freq"]),
        ("Std dev of payout (x bet)", st["std"]),
        ("Max win (x bet)", st["max_win"]),
        ("Max win probability, 1 in", 1 / st["max_win_prob"]),
        ("Spins for ±1 pp RTP accuracy (95%)", (1.96 * st["std"] / 0.01) ** 2),
        ("Simulation: spins", sim_spins),
        ("Simulation: RTP", sim["RTP"]),
        ("Simulation: deviation (in std errors)", (sim["RTP"] - st["RTP"]) / se),
        ("Simulation: 95% interval half-width", 1.96 * se),
    ], columns=["Metric", "Value"])
    summary["Value"] = summary["Value"].map(lambda v: round(v, 6) if isinstance(v, float) else v)
    return symbols, summary


def export_par(reels=REELS, pay=PAYTABLE, path="par_sheet.xlsx", sim_spins=1_000_000, seed=42):
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
    export_par()