"""The budget roll's parity vectors still describe the Python roll.

test/client/budget_test.js holds the client to test/data/zombie_roll_vectors.json.
That only means something while the vectors are what zombie_roll.py actually
produces, so this re-rolls every case in Python and fails if any drifted. Fix a
failure by rerunning tools/gen_roll_vectors.py, never by editing the vectors.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "tools"))
import apstub  # noqa: E402,F401

from gen_roll_vectors import client_model, client_plan  # noqa: E402
from pvz2gardendless import zombie_roll as R  # noqa: E402

VECTORS = os.path.join(HERE, "data", "zombie_roll_vectors.json")
normal = lambda x: json.loads(json.dumps(x, sort_keys=True))

with open(VECTORS, encoding="utf8") as fh:
    vectors = json.load(fh)

t = R.tables()
failed = []
tables = {
    "zombies": {c: [z["hp"], z["cost"], z["tier"], z["excluded"] or "",
                    1 if z.get("carry", True) else 0,
                    1 if z.get("multilane") else 0]
                for c, z in sorted(t.zombies.items())},
    "grave_hp": dict(sorted(t.model["grave_hp"].items())),
    "field_names": {k: sorted(v) for k, v in t.field_names.items()},
}
if normal(tables) != vectors["tables"]:
    failed.append("the zombie tables changed")

cases = 0
for case in vectors["fixtures"] + vectors["rolls"]:
    lid = case["level"]
    if normal(client_model(t.model["levels"][lid])) != case["model"]:
        failed.append(f"{lid}: the level model changed")
    for p in case["plans"]:
        cases += 1
        got = normal(client_plan(R.roll_level(p["seed"], lid, p["dinos"], p["goal"])))
        if got != p["plan"]:
            failed.append(f"{lid} seed {p['seed']}: the Python roll no longer gives this plan")

for f in failed[:10]:
    print("  FAIL  " + f)
if failed:
    print(f"\n{len(failed)} FAILURE(S): rerun tools/gen_roll_vectors.py")
    sys.exit(1)
print(f"  ok    {len(vectors['fixtures'])} fixtures, {len(vectors['rolls'])} roll levels, "
      f"{cases} plans all still what zombie_roll.py produces")
print("\nROLL VECTORS OK")
