# PvZ2 Gardendless — Archipelago World

An [Archipelago](https://archipelago.gg) multiworld integration for **PvZ2 Gardendless**, a web-based
reimagining of Plants vs. Zombies 2 ([PVZGE-Electron](https://github.com/Twig6943/PVZGE-Electron) /
[pvzge_web](https://github.com/Gzh0821/pvzge_web)). Each world (except Ancient Egypt) is unlocked by
finding its unique Key item, Modern Day unlocks once a configurable number of world goals are met, and
victory is defeating the Modern Day Zomboss.

## Installation

### Full build (packages the game client as an .exe)

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
6. Run `npm run build:win` (or `:mac` / `:linux`), producing `PvZ Gardendless AP.exe`.

This takes several minutes the first time (clone + `npm install` + packaging).

**Requirements:** Python 3.8+, Node.js 18+, Git, and an internet connection for the initial clone.

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
