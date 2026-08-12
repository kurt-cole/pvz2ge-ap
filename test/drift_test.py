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
STUBS = {"svSt", "toast", "log", "installStoreHook_stub"}

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
            if name in STUBS:
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
