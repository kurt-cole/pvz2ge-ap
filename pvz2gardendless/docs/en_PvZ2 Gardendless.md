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

## Do I have to play all thirteen worlds?

No. **World Count** sets how many main worlds the seed uses, counting Ancient Egypt but not Modern
Day, and the generator picks the rest at random — set it to `random` and it picks the number too. Use
**Enabled Worlds** to name worlds you definitely want; any remaining slots are filled at random around
them, and naming more worlds than the count asks for keeps all of them.

Ancient Egypt is always in, since it is the only world playable with no items. Modern Day is always in,
since that is where the run ends.

Worlds left out are gone completely: their levels are not locations, their World Key is not in the item
pool, and they stay locked for the whole run. Everything outside the main worlds — the side paths, the
Danger Rooms, the store — is unaffected, so even a one-world seed still has a few hundred checks.

**Worlds Required** shrinks to fit. Ask for 4 world keys in a 3-world seed and the run needs 3.

## What does Randomize Conveyor Plants do?

Conveyor levels hand you plants on a belt instead of letting you pick a seed bank. With this on, the
plants on that belt are replaced at random, drawn from the whole roster.

Each belt entry keeps the level's own drop weight and counts, so the level runs at the pace it was
designed to — only the plant changes. The roll is fixed per level, so retrying is not a reroll.

Bowling, power-tile and potion levels are left alone. Their belts deliver projectiles and tools rather
than plants, and swapping those out would make the level unplayable.

This does not leak progression. Conveyor levels already hand out plants regardless of what
Archipelago has sent you, and you do not keep what comes down the belt.

## What is the goal?

Clear one specific Modern Day level, chosen by the **Modern Day Victory** option:

- **World Key** — clear `modern16`, the World Key level. The shortest goal.
- **Zomboss** — beat the Modern Day Zomboss at roughly level 33. The default.
- **Completion** — clear `modern44`, the final Modern Day level. The longest.

This is independent of the goal type, which only decides how much of the rest of the game you need
before Modern Day opens at all.

## What items and locations get shuffled?

**Locations** are the levels themselves — 761 of them across every world, the side paths, and the
Danger Rooms — plus, with Shopsanity enabled, 39 one-time store purchases. Lowering **World Count**
removes the levels of the worlds it leaves out.

**Items** are:

- **Plants** — the full roster. A handful are required by logic: Lily Pad for Big Wave Beach,
  Perfume-shroom for Jurassic Marsh, and Hot Potato, Pepper-pult or Fire Peashooter for Frostbite
  Caves.
- **World Keys** — one per locked world.
- **Upgrades** — the fourteen permanent ones, with **Shuffle Upgrades** on. Nine of them are normally
  level rewards and five are store purchases; with the option on, clearing that level or making that
  purchase still sends the check, but the upgrade itself goes into the multiworld and only takes
  effect once you receive it. With the option off they are handed out as they always have been and
  are not items at all.

  The tiered ones are **progressive**, because each level of a tier does the same thing and the game
  simply adds them up — there is no "level 2" to receive out of order:

  | Item | Copies | Each copy gives |
  | --- | --- | --- |
  | Progressive Starting Sun | 2 | +25 starting sun |
  | Progressive Plant Food Slot | 2 | +1 plant food held (base 3) |
  | Progressive Seed Slot | 2 | +1 seed slot (base 6) |
  | Progressive Sun Shovel | 3 | +0.25 sun shovel rate |
  | Progressive Manual Mower | 2 | +1 manual mower |
  | Wall-nut First Aid | 1 | — |
  | Plant Food Refresh | 1 | — |
  | Sky Shield | 1 | — |
- **Coins and gems** — filler, and the currency the store runs on.
- **Random Plant Costume** — filler. Each one dresses a plant you already own in
  a costume you do not have yet, picked at random from the 309 the game has
  across 120 plants. Purely cosmetic. One arriving before you own any plant is
  held and applied once you do.
- **Lawn Mower Trap** — sets off every lawn mower on the field at once. They roll out and are spent,
  leaving those lanes with no last line of defence for the rest of the level. A trap received while
  you are not in a level is held and applied when the next one starts.

## Which items can be in another player's world?

Any of them. All plants, world keys, upgrades, filler and traps can land in any world in the
multiworld.

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