"""Extra unit tests for high coverage across subclients, facade, and discovery."""
import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from fritzconnection.core.exceptions import FritzActionError

from fritz_avm_client import FritzClient, Settings, MeshDiscovery
from fritz_avm_client.hosts import HostsClient
from fritz_avm_client.wlan import WlanClient
from fritz_avm_client.admin import AdminClient
from fritz_avm_client.router import RouterClient
from fritz_avm_client.models import WlanStats
from fritz_avm_client.exceptions import (
    FritzConnectionError,
    FritzTimeoutError,
    FritzAuthenticationError,
    FritzProtocolError,
)


def test_client_init_and_retry_logic():
    settings = Settings(fritz_host="192.168.178.1", fritz_password="test")

    with patch("fritz_avm_client.client.FritzConnection") as mock_fc_cls:
        mock_fc_cls.side_effect = Exception("401 Unauthorized")
        with pytest.raises(FritzAuthenticationError):
            FritzClient(settings)

        mock_fc_cls.side_effect = Exception("Connection timeout")
        with pytest.raises(FritzTimeoutError):
            FritzClient(settings)

        mock_fc_cls.side_effect = Exception("Socket error")
        with pytest.raises(FritzConnectionError):
            FritzClient(settings)

    with patch("fritz_avm_client.client.FritzConnection"):
        client = FritzClient(settings)

        # Retry loop with backoff execution
        mock_func = MagicMock()
        mock_func.side_effect = [FritzTimeoutError("transient"), "success"]
        res = client._execute_with_retry(mock_func, max_retries=2, initial_backoff=0.001)
        assert res == "success"
        assert mock_func.call_count == 2

        mock_func.reset_mock()
        mock_func.side_effect = FritzConnectionError("persistent")
        with pytest.raises(FritzConnectionError):
            client._execute_with_retry(mock_func, max_retries=1, initial_backoff=0.001)


def test_client_facade_and_context_manager():
    settings = Settings(fritz_host="192.168.178.1", fritz_password="test")
    with patch("fritz_avm_client.client.FritzConnection"):
        client = FritzClient(settings)

        with client as c:
            assert c == client

        # close exception path
        client.fc.close = MagicMock(side_effect=Exception("close error"))
        client.close()

        # capabilities
        assert client.get_capabilities() is not None

        # get_mesh_info
        mock_hosts = MagicMock()
        mock_hosts.get_mesh_topology.return_value = {"nodes": []}
        client.hosts_client._hosts = mock_hosts
        assert client.get_mesh_info() == {"nodes": []}

        mock_hosts.get_mesh_topology.side_effect = Exception("SOAP error")
        assert client.get_mesh_info() is None

        # get_device_stats
        mock_hosts.get_specific_host_entry.return_value = {
            "X_AVM-DE_RxBytes": 100,
            "X_AVM-DE_TxBytes": 200,
        }
        assert client.get_device_stats("00:11:22:33:44:55") == {"rx_bytes": 100, "tx_bytes": 200}

        mock_hosts.get_specific_host_entry.side_effect = Exception("SOAP error")
        assert client.get_device_stats("00:11:22:33:44:55") is None

        # get_all_hosts & get_wlan_devices
        with patch.object(client.hosts_client, "get_hosts_info") as mock_gi, patch.object(
            client.wlan_client, "get_associated_devices"
        ) as mock_ad, patch.object(client.wlan_client, "get_wlan_stats") as mock_ws:
            mock_gi.return_value = [{"name": "Device"}]
            assert client.get_all_hosts() == [{"name": "Device"}]

            mock_ws.return_value = [MagicMock(service_index=1)]
            mock_ad.return_value = [
                {
                    "MACAddress": "AA:BB:CC:DD:EE:FF",
                    "NewX_AVM-DE_SignalStrength": 75,
                    "NewX_AVM-DE_Speed": 300,
                }
            ]
            wlan_devs = client.get_wlan_devices()
            assert len(wlan_devs) == 1
            assert wlan_devs[0]["MACAddress"] == "AA:BB:CC:DD:EE:FF"

        # discover_mesh
        with patch.object(client.mesh_discovery, "discover") as mock_disc:
            mock_disc.return_value = ([], [])
            mesh_topo = client.discover_mesh()
            assert len(mesh_topo.nodes) == 0

        # get_wan_stats
        with patch.object(client.router_client, "get_wan_stats") as mock_wan, patch.object(
            client.router_client, "get_dsl_stats"
        ) as mock_dsl:
            mock_wan_obj = MagicMock()
            mock_wan_obj.total_bytes_sent = 1000
            mock_wan_obj.total_bytes_received = 2000
            mock_wan_obj.current_download_rate = 500
            mock_wan_obj.current_upload_rate = 100
            mock_wan_obj.max_upstream_rate = 1000
            mock_wan_obj.max_downstream_rate = 5000
            mock_wan_obj.device_uptime = 3600
            mock_wan_obj.connection_uptime = 1800
            mock_wan_obj.is_connected = True
            mock_wan_obj.external_ip = "1.2.3.4"
            mock_wan_obj.cpu_temperatures = {"cpu0": 45.0}
            mock_wan.return_value = mock_wan_obj

            mock_dsl_obj = MagicMock()
            mock_dsl_obj.downstream_attenuation = 10.0
            mock_dsl_obj.upstream_attenuation = 5.0
            mock_dsl_obj.downstream_noise_margin = 15.0
            mock_dsl_obj.upstream_noise_margin = 12.0
            mock_dsl.return_value = mock_dsl_obj

            wan = client.get_wan_stats()
            assert wan["bytes_received"] == 2000
            assert wan["external_ip"] == "1.2.3.4"

        # get_wlan_traffic_stats
        with patch.object(client.wlan_client, "get_wlan_stats") as mock_wlan:
            stat = WlanStats(total_packets_sent=10, total_packets_received=20, connected_clients=2)
            mock_wlan.return_value = [stat]
            traffic = client.get_wlan_traffic_stats()
            assert traffic["total_packets_sent"] == 10
            assert traffic["connected_clients"] == 2

        # get_wan_stats_typed
        with patch.object(client.router_client, "get_wan_stats") as mock_wan:
            mock_wan.return_value = MagicMock()
            assert client.get_wan_stats_typed() is not None

        # get_cpu_temperatures
        with patch.object(client.router_client, "get_cpu_temperatures") as mock_cpu:
            mock_cpu.return_value = {"cpu0": 50.0}
            assert client.get_cpu_temperatures() == {"cpu0": 50.0}


def test_admin_client_coverage():
    mock_fc = MagicMock()
    admin = AdminClient(mock_fc)

    mock_fc.call_action.return_value = {}
    assert admin.delete_host("00:11:22:33:44:55") is True

    with pytest.raises(ValueError):
        admin.delete_host("invalid-mac")

    mock_fc.call_action.side_effect = TimeoutError("Timeout")
    with pytest.raises(FritzTimeoutError):
        admin.delete_host("00:11:22:33:44:55")

    mock_fc.call_action.side_effect = Exception("nosuchnode")
    with pytest.raises(FritzProtocolError):
        admin.delete_host("00:11:22:33:44:55")

    mock_fc.call_action.side_effect = Exception("Generic error")
    with pytest.raises(FritzConnectionError):
        admin.delete_host("00:11:22:33:44:55")


def test_hosts_client_extra_coverage():
    mock_fc = MagicMock()
    hosts = HostsClient(mock_fc)
    mock_hosts = MagicMock()
    hosts._hosts = mock_hosts

    # get_hosts_info
    mock_hosts.get_hosts_info.return_value = [{"name": "host1"}]
    assert hosts.get_hosts_info() == [{"name": "host1"}]

    mock_hosts.get_hosts_info.side_effect = FritzTimeoutError("Timeout")
    with pytest.raises(FritzTimeoutError):
        hosts.get_hosts_info()

    mock_hosts.get_hosts_info.side_effect = TimeoutError("Timeout")
    with pytest.raises(FritzTimeoutError):
        hosts.get_hosts_info()

    mock_hosts.get_hosts_info.side_effect = Exception("Generic error")
    with pytest.raises(FritzConnectionError):
        hosts.get_hosts_info()

    # get_host_details
    mock_hosts.get_generic_host_entry.return_value = {"IPAddress": "192.168.178.10"}
    assert hosts.get_host_details(0) == {"IPAddress": "192.168.178.10"}

    mock_hosts.get_generic_host_entry.side_effect = Exception("401 Unauthorized")
    with pytest.raises(FritzAuthenticationError):
        hosts.get_host_details(0)

    mock_hosts.get_generic_host_entry.side_effect = Exception("invalid index")
    assert hosts.get_host_details(99) == {}

    mock_hosts.get_generic_host_entry.side_effect = TimeoutError("Timeout")
    with pytest.raises(FritzTimeoutError):
        hosts.get_host_details(0)

    mock_hosts.get_generic_host_entry.side_effect = Exception("Generic error")
    with pytest.raises(FritzConnectionError):
        hosts.get_host_details(0)

    # get_host_number
    type(mock_hosts).host_number = PropertyMock(return_value=15)
    assert hosts.get_host_number() == 15

    type(mock_hosts).host_number = PropertyMock(side_effect=Exception("401 Unauthorized"))
    with pytest.raises(FritzAuthenticationError):
        hosts.get_host_number()

    type(mock_hosts).host_number = PropertyMock(side_effect=TimeoutError("Timeout"))
    with pytest.raises(FritzTimeoutError):
        hosts.get_host_number()

    type(mock_hosts).host_number = PropertyMock(side_effect=Exception("Generic"))
    with pytest.raises(FritzConnectionError):
        hosts.get_host_number()


def test_wlan_client_coverage():
    mock_fc = MagicMock()
    wlan = WlanClient(mock_fc)

    with patch("fritz_avm_client.wlan.FritzWLAN") as mock_wlan_cls:
        wlan1 = MagicMock()
        wlan1.ssid = "MyWiFi"
        wlan1.channel = 6
        wlan1.get_associated_devices.return_value = [{"MACAddress": "AA:BB:CC:DD:EE:FF"}]
        mock_wlan_cls.return_value = wlan1

        stats = wlan.get_wlan_stats()
        assert len(stats) == 4
        assert stats[0].ssid == "MyWiFi"
        assert stats[0].connected_clients == 1

        devs = wlan.get_associated_devices(1)
        assert len(devs) == 1

        mock_wlan_cls.side_effect = TimeoutError("WLAN timeout")
        with pytest.raises(FritzTimeoutError):
            wlan.get_wlan_stats()

        mock_wlan_cls.side_effect = Exception("401 Unauthorized")
        with pytest.raises(FritzAuthenticationError):
            wlan.get_wlan_stats()

        mock_wlan_cls.side_effect = FritzActionError("Action failed")
        assert wlan.get_wlan_stats() == []

        mock_wlan_cls.side_effect = Exception("nosuchservice")
        assert wlan.get_wlan_stats() == []

        mock_wlan_cls.side_effect = Exception("Generic connection error")
        with pytest.raises(FritzConnectionError):
            wlan.get_wlan_stats()

        # Reset mock_wlan_cls side_effect
        mock_wlan_cls.side_effect = None
        mock_wlan_cls.return_value = wlan1

        # Test error paths in get_associated_devices
        wlan1.get_associated_devices.side_effect = TimeoutError("Timeout")
        with pytest.raises(FritzTimeoutError):
            wlan.get_associated_devices(1)

        wlan1.get_associated_devices.side_effect = Exception("401 Unauthorized")
        assert wlan.get_associated_devices(1) == []

        wlan1.get_associated_devices.side_effect = Exception("nosuchservice")
        assert wlan.get_associated_devices(1) == []

        wlan1.get_associated_devices.side_effect = Exception("Generic error")
        assert wlan.get_associated_devices(1) == []


def test_router_client_full_coverage():
    mock_fc = MagicMock()
    router = RouterClient(mock_fc)
    mock_status = MagicMock()
    router._status = mock_status

    mock_status.get_cpu_temperatures.return_value = [55.0]
    assert router.get_cpu_temperatures() == {"cpu0": 55.0}

    mock_status.get_cpu_temperatures.side_effect = Exception("nosuchservice")
    assert router.get_cpu_temperatures() == {}

    mock_status.get_cpu_temperatures.side_effect = TimeoutError("Timeout")
    with pytest.raises(FritzTimeoutError):
        router.get_cpu_temperatures()

    mock_status.get_cpu_temperatures.side_effect = Exception("Generic")
    assert router.get_cpu_temperatures() == {}

    # get_dsl_stats
    mock_status.attenuation = (10.0, 5.0)
    mock_status.noise_margin = (15.0, 12.0)
    dsl = router.get_dsl_stats()
    assert dsl.downstream_attenuation == 10.0

    type(mock_status).attenuation = PropertyMock(side_effect=TimeoutError("Timeout"))
    with pytest.raises(FritzTimeoutError):
        router.get_dsl_stats()

    type(mock_status).attenuation = PropertyMock(side_effect=Exception("nosuchservice"))
    assert router.get_dsl_stats().downstream_attenuation is None

    # get_wan_stats
    mock_status2 = MagicMock()
    router._status = mock_status2
    mock_status2.bytes_received = 1000
    mock_status2.bytes_sent = 500
    mock_status2.transmission_rate = (100, 50)
    mock_status2.max_bit_rate = (5000, 1000)
    mock_status2.uptime = 3600
    mock_status2.connection_uptime = 1800
    mock_status2.external_ip_address = "1.1.1.1"
    type(mock_status2).device_uptime = PropertyMock(side_effect=Exception("error"))
    type(mock_status2).connection_uptime = PropertyMock(side_effect=Exception("error"))
    type(mock_status2).external_ip = PropertyMock(side_effect=Exception("error"))
    wan_opt = router.get_wan_stats()
    assert wan_opt.total_bytes_received == 1000

    type(mock_status2).bytes_received = PropertyMock(side_effect=TimeoutError("Timeout"))
    with pytest.raises(FritzTimeoutError):
        router.get_wan_stats()

    type(mock_status2).bytes_received = PropertyMock(side_effect=Exception("Generic"))
    with pytest.raises(FritzConnectionError):
        router.get_wan_stats()


def test_mesh_discovery_advanced_scenarios():
    mock_client = MagicMock()
    mock_client.get_wlan_devices.return_value = [
        {
            "device_mac": "AA:BB:CC:11:22:33",
            "ap_mac": "00:11:22:33:44:55",
            "signal_strength": 80,
            "speed": 1200,
        }
    ]
    mock_client.get_all_hosts.return_value = [
        {"name": "FRITZ.Box", "mac": "00:11:22:33:44:55", "ip": "192.168.178.1", "status": True},
        {
            "name": "FRITZ!Repeater 1200",
            "mac": "00:11:22:33:44:66",
            "ip": "192.168.178.2",
            "status": True,
        },
        {
            "name": "FRITZ!Powerline 1260",
            "mac": "00:11:22:33:44:77",
            "ip": "192.168.178.3",
            "status": True,
        },
        {
            "name": "CustomDevice",
            "mac": "AA:BB:CC:11:22:33",
            "ip": "192.168.178.50",
            "status": True,
        },
        {"name": "StaticDevice", "mac": "AA:BB:CC:11:22:44", "ip": "10.0.0.5", "status": True},
    ]
    mock_client.get_mesh_info.return_value = {
        "nodes": [
            {
                "uid": "node1",
                "device_name": "fritz.box",
                "device_mac_address": "00:11:22:33:44:55",
                "device_vendor_class_id": "AVM",
                "device_capabilities": ["ROUTER"],
                "node_interfaces": [
                    {"type": "WLAN", "mac_address": "00:11:22:33:44:55"},
                    {
                        "type": "Ethernet",
                        "node_links": [
                            {
                                "node_1_uid": "node1",
                                "node_2_uid": "node2",
                                "cur_data_rate_rx": 1000000,
                                "cur_data_rate_tx": 1000000,
                            }
                        ],
                    },
                ],
                "ip_addresses": [
                    {"version": "V4", "value": "192.168.178.1/24", "attributes": ["DHCP"]}
                ],
            },
            {
                "uid": "node2",
                "device_name": "Repeater",
                "device_mac_address": "00:11:22:33:44:66",
                "device_vendor_class_id": "AVM_REPEATER",
                "device_capabilities": ["WLAN_ACCESS_POINT"],
                "node_interfaces": [],
                "ip_addresses": [{"version": "V4", "value": "192.168.178.2/24"}],
            },
            {
                "uid": "node3",
                "device_name": "Powerline",
                "device_mac_address": "00:11:22:33:44:77",
                "device_vendor_class_id": "AVM_POWERLINE",
                "device_capabilities": [],
                "node_interfaces": [],
                "ip_addresses": [{"version": "V4", "value": "192.168.178.3/24"}],
            },
        ]
    }
    mock_client.get_device_stats.return_value = {"rx_bytes": 5000, "tx_bytes": 3000}

    discovery = MeshDiscovery(
        mock_client,
        static_mappings={"10.0.0.5": "fritz.box"},
        manual_hierarchy={"00:11:22:33:44:77": "Repeater-4466"},
    )
    nodes, devices = discovery.discover()

    assert len(nodes) >= 3
    assert len(devices) >= 2

    dev_custom = [d for d in devices if d.name == "CustomDevice"][0]
    assert dev_custom.extra.get("signal_strength") == 80
    assert dev_custom.rx_bytes == 5000
