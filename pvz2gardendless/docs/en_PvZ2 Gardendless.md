# PvZ2 Gardendless

## Where is the options page?

The [player options page for this game](../player-options) contains all the options you need to
configure and export a config file.

## What does randomization do to this game?

Every plant is taken away from you. Plants normally handed out by beating levels — and the four the
game grants at the very start — are instead scattered across the multiworld, and the game refuses to
let you use one until Archipelago actually sends it to you. You are guaranteed one cheap attacking
plant at the start of the run so you always have something to place.

Each world other than Ancient Egypt is locked behind its own **World Key** item, so the order you see
the game in is decided by the multiworld rather than by the map. Ancient Egypt is split into four
sequential stretches, each one wanting at least one sun-producing plant and one cheap attacker before
the logic considers it survivable.

Modern Day is the exception: it has no key. It opens once you have met a configurable number of world
goals — world trophies, world completions, or world keys, whichever you pick.

## What is the goal?

Clear one specific Modern Day level, chosen by the **Modern Day Victory** option:

- **World Key** — clear `modern16`, the World Key level. The shortest goal.
- **Zomboss** — beat the Modern Day Zomboss at roughly level 33. The default.
- **Completion** — clear `modern44`, the final Modern Day level. The longest.

This is independent of the goal type, which only decides how much of the rest of the game you need
before Modern Day opens at all.

## What items and locations get shuffled?

**Locations** are the levels themselves — 761 of them across every world, the side paths, and the
Danger Rooms — plus, with Shopsanity enabled, 39 one-time store purchases.

**Items** are:

- **Plants** — the full roster. A handful are required by logic: Lily Pad for Big Wave Beach,
  Perfume-shroom for Jurassic Marsh, and Hot Potato, Pepper-pult or Fire Peashooter for Frostbite
  Caves.
- **World Keys** — one per locked world.
- **Coins and gems** — filler, and the currency the store runs on.
- **Lawn Mower Trap** — sets off every lawn mower on the field at once. They roll out and are spent,
  leaving those lanes with no last line of defence for the rest of the level. A trap received while
  you are not in a level is held and applied when the next one starts.

## Which items can be in another player's world?

Any of them. All plants, world keys, filler and traps can land in any world in the multiworld.

## What does another world's item look like in PvZ2 Gardendless?

Nothing in-game marks it. Completing a level sends the check and the Archipelago client reports what
was found there, so the item text arrives through the client rather than through the game.

## When the player receives an item, what happens?

The client grants it immediately and shows a toast. Plants become placeable from that moment on;
before then the game hides them and suppresses their description tip. Coins and gems are added to
your balance. Traps fire at once if you are in a level, or the next time you start one.

## Notes on Shopsanity

Enabling Shopsanity turns the store's 39 one-time, gem-priced purchases into checks. Buying a plant
still will not grant it — plants only ever come from Archipelago — so a purchase spends the currency
and sends the check.

The repeatable gem, coin and sprout bundles are excluded because they can be bought over and over,
and four ticket-priced plants are excluded because tickets have no Archipelago source and would be
pure grind.

**Known limitation:** most store entries are gated behind an in-game level in addition to their
price, and logic does not currently model that. See the development notes in the repository README.
