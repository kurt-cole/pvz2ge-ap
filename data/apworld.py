"""Import the apworld offline.

`pvz2gardendless/__init__.py` imports `worlds.AutoWorld`, which only exists
inside a full Archipelago checkout. test/apstub.py is the repo's hand-written
stand-in for it, and importing apstub registers those module names -- so this
one import is all it takes to read the real generation code with no AP
installed. Every module here that touches the apworld imports through this.

Nothing is copied or mirrored: constants, locations and items are the real
ones, which is what makes the site show the logic that actually ships.
"""
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)

for path in (os.path.join(_ROOT, "test"), _ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)

import apstub  # noqa: F401,E402  -- registers BaseClasses, Options, worlds.*

from pvz2gardendless import constants as C          # noqa: E402,F401
from pvz2gardendless import items as I              # noqa: E402,F401
from pvz2gardendless import locations as L          # noqa: E402,F401
from pvz2gardendless import zombie_data as Z        # noqa: E402,F401
