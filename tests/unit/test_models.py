"""Unit tests for domain models."""
import pytest
from fritz_avm_client.models import WanStats, Node, Device, MeshTopology


def test_wan_stats_immutability():
    stats = WanStats(total_bytes_received=100, total_bytes_sent=50)
    assert stats.total_bytes_received == 100
    with pytest.raises(AttributeError):
        stats.total_bytes_received = 200  # type: ignore


def test_node_model():
    node = Node(name="Repeater-1", mac="AA:BB:CC:DD:EE:FF", ip="192.168.178.50", is_repeater=True)
    assert node.name == "Repeater-1"
    assert node.is_repeater is True
    assert node.is_router is False


def test_mesh_topology_model():
    node = Node(name="Router", mac="11:22:33:44:55:66", is_router=True)
    device = Device(name="Phone", mac="AA:11:22:33:44:55", is_active=True)
    topology = MeshTopology(nodes=(node,), devices=(device,))
    assert len(topology.nodes) == 1
    assert len(topology.devices) == 1
