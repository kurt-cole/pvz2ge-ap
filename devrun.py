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
  python devrun.py /path/to/PVZGE-Electron   # override build dir

Without an argument the build directory is resolved from host.yaml's
pvz2gardendless.build_directory, then from the installer's default
(~/pvzge_ap_build).
"""

import importlib.util
import os
import subprocess
import sys

HERE   = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.join(HERE, "pvz2gardendless", "build_pvzge_ap.py")

# The installer's own default, and the fallback here when nothing else says
# otherwise. Kept in sync with build_pvzge_ap.py's BuilderApp default.
DEFAULT_BUILD_DIR = os.path.normpath(os.path.expanduser("~/pvzge_ap_build"))

# Retained so an existing Windows checkout keeps working without arguments.
# Only used when it is actually on disk, so it costs other platforms nothing.
LEGACY_ELECTRON_DIR = r"C:\Games (C)\pvz 2\Archipelago PVZ2\PVZGE-Electron"


def host_yaml_build_dir():
    """pvz2gardendless.build_directory from host.yaml, if Archipelago is importable.

    devrun runs outside Archipelago as often as not, so a failure to import it
    is expected and not worth reporting.
    """
    try:
        from settings import get_settings
        value = get_settings().pvz2gardendless.build_directory
    except Exception:
        return None
    return os.path.normpath(os.path.expanduser(value)) if value else None


def resolve_electron_dir(args):
    """First candidate that exists: CLI argument, host.yaml, the default.

    Falls through to the default even when it is absent so the error message
    names the path the installer would have used.
    """
    if args:
        return os.path.normpath(os.path.expanduser(args[0]))

    candidates = []
    from_yaml = host_yaml_build_dir()
    if from_yaml:
        candidates.append(os.path.join(from_yaml, "PVZGE-Electron"))
    candidates.append(os.path.join(DEFAULT_BUILD_DIR, "PVZGE-Electron"))
    candidates.append(LEGACY_ELECTRON_DIR)

    for path in candidates:
        if os.path.isdir(os.path.join(path, "pvzge_web", "docs")):
            return path
    return candidates[0]


def load_patch_content() -> str:
    spec = importlib.util.spec_from_file_location("build_pvzge_ap", SOURCE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # safe: main() is __main__-guarded
    return mod.TMPPATCH_CONTENT


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    electron_dir = resolve_electron_dir(args)

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
