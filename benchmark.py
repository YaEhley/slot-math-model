import os
import platform
import statistics
import time

import numpy as np

from slot import simulate
from fast_sim import simulate_fast

N = 10_000_000          # same number of spins for every implementation
CHUNK = 2_500_000       # 4 chunks, so each of the 4 workers gets work
WORKERS = 4
REPEATS = 5
SEED = 42

IMPLEMENTATIONS = {
    "Pure Python": lambda: simulate(N, seed=SEED),
    "NumPy, 1 worker": lambda: simulate_fast(N, seed=SEED, chunk=CHUNK, workers=1),
    f"NumPy, {WORKERS} workers": lambda: simulate_fast(N, seed=SEED, chunk=CHUNK, workers=WORKERS),
}


def measure(fn, repeats):
    times = []
    for _ in range(repeats):
        t = time.perf_counter()
        fn()
        times.append(time.perf_counter() - t)
    return times


if __name__ == "__main__":
    print(f"- CPU: {platform.processor()} ({os.cpu_count()} logical processors)")
    print(f"- OS: {platform.platform()}")
    print(f"- Python: {platform.python_version()}, NumPy: {np.__version__}")
    print(f"- Spins per run: {N:,}; measurements per implementation: {REPEATS}; "
          f"workers: {WORKERS}, chunk: {CHUNK:,}\n")

    print("| Implementation | Spins per run | Median time (s) | Min-max (s) | Throughput (M spins/s) |")
    print("|---|---|---|---|---|")
    for name, fn in IMPLEMENTATIONS.items():
        times = measure(fn, REPEATS)
        med = statistics.median(times)
        print(f"| {name} | {N:,} | {med:.2f} | {min(times):.2f}-{max(times):.2f} | {N / med / 1e6:.2f} |")