"""Round logic: one spin and its payout."""
from config import REELS, PAYTABLE

def spin(rng, reels=REELS):
    """One round: an independent random stop on every reel."""
    return tuple(rng.choice(reel) for reel in reels)

def evaluate(symbols, bet=1, pay=PAYTABLE):
    """Payout of one round: only three identical symbols pay."""
    a, b, c = symbols
    return bet * pay[a] if a == b == c else 0