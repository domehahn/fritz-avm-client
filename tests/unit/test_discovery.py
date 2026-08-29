"""Unit tests for MeshDiscovery with error propagation, mesh_type scoping, and nullable stats."""
import pytest
from unittest.mock import MagicMock
from fritz_avm_client.discovery import MeshDiscovery
from fritz_avm_client.exceptions import FritzTimeoutError, FritzAuthenticationError


def test_discovery_basic():
    mock_client = MagicMock()
    mock_client.get_wlan_devices.return_value = []
    mock_client.get_all_hosts.return_value = [
        {
            "name": "FRITZ.Box",
            "mac": "00:11:22:33:44:55",
            "ip": "192.168.178.1",
            "status": True,
            "interface_type": "Ethernet",
        },
        {
            "name": "Laptop",
            "mac": "AA:BB:CC:DD:EE:FF",
            "ip": "192.168.178.20",
            "status": True,
            "interface_type": "802.11",
        },
    ]
    mock_client.get_mesh_info.return_value = {
        "nodes": [
            {
                "uid": "node1",
                "device_name": "fritz.box",
                "device_mac_address": "00:11:22:33:44:55",
                "is_router": True,
                "is_repeater": False,
                "is_powerline": False,
            }
        ]
    }
    mock_client.get_device_stats.return_value = None

    discovery = MeshDiscovery(mock_client)
    nodes, devices = discovery.discover()

    assert len(nodes) >= 1
    assert nodes[0].is_router is True
    assert nodes[0].name == "fritz.box"

    assert len(devices) >= 1
    laptop = [d for d in devices if d.name == "Laptop"][0]
    assert laptop.rx_bytes is None
    assert laptop.tx_bytes is None


def test_discovery_mesh_type_per_host_scoping():
    mock_client = MagicMock()
    mock_client.get_wlan_devices.return_value = []
    mock_client.get_all_hosts.return_value = [
        {"name": "FRITZ.Box", "mac": "00:11:22:33:44:55", "ip": "192.168.178.1", "status": True},
        {"name": "MyRepeater", "mac": "11:22:33:44:55:66", "ip": "192.168.178.2", "status": True},
        {
            "name": "RegularPhone",
            "mac": "22:33:44:55:66:77",
            "ip": "192.168.178.30",
            "status": True,
        },
    ]
    mock_client.get_mesh_info.return_value = {
        "nodes": [
            {
                "uid": "node1",
                "device_name": "FRITZ.Box",
                "device_mac_address": "00:11:22:33:44:55",
                "is_router": True,
            },
            {
                "uid": "node2",
                "device_name": "MyRepeater",
                "device_mac_address": "11:22:33:44:55:66",
                "is_repeater": True,
            },
        ]
    }
    mock_client.get_device_stats.return_value = {"rx_bytes": 1000, "tx_bytes": 500}

    discovery = MeshDiscovery(mock_client)
    nodes, devices = discovery.discover()

    phone = [d for d in devices if d.name == "RegularPhone"][0]
    assert phone.rx_bytes == 1000
    assert phone.tx_bytes == 500


def test_discovery_exception_propagation():
    mock_client = MagicMock()
    mock_client.get_wlan_devices.side_effect = FritzTimeoutError("Connection timeout")

    discovery = MeshDiscovery(mock_client)
    with pytest.raises(FritzTimeoutError):
        discovery.discover()


def test_discovery_auth_error_propagation():
    mock_client = MagicMock()
    mock_client.get_wlan_devices.side_effect = FritzAuthenticationError("Auth failed")

    discovery = MeshDiscovery(mock_client)
    with pytest.raises(FritzAuthenticationError):
        discovery.discover()
