"""
PvZ2 Gardendless: can a conveyor belt beat its level? Design: POWER_SIM.md,
"Conveyor levels".

    passes(level_id, belt, plan, hp_scale=1.0) -> bool
    score(level_id, belt, plan) -> float

`belt` is a belt_roll.Belt (or None for the belt as shipped), `plan` the
level's budget-roll plan (None: vanilla zombies). Deterministic. `score` is the
highest zombie-HP scale the belt still beats; the belt guard compares a roll's
score with the vanilla belt's against the vanilla zombies.

Delivery [data, game Conveyor]: the next packet comes after the
DropDelayConditions delay for the number of packets on the belt (0 -> 5 s, a
full belt of 10 stops). Each packet is a weighted pick: an entry's count is its
copies on the lawn and on the belt; at MaxCount its weight is multiplied by
MaxWeightFactor, at or under MinCount by MinWeightFactor, a cooldown zeroes it,
MaxDelivered retires it. [guess] The random pick is replaced by a smooth
weighted round-robin, which deals the expected proportions in order. A wave's
ModifyConveyor Add re-caps a card already on the belt or adds one; a Remove
takes it off.

Lawn [data]: the level's InitialPlantProperties and ProtectThePlant plants
stand from the start; an ice-cubed one stands once a delivered Hot Potato
thaws it, one potato per plant.

Play [guess]: a delivered plant is planted at once in the lane with the most
zombie HP per plant already there (instants are held on the belt and spent
where a lane would otherwise be lost, which also slows the belt the way
holding packets does). A lane holds LANE_TILES - 1 plants, or the deck on a
ship lawn unless the plant floats; a Pumpkin sits over a plant and takes no
tile. A Sweet Potato is planted on delivery where it covers the most lanes.

Fight: each lane kills its zombies in turn at the damage rate of the plants in
it (power_sim's per-copy rates; short-range plants counted for the share of the
walk the zombie spends in reach), walls add eat time, slows stretch the walk.
A lane is lost, or on a ship lawn the ship is hit, exactly as in power_sim.
Wave times depend on the fight and the belt's adds on wave times, so it runs
twice: timer-only wave times first, then the times the first fight produced.

A Zomboss battle (belt record `boss`) has no waves: the mech cycles through its
stage's weighted actions, and the fight is won when its stages' HP is dealt
(see _boss_schedule).
"""

from typing import Any, Dict, List, Optional, Tuple

from . import level_model
from . import power_sim as P
from .sim_data import SIM_DATA

BELTS = SIM_DATA.get("belts", {})
CODENAMES = SIM_DATA.get("codenames", {})
BELT_MAX = 10
DROP_DEFAULT = 5.0
# A level with a *Mowers module has one mower per lane: the lane's first leak
# is cleared. Plant food: carriers drop it at their wave's first kills, and one
# spent on a lane that would be lost deals PF_BURST [guess: Peashooter's 60
# peas x 20, Ampereum's 1200] to the zombie breaking through.
MOWERS = True
PF_BURST = 1200.0
STEP = 0.5              # re-check when no card can be picked (the game: 1/60 s)
INF = float("inf")

# Plants whose effect is not in their record [data, PlantProps / game code]:
# Pumpkin is armour over a plant (no tile of its own). A Sweet Potato draws the
# zombies of the lanes next to it into its own (NormalAttractWidth 2 [guess:
# one lane each side]). A Mirror-nut fires a 550 pea (magnifying_grass) per
# 2000 damage the walls around it take: walls in its lane hit back 0.275 per
# point eaten. An Explode-o-nut blows up for 1800 when its 4000 armour breaks
# and again when it dies: 3600 back per 7000 eaten.
OVERLAY = frozenset({"pumpkin"})
LURE = frozenset({"sweetpotato"})
LURE_REACH = 1
MIRROR = frozenset({"mirrornut"})
MIRROR_RD = 550.0 / 2000.0
DEATH_RD = {"explodeonut": 3600.0 / 7000.0}
THAW = "hotpotato"
# A zombie that bites Garlic leaves for the next lane [data: LaneChangeDuration];
# here it is fielded there instead [guess: the bite's delay is not modelled].
DIVERT = frozenset({"garlic"})
# Instants whose damage lingers: a zombie on the lawn in their lanes at any time
# in the window takes it. Ghost Pepper haunts 10 s (Lifetime) [data]; Lava
# Guava's lava pool [guess: 20 s]. Any other instant hits who is on the lawn
# when it goes off.
LINGER = {"ghostpepper": 10.0, "lavaguava": 20.0}

# Zomboss [data: ZombieProps ZombossStages; user: what the actions do].
# The mech acts every 4-8 s, the action's own length included [user], here
# every BOSS_ACTION_INTERVAL, its midpoint; a repeated action repeats at the same interval. rush destroys the
# plants of 2 lanes [user]: the mech's row and the one below [guess]. shoot destroys a couple of plants on the lawn [user]:
# BOSS_SHOOT_PLANTS, the newest ones [guess: stands in for random]. jump moves
# the row it deploys zombies from [user] (two rows on [guess]). summon spends
# its point budget on its zombie list (power_sim._spend), the budget rising from
# pointMin to pointMax as the stage's HP runs out, and fields the list one
# zombie per 0.5 s before the next action (getZombieToSummon, summonCD)
# [data]; a summon also jumps first (summonAction calls jumpStart). imps throws two imps
# [guess]. Summoned zombies walk in from the mech's column [data: IdleColumn].
# The mech is hit by plants in BOSS_ROWS lanes, at the share of each lane's
# damage its zombies leave free [guess: HitRect not modelled]. The data's idle
# times are inside the 4-8 s, so they are not added on top.
BOSS_RUSH_LANES = 2
BOSS_SHOOT_PLANTS = 2
BOSS_ROWS = 3
BOSS_ACTION_INTERVAL = 6.0
BOSS_IMPS = ("tutorial_imp", 2)
BOSS_OPENING = 15.0     # seconds before the mech's first action [guess]
BOSS_MAX_SECONDS = 900.0
BOSS_PASSES = 4


def _record(cn: str) -> Dict[str, Any]:
    if isinstance(cn, str) and cn.startswith("RTID("):
        cn = cn[5:].split("@", 1)[0]          # a card can be an RTID (reinforce0)
    name = CODENAMES.get(cn)
    return P.PLANTS.get(name, {"k": "none"}) if name else {"k": "none"}


def _floats(cn: str) -> bool:
    return CODENAMES.get(cn) in P.SKY_FLOATING


class _Card:
    __slots__ = ("cn", "w", "minc", "minf", "maxc", "maxf", "cd", "maxcd", "mincd",
                 "left", "cd_t", "maxcd_t", "mincd_t", "credit")

    def __init__(self, e: Dict[str, Any], cn: str, weight_default: float):
        self.cn = cn
        self.w = float(e.get("Weight", weight_default))
        self.minc = float(e.get("MinCount", -1))
        self.minf = float(e.get("MinWeightFactor", 1))
        self.maxc = float(e.get("MaxCount", INF))
        self.maxf = float(e.get("MaxWeightFactor", 1))
        self.cd = float(e.get("CooldownSeconds", 0))
        self.maxcd = float(e.get("MaxCountCooldownSeconds", 0))
        self.mincd = float(e.get("MinCountCooldownSeconds", 0))
        self.left = float(e.get("MaxDelivered", INF))
        self.cd_t = self.maxcd_t = self.mincd_t = -INF
        self.credit = 0.0

    def weight(self, t: float, count: int) -> float:
        w = self.w
        if t < self.cd_t:
            w = 0.0
        if count >= self.maxc:
            w = 0.0 if t < self.maxcd_t else w * self.maxf
        if count <= self.minc:
            w = 0.0 if t < self.mincd_t else w * self.minf
        return w


def _delay(drop: List[List[float]], on_belt: int) -> float:
    """Conveyor.getDelay."""
    if on_belt >= BELT_MAX or not drop:
        return INF
    for max_packets, delay in sorted(drop, key=lambda c: -c[0]):
        if on_belt >= max_packets:
            return delay or DROP_DEFAULT
    return sorted(drop, key=lambda c: -c[0])[-1][1]


def deliveries(level_id: str, belt, wave_times: List[float], horizon: float,
               spent: Optional[List[float]] = None) -> List[Tuple[float, str]]:
    """(time, codename) of every packet the belt deals before `horizon`.

    `spent` is when each held instant left the belt (from the previous fight
    pass); until then it counts as a packet on the belt.
    """
    rec = BELTS[level_id]
    entries = belt.entries() if belt is not None else [dict(e) for e in rec["initial"]]
    mods = belt.mods() if belt is not None else rec["mods"]
    cards = [_Card(e, e["PlantType"], 15.0) for e in entries if e.get("PlantType")]
    by_wave: Dict[int, List] = {}
    for w, adds, removes in mods:
        by_wave.setdefault(w, []).append((adds, removes))
    pending = sorted((wave_times[w - 1], w) for w in by_wave if 0 < w <= len(wave_times))
    out: List[Tuple[float, str]] = []
    lawn: Dict[str, int] = {}
    for _, _, cn, _ in rec.get("preset") or []:
        lawn[cn] = lawn.get(cn, 0) + 1
    held: List[Tuple[float, str]] = []         # instants on the belt: (leaves, cn)
    spent = sorted(spent or [])
    t = 0.0
    nxt = 0.0
    while t <= horizon:
        while pending and pending[0][0] <= t:
            _, w = pending.pop(0)
            for adds, removes in by_wave[w]:
                for e in removes:
                    cn = e.get("Type")
                    cards = [c for c in cards if c.cn != cn]
                for e in adds:
                    cn = e.get("Type")
                    if not cn:
                        continue
                    cards = [c for c in cards if c.cn != cn] + [_Card(e, cn, 40.0)]
        held = [h for h in held if h[0] > t]
        if t >= nxt:
            on_belt = len(held)
            counts = {c.cn: lawn.get(c.cn, 0) + sum(1 for h in held if h[1] == c.cn)
                      for c in cards}
            weights = [c.weight(t, counts[c.cn]) for c in cards]
            total = sum(weights)
            if total <= 0 or on_belt >= BELT_MAX:
                nxt = t + STEP
            else:
                for c, w in zip(cards, weights):
                    c.credit += w
                pick = max(range(len(cards)), key=lambda i: (cards[i].credit, -i)
                           if weights[i] > 0 else (-INF, -i))
                card = cards[pick]
                card.credit -= total
                card.cd_t, card.maxcd_t, card.mincd_t = t + card.cd, t + card.maxcd, t + card.mincd
                card.left -= 1
                if card.left <= 0:
                    cards.pop(pick)
                out.append((t, card.cn))
                kind = _record(card.cn)["k"]
                if kind == "instant":
                    leave = spent.pop(0) if spent else INF
                    held.append((leave, card.cn))
                else:
                    lawn[card.cn] = lawn.get(card.cn, 0) + 1
                nxt = t + _delay(rec["drop"], len(held))
        t = min(nxt, pending[0][0] if pending else INF,
                min((h[0] for h in held if h[0] > t), default=INF))
        if t == INF:
            break
    return out


def _wave_times(first: float, flag: int, waves: int) -> List[float]:
    out, t = [], first
    for w in range(waves):
        out.append(t)
        t += P.WAVE_TIMER + (P.FLAG_EXTRA if flag and (w + 1) % flag == 0 else 0.0)
    return out


def _rate(rec: Dict[str, Any]) -> float:
    """A copy's damage per second into its lane (power_sim's per-copy rate)."""
    if rec["k"] not in ("shooter", "short", "burst"):
        return 0.0
    return P._lane_rate(rec)


def _is_attack(r: Dict[str, Any]) -> bool:
    return r["k"] in ("shooter", "short", "burst", "contact", "chomp")


class _Plant:
    """A plant on the lawn: planted at `t`, gone at `gone` (trampled, shot)."""
    __slots__ = ("t", "r", "cn", "gone")

    def __init__(self, t, r, cn):
        # A plant with a lifespan (Puff-shroom) is gone when it expires.
        self.t, self.r, self.cn = t, r, cn
        self.gone = t + r["life"] if r.get("life") else INF

    def up(self, t):
        return self.t <= t < self.gone


def fight(level_id: str, packets, waves, lanes: int, hp_scale: float = 1.0,
          fixed: Optional[List[Dict[str, Any]]] = None):
    """(passed, wave start times, when each held instant was spent, lawn).

    `fixed` (a Zomboss battle) gives each wave's start time, entry column and
    the plants the mech destroys before it; wave times then do not follow
    kills. `lawn` is (placed, per lane the (entry time, hp) its plants owe)
    for the boss's damage.
    """
    rec = BELTS[level_id]
    ship = P.SHIPS.get(level_id)
    ship_left = [ship["hp"] * (1.0 - P.SHIP_MARGIN)] if ship else None
    boss = rec.get("boss") if fixed is not None else None
    deck = ship["deck"] if ship else P.LANE_TILES - 1
    if boss:
        deck = P.LANE_TILES - boss["reserved"]

    placed: List[List[_Plant]] = [[] for _ in range(lanes)]
    pool: List[Tuple[float, Dict[str, Any], str]] = []
    instants: List[Tuple[float, Dict[str, Any]]] = []
    thaws: List[float] = []
    lures = [lane for lane in (1, 3, 0, 2, 4) if lane < lanes]
    for t, cn in packets:
        r = _record(cn)
        if cn == THAW:
            thaws.append(t)
        elif cn in LURE and lures and r["k"] != "none":
            lane = lures.pop(0)
            placed[lane].append(_Plant(t, r, cn))
        elif r["k"] == "instant":
            instants.append((t, dict(r, cn=cn)))
        elif r["k"] != "none" and r["k"] != "producer":
            pool.append((t, r, cn))
    # Presets: standing from the start, or once a Hot Potato thaws them
    # (front-most first).
    iced = []
    for x, y, cn, flags in rec.get("preset") or []:
        r = _record(cn)
        if r["k"] in ("none", "producer") or not 0 <= y < lanes:
            continue
        if flags == "ice":
            iced.append((-x, y, r, cn))
        else:
            placed[y].append(_Plant(0.0, r, cn))
    for (_, y, r, cn), t in zip(sorted(iced), sorted(thaws)):
        placed[y].append(_Plant(t, r, cn))
    rate_cache: Dict[int, List] = {}
    # When the belt deals walls, a lane keeps its front tile for one [guess:
    # the player's habit; attackers alone would fill it].
    # On a ship lawn zombies stop at the edge and fire at the ship, so walls
    # only take deck tiles and are not planted.
    walled = not ship and any(r["k"] == "utility" and r.get("hp") and cn not in OVERLAY
                              for _, r, cn in pool)

    def tiles(lane, t):
        return sum(1 for p in placed[lane] if p.up(t) and p.cn not in OVERLAY)

    def cap_of(cn):
        if cn in OVERLAY:
            return INF
        return P.LANE_TILES - 1 if (not ship or _floats(cn)) and not boss else deck

    def dirty(lane):
        for x in (lane - 1, lane, lane + 1):
            rate_cache.pop(x, None)

    def plant(lane, by, want_attack):
        """Plant the earliest pooled plant delivered by `by` into `lane`."""
        for i, (t, r, cn) in enumerate(pool):
            if t > by:
                return False
            if _is_attack(r) != want_attack or (ship and not want_attack and r.get("hp")):
                continue
            at = max(t, 0.0)
            if tiles(lane, by) >= cap_of(cn) - (1 if walled and want_attack else 0):
                continue
            pool.pop(i)
            placed[lane].append(_Plant(at, r, cn))
            dirty(lane)
            return True
        return False

    def sources(lane):
        """(time, dps, reach or 0, end) of every copy hitting `lane`."""
        src = rate_cache.get(lane)
        if src is not None:
            return src
        src = []
        for x in (lane - 1, lane, lane + 1):
            if not 0 <= x < lanes:
                continue
            for p in placed[x]:
                r = p.r
                if x != lane and r.get("l", 1) < 3:
                    continue
                d = _rate(r)
                if d:
                    reach = r.get("r", 0) if r["k"] == "short" else 0
                    src.append((p.t, d, reach, p.gone))
        rate_cache[lane] = src
        return src

    def rate_of(lane, t_wave=0.0, front=0.0, speed=1.0, spawn=P.SPAWN_X):
        """Damage-rate segments for a zombie walking in at t_wave: a
        short-range copy counts from the moment the zombie is in its reach."""
        deltas = []
        for t, d, reach, end in sources(lane):
            if reach:
                t = max(t, t_wave + max(0.0, spawn - front - 0.5 - reach) / speed)
            if t >= end:
                continue
            deltas.append((t, d))
            if end < INF:
                deltas.append((end, -d))
        seg, value = [(0.0, 0.0)], 0.0
        for t, dx in sorted(deltas):
            value += dx
            if seg[-1][0] == t:
                seg[-1] = (t, value)
            else:
                seg.append((t, value))
        return seg

    uses = sorted(instants, key=lambda u: u[0])
    spent: List[float] = []
    busy = [0.0] * lanes
    # Per lane: kills still pending as (start, hp, front, speed, spawn),
    # replayed at the lane's current plants so a later copy also speeds up the
    # zombies already walking (power_sim's queue).
    queue: List[List[Tuple[float, float, float, float, float]]] = [[] for _ in range(lanes)]
    eaten = [0.0] * lanes
    mower = [bool(rec.get("mowers"))] * lanes
    food: List[float] = []                          # plant food ready times
    pf_per_wave = rec.get("pf") or []
    kill_log: List[List[Tuple[float, float]]] = [[] for _ in range(lanes)]

    def replay(lane):
        """When the lane is free of every queued kill."""
        done = busy[lane]
        for s0, h0, f0, v0, x0 in queue[lane]:
            done = P._time_to_deal(rate_of(lane, s0, f0, v0, x0), max(done, s0), h0)
        return done
    chew_free: Dict[int, float] = {}                 # id(chomper) -> free at
    load = [0.0] * lanes
    t_wave = fixed[0]["t"] if fixed else rec["first"]
    starts: List[float] = []

    def to_ship(amount):
        ship_left[0] -= amount
        return ship_left[0] >= 0.0

    def spend(deadline):
        """Use the earliest held instant that can still land by `deadline`;
        returns (time, damage, record) or None."""
        for i, (ready, r) in enumerate(uses):
            land = ready + r.get("a", 0.0)
            if land <= deadline:
                uses.pop(i)
                spent.append(max(ready, land - r.get("a", 0.0)))
                return max(land, 0.0), r.get("d", 0.0), r
        return None

    # Area instants already spent: [lanes, targets left, damage, from, to].
    blasts: List[List[Any]] = []

    def lose():
        return False, starts, spent, (placed, kill_log)

    for w, zombies in enumerate(waves):
        if fixed:
            t_wave = fixed[w]["t"]
            for lane_set, n in fixed[w].get("destroy", ()):
                _destroy(placed, lane_set, n, t_wave)
                for x in range(lanes):
                    rate_cache.pop(x, None)
            if boss:
                # The player plants what the belt gave without waiting for a
                # zombie to call for it: attackers into the emptiest lane.
                while pool and pool[0][0] <= t_wave:
                    t, r, cn = pool[0]
                    if not _is_attack(r):
                        break
                    lane = min(range(lanes), key=lambda x: (tiles(x, t_wave), x))
                    if tiles(lane, t_wave) >= cap_of(cn):
                        break
                    pool.pop(0)
                    placed[lane].append(_Plant(max(t, 0.0), r, cn))
                    dirty(lane)
        spawn = fixed[w].get("x", P.SPAWN_X) if fixed else P.SPAWN_X
        starts.append(t_wave)
        here = [0.0] * lanes
        kills = []
        for hp, walk, eat, row, noswallow, sdps, crash, garg in sorted(zombies, key=lambda z: -z[0]):
            lane = row if 0 <= row < lanes else min(range(lanes),
                                                     key=lambda x: (here[x], load[x]))
            lure = [x for x in range(max(0, lane - LURE_REACH), min(lanes, lane + LURE_REACH + 1))
                    if any(p.up(t_wave) and p.cn in LURE for p in placed[x])]
            if lure and lane not in lure:
                lane = min(lure, key=lambda x: (abs(x - lane), x))
            elif any(p.up(t_wave) and p.cn in DIVERT for p in placed[lane]) and not boss:
                side = [x for x in (lane - 1, lane + 1) if 0 <= x < lanes and
                        not any(p.up(t_wave) and p.cn in DIVERT for p in placed[x])]
                if side:
                    lane = min(side, key=lambda x: (load[x], x))
            here[lane] += hp
            load[lane] += hp
            hp *= hp_scale
            if ship and walk <= 0:
                continue
            on_lawn = t_wave + spawn / max(walk, 1e-3)
            for b in blasts:
                if lane in b[0] and b[1] > 0 and b[3] <= on_lawn and t_wave <= b[4]:
                    hp -= b[2]
                    b[1] -= 1
            if hp <= 0:
                kills.append((t_wave, 0.0))
                continue
            half = t_wave + (spawn - 1.0) / max(walk, 1e-3) / 2

            def timing():
                # Copies standing halfway through its walk set its front and
                # slow it, as in power_sim.
                standing = [p for p in placed[lane] if p.up(half)]
                chill = any(p.r.get("ch") for p in standing)
                stop = min(0.8, sum(p.r["fz"] / p.r["i"] * 0.1 for p in standing
                                    if p.r.get("fz") and p.r.get("i")) +
                           sum(p.r["kb"] / p.r["i"] * 2.0 for p in standing
                               if p.r.get("kb") and p.r.get("i")))
                speed = max(walk * (0.5 if chill else 1.0) * (1.0 - stop), 1e-3)
                if ship:
                    return speed, t_wave + max(0.0, spawn - ship["edge"]) / speed, 0.0, standing
                front = float(min(sum(1 for p in standing if p.cn not in OVERLAY),
                                  P.LANE_TILES - 1))
                deadline = t_wave + max(0.0, spawn - front - 0.5) / speed + \
                    P.PLANT_BITE * max(1.0, front)
                # A Gargantuar smashes a wall like any plant: no eat time.
                walls = 0.0 if garg else sum(p.r["hp"] for p in standing
                                             if p.r["k"] == "utility" and p.r.get("hp")) - eaten[lane]
                if walls > 0:
                    deadline += walls / max(eat, 1.0)
                return speed, deadline, walls, standing

            def outcome(hp_left):
                """(hp left, kill time, chomper used, deadline, walls, front, speed)."""
                speed, deadline, walls, standing = timing()
                front = 0.0 if ship else float(min(sum(1 for p in standing if p.cn not in OVERLAY),
                                                   P.LANE_TILES - 1))
                if not ship:
                    hp_left -= sum(p.r.get("d", 0.0) / max(p.r.get("i", 0.5), 0.05) / speed
                                   for p in standing if p.r["k"] == "contact")
                if hp_left > 0 and not noswallow:
                    for p in placed[lane]:
                        if p.r["k"] != "chomp" or not p.up(t_wave):
                            continue
                        free = max(chew_free.get(id(p), p.t), t_wave)
                        if free <= deadline:
                            return hp_left, free, p, deadline, walls, front, speed
                if hp_left <= 0:
                    return hp_left, t_wave, None, deadline, walls, front, speed
                seg = rate_of(lane, t_wave, front, speed, spawn)
                free = replay(lane)
                done = P._time_to_deal(seg, max(free, t_wave), hp_left)
                # A wall that hits back (Lychee, Explode-o-nut, any wall in a
                # Mirror-nut's lane) wounds it while it eats.
                mirror = any(p.cn in MIRROR for p in standing)
                back = [(p.r["hp"], p.r.get("rd", 0.0) + DEATH_RD.get(p.cn, 0.0) +
                         (MIRROR_RD if mirror else 0.0))
                        for p in standing if p.r["k"] == "utility" and p.r.get("hp")]
                back = [(h, rd) for h, rd in back if rd > 0]
                start_eat = deadline - walls / max(eat, 1.0)
                if back and walls > 0 and done > start_eat:
                    eaten_now = min(walls, (done - start_eat) * eat)
                    share = sum(h * rd for h, rd in back) / max(walls + eaten[lane], 1.0)
                    done = P._time_to_deal(seg, max(free, t_wave),
                                           max(0.0, hp_left - eaten_now * share))
                    if hp_left - eaten_now * share <= 0:
                        # The walls kill it: nothing left for the lane's queue.
                        done = min(done, start_eat + hp_left / max(share * eat, 1e-9))
                        return 0.0, done, None, deadline, walls, front, speed
                return hp_left, done, None, deadline, walls, front, speed

            while True:
                left, done, chomp, deadline, walls, front, speed = outcome(hp)
                if done <= deadline:
                    break
                if not (plant(lane, deadline, True) or plant(lane, deadline, False)):
                    break
            while done > deadline:
                use = spend(deadline)
                if use is None and food and food[0] <= deadline and any(
                        _rate(p.r) for p in placed[lane] if p.up(deadline)):
                    use = (max(food.pop(0), t_wave), PF_BURST, None)
                if use is None:
                    break
                at, dmg, r = use
                if r is not None and r.get("t", 1) > 1:
                    # An area instant also hits the wave's later zombies in
                    # its lanes, up to its target count.
                    # The rest take its splash where it has one (Grapeshot,
                    # Ice Bloom), else the full hit.
                    reach = r.get("l", 1) // 2
                    blasts.append([set(range(lane - reach, lane + reach + 1)),
                                   99 if r.get("cn") in LINGER else r.get("t", 1) - 1,
                                   r.get("x") or dmg, at,
                                   at + LINGER.get(r.get("cn"), 0.0)])
                hp -= dmg
                left, done, chomp, deadline, walls, front, speed = outcome(hp)
                if left <= 0 or hp <= 0:
                    done = max(at, t_wave)
                    break
            if chomp is not None and done <= deadline:
                chew_free[id(chomp)] = done + chomp.r.get("i", 17.0)
                kills.append((done, hp))
                continue
            if done > deadline and ship and not crash:
                # It fires at the ship until it dies, so a plant delivered
                # while it fires is planted against it too.
                while plant(lane, done, True):
                    left, done, chomp, deadline, walls, front, speed = outcome(hp)
            if done > deadline:
                if not ship and MOWERS and mower[lane]:
                    # The lane's mower clears it once [calibration switch].
                    mower[lane] = False
                    queue[lane].clear()
                    busy[lane] = t_wave
                    kills.append((deadline, hp))
                    continue
                if not ship:
                    return lose()
                if crash:
                    if not to_ship(crash):
                        return lose()
                    kills.append((deadline, hp))
                    continue
                if done == INF or not to_ship(sdps * (done - deadline)):
                    return lose()
            if walls > 0:
                at_wall = deadline - walls / max(eat, 1.0)
                if done > at_wall:
                    eaten[lane] += (done - at_wall) * eat
                    # Walls eaten through are gone, front (newest) first,
                    # which frees their tiles.
                    for p in sorted((p for p in placed[lane] if p.up(done) and
                                     p.r["k"] == "utility" and p.r.get("hp")), key=lambda p: -p.t):
                        if eaten[lane] < p.r["hp"]:
                            break
                        eaten[lane] -= p.r["hp"]
                        p.gone = min(done, deadline)
                        dirty(lane)
            if left > 0 and chomp is None:
                queue[lane].append((t_wave, left, front, speed, spawn))
            kills.append((done, hp))
            if chomp is None:
                kill_log[lane].append((t_wave, max(0.0, left)))
        carriers = pf_per_wave[w] if w < len(pf_per_wave) else 0
        if carriers:
            food.extend(sorted(t for t, _ in kills)[:carriers])
            food.sort()
        if fixed:
            nxt = fixed[w + 1]["t"] if w + 1 < len(fixed) else t_wave
        else:
            timer = t_wave + P.WAVE_TIMER + (P.FLAG_EXTRA if rec["flag"] and (w + 1) % rec["flag"] == 0
                                             else 0.0)
            nxt = timer
            whole = sum(h for _, h in kills)
            if whole > 0:
                gone = 0.0
                for done, h in sorted(kills):
                    gone += h
                    if gone >= whole * (1.0 - rec["next"]):
                        nxt = min(timer, max(t_wave + P.EARLY_WAVE_MIN, done))
                        break
        t_wave = nxt
        for lane in range(lanes):
            # Kills done before the next wave leave the queue for good.
            done, keep = busy[lane], 0
            for k, (s0, h0, f0, v0, x0) in enumerate(queue[lane]):
                done = P._time_to_deal(rate_of(lane, s0, f0, v0, x0), max(done, s0), h0)
                if done > t_wave:
                    break
                busy[lane], keep = done, k + 1
            del queue[lane][:keep]
    return True, starts, spent, (placed, kill_log)


def _destroy(placed, lane_set, n, t):
    """Destroy plants standing at `t`: every plant in `lane_set` (a rush), or
    the `n` newest on the lawn (a shot)."""
    if lane_set:
        for x in lane_set:
            if 0 <= x < len(placed):
                for p in placed[x]:
                    if p.up(t):
                        p.gone = t
        return
    up = sorted((p for lane in placed for p in lane if p.up(t)), key=lambda p: -p.t)
    for p in up[:n]:
        p.gone = t


# ── Zomboss ──────────────────────────────────────────────────────────────────

def _summon(zlist, points, swap):
    """Expected (count, hp, walk, eat) of a summon of `points` from `zlist`."""
    costs = level_model.load()["zombies"]
    pool = []
    for cn in zlist:
        z = P.ZOMBIES.get(swap.get(cn, cn))
        cost = costs.get(cn, {}).get("cost", 0)
        if z and z["hp"] > 0 and cost > 0:
            pool.append((cost, z["hp"], z["walk"], z["eat"]))
    if not pool:
        return 0.0, 0.0, 0.0, 0.0
    return P._spend(tuple(sorted(pool)), int(points))


def _boss_schedule(level_id: str, lanes: int, stage_ends: List[float], swap) -> Tuple[List, List]:
    """(waves, fixed) of a Zomboss battle whose stages end at `stage_ends`.

    The mech acts every BOSS_ACTION_INTERVAL; the actions come in their weights'
    proportions by smooth weighted round-robin [guess: stands in for random].
    """
    boss = BELTS[level_id]["boss"]
    row = min(max(0, boss["row"]), lanes - 1)
    waves, fixed = [], []
    t = BOSS_OPENING
    for k, stage in enumerate(boss["stages"]):
        end = stage_ends[k] if k < len(stage_ends) else BOSS_MAX_SECONDS
        begin = t
        acts = [a for a in stage["actions"] if a[1] > 0]
        credit = [0.0] * len(acts)
        total = sum(a[1] for a in acts)
        while t < end and acts and t < BOSS_MAX_SECONDS:
            for i, a in enumerate(acts):
                credit[i] += a[1]
            i = max(range(len(acts)), key=lambda j: (credit[j], -j))
            credit[i] -= total
            name, _, reps, points, zlist = acts[i]
            reps = max(1, int(round(reps)))
            for _ in range(reps):
                zs, destroy = [], []
                if name == "summon":
                    row = (row + 2) % lanes
                    lo, hi = points if isinstance(points, list) else (points, points)
                    progress = min(1.0, max(0.0, (t - begin) / max(end - begin, 1.0)))
                    n, hp, walk, eat = _summon(zlist, lo + progress * (hi - lo), swap)
                    rows = [x for x in (row - 1, row, row + 1) if 0 <= x < lanes]
                    for j in range(int(round(n))):
                        zs.append((hp, walk, eat, rows[j % len(rows)], False, 0.0, 0.0, False))
                    t += 0.5 * n
                elif name == "imps":
                    z = P.ZOMBIES.get(swap.get(BOSS_IMPS[0], BOSS_IMPS[0])) or \
                        {"hp": 190, "walk": 0.185, "eat": 100}
                    for j in range(BOSS_IMPS[1]):
                        zs.append((z["hp"], z["walk"], z["eat"], row, False, 0.0, 0.0, False))
                elif name in ("rush", "rush2") and BOSS_RUSH_LANES:
                    destroy.append((set(range(row, row + BOSS_RUSH_LANES)), 0))
                elif name == "shoot" and BOSS_SHOOT_PLANTS:
                    destroy.append((None, BOSS_SHOOT_PLANTS))
                elif name == "jump":
                    row = (row + 2) % lanes
                if zs or destroy:
                    waves.append(zs)
                    fixed.append({"t": t, "x": boss.get("column", 6) + 0.5, "destroy": destroy})
                t += BOSS_ACTION_INTERVAL
        t = max(t, end)
    return waves, fixed


def _boss_damage(lawn, lanes, horizon: float, step: float = 1.0) -> List[Tuple[float, float]]:
    """Cumulative damage the mech takes by each time: what a lane deals while
    none of its zombies is still owed damage, at BOSS_ROWS / lanes of it."""
    placed, kill_log = lawn
    share = min(1.0, BOSS_ROWS / max(1, lanes))
    out, total, t = [], 0.0, 0.0
    owe = [0.0] * lanes
    due = [sorted(k) for k in kill_log]
    while t < horizon:
        for x in range(lanes):
            rate = 0.0
            for y in (x - 1, x, x + 1):
                if not 0 <= y < lanes:
                    continue
                for p in placed[y]:
                    r = p.r
                    if (y != x and r.get("l", 1) < 3) or not p.up(t):
                        continue
                    # Short reach does not get to the mech's columns.
                    if r["k"] == "short" and r.get("r", 0) < 4:
                        continue
                    rate += _rate(r)
            while due[x] and due[x][0][0] <= t:
                owe[x] += due[x].pop(0)[1]
            pay = rate * step
            use = min(owe[x], pay)
            owe[x] -= use
            total += (pay - use) * share
        t += step
        out.append((t, total))
    return out


def _boss_fight(level_id, belt, lanes, hp_scale, swap) -> bool:
    boss = BELTS[level_id]["boss"]
    hps = [s["hp"] * hp_scale for s in boss["stages"]]
    need = [sum(hps[:k + 1]) for k in range(len(hps))]
    # First guess: each stage lasts 60 s; then the times the mech's damage
    # curve crosses each stage's HP.
    ends = [BELTS[level_id]["first"] + 60.0 * (k + 1) for k in range(len(hps))]
    spent = None
    for _ in range(BOSS_PASSES):
        waves, fixed = _boss_schedule(level_id, lanes, ends, swap)
        if not waves:
            return True
        horizon = min(BOSS_MAX_SECONDS, ends[-1]) + P.END_PAD
        packets = deliveries(level_id, belt, [], horizon, spent)
        ok, _, spent, lawn = fight(level_id, packets, waves, lanes, hp_scale, fixed)
        if not ok:
            return False
        curve = _boss_damage(lawn, lanes, horizon)
        new = []
        for target in need:
            hit = next((t for t, d in curve if d >= target), INF)
            new.append(hit)
        if new[-1] == INF:
            if ends[-1] >= BOSS_MAX_SECONDS:
                return False
            ends = [min(e * 1.5, BOSS_MAX_SECONDS) if n == INF else n for e, n in zip(ends, new)]
            continue
        if all(abs(a - b) < 5.0 for a, b in zip(new, ends)):
            return True
        ends = new
    return ends[-1] < BOSS_MAX_SECONDS


def passes(level_id: str, belt=None, plan: Optional[Dict[str, Any]] = None,
           hp_scale: float = 1.0, swap: Optional[Dict[str, str]] = None) -> bool:
    """The belt beats the level's (rolled) zombies. Two passes; see above.

    `swap` maps a Zomboss summon's codenames to what the zombie rando makes
    of them (the client swaps those per codename, outside the plan).
    """
    rec = BELTS[level_id]
    waves, lanes = P.roster(level_id, plan)
    if rec.get("boss"):
        return _boss_fight(level_id, belt, lanes, hp_scale, dict(swap or {}))
    if not waves:
        return True
    times = _wave_times(rec["first"], rec["flag"], len(waves))
    horizon = times[-1] + P.WAVE_TIMER + P.FLAG_EXTRA + P.END_PAD
    spent = None
    result = False
    for _ in range(2):
        packets = deliveries(level_id, belt, times, horizon, spent)
        result, starts, spent, _ = fight(level_id, packets, waves, lanes, hp_scale)
        if not result:
            break
        times = starts + times[len(starts):]
    return result


SCORE_LO, SCORE_HI, SCORE_STEPS = 0.05, 4.0, 7


def score(level_id: str, belt=None, plan: Optional[Dict[str, Any]] = None,
          swap: Optional[Dict[str, str]] = None) -> float:
    """The highest zombie-HP scale (to SCORE_STEPS halvings between SCORE_LO
    and SCORE_HI) at which the belt still beats the level; 0 if it fails even
    at SCORE_LO."""
    if not passes(level_id, belt, plan, SCORE_LO, swap):
        return 0.0
    if passes(level_id, belt, plan, SCORE_HI, swap):
        return SCORE_HI
    lo, hi = SCORE_LO, SCORE_HI
    for _ in range(SCORE_STEPS):
        mid = (lo * hi) ** 0.5
        if passes(level_id, belt, plan, mid, swap):
            lo = mid
        else:
            hi = mid
    return lo
