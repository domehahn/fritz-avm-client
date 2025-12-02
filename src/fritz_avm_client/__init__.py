"""Fritz!Box AVM Client - Extended client for AVM Fritz!Box routers."""

__version__ = "0.1.0"

from .client import FritzClient
from .models import Node, Device
from .discovery import MeshDiscovery
from .config import Settings

__all__ = [
    "FritzClient",
    "Node",
    "Device",
    "MeshDiscovery",
    "Settings",
]
