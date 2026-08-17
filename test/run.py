"""Run the whole offline test suite.

    python test/run.py

Archipelago is not importable outside a full AP checkout, so generation is
exercised against apstub.py, a hand-written stand-in for BaseClasses, Options,
settings and worlds.*. Nothing here needs Archipelago, Node modules, the game
source, or a built apworld -- it is all pure logic.

Node is optional: the JS suites are skipped with a warning if it is missing,
since the Python suites cover generation on their own.
"""
import os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
CLIENT = os.path.join(HERE, "client")

PY_SUITES = [
    ("generation", "gen_test.py",    "pool, locations, options, item IDs"),
    ("spheres",    "sphere_test.py", "reachability and sphere depth"),
    ("drift",      "drift_test.py",  "client JS copies match the real client"),
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
    ("costumes", "costume_test.js",  "costume grants and the shuffle trap"),
    ("connect",  "connect_test.js",  "wss:// first, ws:// fallback"),
    ("features", "feature_test.js",  "opening the store from egypt6 progress"),
    ("currency", "currency_test.js", "restoring the balance the game wipes at boot"),
]


def run(label, cmd, cwd, blurb):
    # flush before handing the terminal to the child, or our headers buffer up
    # and print after all the subprocess output.
    print(f"\n{'=' * 70}\n  {label}  --  {blurb}\n{'=' * 70}", flush=True)
    result = subprocess.run(cmd, cwd=cwd)
    return result.returncode == 0


def main():
    results = []
    for label, script, blurb in PY_SUITES:
        results.append((label, run(label, [sys.executable, script], HERE, blurb)))

    node = shutil.which("node")
    if not node:
        print("\n  WARNING: node not on PATH -- skipping the client JS suites.")
        print("  The Python suites above still cover generation.")
    else:
        for label, script, blurb in JS_SUITES:
            results.append((label, run(label, [node, script], CLIENT, blurb)))

    print(f"\n{'=' * 70}")
    failed = [label for label, ok in results if not ok]
    for label, ok in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {label}")
    if failed:
        print(f"\n{len(failed)} SUITE(S) FAILED: {', '.join(failed)}")
        return 1
    print(f"\nALL {len(results)} SUITES PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
