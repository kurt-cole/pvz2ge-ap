"""
PvZ2 Gardendless — location definitions and goal/victory location lookups.
"""

import dataclasses
from typing import Dict, List, Optional, Set

from BaseClasses import Location

from .constants import (
    ALL_WORLD_REGIONS, BASE_ID, GAME_NAME, SHOP_COMMODITIES, SHOP_REGION,
    SIDE_PATH_REGIONS, shop_location_name,
)
from .options import GoalType


class PvZ2Location(Location):
    """Every location this world puts into the multiworld. Subclassing purely
    to carry `game`: a bare BaseClasses.Location reports game == "Generic"."""
    game: str = GAME_NAME


@dataclasses.dataclass
class PvZ2LocationData:
    """Static definition of a location -- name, region, ID and role flags."""
    name: str
    region: str
    code: int
    is_victory: bool = False
    is_shop: bool = False


def _make_locs() -> List[PvZ2LocationData]:
    locs = []
    id_ = BASE_ID + 0x10000

    def add(name, region, victory=False, shop=False):
        nonlocal id_
        locs.append(PvZ2LocationData(name, region, id_, victory, shop))
        id_ += 1

    # ── Tutorial ──
    add("Sunflower Unlock", "Tutorial")
    add("Wall-nut Unlock", "Tutorial")
    add("Potatomine Unlock", "Tutorial")
    add("Sauce Unlock", "Tutorial")

    # ── Ancient Egypt ──
    add("random_zomboss_egypt", "Ancient Egypt", victory=True)
    add("Map Unlock", "Ancient Egypt")
    add("Cabbagepult Unlock", "Ancient Egypt")
    add("Bloomerang Unlock", "Ancient Egypt")
    add("Powerupgadget Unlock", "Ancient Egypt")
    add("Iceburg Unlock", "Ancient Egypt")
    add("Branch Unlock Egypt 6", "Ancient Egypt")
    add("Note Egypt Unlock", "Ancient Egypt")
    add("World Key - Ancient Egypt", "Ancient Egypt")
    add("Gravebuster Unlock", "Ancient Egypt")
    add("egypt10", "Ancient Egypt Mid1")
    add("Branch Unlock Egypt 11", "Ancient Egypt Mid1")
    add("Dangerroom Egypt Unlock", "Ancient Egypt Mid1")
    add("Bonkchoy Unlock", "Ancient Egypt Mid1")
    add("egypt14", "Ancient Egypt Mid1")
    add("Branch Unlock Egypt 15", "Ancient Egypt Mid1")
    add("egypt16", "Ancient Egypt Mid1")
    add("Upgrade Pf Slots Lvl1 Unlock", "Ancient Egypt Mid1")
    add("egypt18", "Ancient Egypt Mid1")
    add("Repeater Unlock", "Ancient Egypt Mid1")
    add("egypt20", "Ancient Egypt Mid2")
    add("egypt20_1", "Ancient Egypt Mid2")
    add("Upgrade Starting Sun Lvl1 Unlock", "Ancient Egypt Mid2")
    add("egypt21_1", "Ancient Egypt Mid2")
    add("Branch Unlock Egypt 22", "Ancient Egypt Mid2")
    add("egypt22_1", "Ancient Egypt Mid2")
    add("Dangerroom Egypt Minigame Unlock", "Ancient Egypt Mid2")
    add("Twinsunflower Unlock", "Ancient Egypt Mid2")
    add("egypt24_1", "Ancient Egypt Mid2")
    add("Worldtrophy Egypt Unlock", "Ancient Egypt Mid2")
    add("egypt26", "Ancient Egypt Mid2")
    add("Branch Unlock Egypt 27", "Ancient Egypt Mid2")
    add("egypt28", "Ancient Egypt Mid2")
    add("egypt29", "Ancient Egypt Mid2")
    add("Branch Unlock Egypt 30", "Ancient Egypt Late")
    add("Dangerroom Egypt2 Unlock", "Ancient Egypt Late")
    add("egypt32", "Ancient Egypt Late")
    add("egypt33", "Ancient Egypt Late")
    add("Branch Unlock Egypt 34", "Ancient Egypt Late")
    add("egypt35", "Ancient Egypt Late")
    add("egypt_dangerroom", "Ancient Egypt Late")
    add("egypt_dangerroom2", "Ancient Egypt Late")
    add("egypt_dangerroom_minigame", "Ancient Egypt Late")
    add("random_egypt", "Ancient Egypt Late")

    # ── Pirate Seas ──
    add("random_zomboss_pirate", "Pirate Seas", victory=True)
    add("Kernelpult Unlock", "Pirate Seas")
    add("pirate2", "Pirate Seas")
    add("Snapdragon Unlock", "Pirate Seas")
    add("Dangerroom Pirate Unlock", "Pirate Seas")
    add("Branch Unlock Pirate 5", "Pirate Seas")
    add("Spikeweed Unlock", "Pirate Seas")
    add("Note Pirate Unlock", "Pirate Seas")
    add("World Key - Pirate Seas", "Pirate Seas")
    add("Springbean Unlock", "Pirate Seas")
    add("pirate10", "Pirate Seas")
    add("Coconutcannon Unlock", "Pirate Seas")
    add("Upgrade Sunshovel Lvl1 Unlock", "Pirate Seas")
    add("pirate13", "Pirate Seas")
    add("Threepeater Unlock", "Pirate Seas")
    add("pirate15", "Pirate Seas")
    add("Branch Unlock Pirate 16", "Pirate Seas")
    add("pirate17", "Pirate Seas")
    add("Spikerock Unlock", "Pirate Seas")
    add("pirate18_1", "Pirate Seas")
    add("Branch Unlock Pirate 19", "Pirate Seas")
    add("pirate20", "Pirate Seas")
    add("pirate20_1", "Pirate Seas")
    add("Upgrade 7 Slots Unlock", "Pirate Seas")
    add("pirate22", "Pirate Seas")
    add("pirate22_1", "Pirate Seas")
    add("Branch Unlock Pirate 23", "Pirate Seas")
    add("pirate23_1", "Pirate Seas")
    add("Cherry Bomb Unlock", "Pirate Seas")
    add("pirate24_1", "Pirate Seas")
    add("Worldtrophy Pirate Unlock", "Pirate Seas")
    add("pirate26", "Pirate Seas")
    add("Branch Unlock Pirate 27", "Pirate Seas")
    add("pirate28", "Pirate Seas")
    add("pirate29", "Pirate Seas")
    add("Branch Unlock Pirate 30", "Pirate Seas")
    add("pirate31", "Pirate Seas")
    add("pirate32", "Pirate Seas")
    add("Dangerroom Pirate2 Unlock", "Pirate Seas")
    add("pirate34", "Pirate Seas")
    add("pirate35", "Pirate Seas")
    add("pirate_dangerroom", "Pirate Seas")
    add("pirate_dangerroom2", "Pirate Seas")
    add("random_pirate", "Pirate Seas")

    # ── Wild West ──
    add("random_zomboss_cowboy", "Wild West", victory=True)
    add("Splitpea Unlock", "Wild West")
    add("Branch Unlock Cowboy 2", "Wild West")
    add("Dangerroom Cowboy Unlock", "Wild West")
    add("Chilibean Unlock", "Wild West")
    add("cowboy5", "Wild West")
    add("Peapod Unlock", "Wild West")
    add("Note Cowboy Unlock", "Wild West")
    add("World Key - Wild West", "Wild West")
    add("Lightningreed Unlock", "Wild West")
    add("cowboy10", "Wild West")
    add("Upgrade Sunshovel Lvl2 Unlock", "Wild West")
    add("Melonpult Unlock", "Wild West")
    add("cowboy12_1", "Wild West")
    add("cowboy13", "Wild West")
    add("Branch Unlock Cowboy 14", "Wild West")
    add("Upgrade Wallnut Firstaid Unlock", "Wild West")
    add("cowboy16", "Wild West")
    add("Branch Unlock Cowboy 17", "Wild West")
    add("Tallnut Unlock", "Wild West")
    add("cowboy18_1", "Wild West")
    add("cowboy19", "Wild West")
    add("Upgrade Pf Refresh Unlock", "Wild West")
    add("cowboy21", "Wild West")
    add("Branch Unlock Cowboy 22", "Wild West")
    add("cowboy22_1", "Wild West")
    add("cowboy23", "Wild West")
    add("cowboy23_1", "Wild West")
    add("Wintermelon Unlock", "Wild West")
    add("cowboy24_1", "Wild West")
    add("Worldtrophy Cowboy Unlock", "Wild West")
    add("Branch Unlock Cowboy 26", "Wild West")
    add("cowboy27", "Wild West")
    add("cowboy28", "Wild West")
    add("cowboy29", "Wild West")
    add("Branch Unlock Cowboy 30", "Wild West")
    add("cowboy31", "Wild West")
    add("cowboy32", "Wild West")
    add("Dangerroom Cowboy2 Unlock", "Wild West")
    add("Branch Unlock Cowboy 34", "Wild West")
    add("cowboy35", "Wild West")
    add("cowboy_dangerroom", "Wild West")
    add("cowboy_dangerroom2", "Wild West")
    add("random_cowboy", "Wild West")

    # ── Far Future ──
    add("random_zomboss_future", "Far Future", victory=True)
    add("Laser Bean Unlock", "Far Future")
    add("future2", "Far Future")
    add("Blover Unlock", "Far Future")
    add("Dangerroom Future Unlock", "Far Future")
    add("Branch Unlock Future 5", "Far Future")
    add("Citron Unlock", "Far Future")
    add("Note Future Unlock", "Far Future")
    add("World Key - Far Future", "Far Future")
    add("Empea Unlock", "Far Future")
    add("future10", "Far Future")
    add("future10_1", "Far Future")
    add("future10_2", "Far Future")
    add("future10_3", "Far Future")
    add("future10_4", "Far Future")
    add("Branch Unlock Future 11", "Far Future")
    add("future12", "Far Future")
    add("Holonut Unlock", "Far Future")
    add("future14", "Far Future")
    add("Branch Unlock Future 15", "Far Future")
    add("future16", "Far Future")
    add("Magnifyinggrass Unlock", "Far Future")
    add("future18", "Far Future")
    add("future19", "Far Future")
    add("Upgrade Manual Mowers 1 Unlock", "Far Future")
    add("future21", "Far Future")
    add("Branch Unlock Future 22", "Far Future")
    add("future23", "Far Future")
    add("Powerplant Unlock", "Far Future")
    add("Worldtrophy Future Unlock", "Far Future")
    add("future26", "Far Future")
    add("Branch Unlock Future 27", "Far Future")
    add("future28", "Far Future")
    add("future29", "Far Future")
    add("Branch Unlock Future 30", "Far Future")
    add("future31", "Far Future")
    add("Dangerroom Future2 Unlock", "Far Future")
    add("Dangerroom Future Sunbomb Unlock", "Far Future")
    add("Branch Unlock Future 34", "Far Future")
    add("future35", "Far Future")
    add("future_dangerroom", "Far Future")
    add("future_dangerroom2", "Far Future")
    add("future_dangerroom_sunbomb", "Far Future")
    add("random_future", "Far Future")

    # ── Dark Ages ──
    add("random_zomboss_dark", "Dark Ages", victory=True)
    add("Sunshroom Unlock", "Dark Ages")
    add("Puffshroom Unlock", "Dark Ages")
    add("dark3", "Dark Ages")
    add("Fumeshroom Unlock", "Dark Ages")
    add("dark5", "Dark Ages")
    add("Sunbean Unlock", "Dark Ages")
    add("dark7", "Dark Ages")
    add("Branch Unlock Dark 8", "Dark Ages")
    add("Note Dark Unlock", "Dark Ages")
    add("World Key - Dark Ages", "Dark Ages")
    add("Branch Unlock Dark 11", "Dark Ages")
    add("Dangerroom Dark Unlock", "Dark Ages")
    add("Branch Unlock Dark 13", "Dark Ages")
    add("dark14", "Dark Ages")
    add("Magnetshroom Unlock", "Dark Ages")
    add("dark16", "Dark Ages")
    add("dark17", "Dark Ages")
    add("Branch Unlock Dark 18", "Dark Ages")
    add("dark18_1", "Dark Ages")
    add("dark19", "Dark Ages")
    add("Worldtrophy Dark Unlock", "Dark Ages")
    add("Scaredyshroom Unlock", "Dark Ages")
    add("dark22", "Dark Ages")
    add("Branch Unlock Dark 23", "Dark Ages")
    add("Branch Unlock Dark 24", "Dark Ages")
    add("Branch Unlock Dark 25", "Dark Ages")
    add("Dangerroom Dark2 Unlock", "Dark Ages")
    add("Dangerroom Dark Potion Unlock", "Dark Ages")
    add("dark28", "Dark Ages")
    add("Branch Unlock Dark 29", "Dark Ages")
    add("dark30", "Dark Ages")
    add("dark_dangerroom", "Dark Ages")
    add("dark_dangerroom2", "Dark Ages")
    add("dark_dangerroom_potion", "Dark Ages")
    add("random_dark", "Dark Ages")

    # ── Big Wave Beach ──
    add("random_beach", "Big Wave Beach", victory=True)
    add("Lilypad Unlock", "Big Wave Beach")
    add("beach2", "Big Wave Beach")
    add("beach3", "Big Wave Beach")
    add("Branch Unlock Beach 4", "Big Wave Beach")
    add("beach5", "Big Wave Beach")
    add("Tanglekelp Unlock", "Big Wave Beach")
    add("beach7", "Big Wave Beach")
    add("Branch Unlock Beach 8", "Big Wave Beach")
    add("beach9", "Big Wave Beach")
    add("beach10", "Big Wave Beach")
    add("Bowlingbulb Unlock", "Big Wave Beach")
    add("Branch Unlock Beach 12", "Big Wave Beach")
    add("beach13", "Big Wave Beach")
    add("Branch Unlock Beach 14", "Big Wave Beach")
    add("Note Beach Unlock", "Big Wave Beach")
    add("World Key - Big Wave Beach", "Big Wave Beach")
    add("Branch Unlock Beach 17", "Big Wave Beach")
    add("beach18", "Big Wave Beach")
    add("Guacodile Unlock", "Big Wave Beach")
    add("Dangerroom Beach Unlock", "Big Wave Beach")
    add("beach21", "Big Wave Beach")
    add("Branch Unlock Beach 22", "Big Wave Beach")
    add("beach23", "Big Wave Beach")
    add("Dangerroom Beach Minigame Unlock", "Big Wave Beach")
    add("Branch Unlock Beach 25", "Big Wave Beach")
    add("beach26", "Big Wave Beach")
    add("Banana Unlock", "Big Wave Beach")
    add("beach28", "Big Wave Beach")
    add("beach29", "Big Wave Beach")
    add("Branch Unlock Beach 30", "Big Wave Beach")
    add("Seashroom Unlock", "Big Wave Beach")
    add("Worldtrophy Beach Unlock", "Big Wave Beach")
    add("beach33", "Big Wave Beach")
    add("beach34", "Big Wave Beach")
    add("beach35", "Big Wave Beach")
    add("Dangerroom Beach2 Unlock", "Big Wave Beach")
    add("beach37", "Big Wave Beach")
    add("beach38", "Big Wave Beach")
    add("beach39", "Big Wave Beach")
    add("beach40", "Big Wave Beach")
    add("beach41", "Big Wave Beach")
    add("beach42", "Big Wave Beach")
    add("beach_dangerroom", "Big Wave Beach")
    add("beach_dangerroom2", "Big Wave Beach")
    add("beach_dangerroom_minigame_beach", "Big Wave Beach")
    add("beach_dangerroom_minigame_cowboy", "Big Wave Beach")
    add("beach_dangerroom_minigame_dark", "Big Wave Beach")
    add("beach_dangerroom_minigame_egypt", "Big Wave Beach")
    add("beach_dangerroom_minigame_future", "Big Wave Beach")
    add("beach_dangerroom_minigame_iceage", "Big Wave Beach")
    add("beach_dangerroom_minigame_lostcity", "Big Wave Beach")
    add("beach_dangerroom_minigame_pirate", "Big Wave Beach")

    # ── Frostbite Caves ──
    add("iceage_dangerroom", "Frostbite Caves", victory=True)
    add("Hotpotato Unlock", "Frostbite Caves")
    add("iceage2", "Frostbite Caves")
    add("iceage3", "Frostbite Caves")
    add("Branch Unlock Iceage 4", "Frostbite Caves")
    add("iceage5", "Frostbite Caves")
    add("Pepperpult Unlock", "Frostbite Caves")
    add("iceage7", "Frostbite Caves")
    add("Branch Unlock Iceage 8", "Frostbite Caves")
    add("iceage9", "Frostbite Caves")
    add("iceage10", "Frostbite Caves")
    add("Chardguard Unlock", "Frostbite Caves")
    add("Branch Unlock Iceage 12", "Frostbite Caves")
    add("iceage13", "Frostbite Caves")
    add("Branch Unlock Iceage 14", "Frostbite Caves")
    add("Note Iceage Unlock", "Frostbite Caves")
    add("World Key - Frostbite Caves", "Frostbite Caves")
    add("Branch Unlock Iceage 17", "Frostbite Caves")
    add("iceage18", "Frostbite Caves")
    add("Stunion Unlock", "Frostbite Caves")
    add("Dangerroom Iceage Unlock", "Frostbite Caves")
    add("iceage21", "Frostbite Caves")
    add("Branch Unlock Iceage 22", "Frostbite Caves")
    add("iceage23", "Frostbite Caves")
    add("Branch Unlock Iceage 24", "Frostbite Caves")
    add("iceage24_B", "Frostbite Caves")
    add("iceage25", "Frostbite Caves")
    add("Xshot Unlock", "Frostbite Caves")
    add("iceage27", "Frostbite Caves")
    add("iceage28", "Frostbite Caves")
    add("Branch Unlock Iceage 29", "Frostbite Caves")
    add("Worldtrophy Iceage Unlock", "Frostbite Caves")
    add("Branch Unlock Iceage 31", "Frostbite Caves")
    add("iceage32", "Frostbite Caves")
    add("iceage33", "Frostbite Caves")
    add("Branch Unlock Iceage 34", "Frostbite Caves")
    add("Dangerroom Iceage2 Unlock", "Frostbite Caves")
    add("iceage36", "Frostbite Caves")
    add("iceage37", "Frostbite Caves")
    add("iceage38", "Frostbite Caves")
    add("iceage39", "Frostbite Caves")
    add("iceage40", "Frostbite Caves")
    add("iceage_dangerroom2", "Frostbite Caves")

    # ── Lost City ──
    add("lostcity_dangerroom", "Lost City", victory=True)
    add("Redstinger Unlock", "Lost City")
    add("lostcity2", "Lost City")
    add("lostcity3", "Lost City")
    add("Branch Unlock Lostcity 4", "Lost City")
    add("lostcity5", "Lost City")
    add("Akee Unlock", "Lost City")
    add("lostcity7", "Lost City")
    add("Branch Unlock Lostcity 8", "Lost City")
    add("lostcity9", "Lost City")
    add("Endurian Unlock", "Lost City")
    add("lostcity11", "Lost City")
    add("Branch Unlock Lostcity 12", "Lost City")
    add("lostcity13", "Lost City")
    add("Branch Unlock Lostcity 14", "Lost City")
    add("Note Lostcity Unlock", "Lost City")
    add("World Key - Lost City", "Lost City")
    add("Branch Unlock Lostcity 17", "Lost City")
    add("lostcity18", "Lost City")
    add("Stallia Unlock", "Lost City")
    add("Dangerroom Lostcity Unlock", "Lost City")
    add("lostcity21", "Lost City")
    add("lostcity22", "Lost City")
    add("Branch Unlock Lostcity 23", "Lost City")
    add("lostcity24", "Lost City")
    add("lostcity25", "Lost City")
    add("Goldleaf Unlock", "Lost City")
    add("lostcity27", "Lost City")
    add("Branch Unlock Lostcity 28", "Lost City")
    add("lostcity29", "Lost City")
    add("Branch Unlock Lostcity 30", "Lost City")
    add("lostcity31", "Lost City")
    add("Worldtrophy Lostcity Unlock", "Lost City")
    add("Branch Unlock Lostcity 33", "Lost City")
    add("Branch Unlock Lostcity 34", "Lost City")
    add("Branch Unlock Lostcity 35", "Lost City")
    add("Branch Unlock Lostcity 36", "Lost City")
    add("lostcity37", "Lost City")
    add("Branch Unlock Lostcity 38", "Lost City")
    add("Dangerroom Lostcity2 Unlock", "Lost City")
    add("Branch Unlock Lostcity 40", "Lost City")
    add("Branch Unlock Lostcity 41", "Lost City")
    add("lostcity42", "Lost City")
    add("lostcity_dangerroom2", "Lost City")

    # ── Kongfu Temple ──
    add("kongfu_dangerroom", "Kongfu Temple", victory=True)
    add("Firegourd Unlock", "Kongfu Temple")
    add("kongfu2", "Kongfu Temple")
    add("kongfu3", "Kongfu Temple")
    add("kongfu4", "Kongfu Temple")
    add("kongfu5", "Kongfu Temple")
    add("Snowpea Unlock", "Kongfu Temple")
    add("kongfu7", "Kongfu Temple")
    add("World Key - Kongfu Temple", "Kongfu Temple")
    add("kongfu9", "Kongfu Temple")
    add("Bambooshoot Unlock", "Kongfu Temple")
    add("kongfu11", "Kongfu Temple")
    add("kongfu12", "Kongfu Temple")
    add("Turnip Unlock", "Kongfu Temple")
    add("Dangerroom Kongfu Unlock", "Kongfu Temple")
    add("kongfu15", "Kongfu Temple")
    add("kongfu16", "Kongfu Temple")
    add("kongfu17", "Kongfu Temple")
    add("kongfu18", "Kongfu Temple")
    add("Peach Unlock", "Kongfu Temple")
    add("kongfu20", "Kongfu Temple")
    add("kongfu21", "Kongfu Temple")
    add("kongfu22", "Kongfu Temple")
    add("kongfu23", "Kongfu Temple")
    add("kongfu24", "Kongfu Temple")
    add("kongfu25", "Kongfu Temple")
    add("kongfu26", "Kongfu Temple")
    add("kongfu27", "Kongfu Temple")
    add("kongfu28", "Kongfu Temple")
    add("Lychee Unlock", "Kongfu Temple")
    add("Dangerroom Kongfu2 Unlock", "Kongfu Temple")
    add("kongfu31", "Kongfu Temple")
    add("kongfu32", "Kongfu Temple")
    add("kongfu33", "Kongfu Temple")
    add("Solarsage Unlock", "Kongfu Temple")
    add("kongfu35", "Kongfu Temple")
    add("kongfu36", "Kongfu Temple")
    add("kongfu37", "Kongfu Temple")
    add("kongfu38", "Kongfu Temple")
    add("kongfu39", "Kongfu Temple")
    add("kongfu40", "Kongfu Temple")
    add("kongfu41", "Kongfu Temple")
    add("kongfu42", "Kongfu Temple")
    add("kongfu43", "Kongfu Temple")
    add("kongfu44", "Kongfu Temple")
    add("kongfu45", "Kongfu Temple")
    add("Cantaloupe Unlock", "Kongfu Temple")
    add("Dangerroom Kongfu3 Unlock", "Kongfu Temple")
    add("kongfu48", "Kongfu Temple")
    add("kongfu_dangerroom2", "Kongfu Temple")
    add("kongfu_dangerroom3", "Kongfu Temple")
    add("kongfu_dangerroom4", "Kongfu Temple")

    # ── Neon Mixtape Tour ──
    add("eighties_dangerroom", "Neon Mixtape Tour", victory=True)
    add("Phatbeet Unlock", "Neon Mixtape Tour")
    add("eighties2", "Neon Mixtape Tour")
    add("eighties3", "Neon Mixtape Tour")
    add("eighties4", "Neon Mixtape Tour")
    add("Celerystalker Unlock", "Neon Mixtape Tour")
    add("eighties6", "Neon Mixtape Tour")
    add("eighties7", "Neon Mixtape Tour")
    add("eighties8", "Neon Mixtape Tour")
    add("Thymewarp Unlock", "Neon Mixtape Tour")
    add("eighties10", "Neon Mixtape Tour")
    add("eighties11", "Neon Mixtape Tour")
    add("Branch Unlock Eighties 12", "Neon Mixtape Tour")
    add("eighties13", "Neon Mixtape Tour")
    add("Branch Unlock Eighties 14", "Neon Mixtape Tour")
    add("eighties15", "Neon Mixtape Tour")
    add("World Key - Neon Mixtape Tour", "Neon Mixtape Tour")
    add("Garlic Unlock", "Neon Mixtape Tour")
    add("eighties18", "Neon Mixtape Tour")
    add("eighties19", "Neon Mixtape Tour")
    add("Dangerroom Eighties Unlock", "Neon Mixtape Tour")
    add("Sporeshroom Unlock", "Neon Mixtape Tour")
    add("eighties22", "Neon Mixtape Tour")
    add("eighties23", "Neon Mixtape Tour")
    add("Branch Unlock Eighties 24", "Neon Mixtape Tour")
    add("eighties25", "Neon Mixtape Tour")
    add("Intensivecarrot Unlock", "Neon Mixtape Tour")
    add("eighties27", "Neon Mixtape Tour")
    add("eighties28", "Neon Mixtape Tour")
    add("Branch Unlock Eighties 29", "Neon Mixtape Tour")
    add("eighties30", "Neon Mixtape Tour")
    add("eighties31", "Neon Mixtape Tour")
    add("Worldtrophy Eighties Unlock", "Neon Mixtape Tour")

    # ── Jurassic Marsh ──
    add("dino_dangerroom", "Jurassic Marsh", victory=True)
    add("Primalpeashooter Unlock", "Jurassic Marsh")
    add("dino2", "Jurassic Marsh")
    add("dino3", "Jurassic Marsh")
    add("Primalwallnut Unlock", "Jurassic Marsh")
    add("dino5", "Jurassic Marsh")
    add("Branch Unlock Dino 6", "Jurassic Marsh")
    add("Branch Unlock Dino 7", "Jurassic Marsh")
    add("Perfumeshroom Unlock", "Jurassic Marsh")
    add("dino9", "Jurassic Marsh")
    add("dino10", "Jurassic Marsh")
    add("dino11", "Jurassic Marsh")
    add("Branch Unlock Dino 12", "Jurassic Marsh")
    add("dino13", "Jurassic Marsh")
    add("Branch Unlock Dino 14", "Jurassic Marsh")
    add("Note Dino Unlock", "Jurassic Marsh")
    add("World Key - Jurassic Marsh", "Jurassic Marsh")
    add("Primalsunflower Unlock", "Jurassic Marsh")
    add("dino18", "Jurassic Marsh")
    add("dino19", "Jurassic Marsh")
    add("Dangerroom Dino Unlock", "Jurassic Marsh")
    add("dino21", "Jurassic Marsh")
    add("dino22", "Jurassic Marsh")
    add("Primalpotatomine Unlock", "Jurassic Marsh")
    add("Branch Unlock Dino 24", "Jurassic Marsh")
    add("dino25", "Jurassic Marsh")
    add("dino26", "Jurassic Marsh")
    add("dino27", "Jurassic Marsh")
    add("dino28", "Jurassic Marsh")
    add("Branch Unlock Dino 29", "Jurassic Marsh")
    add("dino30", "Jurassic Marsh")
    add("dino31", "Jurassic Marsh")
    add("Worldtrophy Dino Unlock", "Jurassic Marsh")
    add("Branch Unlock Dino 33", "Jurassic Marsh")
    add("dino34", "Jurassic Marsh")
    add("dino35", "Jurassic Marsh")
    add("Dangerroom Dino2 Unlock", "Jurassic Marsh")
    add("Branch Unlock Dino 37", "Jurassic Marsh")
    add("dino38", "Jurassic Marsh")
    add("dino39", "Jurassic Marsh")
    add("dino40", "Jurassic Marsh")
    add("Branch Unlock Dino 41", "Jurassic Marsh")
    add("dino42", "Jurassic Marsh")
    add("dino_dangerroom2", "Jurassic Marsh")

    # ── Modern Day ──
    add("modern_zomboss_01_egypt", "Modern Day", victory=True)
    add("Moonflower Unlock", "Modern Day")
    add("modern2", "Modern Day")
    add("modern3", "Modern Day")
    add("Nightshade Unlock", "Modern Day")
    add("modern5", "Modern Day")
    add("Branch Unlock Modern 6", "Modern Day")
    add("Branch Unlock Modern 7", "Modern Day")
    add("modern8", "Modern Day")
    add("modern9", "Modern Day")
    add("Shadowshroom Unlock", "Modern Day")
    add("modern11", "Modern Day")
    add("Branch Unlock Modern 12", "Modern Day")
    add("modern13", "Modern Day")
    add("Branch Unlock Modern 14", "Modern Day")
    add("Note Modern Unlock", "Modern Day")
    add("World Key - Modern Day", "Modern Day")
    add("Dusklobber Unlock", "Modern Day")
    add("modern18", "Modern Day")
    add("modern19", "Modern Day")
    add("Dangerroom Modern Unlock", "Modern Day")
    add("modern21", "Modern Day")
    add("modern22", "Modern Day")
    add("Grimrose Unlock", "Modern Day")
    add("modern24", "Modern Day")
    add("Branch Unlock Modern 25", "Modern Day")
    add("modern26", "Modern Day")
    add("modern27", "Modern Day")
    add("modern28", "Modern Day")
    add("Branch Unlock Modern 29", "Modern Day")
    add("modern30", "Modern Day")
    add("modern31", "Modern Day")
    add("modern35", "Modern Day")
    add("Branch Unlock Modern 36", "Modern Day")
    add("modern37", "Modern Day")
    add("modern38", "Modern Day")
    add("Branch Unlock Modern 39", "Modern Day")
    add("Dangerroom Modern2 Unlock", "Modern Day")
    add("modern41", "Modern Day")
    add("modern42", "Modern Day")
    add("Branch Unlock Modern 43", "Modern Day")
    add("modern44", "Modern Day")
    add("modern_dangerroom", "Modern Day")
    add("modern_dangerroom2", "Modern Day")
    add("modern_zomboss_02_pirate", "Modern Day")
    add("modern_zomboss_03_cowboy", "Modern Day")
    add("modern_zomboss_04_future", "Modern Day")
    add("modern_zomboss_05_dark", "Modern Day")
    add("modern_zomboss_06_beach", "Modern Day")
    add("modern_zomboss_07_iceage", "Modern Day")
    add("modern_zomboss_08_lostcity", "Modern Day")
    add("modern_zomboss_09_eighties", "Modern Day")
    add("modern_zomboss_10_dino", "Modern Day")

    # ── Aerial Fortress ──
    add("Skyshooter Unlock", "Aerial Fortress")
    add("sky2", "Aerial Fortress")
    add("Upgrade Sky Shield Unlock", "Aerial Fortress")
    add("sky4", "Aerial Fortress")
    add("sky5", "Aerial Fortress")
    add("Pineapple Unlock", "Aerial Fortress")
    add("sky7", "Aerial Fortress")
    add("Moonbean Unlock", "Aerial Fortress")
    add("sky9", "Aerial Fortress")
    add("sky10", "Aerial Fortress")
    add("Anthurium Unlock", "Aerial Fortress")
    add("sky12", "Aerial Fortress")
    add("sky13", "Aerial Fortress")
    add("sky14", "Aerial Fortress")
    add("sky15", "Aerial Fortress")
    add("World Key - Aerial Fortress", "Aerial Fortress")

    # ── Side Paths (always accessible from Tutorial) ──
    add("aloe0", "Aloe Sidepath"); add("aloe1", "Aloe Sidepath"); add("aloe2", "Aloe Sidepath")
    add("aloe3", "Aloe Sidepath"); add("aloe4", "Aloe Sidepath"); add("Aloe Unlock", "Aloe Sidepath")

    add("appease1_0", "Appease Sidepath"); add("appease1_1", "Appease Sidepath")
    add("appease1_2", "Appease Sidepath"); add("Dandelion Unlock", "Appease Sidepath")
    add("appease1_4", "Appease Sidepath"); add("appease1_5", "Appease Sidepath")
    add("Pvine Unlock", "Appease Sidepath"); add("appease2_0", "Appease Sidepath")
    add("appease2_1", "Appease Sidepath"); add("appease2_2", "Appease Sidepath")
    add("appease2_3", "Appease Sidepath"); add("Gatling Unlock", "Appease Sidepath")
    add("Megagatling Unlock", "Appease Sidepath"); add("Torchwood Unlock", "Appease Sidepath")

    add("atombomb0", "Atombomb Sidepath"); add("atombomb1", "Atombomb Sidepath")
    add("atombomb2", "Atombomb Sidepath"); add("atombomb3", "Atombomb Sidepath")
    add("atombomb4", "Atombomb Sidepath"); add("Atombomb Seedling Unlock", "Atombomb Sidepath")

    add("bank_theft1", "Bank Sidepath"); add("bank_theft2", "Bank Sidepath")
    add("bank_theft3", "Bank Sidepath"); add("bank_theft4", "Bank Sidepath")
    add("bank_theft5", "Bank Sidepath")

    add("bloominghearts0", "Bloominghearts Sidepath"); add("bloominghearts1", "Bloominghearts Sidepath")
    add("bloominghearts2", "Bloominghearts Sidepath"); add("bloominghearts3", "Bloominghearts Sidepath")
    add("bloominghearts4", "Bloominghearts Sidepath"); add("Bloominghearts Unlock", "Bloominghearts Sidepath")

    add("buttercup0", "Buttercup Sidepath"); add("buttercup1", "Buttercup Sidepath")
    add("buttercup2", "Buttercup Sidepath"); add("buttercup3", "Buttercup Sidepath")
    add("buttercup4", "Buttercup Sidepath"); add("Buttercup Unlock", "Buttercup Sidepath")

    add("conceal0", "Conceal Sidepath"); add("conceal1", "Conceal Sidepath")
    add("conceal2", "Conceal Sidepath"); add("conceal3", "Conceal Sidepath")
    add("conceal4", "Conceal Sidepath"); add("Gloomvine Unlock", "Conceal Sidepath")
    add("conceal6", "Conceal Sidepath"); add("Murkadamia Unlock", "Conceal Sidepath")
    add("conceal8", "Conceal Sidepath"); add("Shadowpeashooter Unlock", "Conceal Sidepath")
    add("conceal10", "Conceal Sidepath"); add("Noctarine Unlock", "Conceal Sidepath")

    add("doomshroom0", "Doomshroom Sidepath"); add("doomshroom1", "Doomshroom Sidepath")
    add("doomshroom2", "Doomshroom Sidepath"); add("doomshroom3", "Doomshroom Sidepath")
    add("doomshroom4", "Doomshroom Sidepath"); add("Doomshroom Unlock", "Doomshroom Sidepath")

    add("electriccurrant0", "Electriccurrant Sidepath"); add("electriccurrant1", "Electriccurrant Sidepath")
    add("electriccurrant2", "Electriccurrant Sidepath"); add("electriccurrant3", "Electriccurrant Sidepath")
    add("electriccurrant4", "Electriccurrant Sidepath"); add("Electriccurrant Unlock", "Electriccurrant Sidepath")

    add("enlighten0", "Enlighten Sidepath"); add("enlighten1", "Enlighten Sidepath")
    add("enlighten2", "Enlighten Sidepath"); add("enlighten3", "Enlighten Sidepath")
    add("enlighten4", "Enlighten Sidepath"); add("enlighten5", "Enlighten Sidepath")
    add("enlighten6", "Enlighten Sidepath"); add("Shinevine Unlock", "Enlighten Sidepath")

    add("ghostpepper0", "Ghostpepper Sidepath"); add("ghostpepper1", "Ghostpepper Sidepath")
    add("ghostpepper2", "Ghostpepper Sidepath"); add("Ghostpepper Unlock", "Ghostpepper Sidepath")

    add("gloomshroom0", "Gloomshroom Sidepath"); add("gloomshroom1", "Gloomshroom Sidepath")
    add("gloomshroom2", "Gloomshroom Sidepath"); add("gloomshroom3", "Gloomshroom Sidepath")
    add("gloomshroom4", "Gloomshroom Sidepath"); add("gloomshroom5", "Gloomshroom Sidepath")
    add("gloomshroom6", "Gloomshroom Sidepath"); add("Gloomshroom Unlock", "Gloomshroom Sidepath")

    add("goldbloom0", "Goldbloom Sidepath"); add("goldbloom1", "Goldbloom Sidepath")
    add("goldbloom2", "Goldbloom Sidepath"); add("Goldbloom Unlock", "Goldbloom Sidepath")

    add("hotdate1", "Hotdate Sidepath"); add("hotdate2", "Hotdate Sidepath")
    add("Hotdate Unlock", "Hotdate Sidepath")

    add("icebloom0", "Icebloom Sidepath"); add("icebloom1", "Icebloom Sidepath")
    add("icebloom2", "Icebloom Sidepath"); add("icebloom3", "Icebloom Sidepath")
    add("icebloom4", "Icebloom Sidepath"); add("Icebloom Unlock", "Icebloom Sidepath")

    add("iceshroom0", "Iceshroom Sidepath"); add("iceshroom1", "Iceshroom Sidepath")
    add("iceshroom2", "Iceshroom Sidepath"); add("iceshroom3", "Iceshroom Sidepath")
    add("iceshroom4", "Iceshroom Sidepath"); add("Glaciershroom Unlock", "Iceshroom Sidepath")

    add("meteorflower0", "Meteorflower Sidepath"); add("meteorflower1", "Meteorflower Sidepath")
    add("meteorflower2", "Meteorflower Sidepath"); add("Meteorflower Unlock", "Meteorflower Sidepath")

    add("parsnip0", "Parsnip Sidepath"); add("parsnip1", "Parsnip Sidepath")
    add("parsnip2", "Parsnip Sidepath"); add("parsnip3", "Parsnip Sidepath")
    add("parsnip4", "Parsnip Sidepath"); add("Parsnip Unlock", "Parsnip Sidepath")

    add("plantern0", "Plantern Sidepath"); add("plantern1", "Plantern Sidepath")
    add("plantern2", "Plantern Sidepath"); add("plantern3", "Plantern Sidepath")
    add("plantern4", "Plantern Sidepath"); add("Plantern Unlock", "Plantern Sidepath")

    add("reinforce0", "Reinforce Sidepath"); add("reinforce1", "Reinforce Sidepath")
    add("reinforce2", "Reinforce Sidepath"); add("reinforce3", "Reinforce Sidepath")
    add("reinforce4", "Reinforce Sidepath"); add("reinforce5", "Reinforce Sidepath")
    add("reinforce6", "Reinforce Sidepath"); add("Pumpkin Unlock", "Reinforce Sidepath")
    add("reinforce8", "Reinforce Sidepath"); add("Hollyknight Unlock", "Reinforce Sidepath")
    add("reinforce10", "Reinforce Sidepath"); add("Gumnut Unlock", "Reinforce Sidepath")

    add("sapfling0", "Sapfling Sidepath"); add("sapfling1", "Sapfling Sidepath")
    add("sapfling2", "Sapfling Sidepath"); add("sapfling3", "Sapfling Sidepath")
    add("sapfling4", "Sapfling Sidepath"); add("sapfling5", "Sapfling Sidepath")
    add("sapfling6", "Sapfling Sidepath"); add("Sapfling Unlock", "Sapfling Sidepath")

    add("seashooter0", "Seashooter Sidepath"); add("seashooter1", "Seashooter Sidepath")
    add("seashooter2", "Seashooter Sidepath"); add("Seashooter Unlock", "Seashooter Sidepath")

    add("shootingstarfruit1", "Shootingstarfruit Sidepath")
    add("shootingstarfruit2", "Shootingstarfruit Sidepath")
    add("shootingstarfruit3", "Shootingstarfruit Sidepath")

    add("solartomato0", "Solartomato Sidepath"); add("solartomato1", "Solartomato Sidepath")
    add("solartomato2", "Solartomato Sidepath"); add("solartomato3", "Solartomato Sidepath")
    add("solartomato4", "Solartomato Sidepath"); add("Solartomato Unlock", "Solartomato Sidepath")

    add("squash0", "Squash Sidepath"); add("squash1", "Squash Sidepath")
    add("squash2", "Squash Sidepath"); add("Squash Unlock", "Squash Sidepath")

    add("strawburst0", "Strawburst Sidepath"); add("strawburst1", "Strawburst Sidepath")
    add("strawburst2", "Strawburst Sidepath"); add("strawburst3", "Strawburst Sidepath")
    add("strawburst4", "Strawburst Sidepath"); add("strawburst5", "Strawburst Sidepath")
    add("strawburst6", "Strawburst Sidepath"); add("Strawburst Unlock", "Strawburst Sidepath")

    add("sweetpotato0", "Sweetpotato Sidepath"); add("sweetpotato1", "Sweetpotato Sidepath")
    add("sweetpotato2", "Sweetpotato Sidepath"); add("sweetpotato3", "Sweetpotato Sidepath")
    add("sweetpotato4", "Sweetpotato Sidepath"); add("Sweetpotato Unlock", "Sweetpotato Sidepath")

    add("umbrellaleaf0", "Umbrellaleaf Sidepath"); add("umbrellaleaf1", "Umbrellaleaf Sidepath")
    add("umbrellaleaf2", "Umbrellaleaf Sidepath"); add("umbrellaleaf3", "Umbrellaleaf Sidepath")
    add("umbrellaleaf4", "Umbrellaleaf Sidepath"); add("umbrellaleaf5", "Umbrellaleaf Sidepath")
    add("umbrellaleaf6", "Umbrellaleaf Sidepath"); add("umbrellaleaf7", "Umbrellaleaf Sidepath")
    add("umbrellaleaf8", "Umbrellaleaf Sidepath"); add("umbrellaleaf9", "Umbrellaleaf Sidepath")
    add("umbrellaleaf10", "Umbrellaleaf Sidepath"); add("Umbrellaleaf Unlock", "Umbrellaleaf Sidepath")

    add("vamporcini0", "Vamporcini Sidepath"); add("vamporcini1", "Vamporcini Sidepath")
    add("vamporcini2", "Vamporcini Sidepath"); add("Vamporcini Unlock", "Vamporcini Sidepath")

    add("epic_beghouled1", "Epic Beghouled Sidepath")
    add("epic_beghouled2", "Epic Beghouled Sidepath")
    add("epic_beghouled3", "Epic Beghouled Sidepath")
    add("epic_beghouled4", "Epic Beghouled Sidepath")
    add("epic_beghouled5", "Epic Beghouled Sidepath")

    add("floawerpot1", "Floawerpot Sidepath")
    add("floawerpot2", "Floawerpot Sidepath")
    add("floawerpot3", "Floawerpot Sidepath")

    add("mixed_dangerroom2", "Mixed Sidepath")

    add("reinforcemint_try1", "Reinforcemint Sidepath")
    add("reinforcemint_try2", "Reinforcemint Sidepath")
    add("reinforcemint_try3", "Reinforcemint Sidepath")

    add("rhythm1", "Rhythm Sidepath")

    add("sandbox", "Sandbox Sidepath")
    add("sandbox_green", "Sandbox Sidepath")
    add("sandbox_modern", "Sandbox Sidepath")
    add("sandbox_modern_night", "Sandbox Sidepath")
    add("sandbox_sky", "Sandbox Sidepath")

    # ── Shop (only created when shopsanity is on) ──
    # Appended last so every pre-existing location keeps the ID it already
    # had. These stay in the static location_name_to_id map either way --
    # AP requires that mapping to be constant across option combinations --
    # but the Location objects are only built when the option is enabled.
    for commodity in SHOP_COMMODITIES:
        add(shop_location_name(commodity), SHOP_REGION, shop=True)

    return locs


ALL_LOCATIONS = _make_locs()
LOC_NAME_TO_DATA: Dict[str, PvZ2LocationData] = {l.name: l for l in ALL_LOCATIONS}
LOC_NAME_TO_ID:   Dict[str, int]              = {l.name: l.code for l in ALL_LOCATIONS}
VICTORY_LOC_NAMES = [l.name for l in ALL_LOCATIONS if l.is_victory]

# dict.fromkeys, not a set: set iteration order for strings varies between
# processes (hash randomization), which would make the order regions are
# appended to multiworld.regions differ run to run for one seed. AP sorts
# locations and items before shuffling them, so this does not currently move
# a seed's fill -- but nothing guarantees every consumer sorts, and first-seen
# order costs nothing.
ALL_REGIONS = list(dict.fromkeys(l.region for l in ALL_LOCATIONS))


# Every region a location can be in has to be either part of a world (and so
# switchable by the world-selection options) or one of the always-built ones.
# A region in neither would be silently dropped from the seed by the filter in
# active_locations(), taking its locations with it.
_unclassified_regions = (set(ALL_REGIONS) - ALL_WORLD_REGIONS
                         - set(SIDE_PATH_REGIONS) - {"Tutorial", SHOP_REGION})
if _unclassified_regions:
    raise ValueError("regions belong to no world and are not always-built: "
                     f"{sorted(_unclassified_regions)}")


def active_locations(shopsanity: bool,
                     enabled_regions: Set[str]) -> List[PvZ2LocationData]:
    """Locations actually built for a slot with these settings.

    Shop and disabled-world locations stay in the static location_name_to_id
    map regardless (AP requires that to be constant), so they must be filtered
    here rather than out of ALL_LOCATIONS -- and the item pool has to size off
    this, not len(ALL_LOCATIONS), or a slot ends up with more items than it
    has places to put them.

    enabled_regions only decides world regions. Tutorial, the side paths and
    Shop are not part of any world and are always kept.
    """
    return [l for l in ALL_LOCATIONS
            if (shopsanity or not l.is_shop)
            and (l.region not in ALL_WORLD_REGIONS or l.region in enabled_regions)]


# World Trophy locations — the mid-world milestone check in each world.
# Kongfu Temple has no world trophy in the game data and is excluded.
# Modern Day and Aerial Fortress are excluded (goal world / post-unlock).
WORLD_TROPHY_LOCS = [
    "Worldtrophy Egypt Unlock",    # egypt25
    "Worldtrophy Pirate Unlock",   # pirate25
    "Worldtrophy Cowboy Unlock",   # cowboy25
    "Worldtrophy Future Unlock",   # future25
    "Worldtrophy Dark Unlock",     # dark20
    "Worldtrophy Beach Unlock",    # beach32
    "Worldtrophy Iceage Unlock",   # iceage30
    "Worldtrophy Lostcity Unlock", # lostcity32
    "Worldtrophy Eighties Unlock", # eighties32
    "Worldtrophy Dino Unlock",     # dino32
]  # 10 total (Kongfu excluded — no trophy in game data)

# World Completion locations — the final regular level of each world.
# Modern Day and Aerial Fortress are excluded. Neon Mixtape Tour has no
# separate final-level location -- it's shorter than the other worlds and
# its trophy check (eighties32) is also its last level, per the client's
# level mapping (build_pvzge_ap.py's LOC_LEVELS), so it reuses the same
# location name as WORLD_TROPHY_LOCS instead of a distinct "eighties32" name
# that was never added to _make_locs().
WORLD_COMPLETION_LOCS = [
    "egypt35",    # Ancient Egypt
    "pirate35",   # Pirate Seas
    "cowboy35",   # Wild West
    "future35",   # Far Future
    "dark30",     # Dark Ages
    "beach42",    # Big Wave Beach
    "iceage40",   # Frostbite Caves
    "lostcity42", # Lost City
    "kongfu48",   # Kongfu Temple
    "Worldtrophy Eighties Unlock", # Neon Mixtape Tour (eighties32; also its trophy)
    "dino42",     # Jurassic Marsh
]  # 11 total

# World Key locations — the "World Key - X" check present in every world.
# Not necessarily on the same stage per world, and not forced to contain
# that world's own key item (fill is unconstrained). Modern Day and Aerial
# Fortress are excluded (goal world / post-unlock), same set as WORLD_COMPLETION_LOCS.
WORLD_KEY_LOCS = [
    "World Key - Ancient Egypt",
    "World Key - Pirate Seas",
    "World Key - Wild West",
    "World Key - Far Future",
    "World Key - Dark Ages",
    "World Key - Big Wave Beach",
    "World Key - Frostbite Caves",
    "World Key - Lost City",
    "World Key - Kongfu Temple",
    "World Key - Neon Mixtape Tour",
    "World Key - Jurassic Marsh",
]  # 11 total


def goal_locations_for(goal_type: int,
                       enabled_regions: Optional[Set[str]] = None) -> List[str]:
    """The goal locations for this goal type that this slot actually builds.

    enabled_regions drops the goals of worlds the seed left out. Their
    locations are never created, so rules.py would raise looking them up --
    and a goal nobody can reach would lock Modern Day for good. Dropping them
    is what shrinks worlds_required to fit: the caller clamps against the
    length of this list.
    """
    if goal_type == GoalType.option_world_trophies:
        locs = WORLD_TROPHY_LOCS
    elif goal_type == GoalType.option_world_keys:
        locs = WORLD_KEY_LOCS
    else:
        locs = WORLD_COMPLETION_LOCS
    # Also drops names with no matching location at all, so a stale name here
    # just shrinks the goal pool rather than raising during generation.
    return [n for n in locs
            if n in LOC_NAME_TO_DATA
            and (enabled_regions is None
                 or LOC_NAME_TO_DATA[n].region in enabled_regions)]


# How far into Modern Day the run has to go, keyed by ModernDayVictory.
# Modern Day's real order is modern1..modern31, then the ten Zomboss fights,
# then modern35..modern44 -- which is why there is no modern32/33/34 to point
# at: those slots are the Zomboss block.
MODERN_DAY_VICTORY_LOCS = {
    0: "World Key - Modern Day",      # modern16
    1: "modern_zomboss_01_egypt",     # the Zomboss, slot ~33
    2: "modern44",                    # final Modern Day level
}


# ── Location name groups ──────────────────────────────────────────────────────
# Surfaced to players through !hint and to trackers. Built from the same data
# the regions are, so a location cannot end up in the wrong group or be left
# out of one. Groups are computed over ALL_LOCATIONS rather than the active
# set because, like location_name_to_id, AP expects them to be constant across
# option combinations.

def _group_by_region() -> Dict[str, Set[str]]:
    groups: Dict[str, Set[str]] = {}
    for loc in ALL_LOCATIONS:
        groups.setdefault(loc.region, set()).add(loc.name)
    return groups


LOC_NAME_GROUPS: Dict[str, Set[str]] = _group_by_region()

LOC_NAME_GROUPS.update({
    # The three goal sets, so a player can hint the whole Modern Day
    # requirement in one command whatever their goal_type is.
    "World Trophies":    set(WORLD_TROPHY_LOCS),
    "World Completions": set(WORLD_COMPLETION_LOCS),
    # Named "Levels" to stay distinct from the "World Keys" *item* group.
    "World Key Levels":  set(WORLD_KEY_LOCS),
    # Each world's final boss, including the ten Modern Day rematches.
    "Zomboss Fights":    {l.name for l in ALL_LOCATIONS if l.is_victory},
    "Side Paths":        {l.name for l in ALL_LOCATIONS
                          if l.region in SIDE_PATH_REGIONS},
    "Danger Rooms":      {l.name for l in ALL_LOCATIONS
                          if "dangerroom" in l.name.lower()},
    "Upgrades":          {l.name for l in ALL_LOCATIONS
                          if l.name.startswith("Upgrade ")},
})

# A group sharing a name with a location makes !hint ambiguous, and AP has no
# way to tell the player which one it resolved to.
_group_name_clashes = set(LOC_NAME_GROUPS) & set(LOC_NAME_TO_ID)
if _group_name_clashes:
    raise ValueError("location group names collide with location names: "
                     f"{sorted(_group_name_clashes)}")
