import math
import random

import pytest

from slot import REELS, PAYTABLE, evaluate, analytics, spin


def test_paytable_covers_every_reel_symbol():
    on_reels = {s for reel in REELS for s in reel}
    assert on_reels <= set(PAYTABLE)


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


def test_analytics_enumerates_all_combinations():
    assert analytics()["combinations"] == math.prod(len(r) for r in REELS)