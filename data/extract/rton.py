"""An index over the game's converted asset tree.

THE FORMAT, because it is not what it looks like from the outside. Every file
under `docs/assets/resources/import/` is a **Cocos Creator asset pack**: a bare
JSON *array*, whose payload sits nested inside it. The PvZ2 data is the third
element of an entry in that array:

    [1, 0, 0, [["cc.JsonAsset", ...]], [[0,0,1,3]],
     [[0, "egypt19", {"#comment": "Egypt Chal 7, 1p2", "version": 1,
                      "objects": [ {"objclass": ..., "aliases": [...],
                                    "objdata": {...}}, ... ]}]]]

Two things follow, and both are load-bearing:

  1. **The string beside the payload is the document's name, and the document
     name is the RTID group.** `"egypt19"` is the level codename -- the same
     codename the client's LOC_LEVELS maps AP locations onto -- and
     `RTID(pea@ProjectileProps)` resolves in the document named
     `ProjectileProps`.
  2. **`@CurrentLevel` means "this document".** A level's waves are
     `RTID(Wave1@CurrentLevel)` and resolve against their own file, so
     resolution needs to know which document it is standing in. Resolving
     `Wave1` globally would pick whichever level happened to load first.

Defensive throughout. This is ~3500 third-party files that change with every
game update, so a file that will not parse, an object with no alias and a
reference that resolves to nothing are all COUNTED and skipped rather than
raised. `report()` is the honest account of how much of a run was real, and
build.py writes it to coverage.json.
"""
import json
import os
import re
from collections import Counter, defaultdict

RTID_RE = re.compile(r"^RTID\(([^@()]+)@([^@()]+)\)$")

# The group name a document uses to refer to itself.
SELF_GROUP = "CurrentLevel"


def parse_rtid(value):
    """('alias', 'Group') for an RTID string, else None."""
    if not isinstance(value, str) or not value.startswith("RTID("):
        return None
    m = RTID_RE.match(value.strip())
    return (m.group(1), m.group(2)) if m else None


def _find_documents(node, out):
    """Every (name, payload) pair in a Cocos pack.

    Walks rather than indexing [5][0] directly: the wrapper's shape varies with
    how many assets a pack holds, and a hard index would silently miss them.
    """
    if isinstance(node, list):
        if (len(node) >= 3 and isinstance(node[1], str)
                and isinstance(node[2], dict) and "objects" in node[2]):
            out.append((node[1], node[2]))
            return
        for item in node:
            _find_documents(item, out)
    elif isinstance(node, dict):
        for item in node.values():
            _find_documents(item, out)


class Document:
    __slots__ = ("name", "objects", "by_alias")

    def __init__(self, name, payload):
        self.name = name
        self.objects = []          # [(objclass, objdata)]
        self.by_alias = {}         # alias -> objdata
        for obj in payload.get("objects") or []:
            if not isinstance(obj, dict):
                continue
            objdata = obj.get("objdata")
            if not isinstance(objdata, dict):
                objdata = {}
            objclass = obj.get("objclass") or "?"
            self.objects.append((objclass, objdata))
            for alias in obj.get("aliases") or []:
                self.by_alias.setdefault(alias, objdata)

    def of_class(self, objclass):
        return [d for c, d in self.objects if c == objclass]

    def first_of_class(self, *objclasses):
        for objclass in objclasses:
            for c, d in self.objects:
                if c == objclass:
                    return d
        return None


class ObjectIndex:
    def __init__(self):
        self.docs = {}                          # doc name -> Document
        self.by_class = defaultdict(list)       # objclass -> [(doc, alias, data)]
        self.class_counts = Counter()
        self.files_read = 0
        self.files_failed = []
        self.docs_read = 0
        self.objects_read = 0
        self.objects_unaliased = 0
        self.unresolved = Counter()

    # ---- loading -------------------------------------------------------
    def load_tree(self, resource_dir, limit=None):
        for dirpath, _dirs, files in os.walk(resource_dir):
            for name in files:
                if not name.endswith(".json"):
                    continue
                self.load_file(os.path.join(dirpath, name))
                if limit and self.files_read >= limit:
                    return self
        return self

    def load_file(self, path):
        try:
            with open(path, "r", encoding="utf-8-sig") as fh:
                blob = json.load(fh)
        except Exception as exc:                       # noqa: BLE001 -- see docstring
            self.files_failed.append((os.path.basename(path), str(exc)[:120]))
            return
        self.files_read += 1
        found = []
        _find_documents(blob, found)
        for name, payload in found:
            doc = Document(name, payload)
            self.docs_read += 1
            # A duplicate document name is a real ambiguity, not a merge: the
            # first wins and the collision is counted, because silently merging
            # two levels' waves would be invisible and wrong.
            if name in self.docs:
                self.unresolved[f"duplicate document:{name}"] += 1
                continue
            self.docs[name] = doc
            for objclass, objdata in doc.objects:
                self.objects_read += 1
                self.class_counts[objclass] += 1
            aliased = set()
            for alias, objdata in doc.by_alias.items():
                aliased.add(id(objdata))
                for objclass, data in doc.objects:
                    if data is objdata:
                        self.by_class[objclass].append((name, alias, data))
                        break
            for objclass, objdata in doc.objects:
                if id(objdata) not in aliased:
                    self.objects_unaliased += 1
                    self.by_class[objclass].append((name, None, objdata))

    # ---- lookup --------------------------------------------------------
    def resolve(self, value, doc=None):
        """objdata for an RTID string. `doc` is the document it was read from.

        `@CurrentLevel` resolves inside `doc`. Everything else resolves in the
        named group; a group that is not a document name falls back to a
        by-alias sweep, because a handful of groups (LevelModules) are split
        across documents named for their own contents.
        """
        if isinstance(value, dict):
            return value
        ref = parse_rtid(value)
        if not ref:
            return None
        alias, group = ref
        if group == SELF_GROUP:
            hit = doc.by_alias.get(alias) if doc is not None else None
            if hit is not None:
                return hit
        target = self.docs.get(group)
        if target is not None:
            hit = target.by_alias.get(alias)
            if hit is not None:
                return hit
        for candidate in self.docs.values():
            hit = candidate.by_alias.get(alias)
            if hit is not None:
                return hit
        self.unresolved[f"{alias}@{group}"] += 1
        return None

    def alias_of_rtid(self, value):
        ref = parse_rtid(value)
        return ref[0] if ref else None

    def group(self, name):
        """A whole document by name -- 'ZombieProps', 'PlantProps', 'egypt19'."""
        return self.docs.get(name)

    def of_class(self, objclass):
        return self.by_class.get(objclass, [])

    def documents_with(self, objclass):
        """[(name, Document)] for every document holding such an object."""
        return [(name, doc) for name, doc in self.docs.items()
                if any(c == objclass for c, _ in doc.objects)]

    def report(self):
        return {
            "files_read": self.files_read,
            "files_failed": len(self.files_failed),
            "files_failed_sample": self.files_failed[:5],
            "documents": self.docs_read,
            "objects_read": self.objects_read,
            "objects_unaliased": self.objects_unaliased,
            "objclasses_top": dict(self.class_counts.most_common(25)),
            "unresolved_rtids": len(self.unresolved),
            "unresolved_sample": dict(self.unresolved.most_common(15)),
        }


def walk_objclasses(node, out=None):
    """Every nested `objclass` value, for module discovery inside a level."""
    out = [] if out is None else out
    if isinstance(node, list):
        for item in node:
            walk_objclasses(item, out)
    elif isinstance(node, dict):
        cls = node.get("objclass")
        if isinstance(cls, str):
            out.append(cls)
        for item in node.values():
            walk_objclasses(item, out)
    return out
