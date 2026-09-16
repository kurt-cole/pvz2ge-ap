"""
PvZ2 Gardendless: the plant-power loadout simulation. Design: POWER_SIM.md.

simulate(level_id, producer, count, attacker, utility, hp_scale) -> bool

A loadout is one sun producer type (or None) planted `count` times first, one
attacker type, and optionally one utility type. Everything is deterministic:
random ranges in game data are taken at their expected value.

Two phases, so a break-even search over hp_scale re-runs only the second:

  economy(level, loadout) -> Timeline
      sun income (starting sun, the level's sky dropper, producers) and what the
      player buys when: producers, then an attacker per lane, then a utility per
      lane, then more attackers up to the lane cap, then spare walls. Consumable
      uses are banked as they become ready and affordable.

  fight(level, timeline, hp_scale) -> bool
      waves spawn on the game's own timer (or early, once the wave is down to its
      next-wave health threshold); zombies are dealt to lanes; each lane kills its
      zombies front to back. Attackers are bought on the economy's schedule but
      planted in a lane only when a zombie there calls for one (_Lawn). A lane
      fails when a zombie reaches its front plant and eats through it.

Geometry [guess, calibrate]: zombies enter at x = SPAWN_X tiles; producers take
the back columns, attackers stand in front of them, walls and contact plants in
front of the attackers.
"""

from typing import Any, Dict, List, Optional, Tuple

from .sim_data import SIM_DATA
from . import level_model

LANE_TILES = 9
SPAWN_X = 9.5
PRODUCERS_MAX = 10        # two columns on a five-lane lawn
EARLY_WAVE_MIN = 4.5      # WaveZombieDamageCountdown = 4 + rand [data]
WAVE_TIMER = 27.5         # 25 + rand*5 [data]
FLAG_EXTRA = 10.0         # after a flag wave [data]
PLANT_BITE = 3.0          # seconds a zombie spends eating a 300-toughness plant
END_PAD = 60.0

PLANTS = SIM_DATA["plants"]
ZOMBIES = SIM_DATA["zombies"]
LEVELS = SIM_DATA["levels"]

ATTACK_KINDS = ("shooter", "short", "contact", "burst", "instant", "chomp", "sunburn")


def producers() -> List[str]:
    return sorted(n for n, p in PLANTS.items() if p["k"] == "producer")


def attackers() -> List[str]:
    return sorted(n for n, p in PLANTS.items() if p["k"] in ATTACK_KINDS)


def utilities() -> List[str]:
    return sorted(n for n, p in PLANTS.items() if p["k"] == "utility")


# ── roster ───────────────────────────────────────────────────────────────────

def roster(level_id: str, plan: Optional[Dict[str, Any]] = None) -> Tuple[List[List[Tuple]], int]:
    """([wave -> [(hp, walk, eat, row or -1)]], lanes) for a level.

    `plan` is a budget-roll plan (zombie_roll.roll_level); None is the vanilla
    roster. Dynamic spawn points are spent at the expected HP and count of their
    pool.
    """
    level = level_model.load()["levels"][level_id]
    waves_n = max(1, level["waves"])
    groups = plan["groups"] if plan and not plan.get("vanilla") else level["groups"]
    mapping = (plan or {}).get("dynamic") or {}
    waves: List[List[Tuple]] = [[] for _ in range(waves_n + 1)]
    for g in groups:
        w = min(max(1, g["w"]), waves_n)
        rows = g.get("rows")
        for _ in range(g.get("rep", 1)):
            for i, (cn, n) in enumerate(g["z"]):
                z = ZOMBIES.get(cn)
                if not z or z["hp"] <= 0:
                    continue
                for j in range(n):
                    row = rows[(i + j) % len(rows)] - 1 if rows else -1
                    waves[w].append((z["hp"], z["walk"], z["eat"], row,
                                     "noswallow" in z.get("tags", ())))
    costs_of = level_model.load()["zombies"]
    for entry in level["dynamic"]:
        pool = []
        for c in entry["pool"]:
            z = ZOMBIES.get(mapping.get(c, c))
            cost = costs_of.get(c, {}).get("cost", 0)
            if z and z["hp"] > 0 and cost > 0:
                pool.append((cost, z["hp"], z["walk"], z["eat"]))
        if not pool:
            continue
        for w in range(max(1, entry["w"]), waves_n + 1):
            points = entry["p"] + entry["inc"] * (w - entry["w"])
            if points <= 0:
                continue
            n, hp, walk, eat = _spend(tuple(sorted(pool)), int(points))
            for _ in range(int(round(n))):
                waves[w].append((hp, walk, eat, -1, False))
    return waves[1:], level.get("lanes", 5)


_SPEND: Dict[Tuple, Tuple[float, float, float, float]] = {}


def _spend(pool, points):
    """(expected count, mean hp, mean walk, mean eat) of a dynamic spawn budget.

    The spawner keeps picking among the pool zombies it can still afford until
    none fits [guess: uniform among affordable]. Expected values, memoised.
    """
    key = (pool, points)
    if key in _SPEND:
        return _SPEND[key]
    total_n = total_hp = total_walk = total_eat = 0.0

    def go(p, memo={}):
        k = (pool, p)
        if k in memo:
            return memo[k]
        fit = [z for z in pool if z[0] <= p]
        if not fit:
            memo[k] = (0.0, 0.0, 0.0, 0.0)
            return memo[k]
        n = hp = walk = eat = 0.0
        for cost, h, wk, et in fit:
            sn, shp, swk, set_ = go(p - cost)
            n += 1 + sn
            hp += h + shp
            walk += wk + swk
            eat += et + set_
        f = len(fit)
        memo[k] = (n / f, hp / f, walk / f, eat / f)
        return memo[k]

    total_n, total_hp, total_walk, total_eat = go(points)
    out = (total_n, total_hp / total_n if total_n else 0.0,
           total_walk / total_n if total_n else 0.0, total_eat / total_n if total_n else 0.0)
    _SPEND[key] = out
    return out


# ── economy ──────────────────────────────────────────────────────────────────

class Timeline:
    """What the loadout has on the lawn over time, per lane."""
    __slots__ = ("lanes", "rate", "walls", "front", "uses", "ut_uses", "stops", "chill",
                 "placed", "burn", "pcols", "_d_rate", "_d_count")

    def __init__(self, lanes):
        self.lanes = lanes
        # per lane: [(time, damage per second from then on)], cumulative
        self.rate: List[List[Tuple[float, float]]] = [[(0.0, 0.0)] for _ in range(lanes)]
        # per lane: [(time, wall hp added)]
        self.walls: List[List[Tuple[float, float]]] = [[] for _ in range(lanes)]
        # per lane: [(time, column of the front attacker from then on)]
        self.front: List[List[Tuple[float, float]]] = [[(0.0, 0.0)] for _ in range(lanes)]
        # consumable attacker uses, ready times (banked)
        self.uses: List[float] = []
        # consumable utility uses, ready times (banked)
        self.ut_uses: List[float] = []
        # per lane: fraction of time a zombie is stopped, chill (walk x 0.5) on/off
        self.stops: List[float] = [0.0] * lanes
        self.chill: List[bool] = [False] * lanes
        # per lane: times an attacker was placed there
        self.placed: List[List[float]] = [[] for _ in range(lanes)]
        # per lane: sunburn damage delivered at a moment, [(time, damage)]
        self.burn: List[List[Tuple[float, float]]] = [[] for _ in range(lanes)]
        self.pcols = 0
        # per lane: (time, change) of damage rate and attacker count, turned
        # into `rate` and `front` by finish()
        self._d_rate: List[List[Tuple[float, float]]] = [[] for _ in range(lanes)]
        self._d_count: List[List[Tuple[float, int]]] = [[] for _ in range(lanes)]

    def finish(self):
        for lane in range(self.lanes):
            rate, value = [(0.0, 0.0)], 0.0
            for t, dx in sorted(self._d_rate[lane]):
                value += dx
                if rate[-1][0] == t:
                    rate[-1] = (t, value)
                else:
                    rate.append((t, value))
            self.rate[lane] = rate
            front, n = [(0.0, 0.0)], 0
            for t, dx in sorted(self._d_count[lane]):
                n += dx
                col = float(self.pcols + n) if n > 0 else 0.0
                if front[-1][0] == t:
                    front[-1] = (t, col)
                else:
                    front.append((t, col))
            self.front[lane] = front
        return self


def _sky_drops(drop, until):
    out = []
    if not drop:
        return out
    delay, base, rng, inc, mx, value = drop
    t, n = delay, 0
    while t <= until:
        out.append((t, value))
        t += min(mx, base + n * inc + rng / 2)
        n += 1
    return out


def lane_weights(waves, lanes: int) -> List[float]:
    """Share of the level's zombie HP each lane receives.

    Fixed rows count where they are; the rest spread evenly. The simulated player
    plants where the pressure is, which is what a player reading the zombie
    preview does.
    """
    w = [0.0] * lanes
    for wave in waves:
        for hp, _, _, row, _ in wave:
            if 0 <= row < lanes:
                w[row] += hp
            else:
                for i in range(lanes):
                    w[i] += hp / lanes
    return w


def _pick(counts, weights, cap):
    """The lane whose weight per plant already there is highest, under cap."""
    best, score = None, -1.0
    for i, c in enumerate(counts):
        if c >= cap or weights[i] <= 0:
            continue
        v = weights[i] / (c + 1)
        if v > score:
            best, score = i, v
    return best


def lane_cap(pcols: int) -> int:
    """Attackers a lane holds: the tiles in front of the producers, less one for a wall."""
    return max(1, LANE_TILES - pcols - 1)


def economy(level_id: str, producer: Optional[str], count: int, attacker: str,
            utility: Optional[str], horizon: float, lanes: int,
            weights: Optional[List[float]] = None) -> Timeline:
    """Greedy purchases in a fixed priority, at the first moment each is possible.

    Priority: producers until `count`; then one attacker per lane; then one
    utility per lane; then attackers up to lane_cap per lane; then spare
    walls. A consumable attacker or utility is banked as a use instead of placed.
    """
    lv = LEVELS[level_id]
    atk = PLANTS[attacker]
    ut = PLANTS[utility] if utility else None
    pr = PLANTS[producer] if (producer and count) else None
    tl = Timeline(lanes)
    weights = weights or [1.0] * lanes
    active = sum(1 for x in weights if x > 0)

    income = _sky_drops(lv["drop"], horizon)
    sun = float(lv["sun0"])
    ready_p = pr["cd"] * pr["cf"] if pr else 0.0
    ready_a = atk["cd"] * atk["cf"]
    ready_u = ut["cd"] * ut["cf"] if ut else 0.0
    placed_p = 0
    lane_atk = [0] * lanes
    lane_ut = [0] * lanes
    p_cols = (count + lanes - 1) // lanes if pr else 0
    tl.pcols = p_cols
    cap = lane_cap(p_cols)
    atk_bank = atk["k"] == "instant"
    life = atk.get("life", 0.0)
    expiries: List[Tuple[float, int]] = []     # (time, lane) a placed attacker expires
    burner = atk["k"] == "sunburn"
    wsum = sum(weights) or 1.0
    ut_bank = bool(ut) and not ut.get("hp") and ut.get("i", 0.0) == 0.0
    per_copy = _lane_rate(atk)

    t = 0.0
    idx = 0
    while t <= horizon:
        while idx < len(income) and income[idx][0] <= t + 1e-9:
            sun += income[idx][1]
            idx += 1
        while expiries and expiries[0][0] <= t + 1e-9:
            _, lane = expiries.pop(0)
            lane_atk[lane] -= 1
        while True:
            if pr and placed_p < count:
                if ready_p <= t and sun >= pr["s"]:
                    sun -= pr["s"]
                    placed_p += 1
                    ready_p = t + pr["cd"]
                    k = 0
                    while t + pr["ps"] + k * pr["pi"] <= horizon:
                        income.append((t + pr["ps"] + k * pr["pi"], pr["pv"]))
                        k += 1
                    income.sort()
                    continue
                break
            if atk_bank:
                if ready_a <= t and sun >= atk["s"]:
                    sun -= atk["s"]
                    ready_a = t + atk["cd"]
                    tl.uses.append(t)
                    continue
            elif _pick(lane_atk, weights, 1) is not None:
                if ready_a <= t and sun >= atk["s"]:
                    sun -= atk["s"]
                    ready_a = t + atk["cd"]
                    lane = _pick(lane_atk, weights, 1)
                    _place_attacker(tl, lane, t, atk, per_copy, lane_atk, life)
                    if life:
                        expiries.append((t + life, lane))
                        expiries.sort()
                    continue
                break
            if ut and ut_bank:
                if ready_u <= t and sun >= ut["s"]:
                    sun -= ut["s"]
                    ready_u = t + ut["cd"]
                    tl.ut_uses.append(t)
                    continue
            elif ut and _pick(lane_ut, weights, 1) is not None:
                if ready_u <= t and sun >= ut["s"]:
                    sun -= ut["s"]
                    ready_u = t + ut["cd"]
                    _place_utility(tl, _pick(lane_ut, weights, 1), t, ut, lane_ut)
                    continue
                break
            if not atk_bank and _pick(lane_atk, weights, cap) is not None:
                if ready_a <= t and sun >= atk["s"]:
                    sun -= atk["s"]
                    ready_a = t + atk["cd"]
                    lane = _pick(lane_atk, weights, cap)
                    _place_attacker(tl, lane, t, atk, per_copy, lane_atk, life)
                    if life:
                        expiries.append((t + life, lane))
                        expiries.sort()
                    continue
                break
            if ut and ut.get("hp") and ready_u <= t and sun >= ut["s"]:
                sun -= ut["s"]
                ready_u = t + ut["cd"]
                _place_utility(tl, _pick(lane_ut, weights, 99), t, ut, lane_ut)
                continue
            break
        if burner and sum(lane_atk) and sun >= atk.get("sb", 50.0):
            # Shots are paid in sun: whatever the purchases above left, less
            # the price of the next grass while lanes still want one.
            reserve = atk["s"] if _pick(lane_atk, weights, cap) is not None else 0.0
            shots = int(max(0.0, sun - reserve) // atk["sb"])
            if shots:
                sun -= shots * atk["sb"]
                for lane in range(lanes):
                    if lane_atk[lane] and weights[lane] > 0:
                        tl.burn[lane].append((t, shots * atk["d"] * weights[lane] / wsum))
        nxt = horizon + 1.0
        if idx < len(income):
            nxt = income[idx][0]
        for r in (ready_p, ready_a, ready_u):
            if t < r < nxt:
                nxt = r
        if expiries and t < expiries[0][0] < nxt:
            nxt = expiries[0][0]
        t = nxt
    return tl.finish()


def _lane_rate(p):
    """Damage per second one copy puts into its lane (splash counted at half)."""
    if p["k"] in ("shooter", "short", "burst", "contact"):
        extra = p.get("x", 0.0) * max(0, p.get("t", 1) - 1) * 0.5
        return (p.get("d", 0.0) + extra) / max(p.get("i", 1.0), 0.05)
    # Sunburn damage is delivered shot by shot as sun allows (Timeline.burn).
    return 0.0


def _place_attacker(tl, lane, t, atk, per_copy, lane_atk, life):
    lane_atk[lane] += 1
    tl.placed[lane].append(t)
    tl._d_count[lane].append((t, 1))
    if life:
        tl._d_count[lane].append((t + life, -1))
    covered = [lane]
    if atk.get("l", 1) >= 3:
        covered += [x for x in (lane - 1, lane + 1) if 0 <= x < tl.lanes]
    for x in covered:
        tl._d_rate[x].append((t, per_copy))
        if life:
            tl._d_rate[x].append((t + life, -per_copy))


def _place_utility(tl, lane, t, ut, lane_ut):
    lane_ut[lane] += 1
    if ut.get("hp"):
        tl.walls[lane].append((t, ut["hp"]))
    if ut.get("ch"):
        tl.chill[lane] = True
    if ut.get("fz") and ut.get("i"):
        tl.stops[lane] = min(0.8, tl.stops[lane] + ut["fz"] / ut["i"] * 0.1)
    if ut.get("kb") and ut.get("i"):
        tl.stops[lane] = min(0.8, tl.stops[lane] + ut["kb"] / ut["i"] * 2.0)


# ── fight ────────────────────────────────────────────────────────────────────

def _time_to_deal(rate, start, hp):
    """Earliest time the damage segments in `rate`, counted from `start`, reach hp."""
    need = hp
    n = len(rate)
    for i in range(n):
        seg_t, seg_r = rate[i]
        seg_end = rate[i + 1][0] if i + 1 < n else float("inf")
        if seg_end <= start:
            continue
        a = seg_t if seg_t > start else start
        if seg_r > 0:
            if seg_r * (seg_end - a) >= need:
                return a + need / seg_r
            need -= seg_r * (seg_end - a)
    return float("inf")


def _burn_to_deal(burn, start, hp):
    """Earliest moment the sunburn shots delivered after `start` total hp."""
    need = hp
    for t, dmg in burn:
        if t < start:
            continue
        need -= dmg
        if need <= 0:
            return t
    return float("inf")


def _at(segments, t):
    value = segments[0][1]
    for st, v in segments:
        if st > t:
            break
        value = v
    return value


class _Lawn:
    """Attackers the economy bought, planted into lanes as zombies call for them.

    The economy decides when each attacker is affordable; which lane it goes to
    is decided in the fight, the way a player holds sun and plants in the lane a
    zombie actually walks down. A copy counts from its purchase time.
    """
    __slots__ = ("pool", "pcols", "cap", "per_copy", "life", "spread", "times", "_rate",
                 "chill", "freeze", "lanes")

    def __init__(self, tl, atk, fixed):
        self.lanes = tl.lanes
        self.pcols = tl.pcols
        self.cap = lane_cap(tl.pcols)
        self.per_copy = _lane_rate(atk)
        self.life = atk.get("life", 0.0)
        self.spread = atk.get("l", 1) >= 3
        self.chill = bool(atk.get("ch"))
        self.freeze = atk["fz"] / atk["i"] * 0.1 if atk.get("fz") and atk.get("i") else 0.0
        if fixed:
            self.pool = []
            self.times = [sorted(p) for p in tl.placed]
        else:
            self.pool = sorted(t for p in tl.placed for t in p)
            self.times = [[] for _ in range(tl.lanes)]
        self._rate = [None] * tl.lanes

    def alive(self, lane, t):
        life = self.life
        return sum(1 for tp in self.times[lane] if tp <= t and (not life or t < tp + life))

    def front(self, lane, t):
        n = self.alive(lane, t)
        return float(self.pcols + n) if n else 0.0

    def plant(self, lane, by, after):
        """Plant the earliest unplanted copy bought by `by` (alive after `after`)."""
        if self.alive(lane, by) >= self.cap:
            return False
        life = self.life
        for i, tp in enumerate(self.pool):
            if tp > by:
                return False
            if life and tp + life <= after:
                continue
            del self.pool[i]
            self.times[lane].append(tp)
            for x in (lane - 1, lane, lane + 1):
                if 0 <= x < self.lanes:
                    self._rate[x] = None
            return True
        return False

    def rate(self, lane):
        seg = self._rate[lane]
        if seg is None:
            deltas = []
            src = [lane]
            if self.spread:
                src += [x for x in (lane - 1, lane + 1) if 0 <= x < self.lanes]
            for x in src:
                for tp in self.times[x]:
                    deltas.append((tp, self.per_copy))
                    if self.life:
                        deltas.append((tp + self.life, -self.per_copy))
            seg, value = [(0.0, 0.0)], 0.0
            for t, dx in sorted(deltas):
                value += dx
                if seg[-1][0] == t:
                    seg[-1] = (t, value)
                else:
                    seg.append((t, value))
            self._rate[lane] = seg
        return seg


def fight(level_id: str, tl: Timeline, attacker: str, utility: Optional[str], waves,
          hp_scale: float) -> bool:
    lv = LEVELS[level_id]
    atk = PLANTS[attacker]
    ut = PLANTS[utility] if utility else None
    lanes = tl.lanes
    kind = atk["k"]
    reach = atk.get("r", 0)
    lawn = _Lawn(tl, atk, fixed=kind == "sunburn")
    busy = [0.0] * lanes                   # when a lane's damage is next free
    chompers = [[] for _ in range(lanes)]  # per lane: each chomper's free time
    eaten = [0.0] * lanes                  # wall hp already eaten per lane
    uses = list(tl.uses)                   # consumable attacker uses (ready times)
    ut_uses = list(tl.ut_uses)
    ut_stop = 0.0
    if ut and not ut.get("hp"):
        ut_stop = ut.get("fz", 0.0) + ut.get("kb", 0.0) / 0.185
    t_wave = lv["first"]
    # HP dealt to each lane this wave, then so far this level: spawns spread
    # within a wave, and across waves one lane never takes every wave's heaviest.
    load = [0.0] * lanes
    # per lane: kills still pending as (earliest start, hp), replayed whenever a
    # copy is planted so it speeds up the whole queue, earlier waves included.
    queue: List[List[Tuple[float, float]]] = [[] for _ in range(lanes)]

    def timing(lane, walk, eat):
        """(front, speed, walk_in, deadline, walls, uses the utility) for a zombie."""
        # Copies standing halfway through the zombie's walk set the lane's front
        # and slow it; a reactive copy is usually planted after the spawn.
        n = lawn.alive(lane, t_wave + (SPAWN_X - 1.0) / max(walk, 1e-3) / 2)
        chill = tl.chill[lane] or (lawn.chill and n > 0)
        stops = min(0.8, tl.stops[lane] + lawn.freeze * n)
        speed = max(walk * (0.5 if chill else 1.0) * (1.0 - stops), 1e-3)
        front = float(lawn.pcols + n) if n else 0.0
        walk_in = max(0.0, SPAWN_X - front - 0.5) / speed
        # The lane is lost once the zombie has eaten through every plant in
        # it, a PLANT_BITE each; the ones behind keep firing meanwhile.
        deadline = t_wave + walk_in + PLANT_BITE * max(1.0, front)
        walls = sum(h for tw, h in tl.walls[lane] if tw <= deadline) - eaten[lane]
        if walls > 0:
            deadline += walls / max(eat, 1.0)
        stopped = bool(ut_stop and ut_uses and ut_uses[0] <= deadline)
        if stopped:
            deadline += ut_stop
        return front, speed, walk_in, deadline, walls, stopped

    for w, zombies in enumerate(waves):
        dealt = []
        here = [0.0] * lanes
        for hp, walk, eat, row, noswallow in sorted(zombies, key=lambda z: -z[0]):
            lane = row if 0 <= row < lanes else min(range(lanes),
                                                     key=lambda x: (here[x], load[x]))
            here[lane] += hp
            load[lane] += hp
            dealt.append((lane, hp * hp_scale, walk, eat, noswallow))
        # An instant use covers every zombie of this wave in its lanes, up to its
        # target count: {lane: [use time, targets left]}.
        blast: Dict[int, List[float]] = {}
        kills = []
        for lane, hp, walk, eat, noswallow in dealt:
            if kind == "instant":
                front, speed, walk_in, deadline, walls, stopped = timing(lane, walk, eat)
                if stopped:
                    ut_uses.pop(0)
                if atk.get("d", 0.0) < hp:
                    return False
                held = blast.get(lane)
                if held and held[1] > 0 and held[0] <= deadline:
                    held[1] -= 1
                    kills.append((held[0], hp))
                    continue
                arm = atk.get("a", 0.0)
                pick = next((i for i, u in enumerate(uses) if u + arm <= deadline), None)
                if pick is None:
                    return False
                used = max(t_wave, uses.pop(pick) + arm)
                targets = atk.get("t", 1) - 1
                covered = [lane] + ([x for x in (lane - 1, lane + 1) if 0 <= x < lanes]
                                    if atk.get("l", 1) >= 3 else [])
                for x in covered:
                    blast[x] = [used, targets]
                kills.append((used, hp))
                continue
            if kind == "chomp" and noswallow:
                # Only its ChompFailDamage lands; one attacker type cannot finish it.
                return False
            if kind == "chomp":
                # Every chomper planted by the time the zombie reaches it bites
                # once, then chews for `i`.
                slots = chompers[lane]
                while True:
                    front, speed, walk_in, deadline, walls, stopped = timing(lane, walk, eat)
                    while len(slots) < len(lawn.times[lane]):
                        slots.append(lawn.times[lane][len(slots)])
                    arrive = t_wave + (max(0.0, SPAWN_X - front - 1.0 - reach) / speed
                                       if reach else 0.0)
                    done = min((max(s, arrive) for s in slots), default=float("inf"))
                    if done <= deadline or not lawn.plant(lane, deadline, t_wave):
                        break
                if done > deadline:
                    return False
                if stopped:
                    ut_uses.pop(0)
                i = min(range(len(slots)), key=lambda k: max(slots[k], arrive))
                slots[i] = done + atk.get("i", 17.0)
                kills.append((done, hp))
                continue
            if kind == "contact":
                # Each copy is its own tile; a zombie takes its damage while
                # crossing it, whatever else is in the lane.
                while True:
                    front, speed, walk_in, deadline, walls, stopped = timing(lane, walk, eat)
                    copies = sum(1 for tp in lawn.times[lane] if tp <= t_wave + walk_in)
                    per_tile = atk.get("d", 0.0) / max(atk.get("i", 0.5), 0.05) / speed
                    if copies * per_tile >= hp or not lawn.plant(lane, t_wave + walk_in, t_wave):
                        break
                if copies * per_tile < hp:
                    return False
                if stopped:
                    ut_uses.pop(0)
                kills.append((t_wave + walk_in, hp))
                continue
            while True:
                front, speed, walk_in, deadline, walls, stopped = timing(lane, walk, eat)
                start = t_wave
                need_hp = hp
                if kind == "short" and reach:
                    in_reach = t_wave + max(0.0, SPAWN_X - front - 0.5 - reach) / speed
                    start = max(start, in_reach)
                    # Only the copies within reach of the front tile hit a zombie
                    # standing there: the front one and the `reach` tiles behind it.
                    copies = max(1.0, front - lawn.pcols)
                    need_hp = hp * copies / min(copies, int(reach) + 1)
                if kind == "sunburn":
                    done = _burn_to_deal(tl.burn[lane], max(start, busy[lane]), hp)
                else:
                    rate = lawn.rate(lane)
                    done = busy[lane]
                    for s0, h0 in queue[lane]:
                        done = _time_to_deal(rate, max(done, s0), h0)
                    done = _time_to_deal(rate, max(done, start), need_hp)
                if done <= deadline or not lawn.plant(lane, deadline, t_wave):
                    break
            if done > deadline:
                return False
            if stopped:
                ut_uses.pop(0)
            if kind == "sunburn":
                busy[lane] = done
            else:
                queue[lane].append((start, need_hp))
            if walls > 0:
                at_wall = deadline - walls / max(eat, 1.0)
                if done > at_wall:
                    eaten[lane] += (done - at_wall) * eat
            kills.append((done, hp))
        timer = t_wave + WAVE_TIMER + (FLAG_EXTRA if lv["flag"] and (w + 1) % lv["flag"] == 0
                                       else 0.0)
        nxt = timer
        total = sum(h for _, h in kills)
        if total > 0:
            gone = 0.0
            for done, h in sorted(kills):
                gone += h
                if gone >= total * (1.0 - lv["next"]):
                    nxt = min(timer, max(t_wave + EARLY_WAVE_MIN, done))
                    break
        t_wave = nxt
        for lane in range(lanes):
            # Kills done before the next wave leave the queue for good.
            rate, done, keep = lawn.rate(lane), busy[lane], 0
            for k, (s0, h0) in enumerate(queue[lane]):
                done = _time_to_deal(rate, max(done, s0), h0)
                if done > t_wave:
                    break
                busy[lane], keep = done, k + 1
            del queue[lane][:keep]
    return True


def horizon_for(level_id: str, waves) -> float:
    return LEVELS[level_id]["first"] + len(waves) * (WAVE_TIMER + FLAG_EXTRA) + END_PAD


def simulate(level_id: str, producer: Optional[str], count: int, attacker: str,
             utility: Optional[str] = None, hp_scale: float = 1.0, plan=None) -> bool:
    waves, lanes = roster(level_id, plan)
    tl = economy(level_id, producer, count, attacker, utility,
                 horizon_for(level_id, waves), lanes, lane_weights(waves, lanes))
    return fight(level_id, tl, attacker, utility, waves, hp_scale)
