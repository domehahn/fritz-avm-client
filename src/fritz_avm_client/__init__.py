"""Fritz!Box AVM Client Package."""
from __future__ import annotations
from .config import Settings
from .capabilities import FritzCapabilities, CapabilityDetector
from .exceptions import (
    FritzError,
    FritzConfigurationError,
    FritzConnectionError,
    FritzTimeoutError,
    FritzAuthenticationError,
    FritzProtocolError,
    FritzServiceUnavailableError,
    FritzUnsupportedFeatureError,
)
from .models import (
    Node,
    Device,
    WanStats,
    DslStats,
    WlanStats,
    MeshTopology,
    CpuTemperature,
)
from .router import RouterClient
from .hosts import HostsClient
from .wlan import WlanClient
from .admin import AdminClient
from .mesh import MeshDiscovery
from .client import FritzClient

__all__ = [
    "Settings",
    "FritzCapabilities",
    "CapabilityDetector",
    "FritzError",
    "FritzConfigurationError",
    "FritzConnectionError",
    "FritzTimeoutError",
    "FritzAuthenticationError",
    "FritzProtocolError",
    "FritzServiceUnavailableError",
    "FritzUnsupportedFeatureError",
    "Node",
    "Device",
    "WanStats",
    "DslStats",
    "WlanStats",
    "MeshTopology",
    "CpuTemperature",
    "RouterClient",
    "HostsClient",
    "WlanClient",
    "AdminClient",
    "MeshDiscovery",
    "FritzClient",
]
