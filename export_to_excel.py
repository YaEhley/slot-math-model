from collections import Counter
from itertools import product

import pandas as pd

from slot import REEL, REELS, PAYTABLE, evaluate, analytics
from simulation import play


def build_tables(log):
    spins = pd.DataFrame(log)
    a = analytics()

    counts = Counter(REEL)
    params = pd.DataFrame({
        "Symbol": list(PAYTABLE),
        "Items on the feed": [counts[s] for s in PAYTABLE],
        "Probability on the reel": [counts[s] / len(REEL) for s in PAYTABLE],
        "Payout (x the stake)": list(PAYTABLE.values()),
    })

    summary = pd.DataFrame({
        "Indicator of": [
            "Spins",
            "RTP (theory)",
            "RTP (simulation)",
            "Hit frequency (theory)",
            "Hit frequency (simulation)",
            "Standard deviation of the payout (theory)",
            "Final balance (in stakes)",
        ],
        "Value of": [
            len(spins),
            a["RTP"],
            spins["win"].sum() / spins["bet"].sum(),
            a["hit_freq"],
            (spins["win"] > 0).mean(),
            a["std"],
            spins["balance"].iloc[-1],
        ],
    })

    observed = spins["win"].value_counts()
    theory = Counter(evaluate(c) for c in product(*REELS))
    n_theory = sum(theory.values())
    dist = pd.DataFrame({
        "Winnings": sorted(theory),
        "Drops": [int(observed.get(w, 0)) for w in sorted(theory)],
        "Frequency (simulation)": [observed.get(w, 0) / len(spins) for w in sorted(theory)],
        "Frequency (theory)": [theory[w] / n_theory for w in sorted(theory)],
    })

    return params, summary, dist, spins


def export(log, path="slot_results.xlsx"):
    params, summary, dist, spins = build_tables(log)

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        params.to_excel(writer, sheet_name="Parameters", index=False)
        summary.to_excel(writer, sheet_name="Summary", index=False)
        dist.to_excel(writer, sheet_name="Distribution", index=False)
        spins.to_excel(writer, sheet_name="Spins", index=False)

        ws = writer.sheets["Summary"]
        ws["A10"] = "RTP (Excel formula on the 'Spins' sheet)"
        ws["B10"] = "=SUM('Spins'!F:F)/SUM('Spins'!E:E)"

        for ws in writer.sheets.values():
            ws.freeze_panes = "A2"
            for col in ws.iter_cols(max_row=50):
                width = max(len(str(c.value)) for c in col if c.value is not None)
                ws.column_dimensions[col[0].column_letter].width = min(width + 2, 45)

    print(f"Saved: {path}")


if __name__ == "__main__":
    log = play(100_000, seed=42)
    export(log)