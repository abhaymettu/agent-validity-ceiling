# Validity ceiling for agent benchmarks

Every leaderboard comparison assumes a benchmark score predicts something real. This computes how much it can: the classical attenuation ceiling, R^2 <= rho_X * rho_Y * C, applied to SWE-bench Verified using published run-to-run variance.

The finding, in one line: across the full leaderboard (scores 15% to 72%) benchmark reliability is 0.993, so the rank order is real; between frontier models the reachable ceiling falls to R^2 = 0.176, and the binding constraint there is coverage: the benchmark measures a narrow slice of what those models can do.

The writeup is `writeup.md`. All inputs are hardcoded from published papers; nothing is downloaded and no model is called.

## Run it

Needs Python 3.9 or newer with numpy.

```sh
python3 analysis.py                  # prints the tables, writes results.json here
python3 analysis.py --out /tmp/r.json  # write somewhere else
```

## Test

```sh
python3 -m unittest test_reproduce -v
```

The test runs `analysis.py` in a temporary directory and checks that the `results.json` it writes matches the committed one byte for byte. It also checks that the frontier gap decomposition and disattenuation numbers come from the computed frontier reliability (25 / (25 + 1.25^2) = 0.941).

## What this is not

- The inputs are published point estimates, so the ceilings move with the variance studies you believe. The writeup reports the range.
- A ceiling on explainable variance, not a claim that any specific score is fake.
