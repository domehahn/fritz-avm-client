"""Basic tests for fritz-avm-client."""
import os
import pytest
from fritz_avm_client import Settings, FritzClient
from fritz_avm_client.models import Node, Device


def test_settings_defaults():
    """Test Settings with default values."""
    settings = Settings()
    assert settings.fritz_host == "192.168.178.1"
    assert settings.fritz_port == 49000
    assert settings.fritz_use_tls is False


def test_settings_custom():
    """Test Settings with custom values."""
    settings = Settings(
        fritz_host="192.168.1.1",
        fritz_port=12345,
        fritz_username="admin",
        fritz_password="secret"
    )
    assert settings.fritz_host == "192.168.1.1"
    assert settings.fritz_port == 12345
    assert settings.fritz_username == "admin"
    assert settings.fritz_password == "secret"


def test_settings_base_url():
    """Test base URL generation."""
    settings = Settings(fritz_host="192.168.1.1", fritz_port=49000)
    assert settings.fritz_base_url == "http://192.168.1.1:49000"

    settings_tls = Settings(fritz_host="192.168.1.1", fritz_use_tls=True)
    assert settings_tls.fritz_base_url == "https://192.168.1.1:49000"


def test_node_model():
    """Test Node dataclass."""
    node = Node(
        name="Living Room Repeater",
        mac="AA:BB:CC:DD:EE:FF",
        ip="192.168.178.50",
        is_router=False,
        is_repeater=True,
        is_powerline=False,
        extra={'model': 'FRITZ!Repeater 6000'},
        parent_node="Router"
    )

    assert node.name == "Living Room Repeater"
    assert node.mac == "AA:BB:CC:DD:EE:FF"
    assert node.is_repeater is True
    assert node.is_router is False
    assert node.parent_node == "Router"


def test_device_model():
    """Test Device dataclass."""
    device = Device(
        name="iPhone",
        mac="11:22:33:44:55:66",
        ip="192.168.178.100",
        is_active=True,
        connection_type="wlan",
        connected_to="Living Room Repeater",
        rx_bytes=1024000,
        tx_bytes=512000
    )

    assert device.name == "iPhone"
    assert device.is_active is True
    assert device.connection_type == "wlan"
    assert device.rx_bytes == 1024000


@pytest.mark.skipif(not os.getenv("FRITZ_INTEGRATION_TESTS"), reason="FRITZ_INTEGRATION_TESTS=1 not set")
@pytest.mark.integration
def test_client_initialization():
    """Test FritzClient initialization (requires Fritz!Box)."""
    settings = Settings()
    client = FritzClient(settings)
    assert client.fc is not None


@pytest.mark.skipif(not os.getenv("FRITZ_INTEGRATION_TESTS"), reason="FRITZ_INTEGRATION_TESTS=1 not set")
@pytest.mark.integration
def test_get_wan_stats():
    """Test getting WAN statistics (requires Fritz!Box)."""
    settings = Settings()
    client = FritzClient(settings)
    wan_stats = client.get_wan_stats()
    assert 'bytes_sent' in wan_stats


def test_mesh_discovery_initialization():
    """Test MeshDiscovery initialization with optional overrides."""
    from fritz_avm_client import MeshDiscovery
    discovery = MeshDiscovery(
        client=None,
        static_mappings={"192.168.178.50": "Repeater-1"},
        manual_hierarchy={"AA:BB:CC:DD:EE:FF": "fritz.box"},
        model_name_mapping={"FRITZ!Repeater 6000": "Wohnzimmer"}
    )
    assert discovery.static_mappings == {"192.168.178.50": "Repeater-1"}
    assert discovery.manual_hierarchy == {"AA:BB:CC:DD:EE:FF": "fritz.box"}
    assert discovery.model_name_mapping == {"FRITZ!Repeater 6000": "Wohnzimmer"}
    nodes, devices = discovery.discover()
    assert nodes == []
    assert devices == []

