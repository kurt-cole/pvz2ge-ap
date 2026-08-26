"""Guard against the client-JS test copies drifting from the real client.

The injected client lives as one big Python string (TMPPATCH_CONTENT) inside
build_pvzge_ap.py, which node cannot require. So test/client/*_fn.js hold
copies of the functions under test, wrapped in enough stubs to run headless.

That copy is the whole risk: edit the client, forget the copy, and the JS
tests keep passing green against logic the game no longer runs. This asserts
every non-stub function in a _fn.js still appears verbatim (ignoring
whitespace) in build_pvzge_ap.py.

If this fails, the fix is to re-copy the function from build_pvzge_ap.py into
the _fn.js file -- never to relax the check.
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
CLIENT_SRC = os.path.join(REPO, "pvz2gardendless", "build_pvzge_ap.py")

# Harness scaffolding, not client logic: these exist only so the copied
# functions have something to call. They are expected NOT to match.
# An entry is either a bare name (a stub in any file) or "file.js:name" for a
# name that is a stub in ONE file but a real client function elsewhere. Qualify
# wherever you can: a bare name switches the check off everywhere.
STUBS = {"svSt", "toast", "log", "installStoreHook_stub",
         "makeZombiesClass", "setLevel",
         # conveyor_fn.js harness: sets the level's own haveWater flag, which
         # the real client reads off the game rather than declaring.
         "setLevelWater",
         # connect_fn.js harness. setStatus/onPkt/findOrCreateAPSlot/svCfg ARE
         # real client functions, so these are qualified -- connect() only
         # needs something callable, and a copy of each would drag in most of
         # the client. setTimeout is captured so the retry can be run without
         # waiting; reset/runNextTimer drive the harness.
         "connect_fn.js:setStatus", "connect_fn.js:onPkt",
         "connect_fn.js:findOrCreateAPSlot", "connect_fn.js:svCfg",
         "connect_fn.js:setTimeout", "connect_fn.js:reset",
         "connect_fn.js:runNextTimer",
         # goal_fn.js harness. isFinished IS a real client function, so it is
         # qualified: copying it would drag in the tutorial chain and the whole
         # save shape, where all goalPlayed() needs is "has this level been
         # beaten". play() is its counterpart to check() -- the two being
         # separable is the entire point of counting levels played rather than
         # locations checked.
         "goal_fn.js:isFinished", "goal_fn.js:play",
         # store_fn.js harness: stand-ins for the client's socket and module
         # scope, plus applyLocationInfo, which mirrors a switch arm rather
         # than a function and so has nothing to match verbatim.
         "send", "resetShopState", "setLocations", "applyLocationInfo",
         # store_fn.js harness: stands in for the Connected packet, which is
         # what fills slotLocationIds in the real client. slotHasLocation
         # itself IS a copy and is checked.
         "store_fn.js:setSlotLocations",
         # currency_fn.js harness: reset() rebuilds module scope between cases,
         # svSt counts saves. restoreLostCurrency/observeCurrency themselves
         # ARE real client functions and are checked.
         "currency_fn.js:reset", "currency_fn.js:restoreDone",
         # command_fn.js harness: reset() rebuilds module scope between cases,
         # and applyPendingCurrency is modelled rather than copied -- the real
         # one drives the live HUD component, which this suite has no use for.
         # The currency suite checks the real one. apChatLedger, apChatResync
         # and handleChatCommand themselves ARE copies and are checked.
         "command_fn.js:reset", "command_fn.js:applyPendingCurrency",
         # deathlink_fn.js harness: reset() rebuilds module scope between
         # cases, enterLevel() stands in for the game's UI class, and
         # setTimeout is captured so the suppression window can be inspected
         # before it lifts. deathLinkActive, applyDeathLinkPref, sendDeathLink
         # and applyRemoteDeath themselves ARE copies and are checked.
         "deathlink_fn.js:reset", "deathlink_fn.js:enterLevel",
         "deathlink_fn.js:setTimeout",
         # goal_fn.js harness: reset() rebuilds module scope between cases and
         # check() records a check the way fireCheck does. isChecked,
         # victoryLoc, canAccessModernDay, goalMet and maybeSendGoal ARE
         # copies and are checked.
         # goal_fn.js harness: poll() models pollChecks' ORDER -- observe what
         # the save says was beaten, then rebuild the save from the ledger --
         # without the socket, traps, costumes and hook installs the real one
         # also drives. recordPlayed, isPlayed, playedList and
         # restoreLevelProgress, the functions that order exists to protect,
         # ARE copies and are checked.
         "goal_fn.js:reset", "goal_fn.js:check", "goal_fn.js:poll",
         # goal_fn.js harness: setServerChecked() stands in for the Connected
         # packet plus the DataPackage id map, and rebuildAPSave() is cut down
         # to the one step the merge is being judged on. mergeServerChecks
         # itself IS a copy and is checked -- it is the last place a check
         # still implies a level was played.
         "goal_fn.js:setServerChecked", "goal_fn.js:rebuildAPSave",
         # worldgate_fn.js harness: reset() rebuilds module scope between
         # cases, makeKeyListener() stands in for the game class the hook is
         # installed on, and gates() is a slot_data fixture. rebuildLevelGates,
         # unlocksHeld, levelBlockedBy and installLevelGateHook themselves ARE
         # copies and are checked.
         "worldgate_fn.js:reset", "worldgate_fn.js:makeKeyListener",
         "worldgate_fn.js:gates"}

_ws = re.compile(r"\s+")
norm = lambda s: _ws.sub(" ", s).strip()


def functions(text):
    """Every `function name(...) { ... }` in text, by brace matching.

    Regex alone cannot find the closing brace of a function containing nested
    braces, and all of these do.
    """
    out = {}
    for m in re.finditer(r"function (\w+)\s*\(", text):
        name = m.group(1)
        start = text.index("{", m.end() - 1)
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    out[name] = text[m.start():i + 1]
                    break
    return out


def main():
    source = norm(open(CLIENT_SRC, encoding="utf-8").read())
    client_dir = os.path.join(HERE, "client")
    failures, checked, skipped = [], 0, []

    for fname in sorted(os.listdir(client_dir)):
        if not fname.endswith("_fn.js"):
            continue
        text = open(os.path.join(client_dir, fname), encoding="utf-8").read()
        found = functions(text)
        if not found:
            failures.append(f"{fname}: no functions found -- did the format change?")
        for name, body in sorted(found.items()):
            if name in STUBS or f"{fname}:{name}" in STUBS:
                skipped.append(f"{fname}:{name}")
                continue
            if norm(body) in source:
                checked += 1
            else:
                failures.append(
                    f"{fname}: {name}() no longer matches build_pvzge_ap.py -- "
                    f"re-copy it from the client")

    for f in failures:
        print("  FAIL  " + f)
    print(f"  ok    {checked} client functions match build_pvzge_ap.py verbatim")
    print(f"  ok    {len(skipped)} harness stubs skipped ({', '.join(skipped)})")

    if failures:
        print(f"\n{len(failures)} FAILURE(S)")
        return 1
    print("\nCLIENT COPIES IN SYNC")
    return 0


if __name__ == "__main__":
    sys.exit(main())
