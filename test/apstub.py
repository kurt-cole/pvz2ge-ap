"""Minimal Archipelago stubs, enough to import pvz2gardendless and drive
generate_early -> create_regions -> set_rules -> create_items offline."""
import enum, sys, types, dataclasses, random, collections


def mod(name, **attrs):
    m = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules[name] = m
    return m


class ItemClassification(enum.IntFlag):
    filler = 0
    progression = 1
    useful = 2
    trap = 4


class Item:
    game = "Generic"
    def __init__(self, name, classification, code, player):
        self.name, self.classification, self.code, self.player = name, classification, code, player


class Location:
    game = "Generic"
    def __init__(self, player, name, code=None, parent=None):
        self.player, self.name, self.address, self.parent_region = player, name, code, parent
        self.access_rule = lambda state: True
        # AP defaults this to "anything may go here"; forbid_items_for_player
        # narrows it. Fill consults it before placing an item.
        self.item_rule = lambda item: True
        self.item = None
        self.locked = False
    def place_locked_item(self, item):
        self.item, self.locked = item, True
    def can_reach(self, state):
        return self.parent_region.can_reach(state) and self.access_rule(state)


class Entrance:
    def __init__(self, player, name, parent):
        self.player, self.name, self.parent_region, self.connected_region = player, name, parent, None
        self.access_rule = lambda state: True


class Region:
    def __init__(self, name, player, multiworld):
        self.name, self.player, self.multiworld = name, player, multiworld
        self.locations, self.entrances, self.exits = [], [], []
    def connect(self, target, name=None, rule=None):
        e = Entrance(self.player, name or f"{self.name} -> {target.name}", self)
        if rule:
            e.access_rule = rule
        e.connected_region = target
        self.exits.append(e)
        target.entrances.append(e)
        self.multiworld._entrances[(e.name, self.player)] = e
        return e
    def can_reach(self, state):
        return self in getattr(state, "_reachable", ())


class Tutorial:
    def __init__(self, *a, **k): pass


mod("BaseClasses", ItemClassification=ItemClassification, Item=Item,
    Location=Location, Region=Region, Entrance=Entrance, Tutorial=Tutorial)


class AssembleOptions(type):
    pass


class Option:
    default = 0
    def __init__(self, value):
        self.value = value
    @classmethod
    def from_any(cls, data):
        return cls(data)


class Range(Option):
    range_start, range_end = 0, 1
    def __int__(self): return self.value


# Options.Visibility, an IntFlag in real Archipelago. Only used to hide an
# option from the templates/WebHost UI, so the values just have to be distinct
# and OR-able -- nothing offline reads them.
class Visibility(enum.IntFlag):
    none       = 0b0000
    template   = 0b0001
    simple_ui  = 0b0010
    complex_ui = 0b0100
    spoiler    = 0b1000
    all        = 0b1111


class Toggle(Option):
    def __bool__(self): return bool(self.value)


class Choice(Option):
    @property
    def current_key(self):
        for k, v in type(self).__dict__.items():
            if k.startswith("option_") and v == self.value:
                return k[len("option_"):]
        return str(self.value)


class OptionSet(Option):
    valid_keys = []
    default = frozenset()


class DefaultOnToggle(Toggle):
    default = 1


class DeathLink(Toggle):
    pass


@dataclasses.dataclass
class PerGameCommonOptions:
    pass


mod("Options", Choice=Choice, Range=Range, Toggle=Toggle, OptionSet=OptionSet,
    DefaultOnToggle=DefaultOnToggle,
    DeathLink=DeathLink, PerGameCommonOptions=PerGameCommonOptions,
    Option=Option, AssembleOptions=AssembleOptions, Visibility=Visibility)


class Group:
    pass


mod("settings", Group=Group, get_settings=lambda: None)


class World:
    def __init__(self, multiworld, player):
        self.multiworld, self.player = multiworld, player
        self.random = random.Random(12345)


class WebWorld:
    pass


worlds = mod("worlds")
mod("worlds.AutoWorld", World=World, WebWorld=WebWorld)
mod("worlds.generic")


def set_rule(spot, rule):
    spot.access_rule = rule


def add_rule(spot, rule, combine="and"):
    old = spot.access_rule
    spot.access_rule = lambda state: old(state) and rule(state)


def forbid_items_for_player(location, items, player):
    """AP ANDs onto any existing item_rule rather than replacing it."""
    old = location.item_rule
    location.item_rule = lambda item: (
        old(item) and not (item.player == player and item.name in items))


mod("worlds.generic.Rules", set_rule=set_rule, add_rule=add_rule,
    forbid_items_for_player=forbid_items_for_player)
mod("worlds.LauncherComponents")  # no components attr -> ImportError path


class MultiWorld:
    def __init__(self):
        self.regions, self.itempool = [], []
        self.completion_condition, self.precollected = {}, []
        self._entrances, self._locations = {}, {}
        self.indirect = []
        # AP builds this per player before generate_early; fill then places
        # these items in sphere 1 rather than granting them outright.
        self.early_items = collections.defaultdict(dict)
        self.random = random.Random(999)
    def get_entrance(self, name, player):
        return self._entrances[(name, player)]
    def get_location(self, name, player):
        if not self._locations:
            for r in self.regions:
                for l in r.locations:
                    self._locations[(l.name, l.player)] = l
        return self._locations[(name, player)]
    def get_regions(self, player=None):
        return [r for r in self.regions if player is None or r.player == player]
    def push_precollected(self, item):
        self.precollected.append(item)
    def register_indirect_condition(self, region, entrance):
        self.indirect.append((region.name, entrance.name))


class CollectionState:
    """Enough of AP's state to evaluate this world's rules and sweep regions."""

    def __init__(self, multiworld, item_name_groups=None):
        self.multiworld = multiworld
        self.prog_items = {}
        self.item_name_groups = item_name_groups or {}
        self._reachable = set()

    def collect(self, name, count=1):
        self.prog_items[name] = self.prog_items.get(name, 0) + count

    def has(self, name, player, count=1):
        return self.prog_items.get(name, 0) >= count

    def has_any(self, names, player):
        return any(self.prog_items.get(n, 0) for n in names)

    def has_all(self, names, player):
        return all(self.prog_items.get(n, 0) for n in names)

    def has_group(self, group, player, count=1):
        found = 0
        for n in self.item_name_groups.get(group, ()):
            found += self.prog_items.get(n, 0)
            if found >= count:
                return True
        return count <= 0

    def sweep(self):
        """Fixed point over entrance rules from Menu.

        _reachable grows as the sweep runs rather than being assigned at the
        end, so a rule that calls can_reach() on another region -- the Modern
        Day goal rule does -- sees what has been reached so far. That is the
        same reason AP needs register_indirect_condition.
        """
        start = next((r for r in self.multiworld.regions if r.name == "Menu"), None)
        reach = {start} if start else set()
        self._reachable = reach
        changed = True
        while changed:
            changed = False
            for r in list(reach):
                for e in r.exits:
                    tgt = e.connected_region
                    if tgt in reach:
                        continue
                    try:
                        ok = e.access_rule(self)
                    except Exception:
                        ok = False
                    if ok:
                        reach.add(tgt)
                        changed = True
        self._reachable = reach
        return reach

    def can_reach(self, spot, typ=None, player=None):
        if hasattr(spot, "parent_region"):
            return spot.parent_region in self._reachable and spot.access_rule(self)
        return spot in self._reachable

    def reachable_locations(self):
        out = []
        for r in self._reachable:
            for l in r.locations:
                try:
                    if l.access_rule(self):
                        out.append(l)
                except Exception:
                    pass
        return out
