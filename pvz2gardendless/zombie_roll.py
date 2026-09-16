"""
PvZ2 Gardendless: the budget zombie roll (zombie_budget_roll), Python side.

Generation rolls every built level with this and derives requirements from the
result (budget_logic.py); the client re-rolls the
identical plan from the same zombie_seed. So this file is a SPEC as much as code:
integer arithmetic only, one PRNG stream consumed in a fixed order, and every
constant below must match the JS port exactly.

STREAMS. mulberry32, below(n) = (next_u32 * n) >> 32.

The dino stream, FNV-1a("{zombie_seed}|{level id}|dinos"), once per level:
the decision below(1000) against DINO_LEVEL_PERMILLE_BY_GOAL[goal_type]; then,
only when the option is on and the level may take dinos, the rate
below(hi - lo + 1) of its DINO_BANDS band, and per event: wave
below(waves - first + 1), type below(sum of weights), row below(len(rows)).

One attempt stream per guard attempt, FNV-1a("{zombie_seed}|{level id}|budget|
{attempt}"). Draws, in order:

  1. every group, in level model order (Waves order, scheduler events inline):
     each swappable bucket of the group, in BUCKET_ORDER:
       noise below(NOISE_SPAN), types below(d) for list groups,
       one weight below(4) per type, then per type one weighted pick
  2. the dynamic pool map, over the level's pool codenames sorted
  3. the share acceptance draw, only when the roll is over its knee

A level that fails the guard on every attempt ships vanilla.
"""

from bisect import bisect_right
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from . import level_model

MASK = 0xFFFFFFFF

# ── tunables (every one mirrored in the client) ──────────────────────────────

# Per-bucket noise, per mille of the bucket's vanilla HP. Centred above 1000 on
# purpose: counts round toward the cheaper feasible pick, and 900-1100 left the
# median level at 0.966 of its vanilla HP. Measured over 20 seeds x 690 levels,
# 1000-1200 gives median 1.000, p5 0.915, p95 1.064, worst 0.79 to 1.13.
NOISE_LO, NOISE_HI = 1000, 1200
NOISE_SPAN = NOISE_HI - NOISE_LO + 1

# A candidate is feasible for a target when one copy is at most this per mille
# of it, so a group can go to fewer, stronger zombies but not overshoot.
FEASIBLE_PERMILLE = 1100

# Weight of a codename the level did not ship with, against 1 for one it did.
NOVEL_WEIGHT = 3

# A bucket's rolled count is capped at max(vanilla * CAP_MULT, vanilla + CAP_ADD).
# [guess] the engine has no per-wave cap (research 7.5); this is playability.
CAP_MULT, CAP_ADD = 3, 4

# Level guard, per mille of the level's vanilla budget.
LEVEL_OK = (900, 1100)
LEVEL_HARD = (750, 1333)
TRIES = 8

# Decision 4: one type's share of a level's spawns may exceed the vanilla
# maximum share, but acceptance halves every SHARE_HALF per mille past
# vanilla max + SHARE_KNEE. [guess] share by count, knee in percentage points.
SHARE_KNEE = 200
SHARE_HALF = 50

# Travelling dinos: the budget they take.
DINO_BUDGET_PERMILLE = 100     # [user] about 10% of the level's budget
DINO_TYPES = ("ankylo", "ptero", "raptor", "stego", "tyranno")

# Chance per mille that a level gains dinos, indexed by goal_type (world key,
# zomboss, completion). [user] Jurassic Marsh levels inside the goal cut over
# the levels in every other world inside the same cut that can take dinos
# (dinos_allowed), so a seed carries about as many dino levels as Jurassic
# Marsh has. Main world levels only; side paths and danger rooms are not
# counted. Flipping a DINO_TEST_* flag changes the denominator, and
# test/balance_v2_test.py re-derives these.
DINO_LEVEL_PERMILLE_BY_GOAL = (262, 232, 236)   # 16/61, 33/142, 44/186

# The Jurassic Marsh difficulty curve. Every Jurassic level that fields dinos,
# sorted by vanilla HP per wave and cut into DINO_BAND_COUNT bands. Per band:
# (HP per wave ceiling, events per wave per mille low, high, first dino wave,
# weights in DINO_TYPES order). A rolled level uses the band its own HP per
# wave falls in. Derived by derive_dino_bands(); the test holds them equal.
DINO_BAND_COUNT = 4
DINO_BANDS: Tuple[Tuple[int, int, int, int, Tuple[int, ...]], ...] = (
    (4192, 500, 600, 3, (0, 7, 24, 8, 11)),
    (5331, 500, 777, 3, (3, 12, 34, 10, 5)),
    (6462, 500, 1000, 2, (8, 11, 35, 8, 15)),
    (1 << 30, 777, 1400, 2, (8, 26, 51, 6, 27)),
)

# [user] Beach and Pirate stages are off until tested in play. With the Pirate
# flag on, dinos only take lanes that start with planks.
DINO_TEST_BEACH = False
DINO_TEST_PIRATE = False

# A random initial grave has no type; every gravestone is 700 Toughness [data].
GRAVE_DEFAULT_HP = 700

LIST_KINDS = ("jittered", "ground", "storm", "grave_spawn")
FIELD_KINDS = ("raid", "beach", "spider", "parachute")
BUCKET_ORDER = (("generic", "land"), ("generic", "water"), ("skycity", "land"))

# Far Future's flyers: Blover specifically, wherever they land [user].
FAR_FUTURE_FLYERS = frozenset({"future_jetpack", "future_jetpack_disco",
                               "future_jetpack_veteran"})
HAZARD_TAGS = ("jester", "iceblock", "air")

# [user] Nothing new before egypt6. A run's opening is played with whatever the
# multiworld has handed over by then, which in a multi-slot seed is close to
# nothing, so these levels may only field the hazards they shipped with -- the
# same restriction conveyor and preset levels carry, for the same reason. It
# rules out dino events here too: a dino is a hazard the level did not ship.
#
# Measured at the seed that prompted this (3283499693, 12 worlds): egypt1 asked
# for a warming plant and egypt3 for Perfume-shroom, which put the first level
# of the run in sphere 11. Everything from egypt6 on keeps the full travelling
# hazard set.
OPENING_LEVELS = frozenset({
    "tutorial1", "tutorial2", "tutorial3", "tutorial4", "tutorial5",
    "egypt1", "egypt2", "egypt3", "egypt4", "egypt5",
})


# ── the PRNG ─────────────────────────────────────────────────────────────────

def _imul(a: int, b: int) -> int:
    return ((a & MASK) * (b & MASK)) & MASK


def ap_hash(text: str) -> int:
    """FNV-1a over UTF-16 code units, as the client's _apHash (ASCII keys here)."""
    h = 2166136261
    for ch in text:
        h ^= ord(ch)
        h = _imul(h, 16777619)
    return h & MASK


class Stream:
    """mulberry32, yielding integers."""

    def __init__(self, seed: int):
        self.a = seed & MASK

    def next_u32(self) -> int:
        self.a = (self.a + 0x6D2B79F5) & MASK
        a = self.a
        t = _imul(a ^ (a >> 15), 1 | a)
        t = ((t + _imul(t ^ (t >> 7), 61 | t)) & MASK) ^ t
        return (t ^ (t >> 14)) & MASK

    def below(self, n: int) -> int:
        return (self.next_u32() * n) >> 32 if n > 0 else 0


# ── tables derived from the model ────────────────────────────────────────────

class _Tables:
    def __init__(self, model: Dict[str, Any]):
        self.model = model
        self.zombies = model["zombies"]
        self.hp = {c: z["hp"] for c, z in self.zombies.items()}
        self.tier = {c: z["tier"] for c, z in self.zombies.items()}
        pools: Dict[Tuple[str, str], List[str]] = {k: [] for k in BUCKET_ORDER}
        tiers: Dict[str, List[str]] = {}
        for c, z in sorted(self.zombies.items()):
            key = self.bucket_key(c)
            if key and z["hp"] > 0:
                pools[key].append(c)
            if z["tier"]:
                tiers.setdefault(z["tier"], []).append(c)
        # Sorted by (hp, name): a feasibility cut is then one bisect.
        self.pools = {k: sorted(v, key=lambda c: (self.hp[c], c)) for k, v in pools.items()}
        self.pool_hp = {k: [self.hp[c] for c in v] for k, v in self.pools.items()}
        # Codenames that bring a hazard a specific plant answers. A level the
        # player does not bring plants to cannot be asked for that plant, so it
        # never gains one it did not ship with (see roll_level).
        self.hazard_names = {c for c, z in self.zombies.items()
                             if any(f"-{tag}" in z["tier"] for tag in HAZARD_TAGS)
                             or c in FAR_FUTURE_FLYERS}
        self.tiers = tiers
        # Whether the game will hand this codename a wave's plant food. Absent
        # from a model generated before the flag was extracted, which reads as
        # "it can": that is what the roll assumed before this existed.
        self.carry = {c: bool(z.get("carry", True)) for c, z in self.zombies.items()}
        # Zombies that put bodies into the lanes either side of their own
        # without checking whether those lanes are playable. Absent from a model
        # generated before the flag was extracted, which reads as "it does not":
        # that is what the roll assumed before this existed.
        self.multilane_names = {c for c, z in self.zombies.items()
                                if z.get("multilane")}
        # A count-field source may only name a codename the game itself names in
        # that field somewhere: the spawner is written around what it drops.
        self.field_names: Dict[str, set] = {k: set() for k in FIELD_KINDS}
        for level in model["levels"].values():
            for g in level["groups"]:
                if g["k"] in FIELD_KINDS and g.get("p"):
                    self.field_names[g["k"]].add(g["p"])

    def bucket_key(self, codename: str) -> Optional[Tuple[str, str]]:
        z = self.zombies.get(codename)
        if not z:
            return None
        if z["tier"]:
            return ("generic", "water" if "-water" in z["tier"] else "land")
        if z["excluded"] == "skycity":
            # Stage-bound: Aerial Fortress zombies trade only with each other.
            return ("skycity", "land")
        return None


_TABLES: Optional[_Tables] = None


def tables() -> _Tables:
    global _TABLES
    if _TABLES is None:
        _TABLES = _Tables(level_model.load())
    return _TABLES


# ── weighing ─────────────────────────────────────────────────────────────────

def _groups_hp(t: _Tables, groups) -> int:
    return sum(t.hp.get(c, 0) * n * g.get("rep", 1) for g in groups for c, n in g["z"])


def _dynamic_hp(t: _Tables, level, mapping: Dict[str, str]) -> int:
    """Dynamic spend in HP: points over the waves, at the pool's mean HP per point."""
    total = 0
    waves = level["waves"]
    for entry in level["dynamic"]:
        pool = [mapping.get(c, c) for c in entry["pool"]]
        ratios = [t.hp[c] * 1000 // t.zombies[c]["cost"] for c in pool
                  if t.hp.get(c) and t.zombies.get(c, {}).get("cost")]
        if not ratios:
            continue
        milli = sum(ratios) // len(ratios)
        points = 0
        for wave in range(entry["w"], waves + 1):
            p = entry["p"] + entry["inc"] * (wave - entry["w"])
            if p > 0:
                points += p
        total += points * milli // 1000
    return total


def _graves_hp(t: _Tables, level) -> int:
    graves = level["graves"]
    table = t.model["grave_hp"]
    total = sum(table.get(k, 0) * n for k, n in graves["initial"].items())
    total += graves["random_initial"] * GRAVE_DEFAULT_HP
    for _, pool in graves["spawned"]:
        total += sum(table.get(k, 0) * n for k, n in pool.items())
    return total


def _max_share(groups) -> Tuple[int, int]:
    """(largest single-codename count, total count), repeats included."""
    counts: Counter = Counter()
    for g in groups:
        for c, n in g["z"]:
            counts[c] += n * g.get("rep", 1)
    total = sum(counts.values())
    return (max(counts.values()) if counts else 0), total


def _accept_permille(over: int) -> int:
    """1000 halved every SHARE_HALF per mille over the knee, linear in between."""
    q, r = divmod(over, SHARE_HALF)
    base = 1000 >> q if q < 11 else 0
    return base - base * r // (2 * SHARE_HALF)


# ── one level ────────────────────────────────────────────────────────────────

def eligible(level) -> bool:
    return not level["bespoke"] and not level["generated"]


def dinos_allowed(level) -> bool:
    if (not eligible(level) or level["dinos"] or not level["waves"]
            or not level["own_plants"]):
        # own_plants: Perfume-shroom cannot be asked of a level that hands the
        # player its plants.
        return False
    if "Beach" in level["stage"]:
        return DINO_TEST_BEACH
    if "Pirate" in level["stage"]:
        return DINO_TEST_PIRATE and bool(level.get("planks"))
    return True


def level_budget(t: "_Tables", level) -> int:
    """Vanilla HP the level fields: groups, dynamic spend and graves."""
    return (_groups_hp(t, level["groups"]) + _dynamic_hp(t, level, {})
            + _graves_hp(t, level))


def derive_dino_bands(t: "_Tables", count: int = DINO_BAND_COUNT):
    """DINO_BANDS, measured from Jurassic Marsh. See the constant."""
    rows = sorted((level_budget(t, lv) // lv["waves"], lid)
                  for lid, lv in t.model["levels"].items()
                  if lv["world"] == "dino" and eligible(lv) and lv["waves"] and lv["dinos"])
    bands = []
    for b in range(count):
        chunk = rows[b * len(rows) // count:(b + 1) * len(rows) // count]
        levels = [t.model["levels"][lid] for _, lid in chunk]
        rates = sorted(len(lv["dinos"]) * 1000 // lv["waves"] for lv in levels)
        firsts = sorted(min(d[0] for d in lv["dinos"]) for lv in levels)
        weights = Counter(d[1] for lv in levels for d in lv["dinos"])
        ceiling = chunk[-1][0] if b < count - 1 else 1 << 30
        bands.append((ceiling, rates[len(rates) // 4], rates[3 * len(rates) // 4],
                      firsts[len(firsts) // 2], tuple(weights[k] for k in DINO_TYPES)))
    return tuple(bands)


def _dino_events(rng: Stream, level, budget: int) -> List[List[Any]]:
    """Dino events shaped like a Jurassic Marsh level of the same difficulty."""
    waves = level["waves"]
    per_wave = budget // waves
    band = next(b for b in DINO_BANDS if per_wave <= b[0])
    _, lo, hi, first, weights = band
    rate = lo + rng.below(hi - lo + 1)
    first = min(first, waves)
    rows = level.get("planks") if "Pirate" in level["stage"] else [0, 1, 2, 3, 4]
    events = []
    for _ in range(max(1, waves * rate // 1000)):
        wave = first + rng.below(waves - first + 1)
        r = rng.below(sum(weights))
        kind = 0
        while r >= weights[kind]:
            r -= weights[kind]
            kind += 1
        events.append([wave, DINO_TYPES[kind], rows[rng.below(len(rows))]])
    return sorted(events)


def _pick(rng: Stream, cands: List[str], vanilla: set) -> str:
    """Weighted pick: NOVEL_WEIGHT per codename, 1 for one the level shipped."""
    old = [i for i, c in enumerate(cands) if c in vanilla]
    total = NOVEL_WEIGHT * len(cands) - (NOVEL_WEIGHT - 1) * len(old)
    r = rng.below(total)
    lo, hi = 0, len(cands) - 1
    while lo < hi:                      # smallest i with weight(0..i) > r
        mid = (lo + hi) // 2
        cum = NOVEL_WEIGHT * (mid + 1) - (NOVEL_WEIGHT - 1) * bisect_right(old, mid)
        if cum > r:
            hi = mid
        else:
            lo = mid + 1
    return cands[lo]


def _roll_bucket(t: _Tables, rng: Stream, key, entries, vanilla: set,
                 scale: int, field_kind: Optional[str], cap: int,
                 pools) -> List[List[Any]]:
    pool, pool_hp = pools[key]
    if field_kind:
        allowed = t.field_names[field_kind]
        keep = [i for i, c in enumerate(pool) if c in allowed]
        pool, pool_hp = [pool[i] for i in keep], [pool_hp[i] for i in keep]
    if len(pool) < 2:
        return [list(e) for e in entries]
    h = sum(t.hp[c] * n for c, n in entries)
    noise = NOISE_LO + rng.below(NOISE_SPAN)
    target = h * noise // 1000 * scale // 1000
    k = 1 if field_kind else 1 + rng.below(len(entries))
    weights = [1 + rng.below(4) for _ in range(k)]
    wsum = sum(weights)
    picks: Counter = Counter()
    for weight in weights:
        part = target * weight // wsum
        cut = bisect_right(pool_hp, part * FEASIBLE_PERMILLE // 1000)
        cands = pool[:cut] if cut else pool[:1]
        c = _pick(rng, cands, vanilla)
        picks[c] += max(1, (part + t.hp[c] // 2) // t.hp[c])
    while sum(picks.values()) > cap:
        c = max(sorted(picks), key=lambda x: picks[x])
        picks[c] -= 1
        if picks[c] == 0 and len(picks) > 1:
            del picks[c]
    return sorted([c, n] for c, n in picks.items() if n > 0)


def _ensure_carriers(t: _Tables, entries, need: int, pools):
    """Keep a group able to hand out the plant food it owes.

    addPlantFood picks carriers at random from the zombies the wave spawned,
    skipping the ones flagged CannotCarryPlantfoodsInWaves; the grave spawner
    has no second pass for them at all. So a group owing plant food has to
    field at least that many zombies able to take it.

    No draws happen here. The replacement is the nearest-HP carrier in the same
    bucket, by name on a tie, so the stream stays in step with the client.
    """
    if need <= 0 or not entries:
        return entries
    counts = {c: n for c, n in entries}
    carried = sum(n for c, n in counts.items() if t.carry.get(c, True))
    if carried >= need:
        return entries

    def nearest(bucket, hp):
        names = [c for c in pools[bucket][0] if t.carry.get(c, True)]
        if not names:
            return None
        return min(names, key=lambda c: (abs(t.hp.get(c, 0) - hp), c))

    while carried < need:
        swappable = sorted((c for c, n in counts.items()
                            if n > 0 and not t.carry.get(c, True) and t.bucket_key(c)),
                           key=lambda c: (-counts[c], c))
        source = swappable[0] if swappable else next(
            (c for c in sorted(counts) if t.bucket_key(c)), None)
        if source is None:
            break
        pick = nearest(t.bucket_key(source), t.hp.get(source, 0))
        if pick is None:
            break
        if swappable:                    # convert one body rather than add one
            counts[source] -= 1
            if counts[source] == 0:
                del counts[source]
        counts[pick] = counts.get(pick, 0) + 1
        carried += 1
    return sorted([c, n] for c, n in counts.items() if n > 0)


def _attempt(t: _Tables, seed: int, level_id: str, level, attempt: int,
             scale: int, vanilla: set, pools):
    rng = Stream(ap_hash(f"{seed}|{level_id}|budget|{attempt}"))
    groups = []
    done: Dict[str, Dict[str, Any]] = {}
    for g in level["groups"]:
        kind = g["k"]
        out = {"id": g["id"], "w": g["w"], "k": kind, "z": [list(e) for e in g["z"]]}
        for extra in ("f", "rep"):
            if extra in g:
                out[extra] = g[extra]
        if (kind in LIST_KINDS or kind in FIELD_KINDS) and g["id"] in done:
            # One object referenced from several waves (31 levels do this)
            # spawns the same thing each time, and the client can only write it
            # once: reuse its first roll, with no draws.
            prev = done[g["id"]]
            out["z"] = [list(e) for e in prev["z"]]
            if "p" in prev:
                out["p"] = prev["p"]
            if "bring" in g:
                out["bring"] = g["bring"]
        elif kind in LIST_KINDS or kind in FIELD_KINDS:
            entries = g["z"]
            buckets: Dict[Any, list] = {}
            fixed = []
            for c, n in entries:
                key = t.bucket_key(c)
                (buckets.setdefault(key, []) if key else fixed).append([c, n])
            rolled = [list(e) for e in fixed]
            # The count cap belongs to the group (one wave's spawn), shared out
            # by each bucket's vanilla count, so a group split across land and
            # water cannot take the cap twice.
            swappable = sum(n for bucket in buckets.values() for _, n in bucket)
            group_cap = max(swappable * CAP_MULT, swappable + CAP_ADD)
            for key in BUCKET_ORDER:
                if key in buckets:
                    n0 = sum(n for _, n in buckets[key])
                    rolled += _roll_bucket(t, rng, key, buckets[key], vanilla, scale,
                                           kind if kind in FIELD_KINDS else None,
                                           max(1, group_cap * n0 // swappable), pools)
            merged: Counter = Counter()
            for c, n in rolled:
                merged[c] += n
            out["z"] = sorted([c, n] for c, n in merged.items())
            if kind in LIST_KINDS:
                # Field sources name one codename in a field the spawner is
                # written around, so they are left alone: swapping one for a
                # carrier could name something the field may not hold.
                out["z"] = _ensure_carriers(t, out["z"], g.get("pf", 0), pools)
            if kind in FIELD_KINDS and out["z"]:
                out["p"] = out["z"][0][0]
            if "bring" in g:
                out["bring"] = g["bring"]
            done[g["id"]] = out
        groups.append(out)

    mapping = {}
    for c in sorted({c for e in level["dynamic"] for c in e["pool"]}):
        members = t.tiers.get(t.tier.get(c, ""), [])
        if len(members) >= 2:
            pick = members[rng.below(len(members))]
            if pick != c:
                mapping[c] = pick
    return rng, groups, mapping


def roll_level(seed: int, level_id: str, dinos: bool = False,
               goal_type: int = 2) -> Optional[Dict[str, Any]]:
    """The plan for one level, or None when the level is never rolled."""
    t = tables()
    level = t.model["levels"].get(level_id)
    if level is None or not eligible(level):
        return None
    graves = _graves_hp(t, level)
    budget = _groups_hp(t, level["groups"]) + _dynamic_hp(t, level, {}) + graves
    vanilla = {c for g in level["groups"] for c, _ in g["z"]}
    pools = {k: (t.pools[k], t.pool_hp[k]) for k in BUCKET_ORDER}
    drop = set()
    if not level["own_plants"] or level_id in OPENING_LEVELS:
        # Conveyor or preset seed bank: the player cannot bring a counter, so
        # only hazards the level already shipped with may appear. Before egypt6
        # the player HAS no counter yet, which comes to the same thing.
        drop |= t.hazard_names - vanilla
    if level.get("lanes", 5) < 5:
        # A narrower lawn than the game's five lanes, which only the tutorial
        # levels have. A chicken thrower or a barrel puts bodies into the lanes
        # either side of its own and never asks whether those lanes are
        # playable, so on this level they would land where nothing can be
        # planted [user]. A level that ships one keeps it, as with hazards.
        drop |= t.multilane_names - vanilla
    if drop:
        for k in BUCKET_ORDER:
            names = [c for c in t.pools[k] if c not in drop]
            pools[k] = (names, [t.hp[c] for c in names])
    top, count = _max_share(level["groups"])
    knee = min(1000, (top * 1000 // count if count else 0) + SHARE_KNEE)

    # Dinos are decided once per level, on their own stream, so the guard's
    # attempts never change whether a level has them, and a level that gains
    # none rolls exactly as it does with the option off.
    dino_rng = Stream(ap_hash(f"{seed}|{level_id}|dinos"))
    # One decision draw against the goal's chance, so a level that gains dinos
    # at a lower chance also gains them at every higher one.
    added = []
    # The draw is the first operand on purpose: it is taken whatever the answer,
    # so a level that cannot gain dinos still leaves the stream where the client
    # expects it.
    if (dino_rng.below(1000) < DINO_LEVEL_PERMILLE_BY_GOAL[goal_type]
            and dinos and level_id not in OPENING_LEVELS and dinos_allowed(level)):
        added = _dino_events(dino_rng, level, budget)
    scale = 1000 - DINO_BUDGET_PERMILLE if added else 1000

    best = None
    for attempt in range(TRIES):
        rng, groups, mapping = _attempt(t, seed, level_id, level, attempt, scale,
                                        vanilla, pools)
        total = _groups_hp(t, groups) + _dynamic_hp(t, level, mapping) + graves
        if added:
            total = total * 1000 // (1000 - DINO_BUDGET_PERMILLE)
        ratio = total * 1000 // budget if budget else 1000
        top, count = _max_share(groups)
        share = top * 1000 // count if count else 0
        if share > knee and rng.below(1000) >= _accept_permille(share - knee):
            continue
        plan = {"level": level_id, "attempt": attempt, "vanilla": False,
                "budget": budget, "ratio": ratio, "groups": groups,
                "dynamic": mapping, "dinos": sorted(added)}
        if LEVEL_OK[0] <= ratio <= LEVEL_OK[1]:
            return plan
        if best is None or abs(ratio - 1000) < abs(best["ratio"] - 1000):
            best = plan
    if best is not None and LEVEL_HARD[0] <= best["ratio"] <= LEVEL_HARD[1]:
        return best
    return {"level": level_id, "attempt": -1, "vanilla": True, "budget": budget,
            "ratio": 1000, "groups": [dict(g) for g in level["groups"]],
            "dynamic": {}, "dinos": []}


# ── what a plan asks of the player (phase 3 reads these) ─────────────────────

def roster(plan) -> Counter:
    """Static spawns by codename, repeats included."""
    counts: Counter = Counter()
    for g in plan["groups"]:
        for c, n in g["z"]:
            counts[c] += n * g.get("rep", 1)
    return counts


def hazards(plan) -> set:
    """Hazard names the plan fields: tier tags, Far Future flyers, dinos."""
    t = tables()
    level = t.model["levels"][plan["level"]]
    names = set(roster(plan))
    for entry in level["dynamic"]:
        names.update(plan["dynamic"].get(c, c) for c in entry["pool"])
    out = set()
    for c in names:
        tier = t.tier.get(c, "")
        out.update(tag for tag in HAZARD_TAGS if f"-{tag}" in tier)
        if c in FAR_FUTURE_FLYERS:
            out.add("far_future_flyer")
    if plan["dinos"] or level["dinos"]:
        out.add("dino")
    return out
