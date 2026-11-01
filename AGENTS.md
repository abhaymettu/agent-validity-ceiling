# AGENTS.md

- `analysis.py` is the original closed-form ceiling. Its inputs are hardcoded from published
  papers; `python3 -m unittest test_reproduce -v` checks that `results.json` regenerates byte for
  byte. Change an input and you must regenerate `results.json` in the same commit.
- The measured analysis (variance components from per-task results, measured coverage) lives in
  github.com/abhaymettu/benchmeasure (`experiments/swebench.py`). Figures in `figures/` are copied
  from there; regenerate them there, not here.
- Numbers in README.md come from `results.json` here or `results/swebench.json` in benchmeasure.
  Never type a number that no script produces.
- Writing rules: no em dashes anywhere, plain commit messages, no attribution trailers.
