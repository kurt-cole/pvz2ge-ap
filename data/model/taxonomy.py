"""The vocabularies. Every other module speaks these strings and nothing else.

Three orthogonal axes, because a plant is not one thing:

  ELEMENTS   what KIND of thing it does. A plant carries as many as apply --
             Torchwood is kinetic+fire, Cold Snapdragon is ice+fire.
  ROLES      what JOB it does, each with a BAND (b1..b5) saying how well.
             A plant carries a band per role it has: Winter Melon is
             {dps_lob: b4, slow: b4}.
  FLAGS      binary facts that gate placement or answer a threat outright
             (jester_safe, aquatic_only, consumable...).

Threat tokens are the third vocabulary: what a LEVEL demands. They are matched
against plant roles/flags by data/curated/threat_answers.json, so adding a
threat never means editing code.

Bands are DELIBERATELY COARSE. b1..b5 are quintiles of a role's own measured
distribution (see classify.py), not absolute numbers, so a band survives a
balance patch that moves every plant together and only moves when a plant moves
RELATIVE to its peers. Logic that says "a b3 aoe answers this" therefore keeps
meaning the same thing across game updates.
"""

ELEMENTS = (
    "kinetic",     # ordinary physical damage: peas, cabbages, spikes, melee
    "fire",        # burn damage, and the thaw/warmth family
    "ice",         # chill, freeze, and the ice terrain answers
    "electric",    # chaining/arcing damage, ignores some armor
    "poison",      # damage over time, gas, fumes
    "shadow",      # nightshade family; needs Moonflower to reach full output
    "light",       # plasma/laser/beam, pierces a line
    "sun",         # produces sun rather than damage
    "aquatic",     # lives in, or enables, water lanes
    "explosive",   # one-shot area removal
    "arcane",      # everything mechanically singular: hypnosis, time, revive
)

# role -> what having it at all means. The band says how much.
ROLES = {
    "dps_single":  "sustained damage down one lane",
    "dps_aoe":     "sustained damage to more than one zombie at once",
    "dps_pierce":  "damage through a whole lane at once (beam, spikes, chain)",
    "dps_lob":     "arcing damage that ignores what is in front of it",
    "burst":       "a large hit on a short cooldown",
    "instakill":   "removes a zombie regardless of its HP",
    "slow":        "reduces zombie speed, buying crossing time",
    "freeze":      "stops a zombie outright for a period",
    "stun":        "brief hard stop, no damage required",
    "push":        "moves zombies back toward the spawn",
    "wall":        "absorbs damage in front of the lane",
    "shield":      "protects other plants without blocking a lane",
    "sun_econ":    "produces sun",
    "air_clear":   "removes or reaches flying zombies",
    "grave_clear": "removes tombstones and other grid obstructions",
    "warmth":      "a standing WarmingRadius that thaws and melts ice",
    "thaw":        "one-shot unfreeze, no standing radius",
    "hypno":       "turns a zombie against its own side",
    "revive":      "restores a destroyed plant",
    "disarm":      "strips armor or equipment off a zombie",
    "illuminate":  "lights a darkened lawn",
    "lure":        "pulls zombies off their lane or holds them in place",
    "terrain":     "changes the lawn itself (tiles, lily pads, pots)",
    "support":     "buffs other plants rather than acting alone",
}

BANDS = ("b1", "b2", "b3", "b4", "b5")

FLAGS = (
    "jester_safe",     # its damage cannot be reversed by the Jester
    "consumable",      # spent on use
    "timed",           # expires on its own (Lifetime)
    "aquatic_only",    # can only be planted on water
    "land_only",       # cannot be planted on water
    "needs_water_base",  # needs a Lily Pad under it to sit on water
    "sun_hungry",      # spends sun to act (Magnifying Grass)
    "no_data",         # has no _PLANTPROPERTIES sheet; every class is curated
)

# What a LEVEL can demand. Split by where it comes from so a token's provenance
# is never in doubt.
ZOMBIE_TAGS = (
    "garg", "zomboss", "water", "jester", "iceblock", "air", "blocker",
    "hurdle", "burrow", "summoner", "camel",
)

HAZARD_TAGS = (
    "graves",        # tombstones spawn or block tiles
    "tide",          # Big Wave Beach water line advances and retreats
    "sandstorm",     # Ancient Egypt / Wild West wind carries zombies in
    "wind",          # Frostbite Caves gusts blow plants off the lawn
    "ice_terrain",   # slippery / frozen tiles
    "minecart",      # Wild West rails
    "portals",       # Dark Ages / Far Future teleports
    "beat",          # Neon Mixtape Tour tempo effects
    "rain",          # Neon Mixtape Tour puddles
    "gloom",         # Dark Ages darkness, needs a light source
    "lava",          # Jurassic Marsh / Kongfu burning tiles
    "raptor",        # Jurassic Marsh dino pull/throw effects
    "conveyor",      # no plant chooser: you play what the belt gives you
    "locked_slots",  # a forced or restricted seed selection
    "small_grid",    # fewer usable rows or columns than the standard 5x9
    "no_sun_drop",   # no falling sun; all sun must be produced
    "endless",       # Danger Room / survival: pressure never stops rising
    "puzzle",        # the level is a module, not a lane fight (Beghouled...)
    "objective",     # a non-standard win condition: Last Stand, Protect the
                     # Plant, Plants to Die, a time limit. What "clear it"
                     # means changes, so the pressure curve is not the test
    "power_tiles",   # tiles that boost or link plants (Far Future power tiles,
                     # Kongfu taichi, Neon thunder, gold tiles)
    "trap_tiles",    # tiles that destroy what is placed on them (Lost City
                     # traps, Kongfu TNT)
    "potions",       # Dark Ages potions that buff zombies mid-wave
    "mold",          # mold colonies spread across the lawn and must be cleared
)

TOKENS = ZOMBIE_TAGS + HAZARD_TAGS

# Ordered coarse groupings the site colours by, so a 20-token level still reads
# at a glance.
TOKEN_FAMILY = {
    **{t: "zombie" for t in ZOMBIE_TAGS},
    **{t: "hazard" for t in HAZARD_TAGS},
}


def band_of(value, thresholds):
    """Band a number against ascending quintile cuts. thresholds is len 4."""
    for i, cut in enumerate(thresholds):
        if value < cut:
            return BANDS[i]
    return BANDS[-1]


def validate(record):
    """Raise on a plant record that speaks a word not in these vocabularies.

    Cheap, and it is what stops a typo'd role from silently answering nothing.
    """
    bad_el = set(record.get("elements", [])) - set(ELEMENTS)
    bad_ro = set(record.get("roles", {})) - set(ROLES)
    bad_bd = {b for b in record.get("roles", {}).values() if b not in BANDS}
    bad_fl = set(record.get("flags", [])) - set(FLAGS)
    problems = []
    for label, bad in (("elements", bad_el), ("roles", bad_ro),
                       ("bands", bad_bd), ("flags", bad_fl)):
        if bad:
            problems.append(f"{label}={sorted(bad)}")
    if problems:
        raise ValueError(f"{record.get('name')}: unknown {'; '.join(problems)}")
