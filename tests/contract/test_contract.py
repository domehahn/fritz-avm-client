"""Contract tests using anonymized TR-064 response fixtures."""
import pytest
from unittest.mock import MagicMock
from fritz_avm_client import FritzClient, Settings, MeshDiscovery

ANONYMIZED_MESH_TOPOLOGY = {
    'nodes': [
        {
            'uid': 'node_router_1',
            'device_name': 'fritz.box',
            'device_mac_address': '00:11:22:33:44:55',
            'device_vendor_class_id': 'AVM Router',
            'device_capabilities': ['ROUTER', 'WLAN_ACCESS_POINT'],
            'ip_addresses': [{'version': 'V4', 'value': '192.168.178.1/24', 'attributes': ['DHCP']}],
            'node_interfaces': [
                {
                    'type': 'WLAN',
                    'mac_address': '00:11:22:33:44:56',
                    'node_links': [
                        {
                            'node_1_uid': 'node_router_1',
                            'node_2_uid': 'node_repeater_1',
                            'cur_data_rate_rx': 866000,
                            'cur_data_rate_tx': 866000,
                        }
                    ]
                }
            ]
        },
        {
            'uid': 'node_repeater_1',
            'device_name': 'FRITZ!Repeater 2400',
            'device_mac_address': '00:11:22:AA:BB:CC',
            'device_vendor_class_id': 'AVM REPEATER',
            'device_capabilities': ['REPEATER', 'WLAN_ACCESS_POINT'],
            'ip_addresses': [{'version': 'V4', 'value': '192.168.178.2/24', 'attributes': ['DHCP']}],
            'node_interfaces': [
                {
                    'type': 'WLAN',
                    'mac_address': '00:11:22:AA:BB:CD',
                    'node_links': [
                        {
                            'node_1_uid': 'node_repeater_1',
                            'node_2_uid': 'node_router_1',
                            'cur_data_rate_rx': 866000,
                            'cur_data_rate_tx': 866000,
                        }
                    ]
                }
            ]
        }
    ]
}

ANONYMIZED_HOSTS_INFO = [
    {
        'name': 'fritz.box',
        'ip': '192.168.178.1',
        'mac': '00:11:22:33:44:55',
        'status': True,
        'interface_type': 'ethernet',
    },
    {
        'name': 'Repeater-ABCC',
        'ip': '192.168.178.2',
        'mac': '00:11:22:AA:BB:CC',
        'status': True,
        'interface_type': 'wlan',
    },
    {
        'name': 'ClientLaptop',
        'ip': '192.168.178.100',
        'mac': 'AA:BB:CC:11:22:33',
        'status': True,
        'interface_type': '802.11',
    }
]

ANONYMIZED_WLAN_DEVICES = [
    {
        'device_mac': 'AA:BB:CC:11:22:33',
        'ap_mac': '00:11:22:AA:BB:CD',
        'service': 'WLANConfiguration1',
        'ip': '192.168.178.100',
        'signal_strength': 85,
        'speed': 433,
    }
]


def test_contract_mesh_discovery_parsing():
    """Verify mesh topology discovery using contract response fixtures."""
    mock_fc = MagicMock()
    client = MagicMock(spec=FritzClient)
    client.get_wlan_devices.return_value = ANONYMIZED_WLAN_DEVICES
    client.get_mesh_info.return_value = ANONYMIZED_MESH_TOPOLOGY
    client.get_all_hosts.return_value = ANONYMIZED_HOSTS_INFO
    client.get_device_stats.return_value = {'rx_bytes': 1000, 'tx_bytes': 2000}

    discovery = MeshDiscovery(client)
    nodes, devices = discovery.discover()

    assert len(nodes) >= 2
    router_nodes = [n for n in nodes if n.is_router]
    repeater_nodes = [n for n in nodes if n.is_repeater]

    assert len(router_nodes) == 1
    assert len(repeater_nodes) == 1
    assert router_nodes[0].name == 'fritz.box'

    assert len(devices) == 1
    client_dev = devices[0]
    assert client_dev.name == 'ClientLaptop'
    assert client_dev.mac == 'AA:BB:CC:11:22:33'
    assert client_dev.connected_node == repeater_nodes[0].name

