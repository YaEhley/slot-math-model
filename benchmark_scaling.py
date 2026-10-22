import statistics
import time

from fast_sim import simulate_fast

N = 100_000_000
REPEATS = 3
SEED = 42

if __name__ == "__main__":
    print("| Workers | Chunk | Median time (s) | Throughput (M spins/s) |")
    print("|---|---|---|---|")
    for workers in (1, 2, 4):
        for chunk in (500_000, 1_000_000, 5_000_000):
            times = []
            for _ in range(REPEATS):
                t = time.perf_counter()
                simulate_fast(N, seed=SEED, chunk=chunk, workers=workers)
                times.append(time.perf_counter() - t)
            med = statistics.median(times)
            print(f"| {workers} | {chunk:,} | {med:.2f} | {N / med / 1e6:.1f} |")