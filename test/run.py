"""Run the whole offline test suite.

    python test/run.py [-j N] [suite ...]

Suites run in parallel, one per CPU by default; each suite's output prints
whole when it finishes.

Archipelago is not importable outside a full AP checkout, so generation is
exercised against apstub.py, a hand-written stand-in for BaseClasses, Options,
settings and worlds.*. Nothing here needs Archipelago, Node modules, the game
source, or a built apworld -- it is all pure logic.

Node is optional: the JS suites are skipped with a warning if it is missing,
since the Python suites cover generation on their own.
"""
import argparse, os, shutil, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = os.path.dirname(os.path.abspath(__file__))
CLIENT = os.path.join(HERE, "client")

PY_SUITES = [
    ("generation", "gen_test.py",    "pool, locations, options, item IDs"),
    ("spheres",    "sphere_test.py", "reachability and sphere depth"),
    ("drift",      "drift_test.py",  "client JS copies match the real client"),
    ("zombietiers","zombie_tier_test.py", "the zombie swap tiers still partition"),
    ("levelmodel", "level_model_test.py", "the wave-level model matches hand-checked levels"),
    ("balance",    "balance_test.py", "the client's roll replayed over every level"),
    ("balancev2",  "balance_v2_test.py", "the budget zombie roll replayed over every level"),
    ("budget",     "budget_logic_test.py", "generation logic built from the budget roll"),
    ("powersel",   "power_selection_test.py", "the plant-power selection keeps logic small"),
    ("rollvectors","roll_vectors_test.py", "the budget roll's parity vectors are current"),
    ("tracker",    "tracker_test.py", "Universal Tracker rebuilds the same seed"),
]
JS_SUITES = [
    # First: the others require *_fn.js copies, so none of them ever runs the
    # client as one program. This one does, and a client that dies on load
    # makes every other result meaningless.
    ("load",     "load_test.js",     "the whole client survives being loaded"),
    ("upgrades", "upgrade_test.js",  "progressive upgrade grants"),
    ("store",    "store_test.js",    "bought store cards stay gone"),
    ("conveyor", "conveyor_test.js", "belt swaps stay in power band"),
    ("zombies",  "zombie_test.js",   "zombie swaps stay in tier, threats stay put"),
    ("budgetjs", "budget_test.js",   "the client's budget roll matches the Python roll"),
    ("costumes", "costume_test.js",  "costume grants and the shuffle trap"),
    ("connect",  "connect_test.js",  "wss:// first, ws:// fallback"),
    ("features", "feature_test.js",  "opening the store from egypt6 progress"),
    ("currency", "currency_test.js", "restoring the balance the game wipes at boot"),
    ("commands", "command_test.js",  "chat commands driven from any AP client"),
    ("deathlink","deathlink_test.js","the AP panel's DeathLink switch, both directions"),
    ("goal",     "goal_test.js",     "the win condition and what opens Modern Day"),
    ("worldgate","worldgate_test.js","progressive world unlocks, enforced in game"),
    ("tutorial", "tutorial_test.js", "a level is only checked once it is really finished"),
]


def run(label, cmd, cwd, blurb):
    """One suite, output captured so parallel suites do not interleave."""
    start = time.time()
    result = subprocess.run(cmd, cwd=cwd, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True)
    return label, blurb, result.returncode == 0, result.stdout, time.time() - start


def report(entry):
    label, blurb, ok, output, secs = entry
    print(f"\n{'=' * 70}\n  {label} ({secs:.0f}s): {blurb}\n{'=' * 70}")
    print(output, end="", flush=True)


def main():
    ap = argparse.ArgumentParser(description="Run the offline test suite in parallel.")
    ap.add_argument("-j", "--jobs", type=int, default=os.cpu_count() or 4,
                    help="suites run at once (default: one per CPU)")
    ap.add_argument("only", nargs="*", help="suite labels to run (default: all)")
    args = ap.parse_args()

    def wanted(label):
        return not args.only or label in args.only

    jobs = [(label, [sys.executable, script], HERE, blurb)
            for label, script, blurb in PY_SUITES if wanted(label)]
    node = shutil.which("node")
    if not node:
        print("\n  WARNING: node not on PATH, skipping the client JS suites.")
        print("  The Python suites still cover generation.")
    else:
        js = [(label, [node, script], CLIENT, blurb)
              for label, script, blurb in JS_SUITES if wanted(label)]
        # The load suite runs alone and first: a client that dies on load makes
        # every other JS result meaningless.
        if js and js[0][0] == "load":
            first = run(*js[0])
            report(first)
            if not first[2]:
                print("\n  load FAILED, skipping the other JS suites.")
                js = []
            results_first = [first]
            js = js[1:]
        else:
            results_first = []
        jobs += js

    start = time.time()
    results = list(results_first if node else [])
    with ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
        futures = [pool.submit(run, *job) for job in jobs]
        for future in as_completed(futures):
            entry = future.result()
            report(entry)
            results.append(entry)

    print(f"\n{'=' * 70}")
    order = {label: i for i, (label, _, _) in enumerate(JS_SUITES + PY_SUITES)}
    results.sort(key=lambda e: order.get(e[0], 0))
    failed = [e[0] for e in results if not e[2]]
    for label, _, ok, _, secs in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {label:12s} {secs:5.0f}s")
    print(f"  wall clock {time.time() - start:.0f}s")
    if failed:
        print(f"\n{len(failed)} SUITE(S) FAILED: {', '.join(failed)}")
        return 1
    print(f"\nALL {len(results)} SUITES PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
