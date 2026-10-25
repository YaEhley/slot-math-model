# Simple 3-Reel Slot: Math Model

Math model of a 3-reel, 1-payline slot (payout only for three identical symbols),
with exact analytics, Monte Carlo simulation, PAR sheet.
**Live demo:** [yaehley.github.io/slot-math-model](https://yaehley.github.io/slot-math-model/)
(a JavaScript port of the model for illustration; the actual math, tests and simulations are in Python)

## Structure
| File | Role |
|---|---|
| `config.py` | reel strips (symbol weights), paytable, tuning parameters |
| `game.py` | logic of one round |
| `simulate.py` | Monte Carlo: reference loop and vectorized NumPy version |
| `stats.py` | exact analytics, paytable tuning, validation, PAR sheet |

## Setup
```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

## Usage
```bash
python stats.py        # tuning, validation on 100M spins, PAR sheet -> par_sheet.xlsx
python benchmark.py    # speed comparison
pytest                 # tests
```

## How to run tests
```bash
pytest
```

## Math

### Game definition
- 3 reels, 1 payline, 20 stops per reel (all stops equally likely, reels spin independently).
- Payout only for three identical symbols; any other result pays 0.
- Payouts are multipliers of the bet.

Reel strip (identical on all three reels):

| Symbol | Stops | P(symbol on one reel) | Pay (x bet) |
|--------|-------|-----------------------|-------------|
| 7      | 1     | 5%                    | 790         |
| BAR    | 2     | 10%                   | 154         |
| BELL   | 3     | 15%                   | 46          |
| CHERRY | 5     | 25%                   | 12          |
| LEMON  | 9     | 45%                   | 4           |

### Probabilities and RTP
Total number of stop combinations: 20 x 20 x 20 = 8000.

The probability of three identical symbols *s* with *c_s* stops per reel is

    P(s) = (c_s / 20)^3

and the return to player is the expected payout per unit bet:

    RTP = sum over s of P(s) * pay(s)

| Symbol | Combinations | P(three) | 1 in | RTP contribution |
|--------|--------------|----------|------|------------------|
| 7      | 1            | 0.0125%  | 8000 | 9.875%           |
| BAR    | 8            | 0.1000%  | 1000 | 15.400%          |
| BELL   | 27           | 0.3375%  | 296  | 15.525%          |
| CHERRY | 125          | 1.5625%  | 64   | 18.750%          |
| LEMON  | 729          | 9.1125%  | 11   | 36.450%          |
| **Total** | **890**   | **11.125%** |   | **96.000%**      |

## Performance

Environment: Intel64 Family 6 Model 142, 4 logical processors, Windows 10, Python 3.14.6, NumPy 2.5.4.

**Implementations compared** (10,000,000 spins each, median of 5 runs, `benchmark.py`):

| Implementation | Median time (s) | Throughput (M spins/s) |
|---|---|---|
| Pure Python | 40.00 | 0.25 |
| NumPy, 1 worker | 0.33 | 30.07 |
| NumPy, 4 workers | 1.10 | 9.09 |

Vectorization gives about a 120x speed-up over pure Python.
On 10M spins, 4 workers are slower than 1 because process start-up on Windows is a fixed cost of roughly a second.

**Scaling with the number of spins** (NumPy, chunk 2M, `benchmark_large.py`):

| Spins | 1 worker | 4 workers | Speed-up |
|---|---|---|---|
| 100,000,000 (`benchmark_scaling.py`, best of 3 chunk sizes) | 3.6 s | 2.7 s | 1.3x |
| 1,000,000,000 | 34.8 s (28.7 M spins/s) | 18.1 s (55.1 M spins/s) | 1.9x |

Chunk size (0.5M-5M spins) had no measurable effect on speed.
Parallelism pays off on large runs only, and gives less than 4x on a 4-thread laptop CPU.

**Accuracy check on 1,000,000,000 spins:** RTP = 0.96052 vs 0.96000 theoretical
(+1.6 standard errors, standard error = 0.00033). The result is identical for 1 and 4 workers:
it depends on the seed and the chunk size, not on the number of processes.

### Key metrics
- **RTP:** 96.00%
- **Hit frequency:** 890 / 8000 = 11.125% (about 1 win in 9 spins)
- **Max win:** 790x, with probability 1 in 8000
- **Variance:** Var = E[X^2] - RTP^2 = 112.58 - 0.9216 = 111.66, where E[X^2] = sum of P(s) * pay(s)^2
- **Standard deviation of one spin:** about 10.57 (in units of the bet)

### Paytable tuning
`tuning.py` builds the paytable from a target RTP. Each non-top symbol gets a fixed share of the RTP budget,
pay(s) = target * share(s) / P(s) (rounded to an integer), and the top symbol takes the remainder so that
the total matches the target. Moving budget from the jackpot to frequent small wins keeps the RTP and
the hit frequency but lowers the volatility.

### Validation
Results are cross-checked three ways:
1. closed-form formulas (`tuning.py`),
2. full enumeration of all 8000 combinations (`slot.analytics`),
3. Monte Carlo simulation (`simulation.py`, `slot.simulate`).

The standard error of a simulated RTP over N spins is sigma / sqrt(N). With sigma = 10.57,
1,000,000 spins give about +-0.0106 (one standard error), so a single run can differ from 96% by
more than a percentage point. About 4.3 million spins are needed for +-1 percentage point at 95% confidence.
The unit tests check the simulation against theory within 4 standard errors.

Simulation result (1,000,000 spins, seed 42): RTP = 0.955208 , hit frequency = 0.11125

## Limitations
- RNG is Python's `random` (not certified).