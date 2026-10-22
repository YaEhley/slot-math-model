from collections import Counter
from itertools import product

import matplotlib.pyplot as plt

from slot import  analytics, evaluate, REELS, simulate
from simulation import play, cumulative_rtp

def win_distribution(log):
    """A comparison of the observed frequency of each payout with the theoretical frequency."""
    n = len(log)
    observed = Counter(row["win"] for row in log)
    theory = Counter(evaluate(c) for c in product(*REELS))
    n_theory = sum(theory.values())
    print(f"{'winnings':>8} {'observed':>12} {'theory':>10}")
    for w in sorted(theory):
        print(f"{w:>8} {observed[w] / n:>12.5f} {theory[w] / n_theory:>10.5f}")

def rtp_spread(n_spins=1_000_000, n_runs=20, seed=42):
    """RTP of n_runs independent simulations (different seeds)."""
    return [simulate(n_spins, seed=seed + i)["RTP"] for i in range(n_runs)]

def main():
    target = analytics()["RTP"]
    log = play(100_000, seed = 42)
    win_distribution(log)

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(9, 10))

    ax1.plot(cumulative_rtp(log))
    ax1.axhline(target, color="red", linestyle="--", label=f"theoretical RTP = {target:.4f}")
    ax1.set_xscale("log")
    ax1.set_xlabel("spins")
    ax1.set_ylabel("cumulative RTP")
    ax1.legend()

    ax2.plot([row["balance"] for row in log])
    ax2.set_xlabel("spins")
    ax2.set_ylabel("player balance (in bets)")

    ax3.hist(rtp_spread(), bins=10)
    ax3.axvline(target, color="red", linestyle="--")
    ax3.set_xlabel("RTP of a 1,000,000-spin run")
    ax3.set_ylabel("runs")

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()