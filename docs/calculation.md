# Calculation

## How it calculates

- **Background** (BAFU, ecoinvent …): self-contained databases. The matrix is loaded with bw2calc and LU-factorized
  once; cumulative unit scores are cached per method.
- **Foreground** (your own models): read directly from SQLite and solved separately, coupled through the unit scores of
  the background. Because the background never needs foreground products, the system is block-triangular and the
  result is exact:

  ```text
  x_f = A_ff⁻¹ f_f
  x_b = A_bb⁻¹ (f_b − A_bf x_f)
  h   = s_b · (f_b − A_bf x_f) + c · B_f x_f,   s_b = c B_b A_bb⁻¹
  ```

  A change to a model therefore does not need a rebuild of the background matrix.
- **Accuracy:** every solution is improved by iterative refinement; without it, SuperLU deviated noticeably for
  individual BAFU activities. Brightway stores matrix values as float32; bw2calc and LCA Wrench read the same stored
  values. Comparisons with bw2calc and an independent solver are in [validation.md](validation.md).
- **Cross-check:** at the push of a button the app recalculates with plain bw2calc and shows the largest deviation,
  relative to the sum of the contributions.
- **Several background databases:** each calculation factorizes only the databases it uses. Databases that do not link
  to each other are solved block by block (`engine.BlockSolver`): sparse LU for process data, dense LU (LAPACK) for a
  dense input-output table, where it is much faster than a sparse one. EXIOBASE (9,800 sectors) needs about 0.8 GB for
  it. A hybrid model (ecoinvent plus EXIOBASE) corresponds to the two Leontief inverses side by side; nothing is
  inverted explicitly.

## Size and large databases

Measured once during development (`bench_gross.py` and the BAFU data) on an Apple Silicon computer (12 cores), scipy
SuperLU without UMFPACK; not rerun by the tests. Everything except BAFU is synthetic;
the factorization time depends strongly on the structure of the matrix (feedback loops, hubs such as electricity), and
the synthetic matrices are rather pessimistic.

| Case | Factorization before (SuperLU default) | now (`fast_lu`) |
|---|---|---|
| BAFU, real, 11,747 products, 114,000 entries | 4.0 s, 6.8 million entries in L+U | 0.4 s, 0.5 million |
| 2 × BAFU coupled, 23,500 products, giant component 15,600 | 248 s, 106 million entries (about 1.3 GB) | 32 s, 12 million |
| Synthetic "lokal", 6,000 products | 10.4 s | 4.0 s |
| Synthetic "lokal", 8,000 products | 24.8 s, 1.1 GB | 5.9 s, 0.6 GB |
| Synthetic "lokal", 25,000 products, 323,000 entries, 1.0 million emissions | not measured | 117 s, peak 3.5 GB |
| Synthetic "zufall", 25,000 products | not measured | 152 s, peak 2 GB |

"lokal": inputs mostly from nearby processes plus hubs; "zufall": inputs from any earlier process. These are the
argument values of `bench_gross.py`.

`fast_lu` (`engine.py`) chooses the ordering for symmetric patterns without pivot search. The result is checked
(residual of two test systems after the usual refinement); otherwise the default factorization applies.

After the one-time build, in the synthetic case with 25,000 products: unit scores of a method 0.3 to 0.5 s, result
with contributions 0.15 s, Sankey 0.15 s, inventory 0.16 s; a change in your own model 20 ms (8,000 products).

Monte Carlo needs a new factorization per iteration: 0.4 s per iteration and core on BAFU (11,700 products);
synthetic with 6,000 products 11 s, with 8,000 products 43 s. 250 iterations with 4 products × 4 methods took 22 s
on 8 cores (BAFU). If the pivot-free factorization fails the check in an iteration, it continues with the default
one. With 25,000 products and this pessimistic structure an iteration would take minutes. More cores help (up to 8
processes in parallel), and so does more memory (each process holds a factorization). With real ecoinvent data these
figures have not been measured.

Changing background data (only possible in a working copy) rebuilds the matrix.

For large databases, install `scikit-umfpack` (see [install.md](install.md)); this has not been tested here.

To measure again:

```bash
PYTHONPATH=. .venv/bin/python bench_gross.py 25000 12 40 lokal
```

This creates the hidden project `lca-wrench-test-gross`, measures and deletes it (with `BENCH_PROFILE=1` also a
profile). With 25,000 products expect over 30 minutes and 4 GB of memory.

## Changes from outside

If another program (Activity Browser, a script) changes the open project, the app notices and reloads. Before every
request the local web process compares size and modification time of `lci/databases.db`, `databases.json`,
`methods.json` and `setups.pickle`; its own writes are recorded as known after each request. The interface polls every
3 s (and when returning to the tab) and then shows "Another program changed the project. The view has been reloaded."
On reload, Brightway's data state is read again from disk. If only one of your own models was affected (timestamp
"modified" per database), the expensive background matrix stays in memory; for a changed or new background database it
is rebuilt. The undo history is cleared when a model was changed from outside, so that an old step does not overwrite
the foreign change. Open: if another program writes exactly during a running request, this is only detected at the next
change. Tested in `tests/test_external.py` and in the browser.
