import time

from fast_sim import simulate_fast

N = 1_000_000_000
CHUNK = 2_000_000
SEED = 42

if __name__ == "__main__":
    for workers in (1, 4):
        t = time.perf_counter()
        res = simulate_fast(N, seed=SEED, chunk=CHUNK, workers=workers)
        dt = time.perf_counter() - t
        print(f"{workers} worker(s): {dt:.1f} s, {N / dt / 1e6:.1f} M spins/s, "
              f"RTP = {res['RTP']:.5f} (std error {res['std_error']:.5f})")