"""
PvZ2 Gardendless — location definitions and goal/victory location lookups.
"""

import dataclasses
from typing import Dict, List, Optional, Set

from BaseClasses import Location

from .constants import (
    ALL_WORLD_REGIONS, BASE_ID, DANGER_ROOM_LOCATIONS, GAME_NAME,
    SHOP_COMMODITIES, SHOP_EXTRA_COMMODITIES, SHOP_LEGACY_COMMODITIES,
    SHOP_REGION, SHOP_UNLOCK, SIDE_PATH_REGIONS,
    SIDE_PATH_WORLD, UNREACHABLE_LOCATIONS, WORLD_REGIONS,
    shop_location_name,
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
    add("tutorial1", "Tutorial")
    add("tutorial2", "Tutorial")
    add("tutorial3", "Tutorial")
    add("tutorial4", "Tutorial")

    # ── Ancient Egypt ──
    # Ungated: egypt1-5 are the levels a seed is guaranteed to be able to play
    # with nothing but the free starting plant, so they are what sphere 1 is
    # made of. Everything from egypt6 on sits behind the sun producer gate --
    # see rules.py and EGYPT_STRETCH_PLANTS.
    add("random_zomboss_egypt", "Ancient Egypt", victory=True)
    add("egypt1", "Ancient Egypt")
    add("egypt2", "Ancient Egypt")
    add("egypt3", "Ancient Egypt")
    add("egypt4", "Ancient Egypt")
    add("egypt5", "Ancient Egypt")
    # egypt6-9. The sun requirement has moved twice: it began at egypt10, which
    # left nine levels reachable in logic on falling sun alone; it was pulled
    # back to egypt3 (2026-08-12); and it now starts at egypt6, which is where
    # the game itself stops carrying a player who brought no sun. Every level
    # here uses SelectionMethod "chooser", so the player brings their own
    # plants and the client's plant guard blocks anything Archipelago has not
    # sent -- there is no seed bank handing out a Sunflower to fall back on.
    add("egypt6", "Ancient Egypt Mid1")
    add("egypt7", "Ancient Egypt Mid1")
    add("egypt8", "Ancient Egypt Mid1")
    add("egypt9", "Ancient Egypt Mid1")
    add("egypt10", "Ancient Egypt Mid1")
    add("egypt11", "Ancient Egypt Mid1")
    add("egypt12", "Ancient Egypt Mid1")
    add("egypt13", "Ancient Egypt Mid1")
    add("egypt14", "Ancient Egypt Mid1")
    add("egypt15", "Ancient Egypt Mid1")
    add("egypt16", "Ancient Egypt Mid1")
    add("egypt17", "Ancient Egypt Mid1")
    add("egypt18", "Ancient Egypt Mid1")
    add("egypt19", "Ancient Egypt Mid1")
    add("egypt20", "Ancient Egypt Mid2")
    add("egypt20_1", "Ancient Egypt Mid2")
    add("egypt21", "Ancient Egypt Mid2")
    add("egypt21_1", "Ancient Egypt Mid2")
    add("egypt22", "Ancient Egypt Mid2")
    add("egypt22_1", "Ancient Egypt Mid2")
    add("egypt23", "Ancient Egypt Mid2")
    add("egypt24", "Ancient Egypt Mid2")
    add("egypt24_1", "Ancient Egypt Mid2")
    add("egypt25", "Ancient Egypt Mid2")
    add("egypt26", "Ancient Egypt Mid2")
    add("egypt27", "Ancient Egypt Mid2")
    add("egypt28", "Ancient Egypt Mid2")
    add("egypt29", "Ancient Egypt Mid2")
    add("egypt30", "Ancient Egypt Late")
    add("egypt31", "Ancient Egypt Late")
    add("egypt32", "Ancient Egypt Late")
    add("egypt33", "Ancient Egypt Late")
    add("egypt34", "Ancient Egypt Late")
    add("egypt35", "Ancient Egypt Late")
    add("egypt_dangerroom", "Ancient Egypt Late")
    add("egypt_dangerroom2", "Ancient Egypt Late")
    add("egypt_dangerroom_minigame", "Ancient Egypt Late")
    add("random_egypt", "Ancient Egypt Late")

    # ── Pirate Seas ──
    add("random_zomboss_pirate", "Pirate Seas", victory=True)
    add("pirate1", "Pirate Seas")
    add("pirate2", "Pirate Seas")
    add("pirate3", "Pirate Seas")
    add("pirate4", "Pirate Seas")
    add("pirate5", "Pirate Seas")
    add("pirate6", "Pirate Seas")
    add("pirate7", "Pirate Seas")
    add("pirate8", "Pirate Seas")
    add("pirate9", "Pirate Seas")
    add("pirate10", "Pirate Seas")
    add("pirate11", "Pirate Seas")
    add("pirate12", "Pirate Seas")
    add("pirate13", "Pirate Seas")
    add("pirate14", "Pirate Seas")
    add("pirate15", "Pirate Seas")
    add("pirate16", "Pirate Seas")
    add("pirate17", "Pirate Seas")
    add("pirate18", "Pirate Seas")
    add("pirate18_1", "Pirate Seas")
    add("pirate19", "Pirate Seas")
    add("pirate20", "Pirate Seas")
    add("pirate20_1", "Pirate Seas")
    add("pirate21", "Pirate Seas")
    add("pirate22", "Pirate Seas")
    add("pirate22_1", "Pirate Seas")
    add("pirate23", "Pirate Seas")
    add("pirate23_1", "Pirate Seas")
    add("pirate24", "Pirate Seas")
    add("pirate24_1", "Pirate Seas")
    add("pirate25", "Pirate Seas")
    add("pirate26", "Pirate Seas")
    add("pirate27", "Pirate Seas")
    add("pirate28", "Pirate Seas")
    add("pirate29", "Pirate Seas")
    add("pirate30", "Pirate Seas")
    add("pirate31", "Pirate Seas")
    add("pirate32", "Pirate Seas")
    add("pirate33", "Pirate Seas")
    add("pirate34", "Pirate Seas")
    add("pirate35", "Pirate Seas")
    add("pirate_dangerroom", "Pirate Seas")
    add("pirate_dangerroom2", "Pirate Seas")
    add("random_pirate", "Pirate Seas")

    # ── Wild West ──
    add("random_zomboss_cowboy", "Wild West", victory=True)
    add("cowboy1", "Wild West")
    add("cowboy2", "Wild West")
    add("cowboy3", "Wild West")
    add("cowboy4", "Wild West")
    add("cowboy5", "Wild West")
    add("cowboy6", "Wild West")
    add("cowboy7", "Wild West")
    add("cowboy8", "Wild West")
    add("cowboy9", "Wild West")
    add("cowboy10", "Wild West")
    add("cowboy11", "Wild West")
    add("cowboy12", "Wild West")
    add("cowboy12_1", "Wild West")
    add("cowboy13", "Wild West")
    add("cowboy14", "Wild West")
    add("cowboy15", "Wild West")
    add("cowboy16", "Wild West")
    add("cowboy17", "Wild West")
    add("cowboy18", "Wild West")
    add("cowboy18_1", "Wild West")
    add("cowboy19", "Wild West")
    add("cowboy20", "Wild West")
    add("cowboy21", "Wild West")
    add("cowboy22", "Wild West")
    add("cowboy22_1", "Wild West")
    add("cowboy23", "Wild West")
    add("cowboy23_1", "Wild West")
    add("cowboy24", "Wild West")
    add("cowboy24_1", "Wild West")
    add("cowboy25", "Wild West")
    add("cowboy26", "Wild West")
    add("cowboy27", "Wild West")
    add("cowboy28", "Wild West")
    add("cowboy29", "Wild West")
    add("cowboy30", "Wild West")
    add("cowboy31", "Wild West")
    add("cowboy32", "Wild West")
    add("cowboy33", "Wild West")
    add("cowboy34", "Wild West")
    add("cowboy35", "Wild West")
    add("cowboy_dangerroom", "Wild West")
    add("cowboy_dangerroom2", "Wild West")
    add("random_cowboy", "Wild West")

    # ── Far Future ──
    add("random_zomboss_future", "Far Future", victory=True)
    add("future1", "Far Future")
    add("future2", "Far Future")
    add("future3", "Far Future")
    add("future4", "Far Future")
    add("future5", "Far Future")
    add("future6", "Far Future")
    add("future7", "Far Future")
    add("future8", "Far Future")
    add("future9", "Far Future")
    add("future10", "Far Future")
    add("future10_1", "Far Future")
    add("future10_2", "Far Future")
    add("future10_3", "Far Future")
    add("future10_4", "Far Future")
    add("future11", "Far Future")
    add("future12", "Far Future")
    add("future13", "Far Future")
    add("future14", "Far Future")
    add("future15", "Far Future")
    add("future16", "Far Future")
    add("future17", "Far Future")
    add("future18", "Far Future")
    add("future19", "Far Future")
    add("future20", "Far Future")
    add("future21", "Far Future")
    add("future22", "Far Future")
    add("future23", "Far Future")
    add("future24", "Far Future")
    add("future25", "Far Future")
    add("future26", "Far Future")
    add("future27", "Far Future")
    add("future28", "Far Future")
    add("future29", "Far Future")
    add("future30", "Far Future")
    add("future31", "Far Future")
    add("future32", "Far Future")
    add("future33", "Far Future")
    add("future34", "Far Future")
    add("future35", "Far Future")
    add("future_dangerroom", "Far Future")
    add("future_dangerroom2", "Far Future")
    add("future_dangerroom_sunbomb", "Far Future")
    add("random_future", "Far Future")

    # ── Dark Ages ──
    add("random_zomboss_dark", "Dark Ages", victory=True)
    add("dark1", "Dark Ages")
    add("dark2", "Dark Ages")
    add("dark3", "Dark Ages")
    add("dark4", "Dark Ages")
    add("dark5", "Dark Ages")
    add("dark6", "Dark Ages")
    add("dark7", "Dark Ages")
    add("dark8", "Dark Ages")
    add("dark9", "Dark Ages")
    add("dark10", "Dark Ages")
    add("dark11", "Dark Ages")
    add("dark12", "Dark Ages")
    add("dark13", "Dark Ages")
    add("dark14", "Dark Ages")
    add("dark15", "Dark Ages")
    add("dark16", "Dark Ages")
    add("dark17", "Dark Ages")
    add("dark18", "Dark Ages")
    add("dark18_1", "Dark Ages")
    add("dark19", "Dark Ages")
    add("dark20", "Dark Ages")
    add("dark21", "Dark Ages")
    add("dark22", "Dark Ages")
    add("dark23", "Dark Ages")
    add("dark24", "Dark Ages")
    add("dark25", "Dark Ages")
    add("dark26", "Dark Ages")
    add("dark27", "Dark Ages")
    add("dark28", "Dark Ages")
    add("dark29", "Dark Ages")
    add("dark30", "Dark Ages")
    add("dark_dangerroom", "Dark Ages")
    add("dark_dangerroom2", "Dark Ages")
    add("dark_dangerroom_potion", "Dark Ages")
    add("random_dark", "Dark Ages")

    # ── Big Wave Beach ──
    add("random_beach", "Big Wave Beach", victory=True)
    add("beach1", "Big Wave Beach")
    add("beach2", "Big Wave Beach")
    add("beach3", "Big Wave Beach")
    add("beach4", "Big Wave Beach")
    add("beach5", "Big Wave Beach")
    add("beach6", "Big Wave Beach")
    add("beach7", "Big Wave Beach")
    add("beach8", "Big Wave Beach")
    add("beach9", "Big Wave Beach")
    add("beach10", "Big Wave Beach")
    add("beach11", "Big Wave Beach")
    add("beach12", "Big Wave Beach")
    add("beach13", "Big Wave Beach")
    add("beach14", "Big Wave Beach")
    add("beach15", "Big Wave Beach")
    add("beach16", "Big Wave Beach")
    add("beach17", "Big Wave Beach")
    add("beach18", "Big Wave Beach")
    add("beach19", "Big Wave Beach")
    add("beach20", "Big Wave Beach")
    add("beach21", "Big Wave Beach")
    add("beach22", "Big Wave Beach")
    add("beach23", "Big Wave Beach")
    add("beach24", "Big Wave Beach")
    add("beach25", "Big Wave Beach")
    add("beach26", "Big Wave Beach")
    add("beach27", "Big Wave Beach")
    add("beach28", "Big Wave Beach")
    add("beach29", "Big Wave Beach")
    add("beach30", "Big Wave Beach")
    add("beach31", "Big Wave Beach")
    add("beach32", "Big Wave Beach")
    add("beach33", "Big Wave Beach")
    add("beach34", "Big Wave Beach")
    add("beach35", "Big Wave Beach")
    add("beach36", "Big Wave Beach")
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
    add("iceage1", "Frostbite Caves")
    add("iceage2", "Frostbite Caves")
    add("iceage3", "Frostbite Caves")
    add("iceage4", "Frostbite Caves")
    add("iceage5", "Frostbite Caves")
    add("iceage6", "Frostbite Caves")
    add("iceage7", "Frostbite Caves")
    add("iceage8", "Frostbite Caves")
    add("iceage9", "Frostbite Caves")
    add("iceage10", "Frostbite Caves")
    add("iceage11", "Frostbite Caves")
    add("iceage12", "Frostbite Caves")
    add("iceage13", "Frostbite Caves")
    add("iceage14", "Frostbite Caves")
    add("iceage15", "Frostbite Caves")
    add("iceage16", "Frostbite Caves")
    add("iceage17", "Frostbite Caves")
    add("iceage18", "Frostbite Caves")
    add("iceage19", "Frostbite Caves")
    add("iceage20", "Frostbite Caves")
    add("iceage21", "Frostbite Caves")
    add("iceage22", "Frostbite Caves")
    add("iceage23", "Frostbite Caves")
    add("iceage24", "Frostbite Caves")
    add("iceage24_B", "Frostbite Caves")
    add("iceage25", "Frostbite Caves")
    add("iceage26", "Frostbite Caves")
    add("iceage27", "Frostbite Caves")
    add("iceage28", "Frostbite Caves")
    add("iceage29", "Frostbite Caves")
    add("iceage30", "Frostbite Caves")
    add("iceage31", "Frostbite Caves")
    add("iceage32", "Frostbite Caves")
    add("iceage33", "Frostbite Caves")
    add("iceage34", "Frostbite Caves")
    add("iceage35", "Frostbite Caves")
    add("iceage36", "Frostbite Caves")
    add("iceage37", "Frostbite Caves")
    add("iceage38", "Frostbite Caves")
    add("iceage39", "Frostbite Caves")
    add("iceage40", "Frostbite Caves")
    add("iceage_dangerroom2", "Frostbite Caves")

    # ── Lost City ──
    add("lostcity_dangerroom", "Lost City", victory=True)
    add("lostcity1", "Lost City")
    add("lostcity2", "Lost City")
    add("lostcity3", "Lost City")
    add("lostcity4", "Lost City")
    add("lostcity5", "Lost City")
    add("lostcity6", "Lost City")
    add("lostcity7", "Lost City")
    add("lostcity8", "Lost City")
    add("lostcity9", "Lost City")
    add("lostcity10", "Lost City")
    add("lostcity11", "Lost City")
    add("lostcity12", "Lost City")
    add("lostcity13", "Lost City")
    add("lostcity14", "Lost City")
    add("lostcity15", "Lost City")
    add("lostcity16", "Lost City")
    add("lostcity17", "Lost City")
    add("lostcity18", "Lost City")
    add("lostcity19", "Lost City")
    add("lostcity20", "Lost City")
    add("lostcity21", "Lost City")
    add("lostcity22", "Lost City")
    add("lostcity23", "Lost City")
    add("lostcity24", "Lost City")
    add("lostcity25", "Lost City")
    add("lostcity26", "Lost City")
    add("lostcity27", "Lost City")
    add("lostcity28", "Lost City")
    add("lostcity29", "Lost City")
    add("lostcity30", "Lost City")
    add("lostcity31", "Lost City")
    add("lostcity32", "Lost City")
    add("lostcity33", "Lost City")
    add("lostcity34", "Lost City")
    add("lostcity35", "Lost City")
    add("lostcity36", "Lost City")
    add("lostcity37", "Lost City")
    add("lostcity38", "Lost City")
    add("lostcity39", "Lost City")
    add("lostcity40", "Lost City")
    add("lostcity41", "Lost City")
    add("lostcity42", "Lost City")
    add("lostcity_dangerroom2", "Lost City")

    # ── Kongfu Temple ──
    add("kongfu_dangerroom", "Kongfu Temple", victory=True)
    add("kongfu1", "Kongfu Temple")
    add("kongfu2", "Kongfu Temple")
    add("kongfu3", "Kongfu Temple")
    add("kongfu4", "Kongfu Temple")
    add("kongfu5", "Kongfu Temple")
    add("kongfu6", "Kongfu Temple")
    add("kongfu7", "Kongfu Temple")
    add("kongfu8", "Kongfu Temple")
    add("kongfu9", "Kongfu Temple")
    add("kongfu10", "Kongfu Temple")
    add("kongfu11", "Kongfu Temple")
    add("kongfu12", "Kongfu Temple")
    add("kongfu13", "Kongfu Temple")
    add("kongfu14", "Kongfu Temple")
    add("kongfu15", "Kongfu Temple")
    add("kongfu16", "Kongfu Temple")
    add("kongfu17", "Kongfu Temple")
    add("kongfu18", "Kongfu Temple")
    add("kongfu19", "Kongfu Temple")
    add("kongfu20", "Kongfu Temple")
    add("kongfu21", "Kongfu Temple")
    add("kongfu22", "Kongfu Temple")
    add("kongfu23", "Kongfu Temple")
    add("kongfu24", "Kongfu Temple")
    add("kongfu25", "Kongfu Temple")
    add("kongfu26", "Kongfu Temple")
    add("kongfu27", "Kongfu Temple")
    add("kongfu28", "Kongfu Temple")
    add("kongfu29", "Kongfu Temple")
    add("kongfu30", "Kongfu Temple")
    add("kongfu31", "Kongfu Temple")
    add("kongfu32", "Kongfu Temple")
    add("kongfu33", "Kongfu Temple")
    add("kongfu34", "Kongfu Temple")
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
    add("kongfu46", "Kongfu Temple")
    add("kongfu47", "Kongfu Temple")
    add("kongfu48", "Kongfu Temple")
    add("kongfu_dangerroom2", "Kongfu Temple")
    add("kongfu_dangerroom3", "Kongfu Temple")
    add("kongfu_dangerroom4", "Kongfu Temple")

    # ── Neon Mixtape Tour ──
    add("eighties_dangerroom", "Neon Mixtape Tour", victory=True)
    add("eighties1", "Neon Mixtape Tour")
    add("eighties2", "Neon Mixtape Tour")
    add("eighties3", "Neon Mixtape Tour")
    add("eighties4", "Neon Mixtape Tour")
    add("eighties5", "Neon Mixtape Tour")
    add("eighties6", "Neon Mixtape Tour")
    add("eighties7", "Neon Mixtape Tour")
    add("eighties8", "Neon Mixtape Tour")
    add("eighties9", "Neon Mixtape Tour")
    add("eighties10", "Neon Mixtape Tour")
    add("eighties11", "Neon Mixtape Tour")
    add("eighties12", "Neon Mixtape Tour")
    add("eighties13", "Neon Mixtape Tour")
    add("eighties14", "Neon Mixtape Tour")
    add("eighties15", "Neon Mixtape Tour")
    add("eighties16", "Neon Mixtape Tour")
    add("eighties17", "Neon Mixtape Tour")
    add("eighties18", "Neon Mixtape Tour")
    add("eighties19", "Neon Mixtape Tour")
    add("eighties20", "Neon Mixtape Tour")
    add("eighties21", "Neon Mixtape Tour")
    add("eighties22", "Neon Mixtape Tour")
    add("eighties23", "Neon Mixtape Tour")
    add("eighties24", "Neon Mixtape Tour")
    add("eighties25", "Neon Mixtape Tour")
    add("eighties26", "Neon Mixtape Tour")
    add("eighties27", "Neon Mixtape Tour")
    add("eighties28", "Neon Mixtape Tour")
    add("eighties29", "Neon Mixtape Tour")
    add("eighties30", "Neon Mixtape Tour")
    add("eighties31", "Neon Mixtape Tour")
    add("eighties32", "Neon Mixtape Tour")

    # ── Jurassic Marsh ──
    add("dino_dangerroom", "Jurassic Marsh", victory=True)
    add("dino1", "Jurassic Marsh")
    add("dino2", "Jurassic Marsh")
    add("dino3", "Jurassic Marsh")
    add("dino4", "Jurassic Marsh")
    add("dino5", "Jurassic Marsh")
    add("dino6", "Jurassic Marsh")
    add("dino7", "Jurassic Marsh")
    add("dino8", "Jurassic Marsh")
    add("dino9", "Jurassic Marsh")
    add("dino10", "Jurassic Marsh")
    add("dino11", "Jurassic Marsh")
    add("dino12", "Jurassic Marsh")
    add("dino13", "Jurassic Marsh")
    add("dino14", "Jurassic Marsh")
    add("dino15", "Jurassic Marsh")
    add("dino16", "Jurassic Marsh")
    add("dino17", "Jurassic Marsh")
    add("dino18", "Jurassic Marsh")
    add("dino19", "Jurassic Marsh")
    add("dino20", "Jurassic Marsh")
    add("dino21", "Jurassic Marsh")
    add("dino22", "Jurassic Marsh")
    add("dino23", "Jurassic Marsh")
    add("dino24", "Jurassic Marsh")
    add("dino25", "Jurassic Marsh")
    add("dino26", "Jurassic Marsh")
    add("dino27", "Jurassic Marsh")
    add("dino28", "Jurassic Marsh")
    add("dino29", "Jurassic Marsh")
    add("dino30", "Jurassic Marsh")
    add("dino31", "Jurassic Marsh")
    add("dino32", "Jurassic Marsh")
    add("dino33", "Jurassic Marsh")
    add("dino34", "Jurassic Marsh")
    add("dino35", "Jurassic Marsh")
    add("dino36", "Jurassic Marsh")
    add("dino37", "Jurassic Marsh")
    add("dino38", "Jurassic Marsh")
    add("dino39", "Jurassic Marsh")
    add("dino40", "Jurassic Marsh")
    add("dino41", "Jurassic Marsh")
    add("dino42", "Jurassic Marsh")
    add("dino_dangerroom2", "Jurassic Marsh")

    # ── Modern Day ──
    add("modern_zomboss_01_egypt", "Modern Day", victory=True)
    add("modern1", "Modern Day")
    add("modern2", "Modern Day")
    add("modern3", "Modern Day")
    add("modern4", "Modern Day")
    add("modern5", "Modern Day")
    add("modern6", "Modern Day")
    add("modern7", "Modern Day")
    add("modern8", "Modern Day")
    add("modern9", "Modern Day")
    add("modern10", "Modern Day")
    add("modern11", "Modern Day")
    add("modern12", "Modern Day")
    add("modern13", "Modern Day")
    add("modern14", "Modern Day")
    add("modern15", "Modern Day")
    add("modern16", "Modern Day")
    add("modern17", "Modern Day")
    add("modern18", "Modern Day")
    add("modern19", "Modern Day")
    add("modern20", "Modern Day")
    add("modern21", "Modern Day")
    add("modern22", "Modern Day")
    add("modern23", "Modern Day")
    add("modern24", "Modern Day")
    add("modern25", "Modern Day")
    add("modern26", "Modern Day")
    add("modern27", "Modern Day")
    add("modern28", "Modern Day")
    add("modern29", "Modern Day")
    add("modern30", "Modern Day")
    add("modern31", "Modern Day")
    add("modern35", "Modern Day")
    add("modern36", "Modern Day")
    add("modern37", "Modern Day")
    add("modern38", "Modern Day")
    add("modern39", "Modern Day")
    add("modern40", "Modern Day")
    add("modern41", "Modern Day")
    add("modern42", "Modern Day")
    add("modern43", "Modern Day")
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
    add("sky1", "Aerial Fortress")
    add("sky2", "Aerial Fortress")
    add("sky3", "Aerial Fortress")
    add("sky4", "Aerial Fortress")
    add("sky5", "Aerial Fortress")
    add("sky6", "Aerial Fortress")
    add("sky7", "Aerial Fortress")
    add("sky8", "Aerial Fortress")
    add("sky9", "Aerial Fortress")
    add("sky10", "Aerial Fortress")
    add("sky11", "Aerial Fortress")
    add("sky12", "Aerial Fortress")
    add("sky13", "Aerial Fortress")
    add("sky14", "Aerial Fortress")
    add("sky15", "Aerial Fortress")
    add("sky16", "Aerial Fortress")

    # ── Side Paths (always accessible from Tutorial) ──
    add("Aloe 0", "Aloe Sidepath"); add("Aloe 1", "Aloe Sidepath"); add("Aloe 2", "Aloe Sidepath")
    add("Aloe 3", "Aloe Sidepath"); add("Aloe 4", "Aloe Sidepath"); add("Aloe 5", "Aloe Sidepath")

    add("Appease-mint 1_0", "Appease-mint Sidepath"); add("Appease-mint 1_1", "Appease-mint Sidepath")
    add("Appease-mint 1_2", "Appease-mint Sidepath"); add("Appease-mint 1_3", "Appease-mint Sidepath")
    add("Appease-mint 1_4", "Appease-mint Sidepath"); add("Appease-mint 1_5", "Appease-mint Sidepath")
    add("Appease-mint 1_6", "Appease-mint Sidepath"); add("Appease-mint 2_0", "Appease-mint Sidepath")
    add("Appease-mint 2_1", "Appease-mint Sidepath"); add("Appease-mint 2_2", "Appease-mint Sidepath")
    add("Appease-mint 2_3", "Appease-mint Sidepath"); add("Appease-mint 2_4", "Appease-mint Sidepath")
    add("Appease-mint 2_5", "Appease-mint Sidepath"); add("Appease-mint 2_6", "Appease-mint Sidepath")

    add("Atomic Bombegranate 0", "Atomic Bombegranate Sidepath"); add("Atomic Bombegranate 1", "Atomic Bombegranate Sidepath")
    add("Atomic Bombegranate 2", "Atomic Bombegranate Sidepath"); add("Atomic Bombegranate 3", "Atomic Bombegranate Sidepath")
    add("Atomic Bombegranate 4", "Atomic Bombegranate Sidepath"); add("Atomic Bombegranate 5", "Atomic Bombegranate Sidepath")

    add("bank_theft1", "Bank Sidepath"); add("bank_theft2", "Bank Sidepath")
    add("bank_theft3", "Bank Sidepath"); add("bank_theft4", "Bank Sidepath")
    add("bank_theft5", "Bank Sidepath")

    add("Blooming Heart 0", "Blooming Heart Sidepath"); add("Blooming Heart 1", "Blooming Heart Sidepath")
    add("Blooming Heart 2", "Blooming Heart Sidepath"); add("Blooming Heart 3", "Blooming Heart Sidepath")
    add("Blooming Heart 4", "Blooming Heart Sidepath"); add("Blooming Heart 5", "Blooming Heart Sidepath")

    add("Buttercup 0", "Buttercup Sidepath"); add("Buttercup 1", "Buttercup Sidepath")
    add("Buttercup 2", "Buttercup Sidepath"); add("Buttercup 3", "Buttercup Sidepath")
    add("Buttercup 4", "Buttercup Sidepath"); add("Buttercup 5", "Buttercup Sidepath")

    add("Conceal-mint 0", "Conceal-mint Sidepath"); add("Conceal-mint 1", "Conceal-mint Sidepath")
    add("Conceal-mint 2", "Conceal-mint Sidepath"); add("Conceal-mint 3", "Conceal-mint Sidepath")
    add("Conceal-mint 4", "Conceal-mint Sidepath"); add("Conceal-mint 5", "Conceal-mint Sidepath")
    add("Conceal-mint 6", "Conceal-mint Sidepath"); add("Conceal-mint 7", "Conceal-mint Sidepath")
    add("Conceal-mint 8", "Conceal-mint Sidepath"); add("Conceal-mint 9", "Conceal-mint Sidepath")
    add("Conceal-mint 10", "Conceal-mint Sidepath"); add("Conceal-mint 11", "Conceal-mint Sidepath")

    add("Doom-shroom 0", "Doom-shroom Sidepath"); add("Doom-shroom 1", "Doom-shroom Sidepath")
    add("Doom-shroom 2", "Doom-shroom Sidepath"); add("Doom-shroom 3", "Doom-shroom Sidepath")
    add("Doom-shroom 4", "Doom-shroom Sidepath"); add("Doom-shroom 5", "Doom-shroom Sidepath")

    add("Electric Currant 0", "Electric Currant Sidepath"); add("Electric Currant 1", "Electric Currant Sidepath")
    add("Electric Currant 2", "Electric Currant Sidepath"); add("Electric Currant 3", "Electric Currant Sidepath")
    add("Electric Currant 4", "Electric Currant Sidepath"); add("Electric Currant 5", "Electric Currant Sidepath")

    add("Enlighten-mint 0", "Enlighten-mint Sidepath"); add("Enlighten-mint 1", "Enlighten-mint Sidepath")
    add("Enlighten-mint 2", "Enlighten-mint Sidepath"); add("Enlighten-mint 3", "Enlighten-mint Sidepath")
    add("Enlighten-mint 4", "Enlighten-mint Sidepath"); add("Enlighten-mint 5", "Enlighten-mint Sidepath")
    add("Enlighten-mint 6", "Enlighten-mint Sidepath"); add("Enlighten-mint 7", "Enlighten-mint Sidepath")

    add("Ghost Pepper 0", "Ghost Pepper Sidepath"); add("Ghost Pepper 1", "Ghost Pepper Sidepath")
    add("Ghost Pepper 2", "Ghost Pepper Sidepath"); add("Ghost Pepper 3", "Ghost Pepper Sidepath")

    add("Gloom-shroom 0", "Gloom-shroom Sidepath"); add("Gloom-shroom 1", "Gloom-shroom Sidepath")
    add("Gloom-shroom 2", "Gloom-shroom Sidepath"); add("Gloom-shroom 3", "Gloom-shroom Sidepath")
    add("Gloom-shroom 4", "Gloom-shroom Sidepath"); add("Gloom-shroom 5", "Gloom-shroom Sidepath")
    add("Gloom-shroom 6", "Gloom-shroom Sidepath"); add("Gloom-shroom 7", "Gloom-shroom Sidepath")

    add("Gold Bloom 0", "Gold Bloom Sidepath"); add("Gold Bloom 1", "Gold Bloom Sidepath")
    add("Gold Bloom 2", "Gold Bloom Sidepath"); add("Gold Bloom 3", "Gold Bloom Sidepath")

    add("Hot Date 1", "Hot Date Sidepath"); add("Hot Date 2", "Hot Date Sidepath")
    add("Hot Date 3", "Hot Date Sidepath")

    add("Ice Bloom 0", "Ice Bloom Sidepath"); add("Ice Bloom 1", "Ice Bloom Sidepath")
    add("Ice Bloom 2", "Ice Bloom Sidepath"); add("Ice Bloom 3", "Ice Bloom Sidepath")
    add("Ice Bloom 4", "Ice Bloom Sidepath"); add("Ice Bloom 5", "Ice Bloom Sidepath")

    add("Ice-shroom 0", "Ice-shroom Sidepath"); add("Ice-shroom 1", "Ice-shroom Sidepath")
    add("Ice-shroom 2", "Ice-shroom Sidepath"); add("Ice-shroom 3", "Ice-shroom Sidepath")
    add("Ice-shroom 4", "Ice-shroom Sidepath"); add("Ice-shroom 5", "Ice-shroom Sidepath")

    add("Meteor Flower 0", "Meteor Flower Sidepath"); add("Meteor Flower 1", "Meteor Flower Sidepath")
    add("Meteor Flower 2", "Meteor Flower Sidepath"); add("Meteor Flower 3", "Meteor Flower Sidepath")

    add("Parsnip 0", "Parsnip Sidepath"); add("Parsnip 1", "Parsnip Sidepath")
    add("Parsnip 2", "Parsnip Sidepath"); add("Parsnip 3", "Parsnip Sidepath")
    add("Parsnip 4", "Parsnip Sidepath"); add("Parsnip 5", "Parsnip Sidepath")

    add("Plantern 0", "Plantern Sidepath"); add("Plantern 1", "Plantern Sidepath")
    add("Plantern 2", "Plantern Sidepath"); add("Plantern 3", "Plantern Sidepath")
    add("Plantern 4", "Plantern Sidepath"); add("Plantern 5", "Plantern Sidepath")

    add("Reinforce-mint 0", "Reinforce-mint Sidepath"); add("Reinforce-mint 1", "Reinforce-mint Sidepath")
    add("Reinforce-mint 2", "Reinforce-mint Sidepath"); add("Reinforce-mint 3", "Reinforce-mint Sidepath")
    add("Reinforce-mint 4", "Reinforce-mint Sidepath"); add("Reinforce-mint 5", "Reinforce-mint Sidepath")
    add("Reinforce-mint 6", "Reinforce-mint Sidepath"); add("Reinforce-mint 7", "Reinforce-mint Sidepath")
    add("Reinforce-mint 8", "Reinforce-mint Sidepath"); add("Reinforce-mint 9", "Reinforce-mint Sidepath")
    add("Reinforce-mint 10", "Reinforce-mint Sidepath"); add("Reinforce-mint 11", "Reinforce-mint Sidepath")

    add("Sap-fling 0", "Sap-fling Sidepath"); add("Sap-fling 1", "Sap-fling Sidepath")
    add("Sap-fling 2", "Sap-fling Sidepath"); add("Sap-fling 3", "Sap-fling Sidepath")
    add("Sap-fling 4", "Sap-fling Sidepath"); add("Sap-fling 5", "Sap-fling Sidepath")
    add("Sap-fling 6", "Sap-fling Sidepath"); add("Sap-fling 7", "Sap-fling Sidepath")

    add("Seashooter 0", "Seashooter Sidepath"); add("Seashooter 1", "Seashooter Sidepath")
    add("Seashooter 2", "Seashooter Sidepath"); add("Seashooter 3", "Seashooter Sidepath")

    add("shootingstarfruit1", "Shootingstarfruit Sidepath")
    add("shootingstarfruit2", "Shootingstarfruit Sidepath")
    add("shootingstarfruit3", "Shootingstarfruit Sidepath")

    add("Solar Tomato 0", "Solar Tomato Sidepath"); add("Solar Tomato 1", "Solar Tomato Sidepath")
    add("Solar Tomato 2", "Solar Tomato Sidepath"); add("Solar Tomato 3", "Solar Tomato Sidepath")
    add("Solar Tomato 4", "Solar Tomato Sidepath"); add("Solar Tomato 5", "Solar Tomato Sidepath")

    add("Squash 0", "Squash Sidepath"); add("Squash 1", "Squash Sidepath")
    add("Squash 2", "Squash Sidepath"); add("Squash 3", "Squash Sidepath")

    add("Strawburst 0", "Strawburst Sidepath"); add("Strawburst 1", "Strawburst Sidepath")
    add("Strawburst 2", "Strawburst Sidepath"); add("Strawburst 3", "Strawburst Sidepath")
    add("Strawburst 4", "Strawburst Sidepath"); add("Strawburst 5", "Strawburst Sidepath")
    add("Strawburst 6", "Strawburst Sidepath"); add("Strawburst 7", "Strawburst Sidepath")

    add("Sweet Potato 0", "Sweet Potato Sidepath"); add("Sweet Potato 1", "Sweet Potato Sidepath")
    add("Sweet Potato 2", "Sweet Potato Sidepath"); add("Sweet Potato 3", "Sweet Potato Sidepath")
    add("Sweet Potato 4", "Sweet Potato Sidepath"); add("Sweet Potato 5", "Sweet Potato Sidepath")

    add("Umbrella Leaf 0", "Umbrella Leaf Sidepath"); add("Umbrella Leaf 1", "Umbrella Leaf Sidepath")
    add("Umbrella Leaf 2", "Umbrella Leaf Sidepath"); add("Umbrella Leaf 3", "Umbrella Leaf Sidepath")
    add("Umbrella Leaf 4", "Umbrella Leaf Sidepath"); add("Umbrella Leaf 5", "Umbrella Leaf Sidepath")
    add("Umbrella Leaf 6", "Umbrella Leaf Sidepath"); add("Umbrella Leaf 7", "Umbrella Leaf Sidepath")
    add("Umbrella Leaf 8", "Umbrella Leaf Sidepath"); add("Umbrella Leaf 9", "Umbrella Leaf Sidepath")
    add("Umbrella Leaf 10", "Umbrella Leaf Sidepath"); add("Umbrella Leaf 11", "Umbrella Leaf Sidepath")

    add("Vamporcini 0", "Vamporcini Sidepath"); add("Vamporcini 1", "Vamporcini Sidepath")
    add("Vamporcini 2", "Vamporcini Sidepath"); add("Vamporcini 3", "Vamporcini Sidepath")

    add("epic_beghouled1", "Epic Beghouled Sidepath")
    add("epic_beghouled2", "Epic Beghouled Sidepath")
    add("epic_beghouled3", "Epic Beghouled Sidepath")
    add("epic_beghouled4", "Epic Beghouled Sidepath")
    add("epic_beghouled5", "Epic Beghouled Sidepath")

    add("floawerpot1", "Floawerpot Sidepath")
    add("floawerpot2", "Floawerpot Sidepath")
    add("floawerpot3", "Floawerpot Sidepath")

    add("mixed_dangerroom2", "Mixed Sidepath")

    add("reinforcemint_unused_try1", "Reinforcemint Unused Sidepath")
    add("reinforcemint_unused_try2", "Reinforcemint Unused Sidepath")
    add("reinforcemint_unused_try3", "Reinforcemint Unused Sidepath")

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
    # SHOP_LEGACY_COMMODITIES, not SHOP_COMMODITIES: this block is not last in
    # the function, so a name inserted here renumbers every location after it.
    # Commodities added upstream later go at the end, below.
    for commodity in SHOP_LEGACY_COMMODITIES:
        add(shop_location_name(commodity), SHOP_REGION, shop=True)

    # ── Neon Mixtape Tour, second half (added 2026-08-17) ────────────────────
    # The world runs to eighties42; this list stopped at eighties32. Its map
    # chain is nodes 1-42 unbroken -- verified against the world table and the
    # map scene -- so these are ordinary playable levels that simply had no
    # check. eighties39 is also one of the two levels a gem-priced shop card
    # gates on, so shopsanity players had no check for it either.
    #
    # Appended here rather than in the Neon Mixtape Tour block above for the
    # same reason the shop is: IDs are assigned by increment, so inserting
    # them in reading order would renumber every location after eighties32 and
    # break every seed already generated. Position in this list also decides
    # which stretch regions.py puts a location in, and these come last in the
    # world, so the tail of the list is where they belong anyway.
    #
    # eighties32 is the world's Zomboss and carries worldtrophy_eighties;
    # eighties42 is the "2.0" rematch that closes the world. Every world is
    # built that way (egypt25/egypt35, dino32/dino42 ...), which is why
    # WORLD_COMPLETION_LOCS now points at eighties42 rather than the trophy.
    add("eighties33", "Neon Mixtape Tour")
    add("eighties34", "Neon Mixtape Tour")
    add("eighties35", "Neon Mixtape Tour")
    add("eighties36", "Neon Mixtape Tour")
    add("eighties37", "Neon Mixtape Tour")
    add("eighties38", "Neon Mixtape Tour")
    add("eighties39", "Neon Mixtape Tour")
    add("eighties40", "Neon Mixtape Tour")
    add("eighties41", "Neon Mixtape Tour")
    add("eighties42", "Neon Mixtape Tour")
    add("eighties_dangerroom2", "Neon Mixtape Tour")

    # ── Goo Peashooter side path (added 2026-08-17) ──────────────────────────
    # Branches off dark16, which carries the otherNextIslands entry for it, and
    # is laid out exactly like every other plant quest: a demo level on the
    # Dark Ages map (node "16-1"), then five levels on the epic_dark map whose
    # own node labels are 1-5. Missed until now because the location list was
    # built from level definitions rather than map nodes.
    #
    # Named "<Plant> <N>" like every other side path: the plant is the one the
    # levels declare in PlantToIntroduce (PlantFeatures id 206, NAME.en "Goo
    # Peashooter"), and N is the number off the codename, so it lines up with
    # the epic map's own node labels 1-5. 0 is the demo level.
    #
    # The plant itself is NOT an item: the client's plant tables stop at id
    # 165, so all 43 plants above that are unshuffled. Aloe, Seashooter and
    # Ice Bloom are already in the seed on the same footing, so this path is
    # consistent with them -- it adds checks, not a new plant.
    add("Goo Peashooter 0", "Goo Peashooter Sidepath")  # poisonpeashooter0
    add("Goo Peashooter 1", "Goo Peashooter Sidepath")  # poisonpeashooter1
    add("Goo Peashooter 2", "Goo Peashooter Sidepath")  # poisonpeashooter2
    add("Goo Peashooter 3", "Goo Peashooter Sidepath")  # poisonpeashooter3
    add("Goo Peashooter 4", "Goo Peashooter Sidepath")  # poisonpeashooter4
    add("Goo Peashooter 5", "Goo Peashooter Sidepath")  # poisonpeashooter5

    # ── Aerial Fortress, second half (added 2026-08-17) ──────────────────────
    # The world runs to sky31 and this list stopped at sky16, its world-key
    # level. Its map chain is nodes 1-31 unbroken, so these are ordinary
    # levels that simply had no check -- the same gap Neon Mixtape Tour had.
    # sky31 is one of the two levels a gem-priced shop card unlocks on.
    #
    # sky20 awards the dangerroom_sky trophy, so it is what opens sky_dangerroom
    # (see DANGER_ROOM_UNLOCK). sky22, sky23 and sky26 award Bulbkekengi,
    # Loquanado and Pea Commando, none of which AP ships as items -- they are
    # all above plant id 165 -- so the game grants them itself.
    #
    # Appended here rather than in the Aerial Fortress block above so no
    # existing location renumbers; see the Neon Mixtape Tour note.
    for _sky in range(17, 32):
        add(f"sky{_sky}", "Aerial Fortress")
    add("sky_dangerroom", "Aerial Fortress")

    # ── Shop commodities added upstream after the ids above were assigned ────
    # Kurt's build sells these; the older snapshot did not. They must stay last
    # so nothing above them moves. See SHOP_EXTRA_COMMODITIES.
    for commodity in SHOP_EXTRA_COMMODITIES:
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


# Shop check -> the level whose clearing puts that card on the shelf, keyed by
# location name rather than by commodity so both the filter below and rules.py
# can use it directly. SHOP_UNLOCK holds the game's own table; see it for the
# derivation.
SHOP_LOC_UNLOCK = {shop_location_name(c): lvl for c, lvl in SHOP_UNLOCK.items()}

# Every location's declared region, for resolving a shop card's unlock level to
# the world it is in. Built from ALL_LOCATIONS so it cannot drift from them.
_REGION_OF = {l.name: l.region for l in ALL_LOCATIONS}

_missing_unlocks = sorted(set(SHOP_LOC_UNLOCK.values()) - set(_REGION_OF))
if _missing_unlocks:
    raise ValueError(f"shop cards unlock at levels that are not locations: "
                     f"{_missing_unlocks}")


def active_locations(shopsanity: bool,
                     enabled_regions: Set[str],
                     side_paths: bool = True,
                     danger_rooms: bool = True) -> List[PvZ2LocationData]:
    """Locations actually built for a slot with these settings.

    Shop and disabled-world locations stay in the static location_name_to_id
    map regardless (AP requires that to be constant), so they must be filtered
    here rather than out of ALL_LOCATIONS -- and the item pool has to size off
    this, not len(ALL_LOCATIONS), or a slot ends up with more items than it
    has places to put them.

    A side path is entered from inside a world (see SIDE_PATH_WORLD), so one
    belonging to a world this seed left out has to go with it -- otherwise its
    locations exist with nothing that can reach them and generation fails.
    Tutorial and Shop are always kept.

    Shop checks are filtered the same way, one card at a time: 29 of the 39
    carry an UnlockLevel naming a specific level (SHOP_UNLOCK), so a card whose
    level is in a world this seed left out goes with that world. The other ten
    are on sale from the moment the store button exists and are always kept.

    side_paths=False drops every side path, worldless ones included; that is
    the include_side_paths option. danger_rooms=False drops the 37 Danger Room
    levels, which sit inside their world's own region rather than a region of
    their own; that is include_danger_rooms. Both are off by default as
    options, but both parameters default to True so a caller that predates
    them keeps the old behaviour.
    """
    side_path_regions = set(SIDE_PATH_REGIONS)

    def keep(loc: PvZ2LocationData) -> bool:
        # Never built, under any options: the game has no way to launch these
        # levels, so their checks cannot fire. Not an option, because an
        # unreachable check is not a preference.
        if loc.name in UNREACHABLE_LOCATIONS:
            return False
        if loc.is_shop and not shopsanity:
            return False
        # A card only reaches the shelf once its UnlockLevel is cleared, so a
        # card unlocked by a world this seed left out can never be bought --
        # the same reasoning that drops a dropped world's side paths. Without
        # this a one-world seed carries checks nothing can reach.
        unlock = SHOP_LOC_UNLOCK.get(loc.name)
        if unlock is not None and _REGION_OF[unlock] not in enabled_regions:
            return False
        # Checked before the region tests: a Danger Room lives in a world
        # region (or, for the Mixed one, a side path), so it would otherwise be
        # kept by whichever branch owns it.
        if not danger_rooms and loc.name in DANGER_ROOM_LOCATIONS:
            return False
        if loc.region in ALL_WORLD_REGIONS:
            return loc.region in enabled_regions
        if loc.region in side_path_regions:
            if not side_paths:
                return False
            owner = SIDE_PATH_WORLD.get(loc.region)
            if owner is None:
                return True  # one of the seven the game ties to no world
            return any(r in enabled_regions for r in WORLD_REGIONS[owner])
        return True

    return [l for l in ALL_LOCATIONS if keep(l)]


# World Trophy locations — the mid-world milestone check in each world.
# Kongfu Temple has no world trophy in the game data and is excluded.
# Modern Day and Aerial Fortress are excluded (goal world / post-unlock).
WORLD_TROPHY_LOCS = [
    "egypt25",    # egypt25
    "pirate25",   # pirate25
    "cowboy25",   # cowboy25
    "future25",   # future25
    "dark20",     # dark20
    "beach32",    # beach32
    "iceage30",   # iceage30
    "lostcity32", # lostcity32
    "eighties32", # eighties32
    "dino32",     # dino32
]  # 10 total (Kongfu excluded — no trophy in game data)

# World Completion locations — the final regular level of each world.
# Modern Day and Aerial Fortress are excluded.
#
# Neon Mixtape Tour used to reuse its trophy location here, on the belief that
# the world "is shorter than the other worlds and its trophy check (eighties32)
# is also its last level". Both halves of that were wrong: at 42 levels it is
# joint second-longest, and eighties32 is its mid-world Zomboss. Every world is
# built the same way -- a Zomboss at the trophy (egypt25, dino32, eighties32)
# and a "2.0" rematch at the final level (egypt35, dino42, eighties42) -- so
# this world's completion goal was met ten levels before every other world's,
# and world_completions was indistinguishable from world_trophies for it.
# Fixed 2026-08-17, together with adding eighties33-42.
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
    "eighties42", # Neon Mixtape Tour
    "dino42",     # Jurassic Marsh
]  # 11 total

# World Key locations — the "World Key - X" check present in every world.
# Not necessarily on the same stage per world, and not forced to contain
# that world's own key item (fill is unconstrained). Modern Day and Aerial
# Fortress are excluded (goal world / post-unlock), same set as WORLD_COMPLETION_LOCS.
WORLD_KEY_LOCS = [
    "egypt8",
    "pirate8",
    "cowboy8",
    "future8",
    "dark10",
    "beach16",
    "iceage16",
    "lostcity16",
    "kongfu8",
    "eighties16",
    "dino16",
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
    0: "modern16",      # modern16
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
