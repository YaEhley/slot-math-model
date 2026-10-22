import math
import os
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np

from slot import REELS, PAYTABLE, simulate, analytics
from tuning import symbol_probs

WORKERS = 4

SYMBOLS = list(PAYTABLE)                          # fixed order: symbol -> integer id
ID = {s: i for i, s in enumerate(SYMBOLS)}
PAY = np.array([PAYTABLE[s] for s in SYMBOLS], dtype=np.int64)
REEL_IDS = [np.array([ID[s] for s in reel], dtype=np.int8) for reel in REELS]


def _chunk_counts(n, seed_seq):
    """Plays n spins; returns how many times each symbol won (three of a kind)."""
    rng = np.random.default_rng(seed_seq)
    a, b, c = (ids[rng.integers(0, len(ids), size=n, dtype=np.int32)] for ids in REEL_IDS)
    winners = a[(a == b) & (b == c)]              # symbol ids of winning spins
    return np.bincount(winners, minlength=len(SYMBOLS))


def _summarize(counts, n):
    total = int(counts @ PAY)                     # sum of payouts
    sq = int(counts @ PAY ** 2)                   # sum of squared payouts
    rtp = total / n
    std = math.sqrt(sq / n - rtp ** 2)
    return {"spins": n, "RTP": rtp, "hit_freq": int(counts.sum()) / n,
            "std": std, "std_error": std / math.sqrt(n),
            "wins_by_symbol": dict(zip(SYMBOLS, counts.tolist()))}


def simulate_fast(n_spins, seed=0, chunk=5_000_000, workers=1):
    """Vectorized Monte Carlo. The result depends on (seed, chunk), not on workers."""
    sizes = [chunk] * (n_spins // chunk)
    if n_spins % chunk:
        sizes.append(n_spins % chunk)
    seeds = np.random.SeedSequence(seed).spawn(len(sizes))

    if workers == 1:
        parts = list(map(_chunk_counts, sizes, seeds))
    else:
        with ProcessPoolExecutor(workers) as pool:
            parts = list(pool.map(_chunk_counts, sizes, seeds))
    return _summarize(np.sum(parts, axis=0), n_spins)


if __name__ == "__main__":
    # 1) speed: pure Python vs NumPy, same number of spins
    n_small = 1_000_000
    t = time.perf_counter()
    simulate(n_small, seed=42)
    t_py = time.perf_counter() - t
    t = time.perf_counter()
    simulate_fast(n_small, seed=42)
    t_np = time.perf_counter() - t
    print(f"{n_small:,} spins: pure Python {t_py:.2f} s, NumPy {t_np:.2f} s, x{t_py / t_np:.0f} faster")

    # 2) large run on all cores
    N = 100_000_000
    t = time.perf_counter()
    res = simulate_fast(N, seed=42, workers=WORKERS)
    dt = time.perf_counter() - t
    theory = analytics()
    dev = (res["RTP"] - theory["RTP"]) / res["std_error"]
    print(f"\n{N:,} spins on {WORKERS} workers: {dt:.1f} s ({N / dt / 1e6:.1f} M spins/s)")
    print(f"RTP sim = {res['RTP']:.5f}  theory = {theory['RTP']:.5f}  "
          f"deviation = {dev:+.2f} std errors (std error = {res['std_error']:.5f})")
    print(f"hit freq sim = {res['hit_freq']:.6f}  theory = {theory['hit_freq']:.6f}")

    # 3) wins per symbol vs expectation
    p = symbol_probs(REELS)
    print(f"\n{'symbol':>8} {'observed':>12} {'expected':>14} {'z':>6}")
    for s in SYMBOLS:
        exp = N * p[s]
        obs = res["wins_by_symbol"][s]
        z = (obs - exp) / math.sqrt(exp * (1 - p[s]))
        print(f"{s:>8} {obs:>12,} {exp:>14,.0f} {z:>+6.2f}")