# PvZ2 Gardendless — Archipelago World

An [Archipelago](https://archipelago.gg) multiworld integration for **PvZ2 Gardendless**, a web-based
reimagining of Plants vs. Zombies 2 ([PVZGE-Electron](https://github.com/Twig6943/PVZGE-Electron) /
[pvzge_web](https://github.com/Gzh0821/pvzge_web)). Each world (except Ancient Egypt) is unlocked by
finding three Progressive World items: the first opens it, the other two open its later stretches.
Victory is completing a configurable number of worlds -- each world's Zomboss, its final level, or
its World Key level, whichever the goal type picks.

## Installation

### Full build (sets up the game client as a native app)

This produces the actual game -- an Electron app with the Archipelago client injected -- via a Tk GUI
installer, not a CLI build. Launch it either:

- **From Archipelago**: install the `.apworld`, open the Archipelago Launcher, and click
  **"PvZ2 Gardendless Installer"**.
- **Standalone**: `python pvz2gardendless/build_pvzge_ap.py`

Pick a build directory in the GUI and press START BUILD. It will:

1. Download the few files it uses from `PVZGE-Electron` (the Electron wrapper's `main.js`,
   `package.json` and icons).
2. Download `pvzge_web/docs` (the game, ~1.3GB, from `master`).
3. Overwrite `tmpPatch.js` with the Archipelago client code (save-slot redirection, plant-unlock gating,
   location/item sync, etc.).
4. Patch `main.js` to enable F12 devtools and load the game from the build folder.
5. Download the official Electron release the wrapper names (~100MB, checked against its
   `SHASUMS256.txt`) and drop the wrapper into its `resources/app`, which Electron runs as-is.

The result is `PvZ Gardendless AP/` in the build folder, plus `PvZ Gardendless AP.lnk` on Windows or
`PvZ Gardendless AP.sh` on Linux; on macOS it is `PvZ Gardendless AP.app`. The Linux launcher passes
`--no-sandbox` when the kernel or AppArmor disables unprivileged user namespaces.

**Requirements:** an internet connection. Nothing else: Only Python's standard library is used, which Archipelago already ships.

**Updates are incremental.** Downloads diff GitHub's file listing against the build folder by git
blob SHA (`ap_sync_*.json` caches the hashes), so UPDATE fetches only the files that changed upstream,
and Electron is only downloaded again when the wrapper moves to a new version. The first run fetches
the game as one archive. A build folder made by an older, git/npm-based installer is converted in
place: its game files are hashed rather than downloaded again, and its `node_modules`, `release/`,
`.git` folders and old packaged apps are removed afterwards.

The installer makes about four GitHub API calls per update, well inside GitHub's 60 an hour for
unauthenticated use. Setting `GITHUB_TOKEN` raises that limit if a shared network ever exhausts it.

### Packaging the apworld itself

`build_apworld.py` at the repo root zips the Python world into
`build/pvz2gardendless.apworld`, which is the file you install into Archipelago. It is separate from
the full build above: this packages the logic, that packages the game.

```
python build_apworld.py            # write build/pvz2gardendless.apworld
python build_apworld.py --check    # ...then generate three seeds from the zip itself
python build_apworld.py --list     # show what would ship, write nothing
python build_apworld.py -o path/to/other.apworld
```

Standard library only, and the same on Windows and Linux. It ships the package's `.py` files and the
two guides in `pvz2gardendless/docs/` and nothing else, on an allow-list, so `__pycache__`, `.pyc`
files, scratch JSON and editor leftovers cannot reach a player. A stale `.pyc` inside the zip shadows
the source next to it, which is a confusing way to ship last week's logic.

The output is reproducible: fixed member timestamps and permissions, sorted order, so two builds of
the same sources hash identically and the printed SHA-256 identifies the contents rather than the
moment it was built. `--check` extracts the zip to a temporary directory and runs
`generate_early` through `fill_slot_data` against *that* copy in a child interpreter, which is what
catches a module that imports fine from the repo and is missing from the apworld.

Run `python test/run.py` first; this script does not.

### Fast iteration on the client JS (Primarily for development)

Once you've run the full build once, use `devrun.py` instead of rebuilding -- it skips the
update checks and downloads entirely:

```
python devrun.py                              # patch + launch the installed app
python devrun.py --patch-only                  # just rewrite tmpPatch.js, don't launch
python devrun.py "D:\custom\PVZGE-Electron"    # override build dir
```

It rewrites `tmpPatch.js` from the same client source embedded in `build_pvzge_ap.py` and launches
the installed app, so edits show up in seconds. A build folder from the older npm-based installer
falls back to `npm start`. The default
build directory is `C:\Games (C)\pvz 2\Archipelago PVZ2\PVZGE-Electron`; pass a path as the first
argument if yours differs.