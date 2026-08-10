"""
PvZ2 Gardendless — Archipelago World

Each world (except Ancient Egypt) is unlocked by finding its unique Key item.
Modern Day unlocks once a configurable number of world goals are met:
world keys, world completions (beat the final level), or world trophies.
Victory = defeat the Modern Day Zomboss.
"""

import logging
from typing import Dict, List, Any

from worlds.AutoWorld import World, WebWorld
from BaseClasses import Item, ItemClassification, Tutorial
import settings

from .constants import CHEAP_ATTACKER_PLANTS, GAME_NAME
from .options import PvZ2Options
from .items import (
    FILLER_ITEMS, ITEM_NAME_GROUPS, ITEM_NAME_TO_ID, ITEM_NAME_TO_ITEM,
    PvZ2Item, create_item_pool,
)
from .locations import (
    LOC_NAME_GROUPS, LOC_NAME_TO_ID, MODERN_DAY_VICTORY_LOCS, PvZ2LocationData,
    VICTORY_LOC_NAMES, active_locations as compute_active_locations, goal_locations_for,
)
from .regions import create_regions as build_regions
from .rules import set_rules as apply_rules

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
            "goal_type":          "world_keys",
            "worlds_required":    3,
            "modern_day_victory": "world_key",
            "skip_tutorial":      True,
            "shopsanity":         False,
        },
        "Standard": {
            "goal_type":          "world_keys",
            "worlds_required":    7,
            "modern_day_victory": "zomboss",
            "skip_tutorial":      True,
            "shopsanity":         False,
        },
        "Completionist": {
            "goal_type":          "world_completions",
            "worlds_required":    11,
            "modern_day_victory": "completion",
            "skip_tutorial":      False,
            "shopsanity":         True,
        },
    }


class PvZ2GardendlessWorld(World):
    """
    PvZ2 Gardendless — A web-based reimagining of Plants vs. Zombies 2.
    Each world requires its unique Key item to access. Modern Day unlocks
    once a configurable number of world goals are met. Victory = defeat the
    Modern Day Zomboss.
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

    def generate_early(self) -> None:
        # The base game normally grants Peashooter/Sunflower/etc. via its own
        # BASEUNLOCKLIST, but the AP client's plantProps guard blocks any
        # AP-managed plant until it's actually been received as an item --
        # so without a guaranteed starting plant, a player can be left with
        # zero usable plants until the multiworld happens to send one.
        starter = self.random.choice(CHEAP_ATTACKER_PLANTS)
        self.multiworld.push_precollected(self.create_item(starter))

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
        return self.random.choice(FILLER_ITEMS).name

    def active_locations(self) -> List[PvZ2LocationData]:
        """Locations actually built for this slot's options."""
        return compute_active_locations(bool(self.options.shopsanity))

    def create_items(self) -> None:
        pool = create_item_pool(self, len(self.active_locations()))
        self.multiworld.itempool += pool

    def create_regions(self) -> None:
        build_regions(self)

    def set_rules(self) -> None:
        apply_rules(self)

    def fill_slot_data(self) -> Dict[str, Any]:
        goal_locs = goal_locations_for(self.options.goal_type.value)
        # Must match the clamp in rules.py's modern_day_rule, or the
        # client's canAccessModernDay() enforces a stricter (unreachable)
        # threshold than the generation-time access rule actually requires.
        req = min(self.options.worlds_required.value, len(goal_locs))
        return {
            "death_link":      bool(self.options.death_link),
            "game_version":    "0.8.x",
            "goal_type":       self.options.goal_type.current_key,
            "worlds_required": req,
            "goal_locations":  goal_locs,
            "victory_locations": VICTORY_LOC_NAMES,
            # The single location whose check ends the run. The client used to
            # hardcode the Zomboss; it now reports goal completion off this.
            "modern_day_victory": MODERN_DAY_VICTORY_LOCS[
                self.options.modern_day_victory.value],
            "skip_tutorial":     bool(self.options.skip_tutorial),
            # The client needs this because location_name_to_id is static and
            # always contains the shop entries, so their presence there says
            # nothing about whether this slot actually has them.
            "shopsanity":        bool(self.options.shopsanity),
        }
