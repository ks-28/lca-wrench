"""Size test: a synthetic LCA database of ecoinvent size; measures time and memory of LCA Wrench.

Creates the Brightway project `lca-wrench-test-gross` (its name starts with lca-wrench-test, so the app does not show
it), writes a random but ecoinvent-like database, measures, and deletes the project again.
Usage: .venv/bin/python bench_gross.py [activities] [inputs per activity] [emissions per activity] [random|local]
Default: 25000 activities, 12 inputs, 40 emissions (ecoinvent 3.x: about 20,000 activities, 10-15 inputs, about 40
emissions).
"random": every input comes from any earlier activity (pessimistic, much fill-in during the factorization).
"local": inputs come mostly from the last 1500 activities (supply chains are local), plus hubs like electricity and
transport.
"""

import os
import resource
import sys
import tempfile
import time
import warnings

os.environ.setdefault("LCA_WRENCH_REGISTRY", os.path.join(tempfile.mkdtemp(prefix="lca-wrench-bench-"), "lca-wrench.json"))
warnings.filterwarnings("ignore")

import bw2data as bd  # noqa: E402
import numpy as np  # noqa: E402

PROJECT = "lca-wrench-test-gross"
N = int(sys.argv[1]) if len(sys.argv) > 1 else 25000
K_TECH = int(sys.argv[2]) if len(sys.argv) > 2 else 12
K_BIO = int(sys.argv[3]) if len(sys.argv) > 3 else 40
N_FLOWS = 3000
STRUCTURE = {"zufall": "random", "lokal": "local"}.get(sys.argv[4], sys.argv[4]) if len(sys.argv) > 4 else "random"
WINDOW = 1500


def rss_mb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6  # macOS: bytes


def timed(label, fn):
    t = time.perf_counter()
    out = fn()
    dt = time.perf_counter() - t
    print(f"{label:<46}{dt:8.2f} s   (peak memory {rss_mb():6.0f} MB)", flush=True)
    return out


def build():
    rng = np.random.default_rng(42)
    bio = bd.Database("bio")
    bio.write({("bio", f"f{i}"): {"name": f"Flow {i}", "unit": "kilogram", "categories": ("air",), "type": "emission"}
               for i in range(N_FLOWS)})
    # hub-heavy, mostly acyclic structure like a real LCI: inputs come from "earlier" processes, a few hubs
    # (electricity, transport, ...) are used by very many, and about 3 % of the inputs point backwards (loops)
    hubs = rng.choice(N, size=max(N // 100, 10), replace=False)
    data = {}
    for i in range(N):
        exchanges = [{"input": ("bg", f"p{i}"), "amount": 1.0, "type": "production"}]
        k = max(1, int(rng.poisson(K_TECH)))
        picks = set()
        for _ in range(k):
            r = rng.random()
            if r < 0.30:
                j = int(rng.choice(hubs))
            elif r < 0.97 and i > 0:
                j = int(rng.integers(max(0, i - WINDOW), i)) if STRUCTURE == "local" else int(rng.integers(0, i))
            else:
                j = int(rng.integers(0, N))
            if j != i:
                picks.add(j)
        for j in picks:
            amount = float(rng.lognormal(-2, 1.5)) * (0.02 if j > i else 1.0)  # loop inputs stay small: matrix solvable
            exchanges.append({"input": ("bg", f"p{j}"), "amount": min(amount, 5.0), "type": "technosphere",
                              "uncertainty type": 2, "loc": 0.0, "scale": 0.2})
        for f in rng.choice(N_FLOWS, size=min(max(int(rng.poisson(K_BIO)), 1), N_FLOWS), replace=False):
            exchanges.append({"input": ("bio", f"f{int(f)}"), "amount": float(rng.lognormal(-8, 2)), "type": "biosphere"})
        data[("bg", f"p{i}")] = {"name": f"Prozess {i}", "unit": "kilogram", "location": "CH", "type": "process",
                                 "reference product": f"Produkt {i}", "exchanges": exchanges}
    bd.Database("bg").write(data, searchable=False)
    cfs = [(("bio", f"f{i}"), float(rng.lognormal(0, 1))) for i in range(N_FLOWS)]
    m = bd.Method(("Test", "Klima", "kg CO2-eq"))
    m.register(unit="kg CO2-eq")
    m.write(cfs)
    return ("Test", "Klima", "kg CO2-eq")


def main():
    if PROJECT in bd.projects:
        bd.projects.delete_project(PROJECT, delete_dir=True)
    bd.projects.set_current(PROJECT)
    try:
        print(f"Synthetic ({STRUCTURE}): {N} activities, ~{K_TECH} inputs, ~{K_BIO} emissions per activity, {N_FLOWS} flows")
        method = timed("Write the database (once, Brightway)", build)
        from lca_wrench import analysis, engine, models

        import bw2calc as bc
        from scipy.sparse.linalg import splu

        lca = bc.LCA({bd.get_node(database="bg", code="p0"): 1})
        timed("  of which: load matrices from Brightway", lca.load_lci_data)
        A0 = lca.technosphere_matrix.tocsc()
        timed("  of which: fast LU factorization (fast_lu)", lambda: engine.fast_lu(A0))
        if N <= 8000:
            timed("  for comparison: SuperLU default", lambda: splu(A0))
        if os.environ.get("BENCH_PROFILE"):
            import cProfile
            import pstats

            pr = cProfile.Profile()
            pr.enable()
            engine.system()
            pr.disable()
            pstats.Stats(pr).sort_stats("cumulative").print_stats(14)
            engine._systems.clear()
            engine._backgrounds.clear()
        S = timed("Build in total: load matrix + LU factorization", lambda: engine.system())
        A, B = S.bg.A, S.bg.B
        print(f"  Matrix {A.shape[0]} x {A.shape[1]}, {A.nnz} entries ({A.nnz / A.shape[0]:.1f} per column), biosphere {B.shape}, {B.nnz} entries")
        timed("Unit scores of one method (1 solve)", lambda: S.unit_scores(method))
        nid = int(S.col_ids[N // 2])
        timed("Result of one product incl. contributions", lambda: analysis.contributions(S, nid, 1.0, method))
        timed("Supply chain tree", lambda: analysis.tree(S, nid, 1.0, method, 0.01, 4, 5))
        timed("Sankey", lambda: analysis.sankey(S, nid, 1.0, method, 0.02, 40))
        timed("Inventory", lambda: analysis.inventory(S, nid, 1.0))
        timed("Table 10 products x 1 method", lambda: analysis.score_table(S, [(int(S.col_ids[i]), 1.0) for i in range(100, N, max(N // 10, 1))], [method]))
        # one Monte-Carlo iteration: sample, factorize, solve
        from lca_wrench import montecarlo

        timed("Monte Carlo: 1 iteration, 1 product (1 core)", lambda: montecarlo.run_chunk(PROJECT, [(nid, 1.0)], [method], 1, 1))
        # live model: one own process on top of the background
        models.create_database("Modell")
        pid = models.create_process("Modell", "Mein Produkt", "kilogram", "CH")
        models.add_exchange(pid, int(S.col_ids[10]), 1.0)
        exc = models.add_exchange(pid, int(S.col_ids[N // 3]), 2.0)
        timed("Create a model activity and calculate", lambda: models.system().score({int(pid): 1.0}, method))

        def edit():
            models.update_exchange(int(exc), amount=3.0)
            return models.system().score({int(pid): 1.0}, method)

        timed("Change an amount in the model and recalculate", edit)
    finally:
        bd.projects.set_current("default")
        bd.projects.delete_project(PROJECT, delete_dir=True)


if __name__ == "__main__":
    main()
