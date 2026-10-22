import random
from slot import spin, evaluate

#---------- Independent simulations ----------#
def play(n_spins, seed=None, bet=1):
    """Plays n_spins spins and returns a log: one entry for each spin."""
    rng = random.Random(seed)
    log = []
    balance = 0
    for i in range(1, n_spins + 1):
        symbols = spin(rng)
        win = evaluate(symbols, bet)
        balance += win - bet
        log.append({"spin": i, "r1": symbols[0], "r2": symbols[1], "r3": symbols[2],
                    "bet": bet, "win": win, "balance": balance})
    return log


def cumulative_rtp(log):
    """RTP after each spin: total winnings / total stakes."""
    total_win = total_bet = 0
    result = []
    for row in log:
        total_win += row["win"]
        total_bet += row["bet"]
        result.append(total_win / total_bet)
    return result

