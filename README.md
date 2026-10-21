# Validity ceiling for agent benchmarks

Applies the classical attenuation formula, R^2 <= rho_X * rho_Y * C, to
SWE-bench Verified, using published run-to-run variance. The writeup is
`writeup.md`. All inputs are hardcoded from published papers; nothing is
downloaded and no model is called.

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

The test runs `analysis.py` in a temporary directory and checks that the
`results.json` it writes matches the committed one byte for byte. It also
checks that the frontier gap decomposition and disattenuation numbers come
from the computed frontier reliability (25 / (25 + 1.25^2) = 0.941).
