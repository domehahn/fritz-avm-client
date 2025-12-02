"""Basic tests for fritz-avm-client."""
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
        online=True,
        interface_type="wlan",
        connected_node="Living Room Repeater",
        rx_bytes_total=1024000,
        tx_bytes_total=512000
    )
    
    assert device.name == "iPhone"
    assert device.online is True
    assert device.interface_type == "wlan"
    assert device.rx_bytes_total == 1024000


@pytest.mark.integration
def test_client_initialization():
    """Test FritzClient initialization (requires Fritz!Box)."""
    settings = Settings()
    # This will fail if no Fritz!Box is available
    # Skip in CI/CD environments
    try:
        client = FritzClient(settings)
        assert client.fc is not None
        assert client.hosts is not None
        assert client.status is not None
    except Exception:
        pytest.skip("Fritz!Box not available for testing")


@pytest.mark.integration
def test_get_wan_stats():
    """Test getting WAN statistics (requires Fritz!Box)."""
    settings = Settings()
    try:
        client = FritzClient(settings)
        wan_stats = client.get_wan_stats()
        
        # Check that all expected keys are present
        expected_keys = [
            'total_bytes_sent',
            'total_bytes_received',
            'current_download_rate',
            'current_upload_rate',
            'is_connected',
            'external_ip',
            'attenuation',
            'noise_margin',
            'cpu_temperatures'
        ]
        
        for key in expected_keys:
            assert key in wan_stats
            
    except Exception:
        pytest.skip("Fritz!Box not available for testing")
