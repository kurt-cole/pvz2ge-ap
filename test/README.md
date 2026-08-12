# Offline test suite

```
python test/run.py
```

Needs nothing but Python and (optionally) Node. No Archipelago install, no
game source, no built apworld, no network. The JS suites are skipped with a
warning if `node` is not on PATH.

Archipelago cannot be imported outside a full AP checkout, so `apstub.py` is a
hand-written stand-in for `BaseClasses`, `Options`, `settings` and `worlds.*`,
including `CollectionState`/`sweep`, `early_items`, `get_regions` and
`forbid_items_for_player`. It models only what this world touches.

| Suite | Covers |
| --- | --- |
| `gen_test.py` | Item pool exactly fills locations, no stray keys or regions for disabled worlds, goal clamping, upgrade copies, append-only item IDs, the starting plant, the early sun producer, `early_world_keys` placement |
| `sphere_test.py` | Everything is reachable with the full item set, spheres actually layer rather than opening at once, and each world's entry rules bite |
| `drift_test.py` | Every function in `client/*_fn.js` still matches `build_pvzge_ap.py` |
| `client/upgrade_test.js` | Progressive upgrade grants and prefix logic |
| `client/store_test.js` | A bought store card does not come back |
| `client/conveyor_test.js` | Belt swaps stay inside a plant's power band and are deterministic |
| `client/costume_test.js` | Costume grants, banking, and the shuffle trap never destroying a costume |

## Why the `_fn.js` copies exist

The injected client is one big Python string (`TMPPATCH_CONTENT`) inside
`build_pvzge_ap.py`, which Node cannot `require`. So `client/*_fn.js` hold
copies of the functions under test with just enough stubs to run headless.

That copy is the risk: edit the client, forget the copy, and the JS suites go
on passing against logic the game no longer runs. `drift_test.py` exists to
catch exactly that, asserting every non-stub function still appears verbatim
(whitespace aside) in `build_pvzge_ap.py`.

**If `drift_test.py` fails, re-copy the function out of `build_pvzge_ap.py`.
Never relax the check.**

## Adding a data-derived list

Anything derived from the game files (attackers, single-use plants, fire
auras) gets a named regression test in `gen_test.py` naming the specific
plants that must and must not be there, with the reason. Several of these
lists have been wrong in ways that only showed up in a real seed.

## Harness bugs to watch for

Two of these have produced false passes:

- `Region.can_reach` returning `True` unconditionally made every goal look
  reachable and put Modern Day in sphere 1 of every measurement.
- Probing an item rule with a key taken from the item pool passed vacuously on
  a 1-world seed, which has no keys at all -- `all()` over an empty set is
  `True`. Use a synthetic item.

When a test proves a negative, make it fail on purpose once before trusting it.
