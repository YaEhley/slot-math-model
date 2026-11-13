import os
import platform
import statistics
import sys
import time

import numpy as np

from simulate import simulate_slow, simulate_fast

SEED = 42
WORKERS = 4

# Mode 1: compare the implementations on the same number of spins
N = 10_000_000
CHUNK = 2_500_000       # 4 chunks, so each of the 4 workers gets work
REPEATS = 5

# Mode 2: scaling with the number of spins (NumPy only)
SCALING_SIZES = [(100_000_000, 3), (1_000_000_000, 1)]      # (spins, repeats)
SCALING_CHUNK = 2_000_000


def measure(fn, repeats):
    times = []
    for _ in range(repeats):
        t = time.perf_counter()
        fn()
        times.append(time.perf_counter() - t)
    return times


def print_environment():
    print(f"- CPU: {platform.processor()} ({os.cpu_count()} logical processors)")
    print(f"- OS: {platform.platform()}")
    print(f"- Python: {platform.python_version()}, NumPy: {np.__version__}")


def compare():
    implementations = {
        "Pure Python": lambda: simulate_slow(N, seed=SEED),
        "NumPy, 1 worker": lambda: simulate_fast(N, seed=SEED, chunk=CHUNK, workers=1),
        f"NumPy, {WORKERS} workers": lambda: simulate_fast(N, seed=SEED, chunk=CHUNK, workers=WORKERS),
    }
    print_environment()
    print(f"- Spins per run: {N:,}; measurements per implementation: {REPEATS}; "
          f"workers: {WORKERS}, chunk: {CHUNK:,}\n")
    print("| Implementation | Spins per run | Median time (s) | Min-max (s) | Throughput (M spins/s) |")
    print("|---|---|---|---|---|")
    for name, fn in implementations.items():
        times = measure(fn, REPEATS)
        med = statistics.median(times)
        print(f"| {name} | {N:,} | {med:.2f} | {min(times):.2f}-{max(times):.2f} | {N / med / 1e6:.2f} |")


def scaling():
    print_environment()
    print(f"- chunk: {SCALING_CHUNK:,}; workers: 1 vs {WORKERS}; reported time is the median of the repeats\n")
    print(f"| Spins | Repeats | 1 worker (s) | {WORKERS} workers (s) | Speed-up | {WORKERS} workers (M spins/s) |")
    print("|---|---|---|---|---|---|")
    for n, repeats in SCALING_SIZES:
        t1 = statistics.median(measure(
            lambda: simulate_fast(n, seed=SEED, chunk=SCALING_CHUNK, workers=1), repeats))
        t4 = statistics.median(measure(
            lambda: simulate_fast(n, seed=SEED, chunk=SCALING_CHUNK, workers=WORKERS), repeats))
        print(f"| {n:,} | {repeats} | {t1:.1f} | {t4:.1f} | {t1 / t4:.1f}x | {n / t4 / 1e6:.1f} |")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "scaling":
        scaling()
    else:
        compare()