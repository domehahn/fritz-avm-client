"""Unit tests for RouterClient, HostsClient, WlanClient, AdminClient, and CapabilityDetector with mocks."""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from fritz_avm_client.router import RouterClient
from fritz_avm_client.hosts import HostsClient
from fritz_avm_client.wlan import WlanClient
from fritz_avm_client.admin import AdminClient
from fritz_avm_client.capabilities import CapabilityDetector
from fritz_avm_client.exceptions import FritzTimeoutError, FritzConnectionError


def test_router_client_get_wan_stats():
    mock_fc = MagicMock()
    with patch("fritz_avm_client.router.FritzStatus") as mock_status_cls:
        mock_status = mock_status_cls.return_value
        mock_status.bytes_received = 500000
        mock_status.bytes_sent = 200000
        mock_status.transmission_rate = (1000, 500)
        mock_status.max_byte_rate = (12500000, 2500000)
        mock_status.device_uptime = 3600
        mock_status.connection_uptime = 3600
        mock_status.external_ip = "203.0.113.1"
        mock_status.is_connected = True
        mock_status.attenuation = (10.0, 8.0)
        mock_status.noise_margin = (15.0, 12.0)
        mock_status.get_cpu_temperatures.return_value = [55.0, 60.0]

        router = RouterClient(mock_fc)
        wan = router.get_wan_stats()
        dsl = router.get_dsl_stats()

        assert wan.total_bytes_received == 500000
        assert wan.total_bytes_sent == 200000
        assert wan.current_download_rate == 1000
        assert wan.external_ip == "203.0.113.1"
        assert wan.cpu_temperatures == {"cpu0": 55.0, "cpu1": 60.0}

        assert dsl.downstream_attenuation == 10.0
        assert dsl.upstream_attenuation == 8.0


def test_router_client_exception_propagation():
    mock_fc = MagicMock()
    with patch("fritz_avm_client.router.FritzStatus") as mock_status_cls:
        mock_status = mock_status_cls.return_value
        type(mock_status).bytes_received = patch.object(
            mock_status_cls,
            "bytes_received",
            new_callable=PropertyMock,
            side_effect=TimeoutError("Timeout"),
        )

        router = RouterClient(mock_fc)
        with patch.object(
            type(router.status),
            "bytes_received",
            new_callable=PropertyMock,
            side_effect=TimeoutError("Timeout"),
        ):
            with pytest.raises(FritzTimeoutError):
                router.get_wan_stats()


def test_hosts_client():
    mock_fc = MagicMock()
    with patch("fritz_avm_client.hosts.FritzHosts") as mock_hosts_cls:
        mock_hosts = mock_hosts_cls.return_value
        mock_hosts.get_hosts_info.return_value = [{"name": "TV", "mac": "00:11:22:33:44:55"}]
        mock_hosts.get_generic_host_entry.return_value = {"name": "TV"}
        mock_hosts.host_number = 5

        hosts_client = HostsClient(mock_fc)
        all_hosts = hosts_client.get_hosts_info()
        assert len(all_hosts) == 1
        assert all_hosts[0]["name"] == "TV"
        assert hosts_client.get_host_details(0) == {"name": "TV"}
        assert hosts_client.get_host_number() == 5


def test_hosts_client_exception_propagation():
    mock_fc = MagicMock()
    with patch("fritz_avm_client.hosts.FritzHosts") as mock_hosts_cls:
        mock_hosts = mock_hosts_cls.return_value
        mock_hosts.get_hosts_info.side_effect = TimeoutError("Timeout")

        hosts_client = HostsClient(mock_fc)
        with pytest.raises(FritzTimeoutError):
            hosts_client.get_hosts_info()


def test_wlan_client():
    mock_fc = MagicMock()
    with patch("fritz_avm_client.wlan.FritzWLAN") as mock_wlan_cls:
        mock_wlan = mock_wlan_cls.return_value
        mock_wlan.ssid = "HomeWiFi"
        mock_wlan.channel = 36
        mock_wlan.get_associated_devices.return_value = [{"mac": "11:22:33:44:55:66"}]

        wlan_client = WlanClient(mock_fc)
        stats_list = wlan_client.get_wlan_stats()
        assert len(stats_list) >= 1
        assert stats_list[0].ssid == "HomeWiFi"

        devices = wlan_client.get_associated_devices(1)
        assert len(devices) == 1


def test_admin_client():
    mock_fc = MagicMock()
    admin_client = AdminClient(mock_fc)

    # Valid MAC
    res = admin_client.delete_host("00:11:22:33:44:55")
    assert res is True
    mock_fc.call_action.assert_called_once_with(
        "Hosts1", "X_AVM-DE_DeleteHostEntry", NewMACAddress="00:11:22:33:44:55"
    )

    # Invalid MAC
    with pytest.raises(ValueError):
        admin_client.delete_host("invalid-mac")

    # Connection error on failure
    mock_fc.call_action.side_effect = Exception("Connection lost")
    with pytest.raises(FritzConnectionError):
        admin_client.delete_host("00:11:22:33:44:55")


def test_capability_detector():
    mock_fc = MagicMock()
    mock_fc.services = {
        "Hosts1": None,
        "DeviceInfo1": None,
        "WANIPConnection1": None,
        "WLANConfiguration1": None,
    }
    detector = CapabilityDetector()
    caps = detector.detect(mock_fc)
    assert caps.mesh is True
    assert caps.cpu_temperature is True
    assert caps.dsl_metrics is True
    assert caps.wlan_statistics is True
    assert caps.host_traffic_statistics is True

    # Caching check
    cached = detector.detect(mock_fc)
    assert cached is caps
