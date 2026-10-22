import random
from itertools  import product
#------------- Model parameters -------------#
REEL = ["7"] * 1 + ["BAR"] * 2 + ["BELL"] *3 + ["CHERRY"] * 5 + ["LEMON"] * 9
REELS = [REEL, REEL, REEL]

PAYTABLE = {"7": 790, "BAR": 154, "BELL": 46, "CHERRY": 12, "LEMON": 4}

#------------- Rules of the game -------------#
"""Payout per spin: only three matching symbols."""
def evaluate(symbols, bet=1, pay=PAYTABLE):
    a, b, c = symbols
    return bet * pay[a] if a == b == c else 0

def spin(rng, reels=REELS):
    return tuple(rng.choice(reel) for reel in reels)

def analytics(reels=REELS, pay=PAYTABLE):
    n = 1
    for reel in reels:
        n *= len(reel)
    total = hits = sq = 0
    for combo in product(*reels):
        w = evaluate(combo, pay=pay)
        total += w
        sq += w * w
        hits += w > 0
    rtp = total / n
    var = sq / n - rtp ** 2
    return {"combinations": n, "RTP": rtp, "hit_freq": hits / n,
            "variance": var, "std": var ** 0.5}

#------------- Monte Carlo -------------#
def simulate(n_spins, seed=None, bet=1, reels=REELS, pay=PAYTABLE):
    rng = random.Random(seed)
    total = hits = 0
    for _ in range(n_spins):
        w = evaluate(spin(rng, reels), bet, pay)
        total += w
        hits += w > 0
    return {"spins": n_spins, "RTP": total / (n_spins * bet), "hit_freq": hits / n_spins}

if __name__ == "__main__":
    print("Analytics:", analytics())
    print("Simulation:", simulate(1_000_000, seed=42))
