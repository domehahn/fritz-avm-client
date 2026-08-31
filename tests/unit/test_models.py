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


def test_node_kind():
    assert Node(name="fritz.box", mac="1", is_router=True).kind == "router"
    assert Node(name="R", mac="2", is_repeater=True).kind == "repeater"
    assert Node(name="P", mac="3", is_powerline=True).kind == "powerline"
    # powerline takes precedence over repeater flag
    assert Node(name="P", mac="4", is_repeater=True, is_powerline=True).kind == "powerline"
    assert Node(name="?", mac="5").kind == "unknown"


def test_node_is_placeholder():
    assert Node(name="fritz.repeater", mac="1").is_placeholder is True
    assert Node(name="FRITZ.Powerline", mac="2").is_placeholder is True
    assert Node(name="", mac="3").is_placeholder is True
    assert Node(name="Repeater-OG", mac="4", is_repeater=True).is_placeholder is False
    # the router itself is never a placeholder even though its name matches
    assert Node(name="fritz.box", mac="5", is_router=True).is_placeholder is False
