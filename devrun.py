#!/usr/bin/env python3
"""
Fast dev loop for the AP client JS.

The full installer re-clones the game source, runs `npm install`, and then
packages an exe with electron-builder -- that last step is the 2-5 minute
one. None of it is needed when the only thing that changed is the injected
client, which is a single file: pvzge_web/docs/tmpPatch.js.

This script rewrites just that file from build_pvzge_ap.py's TMPPATCH_CONTENT
and launches the app unpackaged via `npm start` (electron .), which loads the
exact same pvzge_web/docs/index.html the packaged build would.

Requires the full installer to have been run at least once, since it reuses
that build directory (node_modules, cloned game source, patched main.js).

Usage:
  python devrun.py                    # patch + launch
  python devrun.py --patch-only       # patch, don't launch
  python devrun.py "D:\\path\\PVZGE-Electron"   # override build dir
"""

import importlib.util
import os
import subprocess
import sys

# Matches host.yaml's pvz2gardendless.build_directory + the installer's subdir.
DEFAULT_ELECTRON_DIR = r"C:\Games (C)\pvz 2\Archipelago PVZ2\PVZGE-Electron"

HERE   = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, "pvz2gardendless", "build_pvzge_ap.py")


def load_patch_content() -> str:
    spec = importlib.util.spec_from_file_location("build_pvzge_ap", SOURCE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # safe: main() is __main__-guarded
    return mod.TMPPATCH_CONTENT


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    electron_dir = args[0] if args else DEFAULT_ELECTRON_DIR

    docs = os.path.join(electron_dir, "pvzge_web", "docs")
    if not os.path.isdir(docs):
        sys.exit(f"Not found: {docs}\n"
                 "Run the full installer once before using this script.")

    target = os.path.join(docs, "tmpPatch.js")
    content = load_patch_content()
    with open(target, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Patched {target}  ({len(content):,} bytes)")

    if "--patch-only" in sys.argv:
        return

    print(f"Launching: npm start  (cwd={electron_dir})")
    raise SystemExit(subprocess.call("npm start", cwd=electron_dir, shell=True))


if __name__ == "__main__":
    main()
