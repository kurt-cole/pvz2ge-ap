"""
PvZ2 Gardendless: the conveyor swap tables, read from the injected client.

The belt swap's data (ID_TO_CN, CONVEYOR_GROUPS, CONVEYOR_FAMILIES, CONVEYOR_DPS,
the shadow set, the answer sets, the terrain sets) is declared once, in
TMPPATCH_CONTENT (build_pvzge_ap.py). Generation rolls belts now (belt_roll.py),
so rather than keep a second copy that could drift, this module parses those
declarations out of the client source with a small JS-literal reader.

Only the literal forms the declarations use are understood: object and array
literals, single- or double-quoted strings, numbers, `new Set([...])`, and a
bare identifier naming another declaration read here. Anything else raises.
"""

import pkgutil
import re
from typing import Any, Dict, List

_NAMES = (
    "AP_WARM_PLANT", "AP_THREAT_FALLBACK", "AP_PUZZLE_BELTS", "ID_TO_CN",
    "CONVEYOR_GROUPS", "CONVEYOR_FAMILIES", "CONVEYOR_DPS", "CONVEYOR_SHADOW",
    "CONVEYOR_SHADOW_CHANCE", "CONVEYOR_SHADOW_MIN_SLOTS", "CONVEYOR_BELT_LOCKED",
    "CONVEYOR_KILLING_INSTANTS", "CONVEYOR_EXCAVATOR_ANSWERS", "CONVEYOR_TORCH_ANSWERS",
    "CONVEYOR_COLD_ANSWERS", "CONVEYOR_JESTER_ANSWERS", "CONVEYOR_PARASOL_ANSWERS",
    "CONVEYOR_EXCLUDE", "CONVEYOR_WATER_ONLY", "CONVEYOR_TILE_LOCKED", "CONVEYOR_SKY_DEAD",
    "CONVEYOR_LEGACY_GROUPED", "CONVEYOR_NO_DAMAGE",
)


def _client_source() -> str:
    raw = pkgutil.get_data(__package__, "build_pvzge_ap.py")
    if raw is None:
        raise RuntimeError("build_pvzge_ap.py not found next to conveyor_tables.py")
    return raw.decode("utf8")


class _Reader:
    TOKEN = re.compile(r"""
        \s+ | //[^\n]* | /\*.*?\*/                       # skipped
      | (?P<str>'(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*")
      | (?P<num>-?\d+(?:\.\d+)?)
      | (?P<id>[A-Za-z_$][\w$]*)
      | (?P<p>[{}\[\](),:;.])
    """, re.S | re.X)

    def __init__(self, text: str, pos: int, env: Dict[str, Any]):
        self.text, self.pos, self.env = text, pos, env
        self.tok = None
        self._next()

    def _next(self):
        while True:
            m = self.TOKEN.match(self.text, self.pos)
            if not m:
                raise ValueError(f"unreadable JS at {self.text[self.pos:self.pos + 40]!r}")
            self.pos = m.end()
            kind = m.lastgroup
            if kind is None:
                continue
            self.tok = (kind, m.group(kind))
            return

    def _expect(self, p):
        if self.tok != ("p", p):
            raise ValueError(f"expected {p!r}, got {self.tok!r}")
        self._next()

    def value(self):
        kind, v = self.tok
        if kind == "str":
            self._next()
            return v[1:-1].encode().decode("unicode_escape")
        if kind == "num":
            self._next()
            return float(v) if "." in v else int(v)
        if kind == "id" and v == "new":
            self._next()
            if self.tok != ("id", "Set"):
                raise ValueError(f"only `new Set` is read, got {self.tok!r}")
            self._next()
            self._expect("(")
            items = self.value()
            self._expect(")")
            return set(items)
        if kind == "id":
            self._next()
            if v not in self.env:
                raise ValueError(f"unknown identifier {v!r}")
            return self.env[v]
        if (kind, v) == ("p", "["):
            self._next()
            out = []
            while self.tok != ("p", "]"):
                out.append(self.value())
                if self.tok == ("p", ","):
                    self._next()
            self._next()
            return out
        if (kind, v) == ("p", "{"):
            self._next()
            out = {}
            while self.tok != ("p", "}"):
                kk, kv = self.tok
                key = kv[1:-1] if kk == "str" else (int(kv) if kk == "num" else kv)
                self._next()
                self._expect(":")
                out[key] = self.value()
                if self.tok == ("p", ","):
                    self._next()
            self._next()
            return out
        raise ValueError(f"unexpected {self.tok!r}")


def _read(src: str) -> Dict[str, Any]:
    env: Dict[str, Any] = {}
    for name in _NAMES:
        m = re.search(r"\bconst\s+" + name + r"\s*=\s*", src)
        if not m:
            raise ValueError(f"{name} is not declared in TMPPATCH_CONTENT")
        env[name] = _Reader(src, m.end(), env).value()
    return env


T: Dict[str, Any] = _read(_client_source())

# The derived tables, built exactly as the client builds them (build_pvzge_ap.py,
# after CONVEYOR_EXCLUDE). Object.values over integer keys runs in ascending
# key order.
POOL: List[str] = [T["ID_TO_CN"][k] for k in sorted(T["ID_TO_CN"])
                   if T["ID_TO_CN"][k] not in T["CONVEYOR_EXCLUDE"]]
KNOWN = frozenset(POOL)


def build_swaps(damage_rule: bool) -> Dict[str, List[str]]:
    """_apBuildConveyorSwaps: under conveyor_damage_rule the legacy-grouped
    plants (Torchwood) leave their group."""
    swaps: Dict[str, List[str]] = {}
    for key, group in T["CONVEYOR_GROUPS"].items():
        members = [c for c in group if c not in T["CONVEYOR_EXCLUDE"] and
                   not (damage_rule and c in T["CONVEYOR_LEGACY_GROUPED"])]
        if len(members) >= 2:
            for c in members:
                swaps[c] = members
    return swaps


SWAPS: Dict[str, List[str]] = build_swaps(False)          # seeds before the rule
SWAPS_DAMAGE: Dict[str, List[str]] = build_swaps(True)    # conveyor_damage_rule
FAMILY: Dict[str, str] = {}
for _fam, _group in T["CONVEYOR_FAMILIES"].items():
    for _c in _group:
        FAMILY[_c] = _fam
ROLE: Dict[str, str] = {}
for _key, _group in T["CONVEYOR_GROUPS"].items():
    for _c in _group:
        ROLE[_c] = _key.split(":")[0]
DPS: Dict[str, float] = T["CONVEYOR_DPS"]
SHADOW: List[str] = list(T["CONVEYOR_SHADOW"])
BELT_LOCKED = frozenset(T["CONVEYOR_BELT_LOCKED"])
TERRAIN_LOCKED = frozenset(T["CONVEYOR_WATER_ONLY"] | T["CONVEYOR_TILE_LOCKED"])
KILLING = frozenset(T["CONVEYOR_KILLING_INSTANTS"])
NO_DAMAGE = frozenset(T["CONVEYOR_NO_DAMAGE"])


def deals_damage(cn) -> bool:
    """_apDealsDamage: an attacker-group plant with damage of its own."""
    return ROLE.get(cn) == "attacker" and cn not in NO_DAMAGE
THREAT_ANSWERS = {
    "excavator": frozenset(T["CONVEYOR_EXCAVATOR_ANSWERS"]),
    "torch": frozenset(T["CONVEYOR_TORCH_ANSWERS"]),
    "cold": frozenset(T["CONVEYOR_COLD_ANSWERS"]),
    "jester": frozenset(T["CONVEYOR_JESTER_ANSWERS"]),
    "parasol": frozenset(T["CONVEYOR_PARASOL_ANSWERS"]),
}
THREAT_FALLBACK: Dict[str, str] = T["AP_THREAT_FALLBACK"]
PUZZLE_BELTS = frozenset(T["AP_PUZZLE_BELTS"])


def plantable(cn: str, has_water: bool, on_sky: bool) -> bool:
    """window._AP_conveyorPlantable."""
    if cn in T["CONVEYOR_TILE_LOCKED"]:
        return False
    if on_sky and cn in T["CONVEYOR_SKY_DEAD"]:
        return False
    if cn in T["CONVEYOR_WATER_ONLY"]:
        return bool(has_water)
    return True
