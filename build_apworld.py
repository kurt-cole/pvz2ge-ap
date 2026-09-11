#!/usr/bin/env python3
"""Package pvz2gardendless/ into build/pvz2gardendless.apworld.

    python build_apworld.py                # build it
    python build_apworld.py --check        # ...and generate a seed from the zip
    python build_apworld.py --list         # show what would ship, write nothing

An apworld is a zip Archipelago imports as a package, so the only thing that has
to be right is WHAT GOES IN. This ships the package's .py files and the two
player docs and nothing else: no __pycache__, no test data, no generator inputs,
no editor leftovers. A stale .pyc inside the zip shadows the source beside it,
which is a genuinely confusing way to ship last week's logic.

Runs on Windows and Linux with the standard library alone. Paths are handled
through pathlib and written into the zip with forward slashes, which is what the
zip format requires on every platform -- a backslash in a member name is a
filename containing a backslash, not a directory, and Archipelago would fail to
import it.

The output is REPRODUCIBLE: members are added in sorted order with a fixed
timestamp and fixed permissions, so two builds of the same sources hash the same
and the printed SHA-256 is an identity for the contents rather than for the
moment it was built.

This does not run the test suite, clone the game, or touch a build directory.
`python test/run.py` is still the gate before shipping one of these, and
`python pvz2gardendless/build_pvzge_ap.py` is the separate, much larger installer
that packages the game itself.
"""

import argparse
import hashlib
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent
PACKAGE = "pvz2gardendless"
OUT = REPO / "build" / f"{PACKAGE}.apworld"

# What ships, by suffix and by where it sits. An allow-list rather than a
# deny-list: a new kind of file in the package should have to be named here
# before it reaches a player, and the failure mode of forgetting is a missing
# feature rather than a leaked 90MB of game data.
SHIPPED = {
    # every module of the package, wherever it sits inside it
    ".py": lambda rel: True,
    # the guides Archipelago's website serves, which live in docs/ only
    ".md": lambda rel: rel.parent.name == "docs",
}

# Directories never walked into, by name, at any depth.
SKIP_DIRS = {"__pycache__", ".git", ".github", ".idea", ".vscode", ".mypy_cache",
             ".pytest_cache", ".ruff_cache", "test", "tests", "build", "dist"}

# Files never shipped whatever their suffix says.
SKIP_NAMES = {".DS_Store", "Thumbs.db"}

# Fixed zip timestamp, for reproducibility. The zip format cannot store anything
# earlier than 1980, so this is about as early as a date can be.
ZIP_TIME = (1980, 1, 1, 0, 0, 0)
# Fixed member mode: rw-r--r-- for a regular file, which is what an imported
# module needs and no more.
ZIP_MODE = 0o644


def shipped_files(package_root: Path):
    """Every file that belongs in the apworld, repo-relative, sorted."""
    found = []
    for path in package_root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(package_root.parent)
        if any(part in SKIP_DIRS for part in rel.parts[:-1]):
            continue
        if path.name in SKIP_NAMES or path.name.startswith("."):
            continue
        keep = SHIPPED.get(path.suffix.lower())
        if keep and keep(rel):
            found.append(rel)
    return sorted(found, key=lambda rel: rel.as_posix())


def write_apworld(files, out: Path, root: Path = REPO) -> None:
    """Zip `files` (paths relative to `root`) into `out`."""
    out.parent.mkdir(parents=True, exist_ok=True)
    # Written to a temporary file beside the target and moved into place, so an
    # interrupted build leaves the previous apworld intact rather than a
    # half-written zip that Archipelago will try to import.
    tmp = out.with_suffix(out.suffix + ".partial")
    try:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            for rel in files:
                info = zipfile.ZipInfo(rel.as_posix(), date_time=ZIP_TIME)
                info.compress_type = zipfile.ZIP_DEFLATED
                # The high 16 bits of external_attr are the Unix mode. Setting
                # it explicitly is what keeps a build on Windows, where the
                # source files have no mode of their own, byte-identical to one
                # on Linux.
                info.external_attr = ZIP_MODE << 16
                # Relative to the REPO, never to the output: -o may point
                # anywhere, and deriving the source from the destination
                # silently reads the wrong files when it does.
                zf.writestr(info, (root / rel).read_bytes())
        tmp.replace(out)
    finally:
        if tmp.exists():
            tmp.unlink()


def check(out: Path) -> bool:
    """Generate a seed from the built zip, in a child interpreter.

    The point is to exercise the PACKAGED copy rather than the working tree: a
    module left out of the zip imports perfectly well from the repo and not at
    all from the apworld. Run in a subprocess so nothing it imports lands in
    this process, with the extracted zip ahead of test/ on the path.
    """
    harness = REPO / "test" / "apstub.py"
    if not harness.exists():
        print("skipping --check: test/apstub.py is not in this checkout")
        return True
    work = Path(tempfile.mkdtemp(prefix="apworld-check-"))
    try:
        with zipfile.ZipFile(out) as zf:
            zf.extractall(work)
        script = (
            "import sys\n"
            f"sys.path.insert(0, {str(REPO / 'test')!r})\n"
            f"sys.path.insert(0, {str(work)!r})\n"
            "import apstub\n"
            "from apstub import MultiWorld\n"
            f"import {PACKAGE} as W\n"
            f"assert W.__file__.startswith({str(work)!r}), W.__file__\n"
            "from opts import Opts\n"
            "for label, kw in (('default', {}), ('one world', dict(world_count=1)),\n"
            "                  ('everything', dict(world_count=13,\n"
            "                                      include_levels_past_goal=1))):\n"
            "    mw = MultiWorld()\n"
            "    w = W.PvZ2GardendlessWorld(mw, 1)\n"
            "    w.options = Opts(**kw)\n"
            "    w.generate_early(); w.create_regions(); w.set_rules()\n"
            "    w.create_items(); w.fill_slot_data()\n"
            "    print(f'  {label:11s} {len(w.active_locations()):4d} locations, "
            "{len(mw.itempool):4d} items')\n"
        )
        done = subprocess.run([sys.executable, "-c", script],
                              capture_output=True, text=True)
        if done.returncode:
            print("the packaged apworld failed to generate:")
            print(done.stdout.rstrip())
            print(done.stderr.rstrip(), file=sys.stderr)
            return False
        print(done.stdout.rstrip())
        return True
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="generate a seed from the built zip afterwards")
    ap.add_argument("--list", action="store_true",
                    help="print what would ship and exit without writing")
    ap.add_argument("-o", "--output", type=Path, default=OUT,
                    help=f"where to write it (default: {OUT.relative_to(REPO)})")
    args = ap.parse_args()

    package_root = REPO / PACKAGE
    if not (package_root / "__init__.py").is_file():
        print(f"no {PACKAGE}/__init__.py under {REPO}; run this from the repo",
              file=sys.stderr)
        return 1

    files = shipped_files(package_root)
    if not files:
        print(f"nothing to ship out of {package_root}", file=sys.stderr)
        return 1

    if args.list:
        for rel in files:
            print(f"  {rel.as_posix()}")
        print(f"{len(files)} files")
        return 0

    out = args.output if args.output.is_absolute() else REPO / args.output
    before = hashlib.sha256(out.read_bytes()).hexdigest() if out.is_file() else None

    write_apworld(files, out)

    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    with zipfile.ZipFile(out) as zf:
        broken = zf.testzip()
    if broken:
        print(f"the zip is corrupt at {broken}", file=sys.stderr)
        return 1

    try:
        shown = out.relative_to(REPO).as_posix()
    except ValueError:
        shown = str(out)
    print(f"{shown}  {len(files)} files, {out.stat().st_size} bytes")
    for rel in files:
        print(f"  {rel.as_posix()}")
    print(f"sha256 {digest}")
    if before is None:
        print("(new file)")
    elif before == digest:
        print("(identical to the previous build)")

    if args.check and not check(out):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
