import random
from itertools  import product
"""Game config: reel strips (symbol weights) and paytable. Edit weights here only."""
REEL = ["7"] * 1 + ["BAR"] * 2 + ["BELL"] *3 + ["CHERRY"] * 5 + ["LEMON"] * 9
REELS = [REEL, REEL, REEL]

PAYTABLE = {"7": 790, "BAR": 154, "BELL": 46, "CHERRY": 12, "LEMON": 4}

# Design parameters for tuning (see stats.tune_paytable)
TARGET_RTP = 0.96
SHARES = {"BAR": 0.16, "BELL": 0.16, "CHERRY": 0.20, "LEMON": 0.36}      # share of the RTP budget
JACKPOT = "7"                       # takes the remainder of the budget