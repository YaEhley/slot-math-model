import math

import pytest

from slot import analytics, simulate
from simulation import play, cumulative_rtp

N = 200_000


@pytest.fixture(scope="module")
def sim():
    return simulate(N, seed=42)       # one run shared by the tests below


@pytest.fixture(scope="module")
def theory():
    return analytics()


def test_simulation_is_reproducible_with_seed():
    assert simulate(10_000, seed=1) == simulate(10_000, seed=1)
    assert simulate(10_000, seed=1) != simulate(10_000, seed=2)


def test_simulated_rtp_within_4_standard_errors_of_theory(sim, theory):
    se = theory["std"] / math.sqrt(N)
    assert abs(sim["RTP"] - theory["RTP"]) < 4 * se


def test_simulated_hit_frequency_within_4_standard_errors_of_theory(sim, theory):
    p = theory["hit_freq"]
    se = math.sqrt(p * (1 - p) / N)
    assert abs(sim["hit_freq"] - p) < 4 * se


def test_play_log_is_consistent():
    log = play(1_000, seed=7, bet=2)
    total_win = sum(r["win"] for r in log)
    assert [r["spin"] for r in log] == list(range(1, 1_001))
    assert log[-1]["balance"] == total_win - sum(r["bet"] for r in log)
    assert cumulative_rtp(log)[-1] == pytest.approx(total_win / (1_000 * 2))


def test_play_and_simulate_agree_for_same_seed():
    log = play(20_000, seed=5)
    sim = simulate(20_000, seed=5)
    assert sum(r["win"] for r in log) / len(log) == pytest.approx(sim["RTP"])
    assert sum(r["win"] > 0 for r in log) / len(log) == pytest.approx(sim["hit_freq"])