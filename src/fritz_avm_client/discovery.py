"""Mesh network discovery for Fritz!Box."""
from __future__ import annotations
from dataclasses import replace
from typing import List, Tuple, Dict, Any, Optional, TYPE_CHECKING
from .models import Node, Device
from .exceptions import (
    FritzError,
    FritzTimeoutError,
    FritzAuthenticationError,
    FritzConnectionError,
)

if TYPE_CHECKING:
    from .client import FritzClient


class MeshDiscovery:
    """Discover and map Fritz!Box mesh network topology.

    This class provides automatic discovery of:
    - Mesh nodes (router, repeaters, powerline adapters)
    - Client devices and their connections
    - Network hierarchy (parent-child relationships)
    - Device-to-node mappings
    - Link speed aggregation and WLAN stats

    Example:
        >>> from fritz_avm_client import FritzClient, MeshDiscovery, Settings
        >>> settings = Settings(fritz_host="192.168.178.1")
        >>> client = FritzClient(settings)
        >>> discovery = MeshDiscovery(client)
        >>> nodes, devices = discovery.discover()
        >>> for node in nodes:
        ...     print(f"{node.name}: {len([d for d in devices if d.connected_node == node.name])} devices")
    """

    def __init__(
        self,
        client: FritzClient,
        static_mappings: Optional[Dict[str, str]] = None,
        manual_hierarchy: Optional[Dict[str, str]] = None,
        model_name_mapping: Optional[Dict[str, str]] = None,
    ):
        """Initialize mesh discovery.

        Args:
            client: FritzClient instance
            static_mappings: Optional static IP to node name mappings
                Example: {'192.168.178.50': 'Living Room Repeater'}
            manual_hierarchy: Optional manual parent-child relationships (MAC -> Parent Name)
                Example: {'AA:BB:CC:DD:EE:FF': 'fritz.box'}
            model_name_mapping: Optional custom device display name mapping
                Example: {'FRITZ!Repeater 6000': 'Living Room Repeater'}
        """
        self.client = client
        self.static_mappings = static_mappings or {}
        self.manual_hierarchy = manual_hierarchy or {}
        self.model_name_mapping = model_name_mapping or {}

    def discover(self) -> Tuple[List[Node], List[Device]]:
        """Discover all mesh nodes and devices with their connections.

        Returns:
            Tuple of (nodes, devices) where:
                - nodes: List of mesh infrastructure nodes
                - devices: List of client devices with connection info
        """
        nodes: List[Node] = []
        devices: List[Device] = []

        if not self.client:
            return nodes, devices

        try:
            # 1. Get WLAN associations to map WiFi devices to their access points
            wlan_devices = self.client.get_wlan_devices()
            device_mac_to_ap_mac: Dict[str, str] = {}
            device_mac_to_wlan_stats: Dict[str, Dict[str, Any]] = {}
            for wlan_dev in wlan_devices:
                mac = wlan_dev["device_mac"].upper()
                device_mac_to_ap_mac[mac] = wlan_dev["ap_mac"].upper()
                device_mac_to_wlan_stats[mac] = {
                    "signal_strength": wlan_dev.get("signal_strength", 0),
                    "speed": wlan_dev.get("speed", 0),
                }

            # 2. Get mesh topology
            mesh_topology = self.client.get_mesh_info()
            node_uid_to_name: Dict[str, str] = {}
            mac_to_mesh_name: Dict[str, str] = {}
            ap_mac_to_mesh_name: Dict[str, str] = {}
            type_by_mac: Dict[str, Dict[str, bool]] = {}

            if mesh_topology:
                for node_info in mesh_topology.get("nodes", []):
                    node_uid = node_info.get("uid", "")
                    device_name = node_info.get("device_name", "")
                    mac_addr = node_info.get("device_mac_address", "").upper()

                    if node_uid and device_name:
                        node_uid_to_name[node_uid] = device_name

                    if mac_addr and device_name:
                        mac_to_mesh_name[mac_addr] = device_name

                    # Map WLAN interface MACs to device name
                    for interface in node_info.get("node_interfaces", []):
                        if interface.get("type") == "WLAN":
                            wlan_mac = interface.get("mac_address", "").upper()
                            if wlan_mac and device_name:
                                ap_mac_to_mesh_name[wlan_mac] = device_name

                    # Determine node type
                    vendor_id = (node_info.get("device_vendor_class_id") or "").upper()
                    caps = node_info.get("device_capabilities") or []
                    is_repeater = "REPEATER" in vendor_id or "WLAN_ACCESS_POINT" in caps
                    is_powerline = "POWERLINE" in vendor_id
                    is_router = device_name.lower() in ("fritz.box",)

                    if mac_addr:
                        type_by_mac[mac_addr] = {
                            "is_router": is_router,
                            "is_repeater": is_repeater,
                            "is_powerline": is_powerline,
                        }

                # 3. Build node hierarchy & aggregate link speeds
                node_mac_to_parent_name: Dict[str, str] = {}
                node_uid_to_mac: Dict[str, str] = {}
                node_mac_to_link_speeds: Dict[str, Dict[str, int]] = {}

                for node_info in mesh_topology.get("nodes", []):
                    node_uid = node_info.get("uid", "")
                    mac_addr = node_info.get("device_mac_address", "").upper()
                    if node_uid and mac_addr:
                        node_uid_to_mac[node_uid] = mac_addr
                        if mac_addr not in node_mac_to_link_speeds:
                            node_mac_to_link_speeds[mac_addr] = {"rx_kbps": 0, "tx_kbps": 0}

                for node_info in mesh_topology.get("nodes", []):
                    this_node_uid = node_info.get("uid", "")
                    this_node_mac = node_info.get("device_mac_address", "").upper()

                    for interface in node_info.get("node_interfaces", []):
                        for link in interface.get("node_links", []):
                            node_1_uid = link.get("node_1_uid", "")
                            node_2_uid = link.get("node_2_uid", "")

                            cur_rx = link.get("cur_data_rate_rx", 0) or 0
                            cur_tx = link.get("cur_data_rate_tx", 0) or 0

                            if this_node_mac and this_node_mac in node_mac_to_link_speeds:
                                node_mac_to_link_speeds[this_node_mac]["rx_kbps"] += cur_rx
                                node_mac_to_link_speeds[this_node_mac]["tx_kbps"] += cur_tx

                            parent_uid = None
                            if node_1_uid == this_node_uid and node_2_uid in node_uid_to_name:
                                parent_uid = node_2_uid
                            elif node_2_uid == this_node_uid and node_1_uid in node_uid_to_name:
                                parent_uid = node_1_uid

                            if parent_uid and this_node_mac:
                                node_mac_to_parent_name[this_node_mac] = parent_uid
                                break

                # Extract IP addresses from mesh topology
                mesh_mac_to_ip: Dict[str, str] = {}
                for node_info in mesh_topology.get("nodes", []):
                    mac_addr = node_info.get("device_mac_address", "").upper()
                    if mac_addr:
                        for ip_info in node_info.get("ip_addresses", []):
                            if ip_info.get("version") == "V4":
                                ip_addr = ip_info.get("value", "").split("/")[0]
                                if ip_addr and not ip_addr.startswith("169."):
                                    mesh_mac_to_ip[mac_addr] = ip_addr
                                    break

                # Map device IP to node UID from mesh topology node_links
                device_ip_to_node_uid: Dict[str, str] = {}
                for node_info in mesh_topology.get("nodes", []):
                    device_ip = ""
                    for ip_info in node_info.get("ip_addresses", []):
                        if ip_info.get("version") == "V4" and "DHCP" in ip_info.get(
                            "attributes", []
                        ):
                            device_ip = ip_info.get("value", "").split("/")[0]
                            break

                    if not device_ip:
                        continue

                    for interface in node_info.get("node_interfaces", []):
                        for link in interface.get("node_links", []):
                            node_1_uid = link.get("node_1_uid", "")
                            node_2_uid = link.get("node_2_uid", "")
                            this_node_uid = node_info.get("uid", "")
                            if node_1_uid == this_node_uid and node_2_uid:
                                device_ip_to_node_uid[device_ip] = node_2_uid
                                break
                            elif node_2_uid == this_node_uid and node_1_uid:
                                device_ip_to_node_uid[device_ip] = node_1_uid
                                break

            # 4. Get all hosts for detailed device data
            all_hosts = self.client.get_all_hosts()

            mesh_name_to_unique_name: Dict[str, str] = {}
            mesh_name_to_mac: Dict[str, str] = {}

            if mesh_topology:
                for node_info in mesh_topology.get("nodes", []):
                    device_name = node_info.get("device_name", "")
                    mac_addr = node_info.get("device_mac_address", "")
                    if device_name and mac_addr:
                        mesh_name_to_mac[device_name] = mac_addr.upper()

            # Create unique names for infrastructure
            for host in all_hosts:
                name = host.get("name", "Unknown")
                mac = host.get("mac", "")
                upper_name = name.upper()
                mac_key = (mac or "").upper()
                mesh_type = type_by_mac.get(mac_key, {})

                is_repeater = bool(mesh_type.get("is_repeater")) or ("REPEATER" in upper_name)
                is_powerline = (
                    bool(mesh_type.get("is_powerline"))
                    or ("POWERLINE" in upper_name)
                    or ("AVM1220" in upper_name)
                    or ("AVM1260" in upper_name)
                )
                is_router = bool(mesh_type.get("is_router")) or (
                    upper_name.startswith("FRITZ.BOX") or upper_name == "FRITZ.BOX"
                )

                if is_router or is_repeater or is_powerline:
                    mac_upper = (mac or "").upper()
                    mesh_name = mac_to_mesh_name.get(mac_upper)

                    if not mesh_name:
                        mac_suffix = mac.replace(":", "")[-4:] if mac else "Unknown"
                        if is_repeater:
                            unique_name = f"Repeater-{mac_suffix}"
                        elif is_powerline:
                            unique_name = f"Powerline-{mac_suffix}"
                        else:
                            unique_name = name
                    else:
                        unique_name = mesh_name

                    if mesh_name:
                        mesh_name_to_unique_name[mesh_name] = unique_name
                    mesh_name_to_unique_name[name] = unique_name

            uid_to_unique_name: Dict[str, str] = {}
            mac_to_unique_name: Dict[str, str] = {}
            ip_to_host_info: Dict[str, Dict[str, str]] = {}

            for host in all_hosts:
                ip = host.get("ip", "")
                name = host.get("name", "")
                mac = host.get("mac", "").upper()
                if ip:
                    ip_to_host_info[ip] = {"name": name, "mac": mac}

            for mesh_name, mac_addr in mesh_name_to_mac.items():
                if mesh_name in mesh_name_to_unique_name:
                    mac_to_unique_name[mac_addr] = mesh_name_to_unique_name[mesh_name]

            for host in all_hosts:
                mac = host.get("mac", "").upper()
                name = host.get("name", "")
                if name in mesh_name_to_unique_name:
                    unique_name = mesh_name_to_unique_name[name]
                    if mac and unique_name and mac not in mac_to_unique_name:
                        mac_to_unique_name[mac] = unique_name

            if mesh_topology:
                for node_info in mesh_topology.get("nodes", []):
                    node_uid = node_info.get("uid", "")
                    mesh_mac = node_info.get("device_mac_address", "").upper()
                    device_name = node_info.get("device_name", "")

                    if not node_uid:
                        continue

                    vendor_id = (node_info.get("device_vendor_class_id") or "").upper()
                    caps = node_info.get("device_capabilities") or []
                    device_name_upper = device_name.upper()

                    is_router = bool(device_name and device_name.lower() in ("fritz.box",))
                    is_powerline = (
                        "POWERLINE" in vendor_id
                        or "AVM1220" in device_name_upper
                        or "AVM1260" in device_name_upper
                    )
                    is_repeater = (
                        ("REPEATER" in vendor_id or "WLAN_ACCESS_POINT" in caps)
                        and not is_powerline
                        and not is_router
                    )

                    if is_router or is_repeater or is_powerline:
                        host_mac = mesh_mac
                        node_ip = ""
                        for ip_info in node_info.get("ip_addresses", []):
                            if ip_info.get("version") == "V4":
                                node_ip = ip_info.get("value", "").split("/")[0]
                                if node_ip and not node_ip.startswith("169."):
                                    break

                        if node_ip and node_ip in ip_to_host_info:
                            host_mac = ip_to_host_info[node_ip]["mac"]

                        if is_router:
                            unique_name = "fritz.box"
                        elif is_powerline:
                            mac_suffix = host_mac.replace(":", "")[-4:]
                            unique_name = f"Powerline-{mac_suffix}"
                        elif is_repeater:
                            mac_suffix = host_mac.replace(":", "")[-4:]
                            unique_name = f"Repeater-{mac_suffix}"
                        else:
                            mac_suffix = host_mac.replace(":", "")[-4:]
                            unique_name = f"Node-{mac_suffix}"

                        uid_to_unique_name[node_uid] = unique_name
                        mac_to_unique_name[mesh_mac] = unique_name
                        mac_to_unique_name[host_mac] = unique_name
                        if device_name:
                            mesh_name_to_unique_name[device_name] = unique_name

            nodes_by_mac: Dict[str, Node] = {}

            for mesh_name, mac_addr in mesh_name_to_mac.items():
                if mesh_name not in mesh_name_to_unique_name:
                    mesh_type = type_by_mac.get(mac_addr, {})
                    is_repeater = mesh_type.get("is_repeater", False)
                    is_powerline = mesh_type.get("is_powerline", False)
                    is_router = mesh_type.get("is_router", False)

                    if not (is_repeater or is_powerline or is_router):
                        mac_suffix = mac_addr.replace(":", "")[-4:] if mac_addr else "Unknown"
                        mesh_name_to_unique_name[mesh_name] = f"Device-{mac_suffix}"
                        continue

                    mac_suffix = mac_addr.replace(":", "")[-4:] if mac_addr else "Unknown"

                    if is_repeater:
                        unique_name = f"Repeater-{mac_suffix}"
                    elif is_powerline:
                        unique_name = f"Powerline-{mac_suffix}"
                    elif is_router:
                        unique_name = "fritz.box"
                    else:
                        unique_name = f"Node-{mac_suffix}"

                    mesh_name_to_unique_name[mesh_name] = unique_name
                    model_display_name = self.model_name_mapping.get(
                        mesh_name, mesh_name or unique_name
                    )
                    node_ip = mesh_mac_to_ip.get(mac_addr, "")
                    link_speeds = node_mac_to_link_speeds.get(
                        mac_addr.upper(), {"rx_kbps": 0, "tx_kbps": 0}
                    )

                    node = Node(
                        name=unique_name,
                        mac=mac_addr,
                        ip=node_ip,
                        is_router=is_router,
                        is_repeater=is_repeater,
                        is_powerline=is_powerline,
                        extra={
                            "active": True,
                            "mesh_only": True,
                            "model": model_display_name,
                            "parent_uid": node_mac_to_parent_name.get(mac_addr.upper()),
                            "link_rx_kbps": link_speeds["rx_kbps"],
                            "link_tx_kbps": link_speeds["tx_kbps"],
                        },
                        parent_node=None,
                    )
                    nodes_by_mac[mac_addr.upper()] = node

            host_mac_to_mesh_mac: Dict[str, str] = {}
            if mesh_topology:
                for node_info in mesh_topology.get("nodes", []):
                    mesh_mac = node_info.get("device_mac_address", "").upper()
                    vendor_id = (node_info.get("device_vendor_class_id") or "").upper()
                    caps = node_info.get("device_capabilities") or []
                    is_infra = (
                        "REPEATER" in vendor_id
                        or "POWERLINE" in vendor_id
                        or "WLAN_ACCESS_POINT" in caps
                    )

                    if is_infra:
                        node_ip = ""
                        for ip_info in node_info.get("ip_addresses", []):
                            if ip_info.get("version") == "V4":
                                node_ip = ip_info.get("value", "").split("/")[0]
                                if node_ip and not node_ip.startswith("169."):
                                    break

                        if node_ip:
                            for host in all_hosts:
                                if host.get("ip", "") == node_ip:
                                    host_mac = host.get("mac", "").upper()
                                    if host_mac and mesh_mac:
                                        host_mac_to_mesh_mac[host_mac] = mesh_mac
                                    break

            # 5. Create Node and Device objects
            for host in all_hosts:
                name = host.get("name", "Unknown")
                mac = host.get("mac", "")
                ip = host.get("ip", "")
                active = host.get("status", False)
                interface_type = host.get("interface_type", "")

                upper_name = name.upper()
                host_mac_upper = (mac or "").upper()
                mesh_mac_for_host = host_mac_to_mesh_mac.get(host_mac_upper, host_mac_upper)
                mesh_type = type_by_mac.get(mesh_mac_for_host, {})

                is_router = bool(mesh_type.get("is_router")) or (
                    upper_name.startswith("FRITZ.BOX") or upper_name == "FRITZ.BOX"
                )
                is_repeater = not is_router and (
                    bool(mesh_type.get("is_repeater")) or ("REPEATER" in upper_name)
                )
                is_powerline = not is_router and (
                    bool(mesh_type.get("is_powerline"))
                    or ("POWERLINE" in upper_name)
                    or ("AVM1220" in upper_name)
                    or ("AVM1260" in upper_name)
                )

                if is_router or is_repeater or is_powerline:
                    resolved_unique_name: Optional[str] = mac_to_unique_name.get(
                        mesh_mac_for_host or ""
                    )
                    if not resolved_unique_name:
                        if is_router:
                            resolved_unique_name = "fritz.box"
                        elif is_repeater:
                            mac_suffix = (mesh_mac_for_host or "").replace(":", "")[-4:]
                            resolved_unique_name = f"Repeater-{mac_suffix}"
                        elif is_powerline:
                            mac_suffix = (mesh_mac_for_host or "").replace(":", "")[-4:]
                            resolved_unique_name = f"Powerline-{mac_suffix}"

                    mesh_name = mac_to_mesh_name.get(mesh_mac_for_host or "")
                    model_display_name = self.model_name_mapping.get(mesh_name or name, name)
                    parent_uid = node_mac_to_parent_name.get(mesh_mac_for_host or "")
                    link_speeds = node_mac_to_link_speeds.get(
                        mesh_mac_for_host or "", {"rx_kbps": 0, "tx_kbps": 0}
                    )

                    if mesh_mac_for_host and mesh_mac_for_host in nodes_by_mac:
                        existing_node = nodes_by_mac[mesh_mac_for_host]
                        new_extra = dict(existing_node.extra)
                        new_extra["active"] = active
                        new_extra["model"] = model_display_name
                        new_extra["parent_uid"] = parent_uid
                        new_extra["link_rx_kbps"] = link_speeds["rx_kbps"]
                        new_extra["link_tx_kbps"] = link_speeds["tx_kbps"]
                        updated_node = replace(existing_node, ip=ip, extra=new_extra)
                        nodes_by_mac[mesh_mac_for_host] = updated_node
                    else:
                        node = Node(
                            name=resolved_unique_name or "fritz.box",
                            mac=mac,
                            ip=ip,
                            is_router=is_router,
                            is_repeater=is_repeater,
                            is_powerline=is_powerline,
                            extra={
                                "active": active,
                                "model": model_display_name,
                                "parent_uid": parent_uid,
                                "link_rx_kbps": link_speeds["rx_kbps"],
                                "link_tx_kbps": link_speeds["tx_kbps"],
                                "mesh_mac": mesh_mac_for_host,
                            },
                            parent_node=None,
                        )
                        if mesh_mac_for_host:
                            nodes_by_mac[mesh_mac_for_host] = node
                else:
                    connected_node_mesh_name: Optional[str] = None
                    connected_node_uid: Optional[str] = None
                    mapping_source = "none"

                    mac_upper = (mac or "").upper()
                    if mac_upper in device_mac_to_ap_mac:
                        ap_mac = device_mac_to_ap_mac[mac_upper]
                        connected_node_mesh_name = ap_mac_to_mesh_name.get(ap_mac, "")
                        if connected_node_mesh_name:
                            mapping_source = "wlan"

                    if not connected_node_mesh_name and ip in device_ip_to_node_uid:
                        connected_node_uid = device_ip_to_node_uid[ip]
                        if connected_node_uid:
                            mapping_source = "mesh_ip"

                    if not connected_node_mesh_name and ip and ip in self.static_mappings:
                        connected_node_mesh_name = self.static_mappings[ip]
                        mapping_source = "static_ip_override"

                    if not connected_node_mesh_name and not connected_node_uid:
                        connected_node_mesh_name = "fritz.box"
                        mapping_source = "default_router"

                    if mapping_source == "static_ip_override":
                        connected_node = connected_node_mesh_name or "fritz.box"
                    elif mapping_source == "mesh_ip":
                        connected_node = uid_to_unique_name.get(
                            connected_node_uid or "", "fritz.box"
                        )
                    else:
                        connected_node_key = connected_node_mesh_name or "fritz.box"
                        connected_node = mesh_name_to_unique_name.get(
                            connected_node_key, connected_node_key
                        )

                    traffic_stats = self.client.get_device_stats(mac) if mac else None

                    extra_data = {"interface": interface_type, "mapping": mapping_source}
                    if mac_upper in device_mac_to_wlan_stats:
                        wlan_stats = device_mac_to_wlan_stats[mac_upper]
                        extra_data["signal_strength"] = wlan_stats["signal_strength"]
                        extra_data["speed"] = wlan_stats["speed"]

                    device = Device(
                        name=name,
                        mac=mac,
                        ip=ip or None,
                        is_active=active,
                        connection_type=interface_type,
                        connected_to=connected_node,
                        rx_bytes=traffic_stats.get("rx_bytes") if traffic_stats else None,
                        tx_bytes=traffic_stats.get("tx_bytes") if traffic_stats else None,
                        extra=extra_data,
                    )
                    devices.append(device)

            # 6. Resolve all parent UIDs / hierarchy overrides to unique node names
            nodes = []
            for node in nodes_by_mac.values():
                mac_upper = node.mac.upper()
                parent_name = None
                if mac_upper in self.manual_hierarchy:
                    parent_name = self.manual_hierarchy[mac_upper]
                else:
                    parent_uid = node.extra.get("parent_uid")
                    if parent_uid:
                        parent_unique_name = uid_to_unique_name.get(parent_uid)
                        if parent_unique_name:
                            parent_name = mesh_name_to_unique_name.get(
                                parent_unique_name, parent_unique_name
                            )
                nodes.append(replace(node, parent_node=parent_name))

        except (FritzTimeoutError, FritzAuthenticationError, FritzConnectionError, FritzError):
            raise
        except Exception as e:
            raise FritzConnectionError(f"Error during mesh discovery: {e}") from e

        return nodes, devices
