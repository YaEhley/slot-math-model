from collections import Counter
from math import prod

from slot import REELS

SHARES = {"BAR": 0.16, "BELL": 0.16, "CHERRY": 0.20, "LEMON": 0.36}  # proportion of the RTP budget
JACKPOT = "7"   # takes the remaining budget


def symbol_probs(reels):
    """Probability of three-of-a-kind for each symbol (works for different strips)."""
    counts = [Counter(r) for r in reels]
    symbols = dict.fromkeys(s for r in reels for s in r)   # keeps order of appearance
    return {s: prod(c[s] / len(r) for c, r in zip(counts, reels)) for s in symbols}


def stats(reels, pay):
    """Exact RTP, hit frequency, std and max win for a given paytable."""
    p = symbol_probs(reels)
    reachable = [s for s in p if p[s] > 0]            # symbols that can form a win
    missing = [s for s in reachable if s not in pay]
    if missing:
        raise KeyError(f"no payout defined for symbols on the reels: {missing}")

    rtp = sum(p[s] * pay[s] for s in reachable)
    var = sum(p[s] * pay[s] ** 2 for s in reachable) - rtp ** 2
    max_win = max(pay[s] for s in reachable)
    top = [s for s in reachable if pay[s] == max_win]  # all symbols tied for the max win
    return {"RTP": rtp,
            "hit_freq": sum(p[s] for s in reachable if pay[s] > 0),
            "std": var ** 0.5,
            "max_win": max_win,
            "max_win_symbols": top,
            "max_win_prob": sum(p[s] for s in top)}


def tune_paytable(reels, target_rtp, shares, jackpot):
    """Integer paytable whose RTP equals target_rtp (up to rounding of the jackpot)."""
    assert sum(shares.values()) < 1, "shares of non-jackpot symbols must leave room for the jackpot"
    p = symbol_probs(reels)
    pay = {s: round(target_rtp * share / p[s]) for s, share in shares.items()}
    rest = sum(p[s] * pay[s] for s in pay)
    pay[jackpot] = round((target_rtp - rest) / p[jackpot])
    return {s: pay[s] for s in p}      # in reel order


if __name__ == "__main__":
    for target in (0.92, 0.94, 0.96):
        pay = tune_paytable(REELS, target, SHARES, JACKPOT)
        st = stats(REELS, pay)
        print(f"target {target:.2f}: {pay}")
        print(f"   RTP={st['RTP']:.6f}  hit={st['hit_freq']:.5f}  "
              f"std={st['std']:.2f}  max_win={st['max_win']}")