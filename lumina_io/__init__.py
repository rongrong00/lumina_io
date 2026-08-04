from . import util
from . import units
from . import derived
from . import groupcat
from . import snapshot
from . import grid
from . import lightcone
from . import bh
from . import projections
from . import powerspectra
from . import dmo
from ._backend import HAVE_CORE

__version__ = '0.1.0'

def set_num_threads(n):
    if HAVE_CORE:
        from . import _core
        _core.set_num_threads(n)
