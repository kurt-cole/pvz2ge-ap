# PvZ2 Gardendless — Archipelago World

An [Archipelago](https://archipelago.gg) multiworld integration for **PvZ2 Gardendless**, a web-based
reimagining of Plants vs. Zombies 2 ([PVZGE-Electron](https://github.com/Twig6943/PVZGE-Electron) /
[pvzge_web](https://github.com/Gzh0821/pvzge_web)). Each world (except Ancient Egypt) is unlocked by
finding three Progressive World items: the first opens it, the other two open its later stretches.
Victory is completing a configurable number of worlds -- each world's Zomboss, its final level, or
its World Key level, whichever the goal type picks.

## Installation

### Full build (packages the game client as a native app)

This produces the actual game — an Electron app with the Archipelago client injected — via a Tk GUI
installer, not a CLI build. Launch it either:

- **From Archipelago**: install the `.apworld`, open the Archipelago Launcher, and click
  **"PvZ2 Gardendless Installer"**.
- **Standalone**: `python pvz2gardendless/build_pvzge_ap.py`

Pick a build directory in the GUI, then it will:

1. Check that `git`, `node`, and `npm` are on your PATH.
2. Clone `PVZGE-Electron` (the Electron wrapper) and `pvzge_web` (the game source, ~300MB, from `master`).
3. Overwrite `tmpPatch.js` with the Archipelago client code (save-slot redirection, plant-unlock gating,
   location/item sync, etc.).
4. Patch `main.js` to enable F12 devtools.
5. Run `npm install`.
6. Run `npm run build:win` (or `:mac` / `:linux`), producing `PvZ Gardendless AP.exe`,
   `PvZ Gardendless AP.dmg`, or `PvZ Gardendless AP.AppImage` respectively.

On Linux the installer also writes `PvZ Gardendless AP.sh`, a launcher for the unpacked build that
electron-builder leaves in `PVZGE-Electron/release/linux-unpacked/`. It is the fallback for systems
with no FUSE runtime, where an AppImage cannot mount itself, which covers atomic distros such as
Bazzite and SteamOS. It also passes `--no-sandbox` when the kernel has unprivileged user namespaces
disabled.

This takes several minutes the first time (clone + `npm install` + packaging).

**Requirements:** Python 3.8+, Node.js 18+, Git, and an internet connection for the initial clone.
`git`, `node` and `npm` must all be on your PATH; on many Linux distributions `npm` ships as a
separate package from `node`. Nothing else is required, and nothing needs root.

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

Once you've run the full build once, use `devrun.py` instead of rebuilding — it skips the clone,
`npm install`, and packaging steps entirely:

```
python devrun.py                              # patch + launch via `npm start`
python devrun.py --patch-only                  # just rewrite tmpPatch.js, don't launch
python devrun.py "D:\custom\PVZGE-Electron"    # override build dir
```

It rewrites `tmpPatch.js` from the same client source embedded in `build_pvzge_ap.py` and launches
unpackaged via `npm start`, so edits show up in seconds instead of a multi-minute rebuild. The default
build directory is `C:\Games (C)\pvz 2\Archipelago PVZ2\PVZGE-Electron`; pass a path as the first
argument if yours differs.
