"""Where the game source is, and where our artifacts go.

The game checkout is NOT in this repo (see .gitignore: "Base Game/"). Every
extractor takes a root and every consumer tolerates its absence -- the whole
pipeline has a structure-only mode that runs off the apworld alone.
"""
import os

DATA_DIR      = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT     = os.path.dirname(DATA_DIR)
GENERATED_DIR = os.path.join(DATA_DIR, "generated")
CURATED_DIR   = os.path.join(DATA_DIR, "curated")
SITE_DIR      = os.path.join(DATA_DIR, "site")

# Candidate locations for a pvzge_web checkout, most local first. The build
# directory devrun.py defaults to is included so a machine that has already run
# the full installer needs no flag.
_GAME_CANDIDATES = (
    # What the installer actually produces: build/<name>/PVZGE-Electron clones
    # pvzge_web inside itself, so a machine that has run the full build once
    # already has the asset tree and needs no flag.
    os.path.join(REPO_ROOT, "build", "PVZGE-AP", "PVZGE-Electron", "pvzge_web"),
    os.path.join(REPO_ROOT, "Base Game"),
    os.path.join(REPO_ROOT, "Base Game", "pvzge_web"),
    r"C:\Games (C)\pvz 2\Archipelago PVZ2\PVZGE-Electron\pvzge_web",
)


def _discovered_builds():
    """Any build/<anything>/PVZGE-Electron/pvzge_web, so a differently named
    build directory is found without editing this list."""
    root = os.path.join(REPO_ROOT, "build")
    if not os.path.isdir(root):
        return []
    out = []
    for name in sorted(os.listdir(root)):
        candidate = os.path.join(root, name, "PVZGE-Electron", "pvzge_web")
        if os.path.isdir(candidate):
            out.append(candidate)
    return out

# Every converted-JSON asset lives under one of these, relative to the checkout
# root. Tried in order; the first that exists wins.
_RESOURCE_SUBDIRS = (
    os.path.join("docs", "assets", "resources", "import"),
    os.path.join("assets", "resources", "import"),
    os.path.join("resources", "import"),
    "import",
)


def find_game_root(explicit=None):
    """Root of a pvzge_web checkout, or None.

    None is a supported answer everywhere downstream: it means "structure only,
    no measurements", not an error.
    """
    candidates = (([explicit] if explicit else []) + list(_GAME_CANDIDATES)
                  + _discovered_builds())
    for root in candidates:
        if root and os.path.isdir(root) and find_resource_dir(root):
            return os.path.abspath(root)
    return None


def find_resource_dir(game_root):
    """The `import/` tree of converted JSON under a checkout, or None."""
    if not game_root:
        return None
    for sub in _RESOURCE_SUBDIRS:
        path = os.path.join(game_root, sub)
        if os.path.isdir(path):
            return path
    return None


def generated(name):
    return os.path.join(GENERATED_DIR, name)


def curated(name):
    return os.path.join(CURATED_DIR, name)
