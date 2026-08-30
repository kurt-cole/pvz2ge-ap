"""Level structure: waves, spawns, modules, sun and the seed bank.

ONE DOCUMENT IS ONE LEVEL, and the document's name is the level codename --
`egypt19`, `dark22`, `squash3`. That is the same codename the client's
LOC_LEVELS maps AP location names onto, so a record here joins straight onto a
location with no translation table.

A wave has TWO halves and both are counted:

  EXPLICIT   `SpawnZombiesJitteredWaveActionProps` and friends name the exact
             zombies. Straightforward: sum their effective HP.
  DYNAMIC    `WaveManagerModuleProperties.DynamicZombies` gives POOLS, and
             `WaveManagerProperties` gives a POINT BUDGET the generator spends
             on them:

                 budget(n) = WaveSpendingPoints + (n-1) * WaveSpendingPointIncrement

             plus, per active pool, `StartingPoints + (n - StartingWave) *
             PointIncrementPerWave`, which is how a pool phases in (the values
             are negative, so an early wave spends less of its budget on the
             harder pool). Points become HP through the pool's own mean
             HP-per-WavePointCost -- so the DIFFICULTY IS PRICED BY THE GAME,
             not by us. That is the single best thing about this data: the
             wave budget is the game's own statement of how hard wave n is.

THE CLOCK IS NOMINAL. The game advances a wave on a mix of "previous wave is
80-90% dead" (`MinNextWaveHealthPercentage` / `Max...`) and a timer, and the
timer is not in the sheet. So every level is laid on the same synthetic clock,
which makes levels COMPARABLE TO EACH OTHER -- the whole job here. It does not
make any single number a stopwatch reading, and it should never be quoted as
one.
"""
import json

from ..paths import curated
from .rton import walk_objclasses

WAVE_SECONDS = 25.0
FLAG_WAVE_SECONDS = 35.0

# Wave action objclasses that name zombies outright.
_SPAWN_CLASSES = ("SpawnZombiesJitteredWaveActionProps",
                  "SpawnZombiesFromGroundSpawnerProps",
                  "SpawnZombiesWaveActionProps",
                  "SpawnModernPortalsWaveActionProps",
                  "StormWaveActionProps")


def _num(value, default=0.0):
    """A number, or the default. Some of these fields are strings in the data,
    and a level whose budget is "100" must not take the whole run down."""
    return float(value) if isinstance(value, (int, float)) else default


def _load_hazards():
    with open(curated("hazards.json"), "r", encoding="utf-8") as fh:
        return json.load(fh)


def _tokens_for(strings, table, ignore=()):
    """Hazard tokens for a set of module/objclass names. Longest key wins.

    `ignore` drops level plumbing -- stages, mowers, intros, win conditions --
    so the unmapped report stays a list worth reading.
    """
    keys = sorted(table, key=len, reverse=True)
    skip = sorted(ignore, key=len, reverse=True)
    tokens, unmapped = set(), set()
    for name in strings:
        low = name.lower()
        for key in keys:
            if key in low:
                tokens.add(table[key])
                break
        else:
            if not any(s in low for s in skip):
                unmapped.add(name)
    return tokens, unmapped


def _wave_effects(node, out=None):
    """Effect names a wave action states outright, e.g. {"Type": "sandstorm"}.

    A level can carry a mechanic through a WAVE rather than through a module --
    egypt5's storm is a Wave5Event with Type "sandstorm" and no sandstorm module
    anywhere -- so the module scan alone misses it.

    NOT recursive: every nested {"Type": "RTID(mummy@ZombieTypes)"} entry in a
    Zombies list also has a Type, and walking into them collected sixty zombie
    codenames as if they were hazards.
    """
    out = set() if out is None else out
    value = node.get("Type") if isinstance(node, dict) else None
    if isinstance(value, str) and not value.startswith("RTID("):
        out.add(value)
    return out


def _collect_zombies(index, node, doc, out):
    """Every zombie RTID under a wave action, counted."""
    if isinstance(node, dict):
        for key in ("Zombies", "ZombieList", "SpawnZombies"):
            entries = node.get(key)
            if isinstance(entries, list):
                for entry in entries:
                    ref = entry.get("Type") if isinstance(entry, dict) else entry
                    alias = index.alias_of_rtid(ref)
                    if alias:
                        out[alias] = out.get(alias, 0) + 1
        for value in node.values():
            _collect_zombies(index, value, doc, out)
    elif isinstance(node, list):
        for value in node:
            _collect_zombies(index, value, doc, out)
    return out


def _wave_manager(index, doc):
    """(WaveManagerProperties, DynamicZombies list) for a level, or (None, [])."""
    module = doc.first_of_class("WaveManagerModuleProperties")
    props = doc.first_of_class("WaveManagerProperties")
    dynamic = []
    if module:
        props = index.resolve(module.get("WaveManagerProps"), doc) or props
        dynamic = module.get("DynamicZombies") or []
    return props, dynamic


def _pool_hp_per_point(index, pool, zombies):
    """Mean HP bought per wave point in a dynamic pool.

    Averaged over the pool because the generator picks from it; a pool of one
    is exact. Zombies with no cost are skipped rather than treated as free.
    """
    hp = cost = 0.0
    for ref in pool or []:
        alias = index.alias_of_rtid(ref) or (ref if isinstance(ref, str) else None)
        z = zombies.get(alias) or {}
        if z.get("wave_cost"):
            hp += z.get("effective_hp") or 0.0
            cost += z["wave_cost"]
    return (hp / cost) if cost else 0.0


def extract(index, zombies):
    """codename -> level record. `zombies` is extract.zombies.extract output."""
    hazards = _load_hazards()
    module_table = hazards["module_tokens"]
    selection_table = hazards["selection_tokens"]
    ignore = hazards.get("ignore", [])
    unmapped_all = set()
    out = {}

    for name, doc in index.documents_with("LevelDefinition"):
        definition = doc.first_of_class("LevelDefinition")
        seedbank = doc.first_of_class("SeedBankProperties")

        # Modules: the objclasses of everything the level pulls in, plus the
        # RTID alias itself (Gravestones@CurrentLevel names the mechanic even
        # when its properties object is generic).
        module_refs = definition.get("Modules") or []
        if definition.get("StageModule"):
            module_refs = list(module_refs) + [definition["StageModule"]]
        resolved, aliases = [], []
        for ref in module_refs:
            aliases.append(index.alias_of_rtid(ref) or "")
            data = index.resolve(ref, doc)
            if data is not None:
                resolved.append(data)
        modules = sorted({m for m in walk_objclasses(resolved) if m}
                         | {a for a in aliases if a})
        tokens, unmapped = _tokens_for(modules, module_table, ignore)
        unmapped_all |= unmapped

        selection = ((seedbank or {}).get("SelectionMethod") or "chooser").lower()
        sel_token = selection_table.get(selection)
        if sel_token:
            tokens.add(sel_token)
        # No DefaultSunDropper module means no falling sun: everything must be
        # produced. That is a hard requirement, not a nuisance.
        sun_drop = any("sundropper" in a.lower() for a in aliases)
        if not sun_drop:
            tokens.add("no_sun_drop")

        props, dynamic = _wave_manager(index, doc)
        wave_refs = (props or {}).get("Waves") or []
        flag_interval = _num((props or {}).get("FlagWaveInterval"), 10.0)
        base_points = _num((props or {}).get("WaveSpendingPoints"))
        increment = _num((props or {}).get("WaveSpendingPointIncrement"))

        pools = []
        for entry in dynamic:
            if isinstance(entry, dict):
                pools.append({
                    "start_wave": _num(entry.get("StartingWave"), 1.0),
                    "start_points": _num(entry.get("StartingPoints")),
                    "increment": _num(entry.get("PointIncrementPerWave")),
                    "hp_per_point": _pool_hp_per_point(index, entry.get("ZombiePool"),
                                                       zombies),
                    "pool": [index.alias_of_rtid(r) or r
                             for r in (entry.get("ZombiePool") or [])],
                })

        wave_effects = set()
        waves, clock = [], 0.0
        for i, refs in enumerate(wave_refs):
            n = i + 1
            counts = {}
            for ref in (refs if isinstance(refs, list) else [refs]):
                action = index.resolve(ref, doc)
                if action:
                    _collect_zombies(index, action, doc, counts)
                    _wave_effects(action, wave_effects)
            explicit_hp = sum((zombies.get(z, {}).get("effective_hp") or 0.0) * c
                              for z, c in counts.items())
            explicit_points = sum((zombies.get(z, {}).get("wave_cost") or 0.0) * c
                                  for z, c in counts.items())

            # ONE budget for the wave, shared across the pools -- not one each.
            # Giving every pool the full budget multiplied egypt3 by seven and
            # put it above egypt26.
            #
            # The per-pool StartingPoints / PointIncrementPerWave are recorded
            # but NOT spent. Their values are negative and grow more negative
            # (-100, then -40 a wave), so they cannot be a spend; they read as
            # a phase-in or a cost modifier, and which one is not settled by
            # anything in the data. Guessing wrong here moves every level's
            # number, so the model uses only what the game states plainly: the
            # wave budget, at the mean price of whatever pools are live.
            active = [p for p in pools if n >= p["start_wave"]]
            dyn_points = max(0.0, base_points + (n - 1) * increment) if active else 0.0
            rate = (sum(p["hp_per_point"] for p in active) / len(active)) if active else 0.0
            dyn_hp = dyn_points * rate

            is_flag = bool(flag_interval) and (n % int(flag_interval) == 0)
            waves.append({
                "index": i, "at": round(clock, 1), "flag": is_flag,
                "zombies": counts,
                "spawn_hp": round(explicit_hp + dyn_hp, 1),
                "explicit_hp": round(explicit_hp, 1),
                "dynamic_hp": round(dyn_hp, 1),
                "spawn_points": round(explicit_points + dyn_points, 1),
            })
            clock += FLAG_WAVE_SECONDS if is_flag else WAVE_SECONDS

        effect_tokens, effect_unmapped = _tokens_for(wave_effects, module_table, ignore)
        tokens |= effect_tokens
        unmapped_all |= effect_unmapped

        fielded = sorted({z for w in waves for z in w["zombies"]}
                         | {z for p in pools for z in p["pool"] if isinstance(z, str)})
        for z in fielded:
            # NOT `water`. On a zombie that tag is LivesInDeepWater, which means
            # "survives deep water" -- a land zombie drowns, a water one is safe
            # on either terrain (zombie_data.py says so outright). Every
            # Gargantuar carries it, so propagating it would have made every
            # world with a Gargantuar demand Lily Pad. Water as a LEVEL fact
            # comes from the module scan (WaterLanes, LilypadPlacement) alone.
            tokens.update((zombies.get(z, {}).get("tags") or []))
            tokens.discard("water")

        out[name] = {
            "codename": name,
            "selection": selection,
            "starting_sun": definition.get("StartingSun"),
            "sun_drop": sun_drop,
            "level_number": definition.get("LevelNumber"),
            "first_reward": definition.get("FirstRewardParam"),
            "grid": {},          # not stated per level; pressure.py assumes 5 rows
            "modules": modules,
            "dynamic_pools": len(pools),
            "tokens": sorted(tokens),
            "zombies": fielded,
            "waves": waves,
            "wave_count": len(waves),
            "total_hp": round(sum(w["spawn_hp"] for w in waves), 1),
            "total_points": round(sum(w["spawn_points"] for w in waves), 1),
            "duration": round(waves[-1]["at"] + WAVE_SECONDS, 1) if waves else 0.0,
            "source": "extracted",
        }

    # Written back so extending hazards.json is reading a list, not guessing.
    hazards["unmapped"] = sorted(unmapped_all)[:400]
    with open(curated("hazards.json"), "w", encoding="utf-8") as fh:
        json.dump(hazards, fh, indent=2)
    return out
