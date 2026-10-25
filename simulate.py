"""Monte Carlo: a reference loop over the real round logic and a fast vectorized version."""
import math
import random
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from itertools import repeat

import numpy as np

from config import REELS, PAYTABLE
from game import spin, evaluate

def summarize(counts, n, pay):
    """Turns counts of winning symbols (three of a kind) into RTP, hit frequency, std, ..."""
    total = sum(c * pay[s] for s, c in counts.items())
    sq = sum(c * pay[s] ** 2 for s, c in counts.items())
    hits = sum(c for s, c in counts.items() if pay[s] > 0)
    rtp = total / n
    std = math.sqrt(max(sq / n - rtp ** 2, 0.0))
    return {"spins": n, "RTP": rtp, "hit_freq": hits / n, "std": std,
            "std_error": std / math.sqrt(n),
            "wins_by_symbol": {s: counts.get(s, 0) for s in pay}}


def simulate_slow(n_spins, seed=None, reels=REELS, pay=PAYTABLE):
    """Reference implementation: plays the real round logic from game.py, one spin at a time."""
    rng = random.Random(seed)
    counts = Counter()
    for _ in range(n_spins):
        symbols = spin(rng, reels)
        if evaluate(symbols, 1, pay) > 0:
            counts[symbols[0]] += 1
    return summarize(counts, n_spins, pay)


def _chunk_counts(n, seed_seq, reel_ids, n_symbols):
    """Plays n spins at once; returns how many times each symbol won (three of a kind)."""
    rng = np.random.default_rng(seed_seq)
    first, *rest = (ids[rng.integers(0, len(ids), size=n, dtype=np.int32)] for ids in reel_ids)
    win = np.ones(n, dtype=bool)
    for other in rest:
        win &= (other == first)
    return np.bincount(first[win], minlength=n_symbols)


def simulate_fast(n_spins, seed=0, chunk=5_000_000, workers=1, reels=REELS, pay=PAYTABLE):
    """Vectorized Monte Carlo. The result depends on (seed, chunk, model), not on workers."""
    symbols = list(pay)
    ids = {s: i for i, s in enumerate(symbols)}
    reel_ids = [np.array([ids[s] for s in reel], dtype=np.int8) for reel in reels]

    sizes = [chunk] * (n_spins // chunk) + ([n_spins % chunk] if n_spins % chunk else [])
    seeds = np.random.SeedSequence(seed).spawn(len(sizes))
    args = (sizes, seeds, repeat(reel_ids), repeat(len(symbols)))

    if workers == 1:
        parts = list(map(_chunk_counts, *args))
    else:
        with ProcessPoolExecutor(workers) as pool:
            parts = list(pool.map(_chunk_counts, *args))
    counts = np.sum(parts, axis=0).tolist()
    return summarize(dict(zip(symbols, counts)), n_spins, pay)
