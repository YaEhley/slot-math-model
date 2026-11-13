# Simple 3-Reel Slot: Math Model

Math model of a 3-reel, 1-payline slot (payout only for three identical symbols),
with exact analytics, Monte Carlo simulation and a PAR sheet export to Excel.

**Live demo:** [yaehley.github.io/slot-math-model](https://yaehley.github.io/slot-math-model/)
(a JavaScript port of the model for illustration; the actual math, tests and simulations are in Python)

## Structure
| File | Role |
|---|---|
| `config.py` | reel strips (symbol weights), paytable, tuning parameters |
| `game.py` | logic of one round |
| `simulate.py` | Monte Carlo: reference loop and vectorized NumPy version |
| `stats.py` | exact analytics, paytable tuning, validation, PAR sheet |
| `tests/test_game.py` | pytest suite: round logic, exact math, tuning, simulations, PAR sheet |
| `benchmark.py` | speed comparison and scaling (`python benchmark.py`, `python benchmark.py scaling`) |
| `docs/index.html` | JavaScript demo for GitHub Pages |

## Setup
```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

## Usage
```bash
python stats.py               # tuning, validation on 100M spins, PAR sheet -> par_sheet.xlsx
python benchmark.py           # speed comparison, takes a few minutes
pytest                        # run the tests
python benchmark.py scaling   # scaling with the number of spins
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

### Key metrics
- **RTP:** 96.00%
- **Hit frequency:** 890 / 8000 = 11.125% (about 1 win in 9 spins)
- **Max win:** 790x, with probability 1 in 8000
- **Variance:** Var = E[X^2] - RTP^2 = 112.58 - 0.9216 = 111.66, where E[X^2] = sum of P(s) * pay(s)^2
- **Standard deviation of one spin:** about 10.57 (in units of the bet)

### Paytable tuning

`tune_paytable` in `stats.py` builds the paytable from a target RTP (`TARGET_RTP`, `SHARES` and `JACKPOT` in `config.py`). Each non-top symbol gets a fixed share of the RTP budget, pay(s) = target * share(s) / P(s), rounded to an integer, and the top symbol takes the remainder so that the total matches the target. Moving budget from the jackpot to frequent small wins keeps the hit frequency and lowers the volatility.

### Validation
Results are cross-checked three ways:
1. closed-form formulas (`analytics` in `stats.py`),
2. full enumeration of all 8000 combinations through the real round logic (`enumerate_stats` in `stats.py`),
3. Monte Carlo simulation (`simulate.py`): a reference loop over `game.py` (`simulate_slow`) and a vectorized NumPy version (`simulate_fast`).

`simulate_fast` re-implements the round logic in vectorized form, so each simulation
(the reference loop and the vectorized one) is checked statistically against the exact values by the tests.

The standard error of a simulated RTP over N spins is sigma / sqrt(N). With sigma = 10.57,
1,000,000 spins give about ±0.01057 (one standard error). A 95% confidence interval is approximately ±1.96 standard errors. About 4.3 million spins are needed to estimate RTP within ±1 percentage point at 95% confidence.

Reference implementation (`simulate_slow`), 1,000,000 spins, seed 42:
- RTP = 0.955208 (exact: 0.960000, deviation -0.46 standard errors)
- Hit frequency = 0.110819 (exact: 0.111250)
- Sample standard deviation of the payout = 10.4140 (theoretical: 10.5668)
- Standard error of RTP = 0.010414

## Performance

Measured with two runs of `benchmark.py` (default and `scaling`) on one machine.

- CPU: Intel64 Family 6 Model 142 Stepping 9, 4 logical processors
- OS: Windows 10 (10.0.19045)
- Python 3.14.6, NumPy 2.5.4

### Pure Python vs NumPy

The same workload for every implementation: 10,000,000 spins, median of 5 runs
(chunk 2.5M, so each of the 4 workers gets one chunk). Reproduce with `python benchmark.py`.

| Implementation | Median time (s) | Min-max (s) | Throughput (M spins/s) |
|---|---|---|---|
| Pure Python (`simulate_slow`) | 31.98 | 31.44-32.31 | 0.31 |
| NumPy, 1 worker (`simulate_fast`) | 0.27 | 0.26-0.30 | 37.15 |
| NumPy, 4 workers | 0.86 | 0.84-1.24 | 11.62 |

Throughput is computed from the unrounded median time. Single-process NumPy is about 120x faster than the pure Python loop. On this small workload 4 workers are slower than 1: the computation takes
only a fraction of a second, and process start-up on Windows (roughly 0.6-0.8 s, inferred from the timings rather than
measured directly) outweighs the gain from parallelism.

### Scaling with the number of spins

NumPy only, chunk 2M, 1 worker vs 4 workers. Reproduce with `python benchmark.py scaling`.

| Spins | Repeats | 1 worker (s) | 4 workers (s) | Speed-up | 4 workers (M spins/s) |
|---|---|---|---|---|---|
| 100,000,000 | 3 (median) | 2.7 | 2.1 | 1.3x | 47.8 |
| 1,000,000,000 | 1 | 28.9 | 12.7 | 2.3x | 78.9 |

- The speed-up grows with the size of the run: about 0.3x at 10M spins (first table: 0.27 s / 0.86 s,
  chunk 2.5M), 1.3x at 100M and 2.3x at 1B. This is consistent with...
- Parallelism gives less than 4x on this 4-thread CPU. Likely reasons are the start-up cost and
  limited scaling of this memory-heavy workload, but this was not investigated further.
- The 1B row is a single run. Absolute times varied by 20-30% between earlier sessions on the same machine, so ratios are more reliable than absolute numbers.

### Accuracy check on 1,000,000,000 spins

`simulate_fast(1_000_000_000, seed=42, chunk=2_000_000)`: RTP = 0.96052 vs 0.96000 theoretical
(+1.6 standard errors, standard error = 0.00033). Wins per symbol are within 2 standard deviations
of the exact counts. The result depends on the seed and the chunk size, not on the number of processes
(checked in the unit tests on 400,000 spins).

## Limitations
- The reference implementation uses Python's `random` module, while the vectorized implementation uses NumPy's random number generator. Neither is intended for certified casino production use. 