# Demo walkthrough

A short tour with the free BAFU 2025 data.

1. Start LCA Wrench (`.venv/bin/python -m lca_wrench`, or the double-click launcher of a release package). The browser
   opens http://127.0.0.1:8787. On the first visit a tour of ten steps explains the layout ("Tour" repeats it).
2. On the start page, open the project `bafu-2025` (the BAFU database with its background data).
3. Click "Create example model (e-bike)". The model is a simplified teaching example with estimated amounts, not a
   validated dataset.
4. Under "Model", open the assembled e-bike and change an amount (for example the steel). The result at the top updates
   immediately; "Undo" (⌘Z or Ctrl+Z) restores the value.
5. Under "Calculate", open the example's calculation setup (per kilometre), a setup with several products and methods. "Cross-check
   with bw2calc" recalculates with plain bw2calc and shows the largest deviation.
6. Click a number in the table to open the result: "Contributions" by activity or flow, "Sankey", "Supply chain" and
   "Inventory" (with the factor status of each flow, filter and CSV).
7. Under "Calculate", "Run uncertainty analysis" gives box plots and a matrix "A better than B" for the products of the
   setup.
8. Under "Compare", put products side by side, for example a product of the original and of a working copy. In a working
   copy with changes, the result tab "Why different?" splits the difference onto the changed exchanges.

See [features.md](features.md) and [uncertainty.md](uncertainty.md) for what each view does.
