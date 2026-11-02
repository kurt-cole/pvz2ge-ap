"""Generation's belt swap (belt_roll.py) against the client's, and its rules."""
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import apstub  # noqa: E402,F401

from pvz2gardendless import belt_roll as BR  # noqa: E402
from pvz2gardendless import conveyor_tables as CT  # noqa: E402

failed = 0


def fail(msg):
    global failed
    failed += 1
    print("  FAIL  " + msg)


def ok(msg):
    print("  ok    " + msg)


THREAT_SETS = ([], ["cold"], ["jester"], ["excavator", "torch"], ["parasol", "jester"])
SEEDS = [123456789, 1, 2 ** 31 + 7, 987654321]
ATTEMPTS = [0, 1, 3, -1]                 # -1: the guard's vanilla fallback

vectors = []
for level in sorted(BR.BELTS):
    b = BR.BELTS[level]
    for k, seed in enumerate(SEEDS):
        threats = list(THREAT_SETS[(k + len(vectors)) % len(THREAT_SETS)])
        attempt = ATTEMPTS[k]
        # conveyor_damage_rule: on for new seeds; off on the first seed so
        # older seeds' belts stay held to the client too.
        rule = k != 0
        belt = BR.roll(seed, level, attempt, threats, damage_rule=rule)
        want = {"initial": [e["PlantType"] for e in belt.entries()],
                "adds": [[e["Type"] for e in adds if e.get("Type")] for _, adds, _ in belt.mods()]}
        vectors.append({"level": level, "seed": seed, "attempt": attempt, "rule": rule,
                        "threats": threats, "water": b["water"],
                        "sky": b["sky"], "initial": b["initial"],
                        "puzzle": level in CT.PUZZLE_BELTS or attempt < 0,
                        "mods": [[w, [e for e in a if e.get("Type")], [e for e in r if e.get("Type")]]
                                 for w, a, r in b["mods"]],
                        "want": want})

node = shutil.which("node")
if node is None:
    print("  skip  node not found: belt parity with the client not checked")
else:
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(vectors, fh)
        path = fh.name
    try:
        r = subprocess.run([node, "belt_parity_test.js", path], cwd=os.path.join(HERE, "client"),
                           capture_output=True, text=True)
        print(r.stdout.rstrip())
        if r.returncode:
            fail("belt parity with the client: " + r.stderr.strip()[-400:])
    finally:
        os.unlink(path)

# Attempts differ, and every attempt keeps the swap's rules: same role, a
# killing instant stays one, nothing unplantable on the lawn.
differ, broken = 0, []
for level in sorted(BR.BELTS):
    b = BR.BELTS[level]
    a0 = BR.roll(SEEDS[0], level, 0).entries()
    for attempt in (1, 2):
        got = BR.roll(SEEDS[0], level, attempt).entries()
        if got != a0:
            differ += 1
        for e, src in zip(got, b["initial"]):
            o, c = src.get("PlantType"), e["PlantType"]
            if o == c:
                continue
            if (CT.ROLE.get(o) == "instant") != (CT.ROLE.get(c) == "instant") or \
                    (o in CT.KILLING and c not in CT.KILLING) or \
                    not CT.plantable(c, True, b["sky"]):
                broken.append((level, attempt, o, c))
if broken:
    fail(f"rerolled belts break the swap rules: {broken[:4]}")
else:
    ok(f"rerolled belts keep the swap rules ({differ} rerolls differ from attempt 0)")

print(f"\n{failed} FAILURE(S)" if failed else "\nBELT ROLL OK")
sys.exit(1 if failed else 0)
