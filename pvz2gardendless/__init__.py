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
    ALWAYS_ENABLED_WORLDS, GAME_NAME, OPTIONAL_WORLDS, SELECTABLE_WORLDS,
    STARTER_PLANTS, WORLD_REGIONS, WORLD_STRETCHES, progressive_item_name,
)
from .options import PvZ2Options
from .items import (
    FILLER_POOL, ITEM_NAME_GROUPS, ITEM_NAME_TO_ID, ITEM_NAME_TO_ITEM,
    UPGRADE_ITEM_TO_CNS, PvZ2Item, create_item_pool,
)
from .locations import (
    LOC_NAME_GROUPS, LOC_NAME_TO_ID, MODERN_DAY_VICTORY_LOCS, PvZ2LocationData,
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
            # Four worlds counting Ancient Egypt, plus Modern Day, so
            # worlds_required's 3 is comfortably inside what the seed offers.
            "world_count":        4,
            "goal_type":          "world_key",
            "worlds_required":    3,
            "skip_tutorial":      True,
            "shopsanity":         False,
        },
        "Standard": {
            "world_count":        12,
            "goal_type":          "world_key",
            "worlds_required":    7,
            "skip_tutorial":      True,
            "shopsanity":         False,
        },
        "Completionist": {
            "world_count":        12,
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
        self.multiworld.push_precollected(self.create_item(starter))

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

        Named worlds are kept unconditionally and world_count tops the
        selection up at random, so naming more worlds than the count asks for
        gives you all of them rather than a truncated list -- an explicit
        choice is a statement about the seed, the count is only a target.
        """
        chosen = set(self.options.enabled_worlds.value) & set(SELECTABLE_WORLDS)
        chosen.update(ALWAYS_ENABLED_WORLDS)

        # Ancient Egypt counts toward world_count (it is a world you play);
        # Modern Day does not -- it is always present and not selectable, so
        # counting it would silently cost the seed one of the worlds the
        # player asked for. Top up from OPTIONAL_WORLDS, which is
        # list-ordered, so the sample depends only on the slot's seeded RNG.
        short = self.options.world_count.value - len(chosen - {"Modern Day"})
        if short > 0:
            candidates = [w for w in OPTIONAL_WORLDS if w not in chosen]
            chosen.update(self.random.sample(candidates,
                                             min(short, len(candidates))))
        return chosen

    def create_item(self, name: str) -> Item:
        data = ITEM_NAME_TO_ITEM.get(name)
        if data:
            return PvZ2Item(name, data.classification, data.code, self.player)
        return PvZ2Item(name, ItemClassification.filler, None, self.player)

    def get_filler_item_name(self) -> str:
        # Backfills pool slots emptied by mechanisms outside create_items()
        # (e.g. start_inventory_from_pool) -- without this, AP has nothing to
        # call to replace a removed item, leaving that pool slot permanently
        # short and causing "more locations than items" fill failures.
        return self.random.choice(FILLER_POOL).name

    def active_locations(self) -> List[PvZ2LocationData]:
        """Locations actually built for this slot's options."""
        return compute_active_locations(bool(self.options.shopsanity),
                                        self.enabled_regions,
                                        bool(self.options.include_side_paths),
                                        bool(self.options.include_danger_rooms))

    def create_items(self) -> None:
        pool = create_item_pool(self, len(self.active_locations()))
        self.multiworld.itempool += pool

    def create_regions(self) -> None:
        build_regions(self)

    def set_rules(self) -> None:
        apply_rules(self)

    def world_gates(self) -> Dict[str, Any]:
        """The stretch each world's levels are behind, for the client.

        The client enforces these: a level in stretch 1 cannot be STARTED
        until one copy of that world's progressive unlock has arrived, and
        stretch 2 until two have. Only the locked stretches are sent -- a
        world's opening needs nothing, so listing it would be 200 location
        names saying "allowed".

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
            stretches = world_stretches(names)
            gates[world_name] = {
                "item": progressive_item_name(world_name),
                # index 0 is the opening and is deliberately dropped
                "stretches": stretches[1:],
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
