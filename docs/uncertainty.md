# Uncertainty and sensitivity

## Monte Carlo

In "Calculate", the button "Run uncertainty analysis" computes n iterations (100 to 10,000, default 500) as a
background job. Above 2,000 iterations the single draws are not sent to the page, only the statistics. Run times:
[calculation.md](calculation.md).

- **Coupled:** in each iteration the technosphere and biosphere matrices are sampled once (bw2calc/matrix_utils,
  `use_distributions=True`) and used for all products of the calculation setup. A statement such as "A is better than B
  in 93 % of the iterations" therefore refers to a paired difference, not to independent noise. Each method samples its
  characterization factors separately (BAFU has none with uncertainty, so they are identical).
- **Result:** box plot per product (box 25–75 %, whiskers 5–95 %, line = median, diamond = deterministic result), table
  with median, range and spread, and a matrix "A better than B" (lower impact wins, a tie counts half). For lognormal
  data the deterministic value is usually slightly below the median.
- **Input data:** the data sheet shows for every input, emission and resource the range that holds the amount with 95 %
  probability (2.5 and 97.5 percentiles of its distribution), the distribution (lognormal with GSD², normal with
  standard deviation, uniform, triangular, …) and, as a tooltip, the pedigree scores. In your own models a click on it
  sets the distribution (none, lognormal with GSD², normal, uniform, triangular); it can be undone like any change.
  **Pedigree matrix** as in the Activity Browser 3: the five scores (reliability, completeness, temporal, geographical
  and further technological correlation, 1 = best) and a basic uncertainty U_b (as GSD², 1 when empty) give a lognormal
  with σ = √(ln² U_b + Σ ln² U_i) / 2, with the Activity Browser's factors U_i per score (`models.PEDIGREE`). The scores
  and U_b are stored with the exchange (`pedigree`); the editor shows the GSD² while they change and, for ecoinvent
  data, which keep only the scores, works out U_b from σ. Typing a GSD² instead drops the scores. When an amount
  changes, its distribution moves along with the same relative spread.
- **Technique:** background job with progress bar, split over up to 8 processes (`lca_wrench/montecarlo.py`; seed +
  index of the process; the same seed and the same number of cores give the same result). One LU factorization per
  iteration (symmetric mode, with residual check and fallback), then one solve per product.
- **Tests:** `tests/test_montecarlo.py` compares each iteration with a plain bw2calc loop with the same seed, also for an
  own model; coupling (double amount gives exactly double result in every iteration), statistics against numpy,
  reproducibility across processes.
- Your own models are processed at the start of the job (bw2data `process()`); changes during the run no longer affect
  that run.

## What drives the spread? (sensitivity, CTV, Sobol)

Below the uncertainty analysis: choose a product and the number of iterations (300, 1,000 or 3,000; 1,000 or more for
stable Sobol indices), "Analyse". Result: the 10 uncertain data values (inputs between activities and emissions) most
strongly related to the result, each with three measures:

| Measure | What it says | How it is computed |
|---|---|---|
| Rank correlation (Spearman, −1 to +1) | direction, and how strongly the value decides high or low | recorded values against the score of each iteration |
| CTV, contribution to variance | share of the variance under a linear (first-order Taylor) model | `(dh/da)² · var(a)` over the sum for all entries; exact derivatives, no extra iterations |
| Sobol S₁ and S_T | share of the variance from this value alone (S₁), and with all its interactions (S_T) | pick-freeze on pairs of iterations (Saltelli 2010, centred; Jansen), 95 % bootstrap interval |

Above the table: the sum of all linear contributions as a share of the variance of the iterations (close to 100 %
means the result behaves almost linearly and CTV is reliable), and the sums of S₁ and S_T for the 20 values with Sobol
indices. Values that are strong by Sobol but weakly correlated (non-monotonic effects or interactions) are added below
the 10. Because not all data values can be recorded, the procedure is:

1. A pilot with 40 iterations measures how much each matrix entry varies (relative standard deviation).
2. The derivatives of the result with respect to each entry are known exactly: `dh/dA_ij = −s_i · x_j` (s = cumulative
   unit scores, x = scaling vector) and `dh/dB_kj = c_k · x_j`. Candidates are ranked by `|dh/da| · sd(a)`; the best 250 go
   on, the best 20 also get Sobol indices.
3. The actual run records the sampled values of these 250 entries and correlates them with the result. The noise floor
   (an independent value shows about ρ² = 1/(n−1)) is subtracted from the weights; values below 2/√n are marked "not
   significant". The spread of the 250 entries for CTV is then taken from all iterations, not only the pilot.
4. Sobol without extra factorizations: the iterations are taken in pairs (a, b). The score with all values from a but
   entry i from b follows exactly from the factorization of a by a rank-one update (Sherman–Morrison):
   `h' = h − δ s_r x_c / (1 + δ (A⁻¹)_cr)` for a technosphere entry, `h' = h + c_k δ x_j` for a biosphere entry. That costs
   one extra solve per entry and pair; the whole analysis takes about as long as a Monte Carlo run with the same number
   of iterations. `S₁ = mean((f_b − f̄)(f_ab − f_a)) / V`, `S_T = mean((f_a − f_ab)²) / 2V`.

Limits: characterization factors with uncertainty are not examined individually (BAFU has none); only the data values
that end up among the 250 selected (20 for Sobol) are examined, so a value with a small derivative and a large spread
can be missed. With 300 iterations (150 pairs) the Sobol intervals are wide. Tested in `tests/test_montecarlo.py`: the
derivative formulas by finite differences against real solutions, the recorded values against a bw2calc loop with the
same seed, Spearman against `scipy`, the rank-one scores against solving again, the Sobol estimators against a
function with known indices.
