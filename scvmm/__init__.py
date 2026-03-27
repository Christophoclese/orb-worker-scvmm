#!/usr/bin/env python

from importlib.metadata import version
from scvmm.main import ScvmmBackend

__all__ = ['ScvmmBackend']

__version__ = version("orb-worker-scvmm")
