"""Yardmaster - Flatcar Container Linux Release Management Tool"""

import importlib.metadata

__version__ = importlib.metadata.version(__package__)
__author__ = "Flatcar Team"
__license__ = "Apache-2.0"

from yardmaster.core.release import ReleaseManager, ReleaseSpec
from yardmaster.core.version import Channel, Version

__all__ = ["ReleaseManager", "ReleaseSpec", "Version", "Channel"]
