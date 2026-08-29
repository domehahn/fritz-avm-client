"""Typed domain models for Fritz!Box mesh topology, WAN stats, and devices."""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Tuple


@dataclass(frozen=True)
class CpuTemperature:
    """Represents CPU temperature readings."""
    temperatures: Dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class WanStats:
    """WAN connection statistics and real-time rates."""
    total_bytes_received: Optional[int] = None
    total_bytes_sent: Optional[int] = None
    current_download_rate: Optional[int] = None
    current_upload_rate: Optional[int] = None
    max_downstream_rate: Optional[int] = None
    max_upstream_rate: Optional[int] = None
    device_uptime: Optional[int] = None
    connection_uptime: Optional[int] = None
    external_ip: Optional[str] = None
    is_connected: Optional[bool] = None
    cpu_temperatures: Dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class DslStats:
    """DSL line quality metrics."""
    downstream_attenuation: Optional[float] = None
    upstream_attenuation: Optional[float] = None
    downstream_noise_margin: Optional[float] = None
    upstream_noise_margin: Optional[float] = None


@dataclass(frozen=True)
class WlanStats:
    """Aggregated WiFi interface statistics."""
    total_packets_sent: int = 0
    total_packets_received: int = 0


@dataclass(frozen=True)
class Node:
    """Represents a Fritz! device in the mesh (router, repeater, powerline)."""
    name: str
    mac: str
    ip: Optional[str] = None
    is_router: bool = False
    is_repeater: bool = False
    is_powerline: bool = False
    extra: Dict[str, Any] = field(default_factory=dict)
    parent_node: Optional[str] = None


@dataclass(frozen=True)
class Device:
    """Represents a client device (phone, TV, computer, etc.)."""
    name: str
    mac: str
    ip: Optional[str] = None
    online: bool = False
    interface_type: Optional[str] = None
    connected_node: Optional[str] = None
    rx_bytes_total: Optional[int] = None
    tx_bytes_total: Optional[int] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MeshTopology:
    """Complete mesh network topology with nodes and devices."""
    nodes: Tuple[Node, ...] = field(default_factory=tuple)
    devices: Tuple[Device, ...] = field(default_factory=tuple)
