import math
import pandas as pd

from par_sheet import build_par, export_par
from itertools import product

import pytest

from slot import REELS, PAYTABLE, analytics
from tuning import symbol_probs, stats, tune_paytable, SHARES, JACKPOT

UNEVEN = [["A", "A", "B"], ["A", "B"], ["A", "B", "B", "B"]]   # different strips on each reel


def brute_force_probs(reels):
    """Three-of-a-kind probability per symbol, found by counting all stop combinations."""
    total, hits = 0, {}
    for combo in product(*reels):
        total += 1
        if len(set(combo)) == 1:
            hits[combo[0]] = hits.get(combo[0], 0) + 1
    return {s: n / total for s, n in hits.items()}


def test_symbol_probs_hand_calculation():
    p = symbol_probs(UNEVEN)
    assert p["A"] == pytest.approx(1 / 12)   # 2/3 * 1/2 * 1/4
    assert p["B"] == pytest.approx(1 / 8)    # 1/3 * 1/2 * 3/4


def test_symbol_probs_match_brute_force():
    for reels in (UNEVEN, REELS):
        p = symbol_probs(reels)
        brute = brute_force_probs(reels)
        for s in p:
            assert p[s] == pytest.approx(brute.get(s, 0))


def test_stats_hand_calculation():
    reels = [["A", "B"]] * 3
    st = stats(reels, {"A": 10, "B": 0})
    assert st["RTP"] == pytest.approx(1.25)                      # (1/8) * 10
    assert st["hit_freq"] == pytest.approx(1 / 8)
    assert st["std"] ** 2 == pytest.approx(12.5 - 1.25 ** 2)     # E[X^2] - RTP^2
    assert st["max_win"] == 10
    assert st["max_win_symbols"] == ["A"]
    assert st["max_win_prob"] == pytest.approx(1 / 8)


def test_closed_form_matches_enumeration():
    exact, formula = analytics(), stats(REELS, PAYTABLE)
    assert formula["RTP"] == pytest.approx(exact["RTP"])
    assert formula["hit_freq"] == pytest.approx(exact["hit_freq"])
    assert formula["std"] == pytest.approx(exact["std"])


@pytest.mark.parametrize("target", [0.92, 0.94, 0.96])
def test_tuned_paytable_hits_target_rtp(target):
    pay = tune_paytable(REELS, target, SHARES, JACKPOT)
    assert stats(REELS, pay)["RTP"] == pytest.approx(target, abs=1e-4)
    assert all(isinstance(v, int) and v > 0 for v in pay.values())


def test_tune_paytable_rejects_shares_that_leave_no_room_for_jackpot():
    with pytest.raises(AssertionError):
        tune_paytable(
            REELS,
            0.96,
            {"BAR": 0.6, "LEMON": 0.6},
            "7"
        )


def test_par_sheet_is_consistent():
    symbols, summary = build_par(REELS, PAYTABLE, sim_spins=20_000, seed=1)
    st = stats(REELS, PAYTABLE)
    assert symbols["RTP contribution"].sum() == pytest.approx(st["RTP"])
    assert symbols["Share of RTP"].sum() == pytest.approx(1)
    metrics = dict(zip(summary["Metric"], summary["Value"]))
    assert metrics["RTP (theory)"] == pytest.approx(st["RTP"], abs=1e-6)
    assert metrics["Total combinations"] == math.prod(len(r) for r in REELS)

def test_max_win_with_tied_symbols_sums_their_probabilities():
    reels = [["A", "B", "C", "C"]] * 3
    st = stats(reels, {"A": 50, "B": 50, "C": 2})
    assert st["max_win"] == 50
    assert st["max_win_symbols"] == ["A", "B"]
    assert st["max_win_prob"] == pytest.approx(2 * (1 / 4) ** 3)   # 1/32


def test_par_max_win_probability_counts_tied_symbols():
    reels = [["A", "B", "C", "C"]] * 3
    _, summary = build_par(reels, {"A": 50, "B": 50, "C": 2}, sim_spins=1_000, seed=1)
    metrics = dict(zip(summary["Metric"], summary["Value"]))
    assert metrics["Max win probability, 1 in"] == pytest.approx(32)

def test_par_sheet_for_custom_reels_matches_the_model():
    pay = {"A": 10, "B": 20}
    symbols, summary = build_par(UNEVEN, pay, sim_spins=50_000, seed=1)
    st = stats(UNEVEN, pay)
    metrics = dict(zip(summary["Metric"], summary["Value"]))

    # hand calculation: P(A) = 1/12, P(B) = 1/8, 24 combinations, 5 of them win
    assert metrics["Stops per reel"] == "3, 2, 4"
    assert metrics["Total combinations"] == 24
    assert metrics["RTP (theory)"] == pytest.approx(10 / 12 + 20 / 8, abs=1e-6)
    assert metrics["Hit frequency"] == pytest.approx(5 / 24, abs=1e-6)
    assert metrics["Max win (x bet)"] == 20
    assert metrics["Max win probability, 1 in"] == pytest.approx(8)

    # the same numbers must agree with stats() for this model
    assert metrics["RTP (theory)"] == pytest.approx(st["RTP"], abs=1e-6)
    assert metrics["Std dev of payout (x bet)"] == pytest.approx(st["std"], abs=1e-6)

    # symbol table
    by_symbol = symbols.set_index("Symbol")
    assert list(by_symbol["Combinations"]) == [2, 3]            # 2*1*1 and 1*1*3
    assert by_symbol.loc["A", "Count reel 1"] == 2
    assert by_symbol.loc["B", "Count reel 3"] == 3
    assert by_symbol.loc["B", "RTP contribution"] == pytest.approx(2.5)
    assert symbols["RTP contribution"].sum() == pytest.approx(st["RTP"])
    assert symbols["Share of RTP"].sum() == pytest.approx(1)

    # the simulation inside the PAR sheet played this model, not the default one
    assert abs(metrics["Simulation: deviation (in std errors)"]) < 4


def test_export_par_writes_the_custom_model_to_excel(tmp_path):
    path = tmp_path / "par.xlsx"
    export_par(UNEVEN, {"A": 10, "B": 20}, path=str(path), sim_spins=1_000, seed=1)

    df = pd.read_excel(path, sheet_name="Symbols")
    assert list(df["Symbol"]) == ["A", "B"]
    assert list(df["Pay (x bet)"]) == [10, 20]
    assert list(df["Combinations"]) == [2, 3]

    