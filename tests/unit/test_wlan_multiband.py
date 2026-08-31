"""Unit tests for multi-band WLAN association merge and null-list coercion."""

from unittest.mock import MagicMock

from fritz_avm_client.wlan import WlanClient
from fritz_avm_client.discovery import _coerce_null_lists


def test_get_all_associated_devices_merges_bands_and_dedups_by_strongest():
    wc = WlanClient(MagicMock())
    by_idx = {
        1: [{"mac": "AA", "signal": 40, "speed": 72}],  # 2.4 GHz, weak
        2: [
            {"mac": "AA", "signal": 90, "speed": 866},  # 5 GHz, strong -> wins
            {"mac": "BB", "signal": 55, "speed": 200},
        ],
        3: [],
        4: [],
    }
    wc.get_associated_devices = lambda idx: by_idx.get(idx, [])  # type: ignore
    rows = {r["mac"]: r for r in wc.get_all_associated_devices()}
    assert set(rows) == {"AA", "BB"}
    assert rows["AA"]["signal"] == 90 and rows["AA"]["speed"] == 866


def test_get_all_associated_devices_tolerates_key_spellings_and_junk():
    wc = WlanClient(MagicMock())
    wc.get_associated_devices = lambda idx: (  # type: ignore
        [{"MACAddress": "CC", "signal": 60}, "garbage", {"no_mac": 1}] if idx == 1 else []
    )
    rows = wc.get_all_associated_devices()
    assert [r.get("MACAddress") for r in rows] == ["CC"]


def test_coerce_null_lists():
    doc = {
        "nodes": None,
        "schema_version": "1",
        "extra": {"node_interfaces": None, "keep": "x"},
        "list": [{"ip_addresses": None}, {"ip_addresses": [1]}],
    }
    out = _coerce_null_lists(doc)
    assert out["nodes"] == []
    assert out["schema_version"] == "1"
    assert out["extra"]["node_interfaces"] == [] and out["extra"]["keep"] == "x"
    assert out["list"][0]["ip_addresses"] == [] and out["list"][1]["ip_addresses"] == [1]
    assert _coerce_null_lists(None) is None
