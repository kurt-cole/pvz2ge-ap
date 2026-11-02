"""
PvZ2 Gardendless: the conveyor belt swap, rolled at generation.

A Python port of the client's installConveyorHook / _apBeltModSwap /
_apMissingAnswers (TMPPATCH_CONTENT), so generation can see each seed's belt,
simulate it (belt_sim.py) and send the one it keeps (slot_data
conveyor_belts). Tables come from the client source (conveyor_tables.py).

    roll(seed, level_id, attempt, threats) -> Belt

Attempt 0 draws exactly the client's streams: FNV-1a("{seed}|{opening types}")
for the opening belt, FNV-1a("{seed}|wave|{key}|{cn}") per plant a wave adds.
Attempt k > 0 inserts "#{k}" after the seed in both, so it is a fresh roll of
the same rules. node test/client/belt_parity_test.js holds attempt 0 to the
client bit for bit.
"""

from typing import Any, Dict, Iterable, List, Optional, Set

from . import conveyor_tables as CT
from .sim_data import SIM_DATA

BELTS = SIM_DATA.get("belts", {})
MASK = 0xFFFFFFFF

# _apLevelThreats' key order (AP_THREAT_RES).
THREAT_ORDER = ("excavator", "torch", "cold", "jester", "parasol")
THREAT_ZOMBIES = {
    "excavator": {"lostcity_excavator"},
    "torch": {"abbot_torch", "explorer", "explorer_veteran", "kongfu_torch", "monk_torch"},
    "jester": {"birthday_juggler", "dark_juggler", "foodfight_chefster"},
    "parasol": {"lostcity_jane"},
}


def ap_hash(text: str) -> int:
    h = 2166136261
    for ch in text.encode("utf-16-le").decode("utf-16-le"):
        h ^= ord(ch)
        h = (h * 16777619) & MASK
    return h


class Rng:
    """_apRng: mulberry32 returning a float in [0, 1)."""
    __slots__ = ("a",)

    def __init__(self, seed: int):
        self.a = seed & MASK

    def __call__(self) -> float:
        self.a = (self.a + 0x6D2B79F5) & MASK
        a = self.a
        t = _imul(a ^ (a >> 15), 1 | a)
        t = ((t + _imul(t ^ (t >> 7), 61 | t)) & MASK) ^ t
        return ((t ^ (t >> 14)) & MASK) / 4294967296.0


def _imul(a: int, b: int) -> int:
    return (a * b) & MASK


def _pick(rnd: Rng, seq):
    return seq[int(rnd() * len(seq))]


def level_threats(level_id: str, codenames: Iterable[str], stage: str) -> List[str]:
    """_apLevelThreats, from the zombies the level fields as rolled."""
    names = set(codenames)
    out = []
    for key in THREAT_ORDER:
        if key == "cold":
            hit = stage in ("IceageStage", "IceageTutorialStage")
        else:
            hit = bool(names & THREAT_ZOMBIES[key])
        if hit:
            out.append(key)
    return out


class Belt:
    """One rolled belt: what each opening entry became, the threat fallback
    entries appended after it, and what each wave-added plant becomes."""
    __slots__ = ("level", "attempt", "initial", "extra", "wave_map", "shadow")

    def __init__(self, level, attempt):
        self.level, self.attempt = level, attempt
        self.initial: List[Optional[str]] = []
        self.extra: List[Dict[str, Any]] = []
        self.wave_map: Dict[str, str] = {}
        self.shadow = False

    def entries(self) -> List[Dict[str, Any]]:
        """The opening belt as the game will read it (entries, fields kept)."""
        src = BELTS[self.level]["initial"]
        out = [dict(e, PlantType=cn) if cn else dict(e) for e, cn in zip(src, self.initial)]
        return out + [dict(e) for e in self.extra]

    def mods(self) -> List[List[Any]]:
        """[wave, adds, removes] with every plant mapped."""
        out = []
        for w, adds, removes in BELTS[self.level]["mods"]:
            out.append([w,
                        [dict(e, Type=self.wave_map.get(e.get("Type"), e.get("Type")))
                         if e.get("Type") else dict(e) for e in adds],
                        [dict(e, Type=self.wave_map.get(e.get("Type"), e.get("Type")))
                         if e.get("Type") else dict(e) for e in removes]])
        return out

    def slot(self) -> Dict[str, Any]:
        """The slot_data form (see budget_logic / the client's hook)."""
        return {"initial": list(self.initial), "extra": [dict(e) for e in self.extra],
                "map": dict(sorted(self.wave_map.items()))}


def _fits(orig: str, cn: str) -> bool:
    inst = CT.ROLE.get(cn) == "instant"
    return inst == (CT.ROLE.get(orig) == "instant") and (orig not in CT.KILLING or cn in CT.KILLING)


def _missing(threats: List[str], plants: List[str]) -> List[str]:
    """_apMissingAnswers."""
    return [CT.THREAT_FALLBACK[k] for k in threats
            if k in CT.THREAT_FALLBACK and k in CT.THREAT_ANSWERS
            and not any(cn in CT.THREAT_ANSWERS[k] for cn in plants if cn)]


def _js_round(x: float) -> int:
    return int(x + 0.5) if x >= 0 else -int(-x + 0.5)


def roll(seed: int, level_id: str, attempt: int = 0, threats: Iterable[str] = (),
         randomize: bool = True) -> Belt:
    """The belt the client would deal for `attempt` (0 = the client's own;
    -1 = the belt as shipped, the guard's fallback)."""
    if attempt < 0:
        randomize = False
    belt = BELTS[level_id]
    out = Belt(level_id, attempt)
    src = belt["initial"]
    orig = [e.get("PlantType") for e in src]
    out.initial = [None] * len(src)
    threats = [k for k in threats if k in CT.THREAT_ANSWERS]
    answer_sets = [CT.THREAT_ANSWERS[k] for k in threats]
    tag = f"#{attempt}" if attempt else ""
    on_sky = bool(belt["sky"])
    picked = list(orig)

    if randomize and level_id not in CT.PUZZLE_BELTS and src:
        rnd = Rng(ap_hash(f"{seed}{tag}|" + "|".join(c or "" for c in orig)))
        has_water = bool(belt["water"]) or any(
            c in CT.TERRAIN_LOCKED and c != "goldleaf" for c in orig)
        swappable = [bool(c and c in CT.KNOWN and c in CT.SWAPS and c not in CT.BELT_LOCKED
                          and c not in CT.TERRAIN_LOCKED) for c in orig]
        slots = sum(swappable)

        def keep_answer(held, usable_at, keep_moon):
            for answers in answer_sets:
                if any(c and c in answers for c in held):
                    continue
                done = False
                for wide in (False, True):
                    for i in range(len(src)):
                        if not swappable[i] or (keep_moon and held[i] == "moonflower"):
                            continue
                        alone = [a for a in answer_sets if a is not answers and held[i] in a
                                 and not any(j != i and c and c in a for j, c in enumerate(held))]
                        frm = [c for c in usable_at(i, wide)
                               if c in answers and _fits(orig[i], c) and all(c in a for a in alone)]
                        if not frm:
                            continue
                        held[i] = _pick(rnd, frm)
                        done = True
                        break
                    if done:
                        break

        shadow_roll = rnd()
        shadow_done = False
        if CT.SHADOW and slots >= CT.T["CONVEYOR_SHADOW_MIN_SLOTS"] and \
                shadow_roll < CT.T["CONVEYOR_SHADOW_CHANCE"]:
            usable_sh = [c for c in CT.SHADOW if CT.plantable(c, has_water, on_sky)]
            plain = sum(1 for i, c in enumerate(orig) if swappable[i] and CT.ROLE.get(c) != "instant")
            covers = all(any(c in a for c in usable_sh) for a in answer_sets)
            if "moonflower" in usable_sh and plain and covers:
                picks: List[Optional[str]] = []
                taken: Set[str] = set()
                for i, c in enumerate(orig):
                    if not swappable[i]:
                        picks.append(None)
                        continue
                    want = CT.ROLE.get(c)
                    pool = [x for x in usable_sh if CT.ROLE.get(x) == want and _fits(c, x)]
                    if not pool:
                        if want == "instant":
                            picks.append(None)
                            continue
                        pool = usable_sh
                    pick = _pick(rnd, pool)
                    tries = 0
                    while tries < 8 and pick in taken:
                        pick = _pick(rnd, pool)
                        tries += 1
                    taken.add(pick)
                    picks.append(pick)
                if "moonflower" not in picks:
                    for i in range(len(orig) - 1, -1, -1):
                        if picks[i] and CT.ROLE.get(orig[i]) != "instant":
                            picks[i] = "moonflower"
                            break
                held = [p or orig[i] for i, p in enumerate(picks)]
                keep_answer(held, lambda i, wide: usable_sh, True)
                picks = [held[i] if p else None for i, p in enumerate(picks)]
                picked = [p or orig[i] for i, p in enumerate(picks)]
                out.shadow = shadow_done = True

        if not shadow_done:
            used: Set[str] = set()
            new = []
            for c in orig:
                if not c or c not in CT.KNOWN:
                    new.append(c)
                    continue
                cands = CT.SWAPS.get(c)
                if not cands or c in CT.TERRAIN_LOCKED or c in CT.BELT_LOCKED:
                    new.append(c)
                    continue
                usable = [x for x in cands if CT.plantable(x, has_water, on_sky)]
                if len(usable) < 2:
                    new.append(c)
                    continue
                stop = False
                for answers in answer_sets:
                    if c not in answers:
                        continue
                    usable = [x for x in usable if x in answers]
                    if len(usable) < 2:
                        stop = True
                        break
                if stop:
                    new.append(c)
                    continue
                if c in CT.KILLING:
                    usable = [x for x in usable if x in CT.KILLING]
                    if len(usable) < 2:
                        new.append(c)
                        continue
                kin = [x for x in usable if CT.FAMILY.get(x) == CT.FAMILY.get(c)]
                prefer = rnd() < 0.75 and len(kin) >= 2
                frm = kin if prefer else usable
                mine = CT.DPS.get(c)
                if mine:
                    near = [x for x in frm if CT.DPS.get(x) and mine / 2 <= CT.DPS[x] <= mine * 2]
                    if len(near) >= 2:
                        frm = near
                pick = c
                for _ in range(20):
                    cand = _pick(rnd, frm)
                    if cand not in used:
                        pick = cand
                        break
                    pick = cand
                used.add(pick)
                new.append(pick)
            held = list(new)

            def usable_at(i, wide):
                base = sorted(CT.SWAPS) if wide else (CT.SWAPS.get(orig[i]) or [])
                return [x for x in base if CT.plantable(x, has_water, on_sky)]
            keep_answer(held, usable_at, False)
            picked = held

    out.initial = [p if p != o else None for p, o in zip(picked, orig)]
    # The threat fallbacks, appended when the belt deals a real plant.
    cur_entries = [dict(e, PlantType=p) for e, p in zip(src, picked)]
    # The client's shadow path returns before this step, so a shadow deck
    # never gains one.
    if not out.shadow and any(p and p in CT.KNOWN for p in picked):
        add = _missing(threats, picked)
        if add:
            total = sum((e.get("Weight") or 0) for e in cur_entries)
            weight = _js_round(total / len(cur_entries))
            out.extra = [{"PlantType": cn, "Weight": max(1, weight), "MinCount": 1,
                          "MinWeightFactor": 2, "MaxCount": 4, "MaxWeightFactor": 0}
                         for cn in add]
    # _apRememberBelt, then the waves' adds in order (_apBeltModSwap).
    final = picked + [e["PlantType"] for e in out.extra]
    wave_map: Dict[str, str] = {}
    for i, to in enumerate(final):
        if to and i < len(orig) and orig[i] and orig[i] not in wave_map:
            wave_map[orig[i]] = to
    taken = {c for c in final if c}
    key = "|".join(c or "" for c in orig)
    if randomize and level_id not in CT.PUZZLE_BELTS:
        for _, adds, _removes in belt["mods"]:
            for e in adds:
                cn = e.get("Type")
                if not cn or cn in wave_map:
                    continue
                pick = cn
                cands = CT.SWAPS.get(cn)
                if cn in CT.KNOWN and cands and cn not in CT.BELT_LOCKED and \
                        cn not in CT.TERRAIN_LOCKED:
                    has_water = bool(belt["water"]) or any(
                        c in CT.TERRAIN_LOCKED and c != "goldleaf" for c in taken)
                    usable = [x for x in cands if CT.plantable(x, has_water, on_sky)]
                    for answers in answer_sets:
                        if cn in answers:
                            usable = [x for x in usable if x in answers]
                    if cn in CT.KILLING:
                        usable = [x for x in usable if x in CT.KILLING]
                    if len(usable) >= 2:
                        rnd = Rng(ap_hash(f"{seed}{tag}|wave|{key}|{cn}"))
                        kin = [x for x in usable if CT.FAMILY.get(x) == CT.FAMILY.get(cn)]
                        frm = kin if (rnd() < 0.75 and len(kin) >= 2) else usable
                        mine = CT.DPS.get(cn)
                        if mine:
                            near = [x for x in frm if CT.DPS.get(x) and
                                    mine / 2 <= CT.DPS[x] <= mine * 2]
                            if len(near) >= 2:
                                frm = near
                        free = [x for x in frm if x not in taken]
                        if free:
                            pick = _pick(rnd, free)
                wave_map[cn] = pick
                taken.add(pick)
    out.wave_map = {k: v for k, v in wave_map.items() if k != v}
    return out
