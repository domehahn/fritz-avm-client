"""Data models for Fritz!Box mesh topology and devices."""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class Node:
    """Represents a Fritz! device in the mesh (router, repeater, powerline).
    
    Attributes:
        name: Device name (e.g., "Living Room Repeater")
        mac: MAC address
        ip: IP address (if available)
        is_router: True if this is the main router
        is_repeater: True if this is a WiFi repeater
        is_powerline: True if this is a powerline adapter
        extra: Additional device information from Fritz!Box API
        parent_node: Name or MAC of parent node in mesh hierarchy
    """
    name: str
    mac: str
    ip: Optional[str]
    is_router: bool
    is_repeater: bool
    is_powerline: bool
    extra: Dict[str, Any] = field(default_factory=dict)
    parent_node: Optional[str] = None


@dataclass
class Device:
    """Represents a client device (phone, TV, computer, etc.).
    
    Attributes:
        name: Device name
        mac: MAC address
        ip: IP address (if available)
        online: Connection status
        interface_type: Connection type (wlan/lan/guest)
        connected_node: Node name/MAC this device is connected to
        rx_bytes_total: Total bytes received
        tx_bytes_total: Total bytes transmitted
        extra: Additional device information from Fritz!Box API
    """
    name: str
    mac: str
    ip: Optional[str]
    online: bool
    interface_type: Optional[str] = None
    connected_node: Optional[str] = None
    rx_bytes_total: Optional[int] = None
    tx_bytes_total: Optional[int] = None
    extra: Optional[Dict[str, Any]] = None
