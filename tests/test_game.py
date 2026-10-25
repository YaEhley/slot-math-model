import math
import random
from itertools import product

import pandas as pd
import pytest

from config import REELS, PAYTABLE, SHARES, JACKPOT
from game import evaluate, spin
from simulate import simulate_slow, simulate_fast
from stats import (analytics, enumerate_stats, symbol_probs, tune_paytable,
                   build_par, export_par)

UNEVEN = [["A", "A", "B"], ["A", "B"], ["A", "B", "B", "B"]]   # a different strip on each reel
TIED = [["A", "B", "C", "C"]] * 3
N = 200_000


def brute_force_probs(reels):
    """Three-of-a-kind probability per symbol, found by counting all stop combinations."""
    total, hits = 0, {}
    for combo in product(*reels):
        total += 1
        if len(set(combo)) == 1:
            hits[combo[0]] = hits.get(combo[0], 0) + 1
    return {s: n / total for s, n in hits.items()}


# ---------- round logic ----------
def test_paytable_covers_every_reel_symbol():
    assert {s for reel in REELS for s in reel} <= set(PAYTABLE)


@pytest.mark.parametrize("symbol", list(PAYTABLE))
def test_three_of_a_kind_pays_paytable_times_bet(symbol):
    assert evaluate((symbol,) * 3) == PAYTABLE[symbol]
    assert evaluate((symbol,) * 3, bet=5) == 5 * PAYTABLE[symbol]


@pytest.mark.parametrize("combo", [
    ("7", "7", "BAR"), ("7", "BAR", "7"), ("BAR", "7", "7"), ("7", "BAR", "BELL"),
])
def test_anything_but_three_of_a_kind_pays_zero(combo):
    assert evaluate(combo) == 0


def test_spin_returns_one_symbol_from_each_reel():
    rng = random.Random(0)
    for _ in range(1000):
        result = spin(rng)
        assert len(result) == len(REELS)
        assert all(sym in reel for sym, reel in zip(result, REELS))


# ---------- exact math ----------
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


def test_analytics_hand_calculation():
    st = analytics([["A", "B"]] * 3, {"A": 10, "B": 0})
    assert st["RTP"] == pytest.approx(1.25)                      # (1/8) * 10
    assert st["hit_freq"] == pytest.approx(1 / 8)
    assert st["std"] ** 2 == pytest.approx(12.5 - 1.25 ** 2)     # E[X^2] - RTP^2
    assert st["max_win"] == 10
    assert st["max_win_symbols"] == ["A"]
    assert st["max_win_prob"] == pytest.approx(1 / 8)


@pytest.mark.parametrize("reels, pay", [(REELS, PAYTABLE), (UNEVEN, {"A": 10, "B": 20})])
def test_closed_form_matches_enumeration(reels, pay):
    formula, exact = analytics(reels, pay), enumerate_stats(reels, pay)
    assert formula["RTP"] == pytest.approx(exact["RTP"])
    assert formula["hit_freq"] == pytest.approx(exact["hit_freq"])
    assert formula["std"] == pytest.approx(exact["std"])


def test_enumeration_counts_all_combinations():
    assert enumerate_stats()["combinations"] == math.prod(len(r) for r in REELS)
    exact = enumerate_stats(UNEVEN, {"A": 10, "B": 20})
    assert exact["combinations"] == 24
    assert exact["RTP"] == pytest.approx(10 / 12 + 20 / 8)


def test_max_win_with_tied_symbols_sums_their_probabilities():
    st = analytics(TIED, {"A": 50, "B": 50, "C": 2})
    assert st["max_win"] == 50
    assert st["max_win_symbols"] == ["A", "B"]
    assert st["max_win_prob"] == pytest.approx(2 * (1 / 4) ** 3)   # 1/32


# ---------- tuning ----------
@pytest.mark.parametrize("target", [0.92, 0.94, 0.96])
def test_tuned_paytable_hits_target_rtp(target):
    pay = tune_paytable(REELS, target, SHARES, JACKPOT)
    assert analytics(REELS, pay)["RTP"] == pytest.approx(target, abs=1e-4)
    assert all(isinstance(v, int) and v > 0 for v in pay.values())


def test_tune_paytable_rejects_shares_that_leave_no_room_for_jackpot():
    with pytest.raises(ValueError):
        tune_paytable(REELS, 0.96, {"BAR": 0.6, "LEMON": 0.6}, "7")


# ---------- simulation ----------
@pytest.fixture(scope="module")
def theory():
    return analytics()


@pytest.fixture(scope="module")
def slow():
    return simulate_slow(N, seed=42)


@pytest.fixture(scope="module")
def fast():
    return simulate_fast(2_000_000, seed=42)


def test_simulations_are_reproducible_with_seed():
    assert simulate_slow(10_000, seed=1) == simulate_slow(10_000, seed=1)
    assert simulate_slow(10_000, seed=1) != simulate_slow(10_000, seed=2)
    assert simulate_fast(100_000, seed=1) == simulate_fast(100_000, seed=1)
    assert simulate_fast(100_000, seed=1) != simulate_fast(100_000, seed=2)


def test_fast_result_does_not_depend_on_number_of_workers():
    one = simulate_fast(400_000, seed=3, chunk=100_000, workers=1)
    two = simulate_fast(400_000, seed=3, chunk=100_000, workers=2)
    assert one == two


def test_chunking_does_not_change_the_number_of_spins():
    res = simulate_fast(1_050_000, seed=0, chunk=500_000)         # 500k + 500k + 50k
    assert res["spins"] == 1_050_000
    assert sum(res["wins_by_symbol"].values()) / res["spins"] == pytest.approx(res["hit_freq"])


@pytest.mark.parametrize("sim_name, n", [("slow", N), ("fast", 2_000_000)])
def test_simulated_rtp_and_hit_frequency_within_4_standard_errors(request, theory, sim_name, n):
    sim = request.getfixturevalue(sim_name)
    assert abs(sim["RTP"] - theory["RTP"]) < 4 * theory["std"] / math.sqrt(n)
    p = theory["hit_freq"]
    assert abs(sim["hit_freq"] - p) < 4 * math.sqrt(p * (1 - p) / n)


def test_simulations_use_the_model_they_are_given():
    reels, pay = [["A"], ["A"], ["A"]], {"A": 5}
    for res in (simulate_slow(1_000, seed=1, reels=reels, pay=pay),
                simulate_fast(1_000, seed=1, reels=reels, pay=pay)):
        assert res["RTP"] == 5 and res["hit_freq"] == 1


# ---------- PAR sheet ----------
def test_par_sheet_is_consistent():
    symbols, summary = build_par(REELS, PAYTABLE, sim_spins=20_000, seed=1)
    st = analytics()
    assert symbols["RTP contribution"].sum() == pytest.approx(st["RTP"])
    assert symbols["Share of RTP"].sum() == pytest.approx(1)
    metrics = dict(zip(summary["Metric"], summary["Value"]))
    assert metrics["RTP (theory)"] == pytest.approx(st["RTP"], abs=1e-6)
    assert metrics["Total combinations"] == math.prod(len(r) for r in REELS)


def test_par_sheet_describes_the_model_it_is_given():
    pay = tune_paytable(REELS, 0.92, SHARES, JACKPOT)              # differs from PAYTABLE
    symbols, summary = build_par(REELS, pay, sim_spins=20_000, seed=1)
    metrics = dict(zip(summary["Metric"], summary["Value"]))
    assert metrics["RTP (theory)"] == pytest.approx(0.92, abs=1e-4)
    assert list(symbols["Pay (x bet)"]) == list(pay.values())


def test_par_sheet_for_custom_reels_matches_the_model():
    pay = {"A": 10, "B": 20}
    symbols, summary = build_par(UNEVEN, pay, sim_spins=50_000, seed=1)
    st = analytics(UNEVEN, pay)
    metrics = dict(zip(summary["Metric"], summary["Value"]))

    # hand calculation: P(A) = 1/12, P(B) = 1/8, 24 combinations, 5 of them win
    assert metrics["Stops per reel"] == "3, 2, 4"
    assert metrics["Total combinations"] == 24
    assert metrics["RTP (theory)"] == pytest.approx(10 / 12 + 20 / 8, abs=1e-6)
    assert metrics["Hit frequency"] == pytest.approx(5 / 24, abs=1e-6)
    assert metrics["Max win (x bet)"] == 20
    assert metrics["Max win probability, 1 in"] == pytest.approx(8)
    assert metrics["Std dev of payout (x bet)"] == pytest.approx(st["std"], abs=1e-6)

    by_symbol = symbols.set_index("Symbol")
    assert list(by_symbol["Combinations"]) == [2, 3]
    assert by_symbol.loc["B", "RTP contribution"] == pytest.approx(2.5)
    assert abs(metrics["Simulation: deviation (in std errors)"]) < 4   # simulated this model


def test_par_max_win_probability_counts_tied_symbols():
    _, summary = build_par(TIED, {"A": 50, "B": 50, "C": 2}, sim_spins=1_000, seed=1)
    metrics = dict(zip(summary["Metric"], summary["Value"]))
    assert metrics["Max win probability, 1 in"] == pytest.approx(32)


def test_export_par_writes_the_custom_model_to_excel(tmp_path):
    path = tmp_path / "par.xlsx"
    export_par(UNEVEN, {"A": 10, "B": 20}, path=str(path), sim_spins=1_000, seed=1)
    df = pd.read_excel(path, sheet_name="Symbols")
    assert list(df["Symbol"]) == ["A", "B"]
    assert list(df["Pay (x bet)"]) == [10, 20]
    assert list(df["Combinations"]) == [2, 3]