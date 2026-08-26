"""
PvZ2 Gardendless — Archipelago World

Each world (except Ancient Egypt) is unlocked by finding its unique Key item,
Modern Day included.
Victory = complete worlds_required worlds, where completing one means beating
its Zomboss, clearing its final level, or clearing its World Key level --
whichever the goal_type option picks.
"""

import logging
from typing import Dict, List, Any, Set

from worlds.AutoWorld import World, WebWorld
from BaseClasses import Item, ItemClassification, Tutorial
import settings

from .constants import (
    ALWAYS_ENABLED_WORLDS, CHEAP_ATTACKER_PLANTS, EGYPT_SUN_CUT, GAME_NAME,
    JESTER_COUNTER_PLANTS, JESTER_DRAW_COUNT, UNREACHABLE_LOCATIONS, stretches_kept,
    LOGIC_ATTACKER_COUNT, LOGIC_PLANTS, OPTIONAL_WORLDS,
    SELECTABLE_WORLDS, STARTER_PLANTS, SUN_PRODUCER_PLANTS, WORLD_REGIONS,
    WORLD_STRETCHES,
    progressive_item_name, progressive_need, stretch_suffixes,
)
from .options import PvZ2Options, OPTION_GROUPS
from .items import (
    FILLER_POOL, ITEM_NAME_GROUPS, ITEM_NAME_TO_ID, ITEM_NAME_TO_ITEM,
    PLANT_ITEMS, PLANT_NAMES, UPGRADE_ITEM_TO_CNS, PvZ2Item, create_item_pool,
    slot_progression_plants,
)
from .locations import (
    LOC_NAME_GROUPS, LOC_NAME_TO_ID, MODERN_DAY_VICTORY_LOCS, PvZ2LocationData,
    ALL_LOCATIONS,
    VICTORY_LOC_NAMES, active_locations as compute_active_locations, goal_locations_for,
    world_stretches,
)
from .regions import create_regions as build_regions
from .rules import set_rules as apply_rules
from .zombie_data import ZOMBIE_TIERS

# ── Launcher ──────────────────────────────────────────────────────────────────

def _run_builder_gui(*args) -> None:
    """Locate build_pvzge_ap.py and run its Tk installer.

    The installer lives next to this module in a source checkout, and inside
    the archive when the world is installed as an .apworld.
    """
    import importlib.util
    import os
    import tempfile
    import zipfile

    def show_error(message: str) -> None:
        # Imported per call rather than at module scope: this is the only code
        # path that needs Tk, and importing it during world load would pull a
        # GUI toolkit into headless generation.
        import tkinter.messagebox as mb
        mb.showerror("Error", message)

    def run_installer(installer_path: str) -> None:
        spec = importlib.util.spec_from_file_location("build_pvzge_ap", installer_path)
        # spec_from_file_location returns None for a path it cannot handle, and
        # a spec with no loader for some importer types. Reporting that beats
        # the AttributeError the unchecked version raised into the log.
        if spec is None or spec.loader is None:
            show_error(f"Could not load the installer from {installer_path}.")
            return
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.main()

    # Walk up from this module looking for the enclosing .apworld archive.
    apworld_zip = None
    path = __file__
    while True:
        parent = os.path.dirname(path)
        if parent == path:
            break
        if path.endswith(".apworld") and os.path.isfile(path):
            apworld_zip = path
            break
        path = parent

    if apworld_zip is None:
        sibling = os.path.join(os.path.dirname(__file__), "build_pvzge_ap.py")
        if not os.path.isfile(sibling):
            show_error("Could not locate pvz2gardendless.apworld.")
            return
        run_installer(sibling)
        return

    # Extract to a temp directory that is removed once the installer exits.
    # The previous mkdtemp() was never cleaned up, so every launch left one
    # behind. main() blocks until the GUI closes, so tearing the directory
    # down after it returns is safe.
    with tempfile.TemporaryDirectory(prefix="pvz2ge_ap_") as tmp_dir:
        extracted = os.path.join(tmp_dir, "build_pvzge_ap.py")
        try:
            with zipfile.ZipFile(apworld_zip, "r") as zf:
                entry = next((n for n in zf.namelist()
                              if n.endswith("build_pvzge_ap.py")), None)
                if entry is None:
                    show_error("build_pvzge_ap.py not found inside the apworld.")
                    return
                with zf.open(entry) as src_f, open(extracted, "wb") as dst_f:
                    dst_f.write(src_f.read())
        except Exception as e:
            # Deliberately broad: this is a GUI entry point whose job is to
            # turn any extraction failure into a dialog the user can read,
            # rather than a traceback in a log they will never open.
            show_error(f"Failed to extract installer: {e}")
            return
        run_installer(extracted)

def _launch_installer(*args) -> None:
    from worlds.LauncherComponents import launch
    launch(_run_builder_gui, name="PvZ2GE AP Installer")

# Registering the Launcher entry must never take the whole world down with it
# -- a world that fails to import cannot generate at all, and the installer is
# a convenience, not a generation dependency. Only ImportError is swallowed
# (older AP builds, or LauncherComponents moving), and even that is logged:
# the previous bare `except Exception: pass` meant any breakage here showed up
# as the installer silently vanishing from the Launcher with no explanation.
try:
    from worlds.LauncherComponents import components, Component, Type
except ImportError:  # pragma: no cover - depends on the host AP version
    logging.warning(
        "PvZ2 Gardendless: worlds.LauncherComponents unavailable, so the "
        "installer will not appear in the Archipelago Launcher. Generation "
        "is unaffected.", exc_info=True)
else:
    components.append(Component("PvZ2 Gardendless Installer", func=_launch_installer,
        component_type=Type.CLIENT,
        description="Build and install the PvZ2 Gardendless Archipelago mod."))


# ── Settings (persisted to host.yaml) ────────────────────────────────────────

class PvZ2Settings(settings.Group):
    build_directory: str = ""
    """Directory where the PvZ2 Gardendless Archipelago mod will be built."""


# ── World class ───────────────────────────────────────────────────────────────

class PvZ2Web(WebWorld):
    theme = "grass"
    # WebHost reads the groups off the WebWorld, not off the options module --
    # defining OPTION_GROUPS alone leaves every option in the default group.
    # Anything not named here still shows, under AP's own fallback group.
    option_groups = OPTION_GROUPS
    # file_name must match a real file in docs/ -- WebHost reads it straight
    # off disk, and a name that does not resolve 404s the guide.
    tutorials = [Tutorial(
        "Mod Setup Guide", "How to set up the PvZ2 Gardendless Archipelago mod",
        "English", "setup_en.md", "setup/en", ["Trikehard"]
    )]

    # Starting points on the options page. Each preset only names the options
    # it actually means to pin; everything else falls back to its default.
    options_presets = {
        "Short": {
            # Four worlds in total, Ancient Egypt among them, so
            # worlds_required's 3 is comfortably inside what the seed offers.
            "world_count":        4,
            "goal_type":          "world_key",
            "worlds_required":    3,
            "skip_tutorial":      True,
            "shopsanity":         False,
        },
        "Standard": {
            "world_count":        13,
            "goal_type":          "world_key",
            "worlds_required":    7,
            "skip_tutorial":      True,
            "shopsanity":         False,
        },
        "Completionist": {
            "world_count":        13,
            "goal_type":          "completion",
            "worlds_required":    12,
            "skip_tutorial":      False,
            "shopsanity":         True,
        },
    }


class PvZ2GardendlessWorld(World):
    """
    PvZ2 Gardendless — A web-based reimagining of Plants vs. Zombies 2.
    Each world requires its unique Key item to access, Modern Day included.
    Victory = complete a configurable number of worlds, where completing one
    means its Zomboss, its final level or its World Key level.
    """
    game         = GAME_NAME
    settings_key = "pvz2gardendless"
    web          = PvZ2Web()
    settings: PvZ2Settings
    topology_present = True

    item_name_to_id     = ITEM_NAME_TO_ID
    location_name_to_id = LOC_NAME_TO_ID

    options_dataclass = PvZ2Options
    options: PvZ2Options

    item_name_groups     = ITEM_NAME_GROUPS
    location_name_groups = LOC_NAME_GROUPS

    # Which main worlds this seed uses, and the regions they cover. Resolved
    # in generate_early() because create_items(), create_regions(),
    # set_rules() and fill_slot_data() all have to agree on one answer -- a
    # second roll would give them different seeds.
    enabled_worlds:  Set[str]
    enabled_regions: Set[str]

    # WHICH WORLDS THIS SLOT BUILT, filled in by generate_early. Declared with a
    # default for the same reason as the draws below, and this one bit for real:
    # create_item -> slot_progression_plants -> enabled_worlds, so calling
    # create_item on a world that has not been through generate_early raised
    # AttributeError rather than returning an item.
    #
    # That is not a generation path -- generate_early always runs first there --
    # but it IS what a TRACKER does. Universal Tracker resolves items against a
    # world it rebuilds itself, and an exception in create_item leaves it with
    # no item to reason about, which shows up as "I am holding the plant and
    # nothing opened".
    #
    # Empty means "no world named a plant", so classification falls back to the
    # static table. Wrong if it ever happened during real generation, but it
    # cannot: create_regions and create_items both run after generate_early.
    enabled_worlds: Set[str] = frozenset()

    # This slot's cheap-attacker draw, filled in by generate_early. Declared
    # here so create_item has something to read if it is ever called before
    # generate_early: an empty set would silently leave every attacker useful,
    # which reads as a working seed right up until the Egypt 6 gate cannot be
    # satisfied by anything in the pool.
    logic_attackers: frozenset = frozenset()

    # This slot's Jester counter, one of the 36 that can damage him. Same
    # reasoning, same hazard: slot_entry_groups reads it through
    # slot_progression_plants.
    logic_jesters: frozenset = frozenset()

    # What generate_early handed the player. Declared here for the same reason:
    # create_item_pool reads it to keep those plants out of the pool, and an
    # empty default means "nothing granted" rather than an AttributeError.
    starting_plants: list = []

    def generate_early(self) -> None:
        self.enabled_worlds  = self._choose_worlds()
        self.enabled_regions = {region for world in self.enabled_worlds
                                for region in WORLD_REGIONS[world]}

        # The base game normally grants Peashooter/Sunflower/etc. via its own
        # BASEUNLOCKLIST, but the AP client's plantProps guard blocks any
        # AP-managed plant until it's actually been received as an item --
        # so without a guaranteed starting plant, a player can be left with
        # zero usable plants until the multiworld happens to send one.
        # STARTER_PLANTS rather than CHEAP_ATTACKER_PLANTS: the guarantee is
        # only worth something if the plant can hold a lane, and the wider
        # list includes single-use plants (Potato Mine, Chili Bean) and
        # non-damaging support. Those still count for the Egypt logic gate.
        starter = self.random.choice(STARTER_PLANTS)

        # This slot's cheap attackers: the LOGIC_ATTACKER_COUNT of the 46 that
        # rules.py's Egypt 6 gate will name, and therefore the only ones
        # promoted to progression. The other 36 are ordinary useful plants.
        #
        # Naming all 46 cost 36 progression slots for nothing. In a small seed
        # the progression block is what squeezes out every useful plant, every
        # filler and every trap -- an Egypt-only seed had room for not one coin
        # or gem -- and the rule only ever needed ONE of them to be findable.
        #
        # THE STARTER IS DRAWN FIRST AND FORCED INTO THE SET. Two reasons, and
        # both matter:
        #   - it keeps the gate's meaning EXACTLY as it was. The starter is
        #     precollected, so it already satisfied has_any over all 46 in every
        #     seed; drawing the 10 independently would leave the starter outside
        #     them about 78% of the time and quietly turn a dead requirement
        #     into a live one, per seed, which is not a change anyone asked for.
        #   - the draw has to contain at least one plant that can hold a lane.
        #     STARTER_PLANTS is CHEAP_ATTACKER_PLANTS minus the single-use and
        #     non-damaging ones, and a blind draw of 10 can be all Cherry Bomb
        #     and Potato Mine.
        # Set before create_item is called for the starter, since that reads it.
        _rest = [p for p in CHEAP_ATTACKER_PLANTS if p != starter]
        self.logic_attackers = frozenset(
            [starter] + self.random.sample(_rest, LOGIC_ATTACKER_COUNT - 1))

        # This slot's Jester counter, on the same principle: 36 plants can hurt
        # him, the Dark Ages entrance names JESTER_DRAW_COUNT of them, and only
        # those are progression. Naming all 36 would promote all 36 and squeeze
        # a small seed exactly as naming all 46 attackers did.
        #
        # Drawn for EVERY slot, not just seeds with Dark Ages: create_item and
        # the pool floor both consult it, and a world-conditional draw would
        # take a different number of values off world.random and shift every
        # later draw in the seed. Cheap, and it keeps the RNG stream stable.
        self.logic_jesters = frozenset(
            self.random.sample(JESTER_COUNTER_PLANTS, JESTER_DRAW_COUNT))

        # Extra starting plants, when the option asks for them. The cheap
        # attacker above is always the first, so the guarantee it exists for
        # holds at every setting.
        #
        # NO PLANT ANY RULE NAMES IS EVER DRAWN. Anything handed over at
        # generation time satisfies every rule that asks for it before the rule
        # is ever checked, so granting one makes that gate decorative.
        #
        # LOGIC_PLANTS is exactly the sun producers plus every world entry
        # plant, which is the whole static set of rule-named plants -- so this
        # filter maintains itself if a requirement is ever added.
        #
        #   Sun producers: Egypt's egypt6 checkpoint wants one plus a cheap
        #   attacker, and the attacker half is already free from the starter. A
        #   free sun producer takes sphere 1 from 9 to 12, or to 17 with
        #   shopsanity, by opening egypt6-8 plus the store and the Squash quest.
        #
        #   Entry plants: a free Lily Pad does not move sphere 1 -- that world
        #   sits behind an unlock regardless -- but it does mean the world opens
        #   on its unlock alone. At 10 starting plants that was landing in 70%
        #   of seeds, so the requirements added the same day were decorative
        #   more often than not. Kurt asked for them excluded, 2026-08-23.
        #
        # Excluded whether or not their world is in this seed. An entry plant
        # for a world the seed left out gates nothing, but it is also a plant
        # that cannot be used -- an Egypt-only seed has no water, so a free Lily
        # Pad is a dead card in the opening hand. Nothing is lost by dropping it
        # from the draw.
        #
        # The slot's own drawn cheap attackers are NOT excluded: the starter
        # already satisfies that gate, so granting another changes nothing.
        #
        # The Jester group is NOT excluded wholesale: 36 plants can hurt him and
        # only the one this slot drew is named by any rule, so excluding all of
        # them would take a quarter of the roster out of the draw to protect a
        # gate that asks for one plant. The drawn one is excluded, like any
        # other rule-named plant.
        _no_grant = (LOGIC_PLANTS - set(JESTER_COUNTER_PLANTS)) | self.logic_jesters
        extras = []
        want = self.options.starting_plants.value - 1
        if want:
            pool = [p.name for p in PLANT_ITEMS
                    if p.name != starter
                    and p.name not in _no_grant]
            extras = self.random.sample(pool, min(want, len(pool)))

        # Read by create_item_pool, which drops these from the pool. Sorted so
        # the pool is built in a fixed order regardless of how the draw fell.
        self.starting_plants = sorted([starter] + extras)
        for name in self.starting_plants:
            self.multiworld.push_precollected(self.create_item(name))

        # No sun producer is requested or granted here, and none needs to be.
        # It used to be nudged into sphere 1 with multiworld.early_items, which
        # was only ever a request -- fill warns and places normally when it
        # cannot honour one.
        #
        # It is now structural. Sphere 1 is egypt1-5, the tutorial, the shop and
        # (only when include_side_paths is on) the standalone side paths, and
        # every exit from it runs through a sun producer: Egypt's own gate
        # starts at egypt6, and rules.py requires one
        # to enter every other world on top of its key. So fill has to place a
        # sun producer in sphere 1 or the seed does not open at all. sphere_test
        # proves this by brute force over the whole pool rather than by
        # assertion -- see "no item other than a sun producer opens anything".

    def _choose_worlds(self) -> Set[str]:
        """Resolve world_count and enabled_worlds into one set of worlds.

        world_count is a HARD CAP: it is exactly how many worlds the seed gets.
        enabled_worlds picks WHICH ones, and the count tops the selection up at
        random when it is short or trims it at random when it is over.

        Naming more worlds than the count asks for used to give you all of
        them, on the reasoning that an explicit choice outranks a target. That
        stopped working once enabled_worlds carried a default naming eleven
        worlds: every count from 1 to 11 was already satisfied by the default,
        so world_count did nothing at all unless it was raised to 12 or 13.
        The count wins now, so a small seed is a small seed whatever the yaml
        names.

        Ancient Egypt survives the trim whatever happens -- it is the only
        world playable with no items, so a seed without it opens on nothing.
        """
        chosen = set(self.options.enabled_worlds.value) & set(SELECTABLE_WORLDS)
        chosen.update(ALWAYS_ENABLED_WORLDS)

        # Every world counts toward world_count, Ancient Egypt and Modern Day
        # alike: the number is the worlds you get. Modern Day used to be
        # subtracted here because it was forced into every seed on top of the
        # count, which made `world_count: 1` produce two worlds. Sample from
        # OPTIONAL_WORLDS, which is list-ordered, so both the top-up and the
        # trim depend only on the slot's seeded RNG.
        short = self.options.world_count.value - len(chosen)
        if short > 0:
            candidates = [w for w in OPTIONAL_WORLDS if w not in chosen]
            chosen.update(self.random.sample(candidates,
                                             min(short, len(candidates))))
        elif short < 0:
            # Trim from the optional worlds only. Iterating OPTIONAL_WORLDS
            # rather than `chosen` keeps the candidate order list-derived
            # instead of set-derived, which would vary between runs and make
            # the same slot seed produce different worlds.
            droppable = [w for w in OPTIONAL_WORLDS if w in chosen]
            chosen.difference_update(
                self.random.sample(droppable, min(-short, len(droppable))))
        return chosen

    def create_item(self, name: str) -> Item:
        data = ITEM_NAME_TO_ITEM.get(name)
        if data:
            cls = data.classification
            # A PLANT's classification is a per-slot question: which plants are
            # progression depends on this slot's cheap-attacker draw and on
            # which worlds it enabled. Decided here rather than in items.py
            # because PLANT_ITEMS is a module-level list shared by every slot in
            # the multiworld -- stamping a per-slot classification onto it would
            # leak between players.
            #
            # Both directions matter. Promoting is what keeps a named plant
            # satisfiable at all; demoting is what stops an Egypt-only seed
            # carrying 13 entry plants and 36 attackers as progression for rules
            # it never built, which is what left it no room for filler.
            #
            # Only plants are touched. Everything else keeps the static
            # classification it was defined with.
            if name in PLANT_NAMES:
                cls = (ItemClassification.progression
                       if name in slot_progression_plants(self)
                       else ItemClassification.useful)
            return PvZ2Item(name, cls, data.code, self.player)
        return PvZ2Item(name, ItemClassification.filler, None, self.player)

    def get_filler_item_name(self) -> str:
        # Backfills pool slots emptied by mechanisms outside create_items()
        # (e.g. start_inventory_from_pool) -- without this, AP has nothing to
        # call to replace a removed item, leaving that pool slot permanently
        # short and causing "more locations than items" fill failures.
        return self.random.choice(FILLER_POOL).name

    def kept_stretches(self, world_name: str):
        """The stretch suffixes this slot builds for `world_name`.

        One place, because regions.py, world_gates and the unlock count must
        agree: a region built for a stretch the pool ships no unlock for is a
        region nothing can open.
        """
        return stretches_kept(world_name, self.options.goal_type.value,
                              bool(self.options.include_levels_past_goal))

    def active_locations(self) -> List[PvZ2LocationData]:
        """Locations actually built for this slot's options."""
        return compute_active_locations(bool(self.options.shopsanity),
                                        self.enabled_regions,
                                        bool(self.options.include_side_paths),
                                        bool(self.options.include_danger_rooms),
                                        self.options.goal_type.value,
                                        bool(self.options.include_levels_past_goal))

    def create_items(self) -> None:
        pool = create_item_pool(self, len(self.active_locations()))
        self.multiworld.itempool += pool

    def create_regions(self) -> None:
        build_regions(self)

    def set_rules(self) -> None:
        apply_rules(self)

    def world_gates(self) -> Dict[str, Any]:
        """The stretch each world's levels are behind, for the client.

        The client enforces these: a level cannot be STARTED until enough
        copies of that world's progressive unlock have arrived. For most
        worlds that is one for the opening (the unlock that replaced the World
        Key), two for the middle stretch and three for the last; Ancient Egypt
        opens with none and so wants one and two.

        Only stretches that need an unlock are sent. Ancient Egypt's opening
        and its egypt6 checkpoint need none -- that checkpoint is a logic
        requirement, a sun producer, and the client must not refuse to start
        those levels over it.

        Location names rather than game level ids, because the client already
        holds that map (LOC_LEVELS) and duplicating it here is exactly the kind
        of second copy that drifts. regions.py cuts the same worlds with the
        same call, so the gate a player meets and the gate fill reasoned about
        cannot disagree.
        """
        active = self.active_locations()
        gates: Dict[str, Any] = {}
        for world_name in sorted(self.enabled_worlds):
            names = [l.name for l in active
                     if l.region in WORLD_REGIONS[world_name]]
            if len(names) < len(WORLD_STRETCHES) * 2:
                continue  # too small to cut, same test regions.py makes
            # Cut from the world's FULL level list and keep only this slot's
            # stretches -- exactly what regions.py does, and for the same
            # reason. Cutting from the trimmed `names` instead re-derives the
            # milestones from whatever survived, which for the two worlds with
            # no milestone to cut on (Aerial Fortress has neither marker,
            # Kongfu Temple has no Zomboss) lands the fallback cuts somewhere
            # else entirely: 7 to 10 of their levels end up in a different
            # stretch here than regions.py put them in.
            #
            # THAT DISAGREEMENT IS AN UNWINNABLE SEED, not a cosmetic one. This
            # table is what the client refuses level starts on; regions.py is
            # what fill reasons about. If they differ, fill places progression
            # in a level the player cannot start. gen_test cross-checks the two
            # on a TRIMMED seed for precisely this.
            parts = world_stretches(
                [l.name for l in ALL_LOCATIONS
                 if l.region in WORLD_REGIONS[world_name]
                 and l.name not in UNREACHABLE_LOCATIONS],
                EGYPT_SUN_CUT if world_name == "Ancient Egypt" else None)
            suffixes = self.kept_stretches(world_name)
            built = {l.name for l in active}
            # Keyed by how many unlocks the stretch needs, so a stretch that
            # needs none is simply absent. Ancient Egypt's " Early" (egypt6-8)
            # is the case that matters: it is gated on a sun producer, which is
            # logic only, and the client must not refuse to start those levels.
            locked = {}
            for idx, part in enumerate(parts):
                if idx >= len(suffixes):
                    break  # past this slot's goal cut; not built, so not gated
                need = progressive_need(world_name, suffixes[idx])
                if need:
                    locked.setdefault(need, []).extend(
                        [n for n in part if n in built])
            if not locked:
                continue
            gates[world_name] = {
                "item": progressive_item_name(world_name),
                "stretches": [locked.get(n, []) for n in
                              range(1, max(locked) + 1)],
            }
        return gates

    def fill_slot_data(self) -> Dict[str, Any]:
        goal_locs = goal_locations_for(self.options.goal_type.value,
                                       self.enabled_regions)
        # Must match the clamp in rules.py's goal_rule, or the client holds
        # the run to a stricter (unreachable) threshold than the
        # generation-time rule actually requires.
        req = min(self.options.worlds_required.value, len(goal_locs))
        return {
            "death_link":      bool(self.options.death_link),
            "game_version":    "0.8.x",
            "goal_type":       self.options.goal_type.current_key,
            "worlds_required": req,
            # One per world in this seed. Checking worlds_required of them is
            # the win, and the client sends the StatusUpdate off this list.
            "goal_locations":  goal_locs,
            "victory_locations": VICTORY_LOC_NAMES,
            # Modern Day is gated on its key again, and the run no longer ends
            # on one Modern Day level. A client built before 2026-08-23 does
            # not know that: it would hold Modern Day shut behind the goal
            # count and wait for the level below to end the run. So the flag is
            # what a NEW client reads, and modern_day_victory stays in
            # slot_data so an OLD client still has something to finish on.
            "modern_day_keyed":   True,
            # Which levels are behind a progressive world unlock, and how many
            # copies each needs. The client refuses to start one it does not
            # have the unlocks for; seeds generated before 2026-08-23 send no
            # such key and the client leaves every level playable, which is how
            # they always were.
            "world_gates":        self.world_gates(),
            "modern_day_victory": MODERN_DAY_VICTORY_LOCS[
                self.options.modern_day_victory.value],
            "skip_tutorial":     bool(self.options.skip_tutorial),
            # The client needs this because location_name_to_id is static and
            # always contains the shop entries, so their presence there says
            # nothing about whether this slot actually has them.
            "shopsanity":        bool(self.options.shopsanity),
            # With this on the client withholds every permanent upgrade until
            # its item arrives. Seeds generated before the option existed have
            # no key here at all, and the client reads a missing key as off --
            # which is what keeps their upgrades working as they always did.
            "shuffle_upgrades":  bool(self.options.shuffle_upgrades),
            # Item name -> the codenames it grants, in order. The client
            # grants the first N after receiving N copies, which is what makes
            # the progressive items work. Sent rather than duplicated in the
            # client so the two cannot drift.
            "upgrade_items":     UPGRADE_ITEM_TO_CNS,
            "randomize_conveyor": bool(self.options.randomize_conveyor_plants),
            # Per-slot seed for the client's conveyor roll. Generated here so
            # the belt is reproducible for this slot and differs between
            # slots, rather than every player on one seed seeing the same
            # plants. The client folds the level's own plant list into it, so
            # each level rolls differently and a retry is not a reroll.
            "conveyor_seed":     self.random.getrandbits(32),
            "shuffle_zombies":   bool(self.options.shuffle_zombies),
            # The swap tiers, sent rather than duplicated in the client so the
            # two cannot drift. Each tier is a set of zombies the game itself
            # prices the same (see zombie_data for the derivation); the client
            # trades a zombie only for another in its own list, which is what
            # keeps a level's difficulty and every world's threat footprint
            # intact. ~6KB, and only sent when the option is on.
            "zombie_tiers":      (ZOMBIE_TIERS
                                  if self.options.shuffle_zombies else {}),
            # Per-slot seed for the client's zombie roll, for the same reason
            # conveyor_seed exists: the belt and the waves should differ
            # between slots on one seed, and the client folds the level's own
            # zombie list into it so each level rolls differently and a retry
            # is not a reroll.
            "zombie_seed":       self.random.getrandbits(32),
            # Informational for now -- worlds left out simply never receive a
            # key, which is what keeps them locked. Sorted so the value is
            # stable for a given seed rather than varying with set order.
            "enabled_worlds":    sorted(self.enabled_worlds),
        }
