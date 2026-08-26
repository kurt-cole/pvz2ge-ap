"""Universal Tracker support: does a re-generation reproduce the same seed?

UT does not read the multiworld off the server. It RE-RUNS this world's
generation locally, from the player's YAML (or, very often, from no YAML at
all), and shows logic against whatever that produces. Everything this world
ROLLS is therefore a place the tracker and the server can disagree:

  * which worlds the seed contains -- world_count trims the whitelist at
    random, and an empty whitelist is waived entirely, so a re-roll builds
    different REGIONS. Every check in a world the re-roll dropped is shown out
    of logic, and worlds the server never built are shown in it. This is the
    bug the whole feature exists for.
  * which plants the run was handed (precollected, so also absent from the pool)
  * this slot's cheap-attacker and Jester draws, which decide which plants
    create_item promotes to progression -- and a `useful` item is invisible to
    a tracker's logic entirely.

The fix is interpret_slot_data + re_gen_passthrough: the seed's real answers go
out in slot data and come back in generate_early. These tests generate a seed,
hand its slot data to a SECOND world built with different options and a
different RNG, and demand the two agree on everything logic is computed from.

Deliberately paired with a control in each case: the second world's own roll
must actually differ, or the test proves nothing.
"""
import os, random, sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.dirname(_HERE))
import apstub
from apstub import MultiWorld

import pvz2gardendless as W
from pvz2gardendless.constants import GAME_NAME, SELECTABLE_WORLDS
from pvz2gardendless.items import slot_progression_plants
from opts import Opts

FAILURES = []


def check(label, cond, detail=""):
    print(f"  {'ok  ' if cond else 'FAIL'}  {label}")
    if not cond:
        FAILURES.append(f"{label}{': ' + detail if detail else ''}")


def build(seed=None, passthrough=None, **kw):
    """Generate one slot. `passthrough` puts it in the tracker's position."""
    mw = MultiWorld()
    if passthrough is not None:
        # Exactly where UT stashes it: keyed by game name on the multiworld.
        mw.re_gen_passthrough = {GAME_NAME: passthrough}
    w = W.PvZ2GardendlessWorld(mw, 1)
    w.options = Opts(**kw)
    if seed is not None:
        # The tracker's local RNG is not the server's. Nothing about a slot's
        # roll is reproducible from the YAML alone, which is the premise here.
        w.random = random.Random(seed)
    w.generate_early()
    w.create_regions()
    w.set_rules()
    w.create_items()
    return w


def summary(w):
    """Everything a tracker's logic view is computed from."""
    return {
        "worlds":       sorted(w.enabled_worlds),
        "regions":      sorted(r.name for r in w.multiworld.regions),
        "locations":    sorted(l.name for l in w.active_locations()),
        "goal":         sorted(w.goal_locations()),
        "precollected": sorted(i.name for i in w.multiworld.precollected),
        "progression":  sorted(slot_progression_plants(w)),
    }


print("\n=== the hook exists ===")
check("interpret_slot_data returns the slot data it is given",
      W.PvZ2GardendlessWorld.interpret_slot_data(None, {"a": 1}) == {"a": 1})

# ── A randomly-rolled seed, reproduced ───────────────────────────────────────
# No whitelist at all, so world_count picks five worlds AT RANDOM. This is the
# exact configuration Universal Tracker could not follow.
print("\n=== a random five-world seed ===")
_RANDOM_SEED = dict(world_count=5, enabled_worlds=[], shopsanity=True,
                    include_side_paths=True, goal_type=1, worlds_required=3)
server = build(seed=1, **_RANDOM_SEED)
sd = server.fill_slot_data()
print(f"  server worlds: {sorted(server.enabled_worlds)}")

# The tracker, running WITHOUT the player's YAML: every option at its default,
# and an RNG that is not the server's.
naive = build(seed=2)
print(f"  naive  worlds: {sorted(naive.enabled_worlds)}")
check("a tracker with no slot data really does build a different seed",
      summary(naive) != summary(server),
      "the control failed, so the test below proves nothing")

tracked = build(seed=2, passthrough=sd)
print(f"  tracked worlds: {sorted(tracked.enabled_worlds)}")
for key, want in summary(server).items():
    got = summary(tracked)[key]
    check(f"passthrough reproduces {key} ({len(want)})", got == want,
          f"server={want[:6]} tracker={got[:6]}")

# ── The rolled draws specifically ────────────────────────────────────────────
print("\n=== the per-slot draws ===")
check("granted plants come from the seed",
      sorted(tracked.starting_plants) == sorted(server.starting_plants),
      f"{tracked.starting_plants} != {server.starting_plants}")
check("the cheap-attacker draw comes from the seed",
      tracked.logic_attackers == server.logic_attackers)
check("the Jester draw comes from the seed",
      tracked.logic_jesters == server.logic_jesters)

# ── Options the tracker would otherwise default ──────────────────────────────
# UT is routinely run with no YAML. These three shape the location set and were
# never in slot data before, because the injected client has no use for them.
print("\n=== the location-shaping options ===")
_TRIMMED = dict(world_count=13, enabled_worlds=list(SELECTABLE_WORLDS),
                include_side_paths=True, include_danger_rooms=True,
                include_levels_past_goal=True, shopsanity=True,
                goal_type=2, worlds_required=5)
big = build(seed=3, **_TRIMMED)
big_sd = big.fill_slot_data()
big_tracked = build(seed=4, passthrough=big_sd)
check("a defaults-only tracker builds a smaller seed than this one",
      len(build(seed=4).active_locations()) != len(big.active_locations()),
      "the control failed")
check("passthrough reproduces the full location set",
      len(big_tracked.active_locations()) == len(big.active_locations()),
      f"{len(big_tracked.active_locations())} != {len(big.active_locations())}")
check("passthrough reproduces the goal levels",
      sorted(big_tracked.goal_locations()) == sorted(big.goal_locations()))

# ── Every key read back is a key that is actually sent ───────────────────────
# A passthrough read whose key was never put into slot data does not fail: it
# silently falls back to a fresh local roll, which is the failure mode with
# nothing to show for it.
print("\n=== every passthrough key is really in slot data ===")
import re
_SRC = open(os.path.join(os.path.dirname(_HERE), "pvz2gardendless",
                         "__init__.py"), encoding="utf-8").read()
_read = set(re.findall(r'passthrough(?:\.get\(|\[)\s*[\'"]([a-z_]+)[\'"]', _SRC))
_read |= set(re.findall(r'set_value\(\s*"[a-z_]+"\s*,\s*"([a-z_]+)"', _SRC))
_read |= set(re.findall(r'passthrough\.get\(.f.option_\{passthrough\.get\(.([a-z_]+)',
                        _SRC))
_sent = set(sd)
print(f"  read back: {sorted(_read)}")
check("nothing is read out of passthrough that fill_slot_data never sends",
      _read <= _sent, f"missing from slot_data: {sorted(_read - _sent)}")
check("the three rolled draws are all covered by name",
      {"granted_plants", "logic_attackers", "logic_jesters"} <= _read)
check("the worlds themselves are covered", "enabled_worlds" in _read)

# ── A seed predating the feature still works ─────────────────────────────────
# slot_data is versioned by TOLERATING MISSING KEYS. An old seed sends none of
# the new ones, and UT must fall back to its local roll rather than raise.
print("\n=== an old seed, with none of the new keys ===")
_old = {k: v for k, v in sd.items()
        if k not in {"granted_plants", "logic_attackers", "logic_jesters",
                     "include_side_paths", "include_danger_rooms",
                     "include_levels_past_goal"}}
old_tracked = build(seed=5, passthrough=_old)
check("an old seed still reproduces the worlds it did send",
      sorted(old_tracked.enabled_worlds) == sorted(server.enabled_worlds))
check("an empty passthrough generates without raising",
      build(seed=6, passthrough={}) is not None)

print()
if FAILURES:
    print(f"FAILED ({len(FAILURES)}):")
    for f in FAILURES:
        print(f"  - {f}")
    sys.exit(1)
print("tracker: all checks passed")
