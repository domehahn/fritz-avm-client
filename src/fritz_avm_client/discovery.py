"""Mesh network discovery for Fritz!Box."""
from typing import List, Tuple, Dict, Any, Optional
from .models import Node, Device
from .client import FritzClient


class MeshDiscovery:
    """Discover and map Fritz!Box mesh network topology.
    
    This class provides automatic discovery of:
    - Mesh nodes (router, repeaters, powerline adapters)
    - Client devices and their connections
    - Network hierarchy (parent-child relationships)
    - Device-to-node mappings
    
    Example:
        >>> from fritz_avm_client import FritzClient, MeshDiscovery, Settings
        >>> settings = Settings(fritz_host="192.168.178.1")
        >>> client = FritzClient(settings)
        >>> discovery = MeshDiscovery(client)
        >>> nodes, devices = discovery.discover()
        >>> for node in nodes:
        ...     print(f"{node.name}: {len([d for d in devices if d.connected_node == node.mac])} devices")
    """

    def __init__(self, client: FritzClient, 
                 static_mappings: Optional[Dict[str, str]] = None,
                 manual_hierarchy: Optional[Dict[str, str]] = None):
        """Initialize mesh discovery.
        
        Args:
            client: FritzClient instance
            static_mappings: Optional static IP to node name mappings
                Example: {'192.168.178.50': 'Living Room Repeater'}
            manual_hierarchy: Optional manual parent-child relationships
                Example: {'AA:BB:CC:DD:EE:FF': 'router.fritz.box'}
        """
        self.client = client
        self.static_mappings = static_mappings or {}
        self.manual_hierarchy = manual_hierarchy or {}

    def discover(self) -> Tuple[List[Node], List[Device]]:
        """Discover all mesh nodes and devices with their connections.
        
        Returns:
            Tuple of (nodes, devices) where:
                - nodes: List of mesh infrastructure nodes
                - devices: List of client devices with connection info
        """
        nodes = []
        devices = []
        
        if not self.client:
            return nodes, devices
        
        try:
            # Get WLAN associations to map WiFi devices to their access points
            wlan_devices = self.client.get_wlan_devices()
            device_mac_to_ap_mac = {}
            for wlan_dev in wlan_devices:
                device_mac_to_ap_mac[wlan_dev['device_mac'].upper()] = wlan_dev['ap_mac'].upper()
            
            # Get mesh topology
            mesh_topology = self.client.get_mesh_info()
            if not mesh_topology:
                return nodes, devices
            
            # Build mappings
            node_uid_to_name = {}
            mac_to_mesh_name = {}
            ap_mac_to_mesh_name = {}
            type_by_mac: Dict[str, Dict[str, bool]] = {}
            
            # Map node UIDs and MACs to names
            for node_info in mesh_topology.get('nodes', []):
                node_uid = node_info.get('uid', '')
                device_name = node_info.get('device_name', '')
                mac_addr = node_info.get('device_mac_address', '').upper()
                
                if node_uid and device_name:
                    node_uid_to_name[node_uid] = device_name
                
                if mac_addr and device_name:
                    mac_to_mesh_name[mac_addr] = device_name
                
                # Map WLAN interface MACs to device name
                for interface in node_info.get('node_interfaces', []):
                    if interface.get('type') == 'WLAN':
                        wlan_mac = interface.get('mac_address', '').upper()
                        if wlan_mac and device_name:
                            ap_mac_to_mesh_name[wlan_mac] = device_name
                
                # Determine node type
                vendor_id = (node_info.get('device_vendor_class_id') or '').upper()
                caps = node_info.get('device_capabilities') or []
                is_repeater = 'REPEATER' in vendor_id or 'WLAN_ACCESS_POINT' in caps
                is_powerline = 'POWERLINE' in vendor_id
                is_router = 'fritz.box' in device_name.lower()
                
                if mac_addr:
                    type_by_mac[mac_addr] = {
                        'is_router': is_router,
                        'is_repeater': is_repeater,
                        'is_powerline': is_powerline,
                    }
            
            # Build node hierarchy
            node_mac_to_parent_name = {}
            node_uid_to_mac = {}
            
            for node_info in mesh_topology.get('nodes', []):
                node_uid = node_info.get('uid', '')
                mac_addr = node_info.get('device_mac_address', '').upper()
                if node_uid and mac_addr:
                    node_uid_to_mac[node_uid] = mac_addr
            
            # Extract parent-child relationships from node links
            for node_info in mesh_topology.get('nodes', []):
                this_node_mac = node_info.get('device_mac_address', '').upper()
                
                # Check manual hierarchy override
                if this_node_mac in self.manual_hierarchy:
                    parent = self.manual_hierarchy[this_node_mac]
                    if parent:
                        node_mac_to_parent_name[this_node_mac] = parent
                    continue
                
                # Auto-detect from node_links
                for interface in node_info.get('node_interfaces', []):
                    for link in interface.get('node_links', []):
                        node_1_uid = link.get('node_1_uid', '')
                        node_2_uid = link.get('node_2_uid', '')
                        
                        # Determine which is parent (usually the one with lower hop count)
                        if node_1_uid and node_2_uid:
                            node_1_mac = node_uid_to_mac.get(node_1_uid, '')
                            node_2_mac = node_uid_to_mac.get(node_2_uid, '')
                            
                            # Simple heuristic: router is always parent
                            if node_1_mac in type_by_mac and type_by_mac[node_1_mac]['is_router']:
                                if node_2_mac:
                                    node_mac_to_parent_name[node_2_mac] = mac_to_mesh_name.get(node_1_mac, '')
                            elif node_2_mac in type_by_mac and type_by_mac[node_2_mac]['is_router']:
                                if node_1_mac:
                                    node_mac_to_parent_name[node_1_mac] = mac_to_mesh_name.get(node_2_mac, '')
            
            # Create Node objects
            for node_info in mesh_topology.get('nodes', []):
                mac_addr = node_info.get('device_mac_address', '').upper()
                device_name = node_info.get('device_name', '')
                
                node_type = type_by_mac.get(mac_addr, {})
                parent_name = node_mac_to_parent_name.get(mac_addr)
                
                node = Node(
                    name=device_name,
                    mac=mac_addr,
                    ip=None,  # Not directly available in mesh topology
                    is_router=node_type.get('is_router', False),
                    is_repeater=node_type.get('is_repeater', False),
                    is_powerline=node_type.get('is_powerline', False),
                    extra=node_info,
                    parent_node=parent_name
                )
                nodes.append(node)
            
            # Get all hosts for device info
            all_hosts = self.client.get_all_hosts()
            
            # Create Device objects
            for host in all_hosts:
                mac_addr = host.get('mac', '').upper()
                ip_addr = host.get('ip', '')
                name = host.get('name', '') or mac_addr
                is_online = host.get('status', False)
                interface_type = host.get('interface_type', '')
                
                # Determine which node this device is connected to
                connected_node = None
                
                # Check WLAN associations
                if mac_addr in device_mac_to_ap_mac:
                    ap_mac = device_mac_to_ap_mac[mac_addr]
                    connected_node = ap_mac_to_mesh_name.get(ap_mac)
                
                # Check static mappings
                if not connected_node and ip_addr in self.static_mappings:
                    connected_node = self.static_mappings[ip_addr]
                
                # Skip if this is a mesh node itself
                if mac_addr in mac_to_mesh_name:
                    continue
                
                # Get traffic stats
                stats = self.client.get_device_stats(mac_addr)
                
                device = Device(
                    name=name,
                    mac=mac_addr,
                    ip=ip_addr or None,
                    online=is_online,
                    interface_type=interface_type,
                    connected_node=connected_node,
                    rx_bytes_total=stats.get('rx_bytes'),
                    tx_bytes_total=stats.get('tx_bytes'),
                    extra=host
                )
                devices.append(device)
            
        except Exception as e:
            print(f"Error during mesh discovery: {e}")
        
        return nodes, devices
