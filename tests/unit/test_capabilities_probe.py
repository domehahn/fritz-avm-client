"""Unit tests for action-level permission probing."""

from fritz_avm_client.capabilities import PermissionReport, probe_permissions

PROBES = [
    ("mesh_topology", "Hosts1", "X_AVM-DE_GetMeshListPath", {}, "mesh"),
    ("wlan_associations", "WLANConfiguration1", "GetTotalAssociations", {}, "wifi"),
    ("device_log", "DeviceInfo1", "GetDeviceLog", {}, "log"),
]


def test_all_available():
    r = probe_permissions(lambda *a, **k: {}, probes=PROBES)
    assert r.available == {
        "mesh_topology": True,
        "wlan_associations": True,
        "device_log": True,
    }
    assert r.permission_denied == []
    assert r.as_flags() == {
        "mesh_topology": 1,
        "wlan_associations": 1,
        "device_log": 1,
    }
    assert r.unlocks["mesh_topology"] == "mesh"


def test_permission_denied_classified():
    def call(_svc, action, **_kw):
        if action == "GetTotalAssociations":
            return {}
        raise RuntimeError("UPnPError: errorCode: 401 errorDescription: Invalid Action")

    r = probe_permissions(call, probes=PROBES)
    assert r.available == {
        "mesh_topology": False,
        "wlan_associations": True,
        "device_log": False,
    }
    assert sorted(r.permission_denied) == ["device_log", "mesh_topology"]
    assert r.as_flags()["mesh_topology"] == 0


def test_non_permission_failure_not_flagged():
    def call(*_a, **_k):
        raise TimeoutError("read timed out")

    r = probe_permissions(call, probes=PROBES)
    assert all(v is False for v in r.available.values())
    assert r.permission_denied == []


def test_report_defaults():
    r = PermissionReport()
    assert r.available == {} and r.permission_denied == [] and r.unlocks == {}
