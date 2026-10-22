import math

import pytest

from slot import analytics
from fast_sim import simulate_fast

N = 2_000_000


def test_reproducible_with_seed():
    assert simulate_fast(100_000, seed=1) == simulate_fast(100_000, seed=1)
    assert simulate_fast(100_000, seed=1) != simulate_fast(100_000, seed=2)


def test_result_does_not_depend_on_number_of_workers():
    one = simulate_fast(400_000, seed=3, chunk=100_000, workers=1)
    two = simulate_fast(400_000, seed=3, chunk=100_000, workers=2)
    assert one == two


def test_rtp_and_hit_frequency_within_4_standard_errors_of_theory():
    theory = analytics()
    res = simulate_fast(N, seed=42)
    assert abs(res["RTP"] - theory["RTP"]) < 4 * res["std_error"]
    p = theory["hit_freq"]
    assert abs(res["hit_freq"] - p) < 4 * math.sqrt(p * (1 - p) / N)


def test_chunking_does_not_change_the_number_of_spins():
    res = simulate_fast(1_050_000, seed=0, chunk=500_000)    # 500k + 500k + 50k
    assert res["spins"] == 1_050_000
    assert sum(res["wins_by_symbol"].values()) / res["spins"] == pytest.approx(res["hit_freq"])