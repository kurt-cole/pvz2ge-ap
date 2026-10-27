"""The installer's git-free download and app setup, with the network faked.

build_pvzge_ap.py fetches the game by diffing GitHub's file listing against
what is on disk by git blob SHA, and patches the wrapper's main.js. None of it
may need the network to test: remote_commit, remote_tree and _fetch_raw are
swapped for a fake repo held in memory.

  * blob_sha agrees with git's own hash;
  * a first sync writes everything, a second downloads nothing;
  * only changed files are fetched, and only files this put there are removed;
  * a former git checkout (no manifest) is hashed, not re-downloaded;
  * the main.js patches are idempotent, and refuse an unrecognised main.js.
"""
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import apstub  # noqa: E402,F401

try:
    from pvz2gardendless import build_pvzge_ap as b  # noqa: E402
except ImportError as e:  # tkinter missing on a headless Python
    print(f"  skip  installer_test: {e}")
    sys.exit(0)

failed = 0


def fail(msg):
    global failed
    failed += 1
    print("  FAIL  " + msg)


def ok(msg):
    print("  ok    " + msg)


def check(cond, msg):
    (ok if cond else fail)(msg)


# ── blob_sha is git's hash ────────────────────────────────────────────────────

tmp = tempfile.mkdtemp(prefix="ap_installer_test_")
try:
    p = os.path.join(tmp, "f")
    open(p, "wb").close()
    # `git hash-object` of an empty file and of "hello\n".
    check(b.blob_sha(p) == "e69de29bb2d1d6434b8b29ae775ad8c2e48c5391",
          "blob_sha of an empty file matches git")
    with open(p, "wb") as f:
        f.write(b"hello\n")
    check(b.blob_sha(p) == "ce013625030ba8dba906f756967f9e9ca394464a",
          "blob_sha of a small file matches git")

    # ── sync against a fake repo ──────────────────────────────────────────────
    remote = {"docs/a.txt": b"a", "docs/sub/b.txt": b"b", "README.md": b"r"}
    commit = ["1" * 40]
    fetched = []

    b.remote_commit = lambda repo: commit[0]
    b.remote_tree = lambda repo, c, prefixes: {
        k: (b._git_blob_sha(v), len(v)) for k, v in remote.items()
        if k.startswith(prefixes)}

    def fake_raw(repo, c, rel, want):
        fetched.append(rel)
        return remote[rel]
    b._fetch_raw = fake_raw

    root = os.path.join(tmp, "repo")
    man = os.path.join(tmp, "manifest.json")
    repo = ("o", "r", "master")
    quiet = lambda *_: None

    def sync(rehash=False):
        fetched.clear()
        return b.sync_repo(repo, root, ("docs/",), man, quiet, tmp, rehash=rehash)

    os.makedirs(root)
    _, n, _ = sync()
    check(n == 2 and sorted(fetched) == ["docs/a.txt", "docs/sub/b.txt"],
          "a first sync fetches every file under the prefix and nothing else")
    check(open(os.path.join(root, "docs", "sub", "b.txt"), "rb").read() == b"b",
          "files land at their repo paths")

    _, n, _ = sync()
    check(n == 0 and not fetched, "a second sync downloads nothing")

    remote["docs/a.txt"] = b"a2"
    commit[0] = "2" * 40
    _, n, _ = sync()
    check(fetched == ["docs/a.txt"], "only the changed file is fetched")

    with open(os.path.join(root, "docs", "mine.txt"), "w") as f:
        f.write("kept")
    del remote["docs/sub/b.txt"]
    _, _, removed = sync()
    check(removed == 1 and not os.path.exists(os.path.join(root, "docs", "sub", "b.txt")),
          "a file removed upstream is removed locally")
    check(os.path.exists(os.path.join(root, "docs", "mine.txt")),
          "a file this never downloaded is left alone")

    with open(os.path.join(root, "docs", "a.txt"), "wb") as f:
        f.write(b"edited")
    sync()
    check(fetched == ["docs/a.txt"], "a file edited on disk is restored")

    os.remove(man)
    _, n, _ = sync()
    check(n == 0, "no manifest (a former git checkout): files are hashed, not re-downloaded")

    # ── main.js patches ───────────────────────────────────────────────────────
    upstream = (
        "function createWindow() {\n"
        "  win = new BrowserWindow({\n"
        "    width: 1280,\n"
        "  });\n\n"
        "  win.loadFile('pvzge_web/docs/index.html');\n"
        "}\n")
    once, good = b.externalize_game(b.add_window_icon(upstream), "/x/docs")
    twice, _ = b.externalize_game(b.add_window_icon(once), "/x/docs")
    check(good and once == twice, "main.js patches are idempotent")
    check(once.count(b._ICON_MARKER) == 1 and "AP_GAME_DOCS" in once,
          "main.js gets the window icon and the external game path")
    _, good = b.externalize_game("win.loadURL('x')", "/x/docs")
    check(not good, "an unrecognised main.js is refused, not shipped")

    # ── Electron version and asset ────────────────────────────────────────────
    pj = os.path.join(tmp, "package.json")
    with open(pj, "w") as f:
        f.write('{"devDependencies": {"electron": "^39.8.7"}}')
    check(b.electron_version(pj) == "39.8.7", "the Electron range resolves to its floor")
    asset = b.electron_asset("39.8.7", "Windows")
    check(asset.startswith("electron-v39.8.7-win32-") and asset.endswith(".zip"),
          "the Windows asset name follows Electron's release naming")
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\n{failed} FAILURE(S)" if failed else "\nINSTALLER OK")
sys.exit(1 if failed else 0)
