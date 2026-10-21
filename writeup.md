# Validity Ceiling for Agent Benchmarks

Reliability-corrected predictive validity: what agent benchmark scores can
and cannot tell you about real-world performance.

Abhay Mettu, October 2026

---

## The question

Every leaderboard comparison assumes the benchmark score predicts something
about deployment performance. The attenuation formula from classical test
theory gives the upper bound on that prediction. I have not found it applied
to agent benchmarks. This writeup does.

The short version: for the full leaderboard the ceiling is high enough that
benchmark noise is not the main problem. For frontier models (where the
decisions happen), it drops. For close comparisons between models 3 to 5
percentage points apart, benchmark scores can explain at most 13.5% of
real-world performance differences under moderate assumptions. The dominant
constraint is not noise but coverage: SWE-bench measures a narrow slice of
what deployment demands.


## Framework

The classical attenuation formula says the observed correlation between any
two measures is bounded by their reliabilities:

    r_observed <= sqrt(rho_X * rho_Y) * r_true

Rearranged as a ceiling on explained variance:

    R^2_{XY} <= rho_X * rho_Y * C

where:
- rho_X = test-retest reliability of the benchmark
- rho_Y = reliability of the criterion (real-world performance measure)
- C = proportion of criterion-relevant variance the benchmark covers
- R^2_{XY} = maximum achievable coefficient of determination

This is the same framework as Mettu (2026, Zenodo 22739320), which bounded
how well behavioral proxies can measure depression (ceiling R^2 = 0.342 from
PHQ-9 reliability 0.890 and behavioral coverage 0.384). The decomposition
also follows that paper:

    1.000 = benchmark_unreliability
          + criterion_unreliability
          + uncovered_variance
          + ceiling

Each component is a slice of the unit total that accounts for a source of
the gap between perfect prediction and what the benchmark can deliver.


## Data

All inputs are published. No API calls, no compute spend.

**Within-run variance.** Bjarnason, Silva and Monperrus (2026), "On
Randomness in Agentic Evals," collected 60,000 trajectories on SWE-bench
Verified (500 tasks, 10 runs per configuration, 6 model-scaffold pairs plus
temperature-0 controls). Key numbers:

| Configuration                    | Temp | SD (pp) | Range (pp) |
|:---------------------------------|-----:|--------:|-----------:|
| Qwen3-32B + nano-agent           |  0.6 |     0.7 |        2.2 |
| Qwen3-32B + R2E-Gym              |  0.6 |     1.4 |        5.0 |
| DeepSWE-preview + nano-agent     |  1.0 |     1.0 |        3.6 |
| DeepSWE-preview + R2E-Gym        |  1.0 |     1.5 |        5.4 |
| Devstral-2 + nano-agent          |  0.2 |     1.1 |        3.2 |
| Devstral-2 + R2E-Gym             |  0.2 |     1.5 |        4.8 |
| DeepSWE-preview + nano (t=0)     |  0.0 |     1.0 |        3.2 |
| Qwen3-32B + R2E-Gym (t=0)        |  0.0 |     1.8 |        5.4 |

Median SD: 1.25 pp. Temperature 0 does not eliminate variance; infrastructure
nondeterminism persists.

**Between-model variance.** Estimated from the public SWE-bench Verified
leaderboard. Scores range roughly 15% to 72% across all entries. Frontier
models (top 10 to 15) cluster 55% to 72%. Version bumps and scaffold changes
move scores 3 to 5 pp.

**Inter-rater and judgment reliability.** From "Measurement Without Validity"
(arXiv 2608.00794): WebArena Verified kappa = 0.83; LLM-as-judge substring
matching kappa = 0.049 (chance level); three-LLM ensemble kappa = 0.432;
mental health safety evaluation ICC = 0.087 to 0.295. Across 55 papers, 82%
used structurally mismatched, incomplete, or absent IRR metrics.

**Prompt sensitivity.** MMLU: 4 to 5 pp variation with prompt format. MMLU-Pro:
2 pp.


## Results

### Benchmark reliability depends on who you are comparing

The ICC is not a fixed property of a benchmark. It is the ratio of
between-group variance to total variance, and it changes with the population
of models under comparison.

| Population                       | sigma^2_between | sigma^2_within | ICC   |
|:---------------------------------|----------------:|---------------:|------:|
| Full leaderboard (15-72%)        |           225.0 |           1.56 | 0.993 |
| Frontier models (55-72%)         |            25.0 |           1.56 | 0.941 |
| Scaffold variants (same model)   |            12.2 |           1.56 | 0.887 |
| Close comparisons (3-5 pp gap)   |             4.0 |           1.56 | 0.719 |

sigma^2_within = 1.56 pp^2 (median SD of 1.25 pp, squared) from Bjarnason
et al.

Ranking GPT-4 against Llama-7B (full leaderboard): the benchmark is almost
perfectly reliable. Ranking the top three agents against each other (close
comparisons): reliability drops to 0.719.


### The validity ceiling

Combining benchmark reliability with coverage and criterion reliability:

**Frontier models, moderate assumptions (rho_Y = 0.75):**

| Coverage     | Ceiling R^2 | Ceiling r |
|:-------------|------------:|----------:|
| C = 0.40     |       0.282 |     0.531 |
| C = 0.25     |       0.176 |     0.420 |
| C = 0.15     |       0.106 |     0.325 |

**Close comparisons (3-5 pp gap), moderate criterion (rho_Y = 0.75):**

| Coverage     | Ceiling R^2 | Ceiling r |
|:-------------|------------:|----------:|
| C = 0.40     |       0.216 |     0.464 |
| C = 0.25     |       0.135 |     0.367 |
| C = 0.15     |       0.081 |     0.284 |

These are upper bounds. The actual predictive validity is at or below these
numbers.


### Gap decomposition

For frontier models with moderate coverage (C = 0.25) and moderate criterion
reliability (rho_Y = 0.75):

| Source                   | Fraction |
|:-------------------------|---------:|
| Benchmark unreliability  |     5.9% |
| Criterion unreliability  |    23.5% |
| Uncovered variance       |    52.9% |
| **Ceiling (reachable)**  | **17.6%**|

Uncovered variance dominates. The largest gap is not benchmark noise or
criterion noise; it is that the benchmark measures a narrow slice of what
real-world performance requires. SWE-bench tests Python repository-level bug
fixing. Real-world coding agent usefulness includes design decisions, testing,
debugging across languages, multi-file refactoring, communication with humans,
operating under ambiguity, and more.


### Disattenuation

If someone published an observed correlation of r = 0.40 between SWE-bench
score and deployment success, the corrected correlation would be:

    r_corrected = 0.40 / sqrt(0.941 * 0.75) = 0.476

A 19% inflation. The observed 0.40 is not evidence that the benchmark
captures only 16% of real-world variance (0.40^2 = 0.16); it captures
about 23% (0.476^2 = 0.227) of the variance it covers, with the rest lost
to measurement noise.

| r_observed | r_corrected | Inflation |
|-----------:|------------:|----------:|
|       0.20 |       0.238 |    +19.0% |
|       0.30 |       0.357 |    +19.0% |
|       0.40 |       0.476 |    +19.0% |
|       0.50 |       0.595 |    +19.0% |
|       0.60 |       0.714 |    +19.0% |

Inflation is constant because the attenuation factor is multiplicative.


### Cross-check with the multiplicative validity framework

"Measurement Without Validity" (arXiv 2608.00794) models total validity as
a product of pipeline stages: V_total <= V1 * V2 * V3, placing the range at
[0.225, 0.540] with a midpoint of 0.36. Our frontier ceiling with moderate
assumptions is R^2 = 0.176, and our close-comparison ceiling is R^2 = 0.135.
Both sit below that paper's midpoint. The frameworks converge: the comparisons
leaderboard consumers care about most have the lowest validity.


## What this means

1. **Leaderboard rankings across tiers are fine.** When comparing a 20%
   model against a 60% model, benchmark reliability is 0.993 and the
   ceiling is high. The rank order is real.

2. **Frontier comparisons are noisier than they look.** At the frontier,
   reliability drops to 0.941 and the ceiling with moderate coverage sits
   at R^2 = 0.176. A 2 to 3 pp improvement, the typical size of a claimed
   advance, fits inside the single-run variation measured by Bjarnason et al.

3. **Close comparisons are mostly noise.** Choosing between two models 3 to 5
   pp apart on the leaderboard, the ceiling is R^2 = 0.135 at best. The
   benchmark score difference tells you very little about which one will
   perform better in production.

4. **Coverage is the binding constraint, not noise.** The gap decomposition
   shows uncovered variance at 52.9%. Making the benchmark more reliable
   (reducing the 5.9% slice) helps only marginally. The far larger win is
   expanding what the benchmark measures.

5. **Disattenuation is a free correction I have not found applied.** Any observed
   benchmark-to-deployment correlation should be corrected for measurement
   unreliability before drawing conclusions. The correction inflates the
   coefficient by about 19% for frontier-reliability benchmarks. Without
   it, you are systematically underestimating the benchmark's construct-level
   validity and overestimating the gap that "better benchmarks" could close.


## Limitations

**Between-model variance is estimated, not formally sampled.** The sigma^2_between
values come from inspecting the public leaderboard, not from a designed study.
A proper estimate would need item-level data and a variance components model.

**Coverage is assumed, not measured.** The C values (0.15, 0.25, 0.40) are
plausible but not derived from data. Measuring coverage requires defining a
criterion construct and fitting a structural model, which needs deployment
outcome data nobody has published.

**Single benchmark.** The analysis focuses on SWE-bench Verified because it
has the best published variance data. Other benchmarks (WebArena, tau-bench,
GAIA) lack comparable test-retest studies. The ceiling formula applies to
any benchmark; the inputs just need to be measured.

**Criterion reliability is assumed.** Real-world performance measurement
(user satisfaction, task completion, revenue impact) has its own reliability
problems that are poorly characterized.

**Static analysis.** The ceiling is a bound, not a prediction. The actual
R^2 between any benchmark and any criterion can be anywhere from 0 to the
ceiling.


## Notation and sources

| Symbol  | Meaning                                           |
|:--------|:--------------------------------------------------|
| rho_X   | Test-retest reliability of the benchmark          |
| rho_Y   | Reliability of the real-world criterion measure   |
| C       | Coverage: fraction of criterion variance measured |
| R^2     | Coefficient of determination (explained variance) |
| r       | Pearson correlation coefficient                   |
| ICC     | Intraclass correlation coefficient (1,1)          |
| pp      | Percentage points                                 |

**Sources.**

- Bjarnason, B., Silva, A., & Monperrus, M. (2026). On Randomness in
  Agentic Evals. arXiv 2602.07150. 60,000 trajectories on SWE-bench Verified.
- Measurement Without Validity: The Compounding Reliability Problem in
  Agentic AI Evaluation. arXiv 2608.00794. IRR survey and multiplicative
  validity model.
- Beyond Static Leaderboards: Predictive Validity for the Evaluation of
  LLM Agents. arXiv 2606.19704. Rank instability and predictive validity.
- Mettu, A. (2026). The Validity Ceiling: What Passive Behavioral Data Can
  and Cannot Measure About Depression. Zenodo 22739320. Original framework.
- Code Benchmarks Should Prioritize Rigor, Reliability, and Reproducibility.
  arXiv 2501.10711.


## Reproducibility

`python3 analysis.py` regenerates all numbers. No dependencies beyond numpy.
`python3 -m unittest test_reproduce` checks that results.json regenerates exactly.
All inputs are hardcoded from published papers.
