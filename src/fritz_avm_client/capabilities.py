"""Capabilities detection and caching for Fritz!Box devices."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, Any, Dict, List, Tuple
from collections.abc import Callable


@dataclass(frozen=True)
class FritzCapabilities:
    """Represents supported features and metrics of a Fritz!Box device."""

    mesh: bool = False
    cpu_temperature: bool = False
    dsl_metrics: bool = False
    wlan_statistics: bool = False
    host_traffic_statistics: bool = False


class CapabilityDetector:
    """Detects and caches Fritz!Box capabilities."""

    def __init__(self, fc: Any = None) -> None:
        self._cached_capabilities: Optional[FritzCapabilities] = None

    def detect(self, fc: Any) -> FritzCapabilities:
        """Detect capabilities from FritzConnection instance."""
        if self._cached_capabilities is not None:
            return self._cached_capabilities

        mesh = False
        cpu_temp = False
        dsl = False
        wlan = False
        host_traffic = False

        if fc is not None:
            services = getattr(fc, "services", {})
            # Mesh support
            if "Hosts1" in services and hasattr(fc, "call_action"):
                mesh = True

            # CPU Temperature (Status service check)
            try:
                if hasattr(fc, "call_action") and "DeviceInfo1" in services:
                    cpu_temp = True
            except Exception:
                cpu_temp = False

            # DSL Metrics
            if (
                "WANIPConnection1" in services
                or "WANPPPConnection1" in services
                or "WANDSLInterfaceConfig1" in services
            ):
                dsl = True

            # WLAN Statistics
            if "WLANConfiguration1" in services:
                wlan = True

            # Host Traffic Statistics
            if "Hosts1" in services:
                host_traffic = True

        caps = FritzCapabilities(
            mesh=mesh,
            cpu_temperature=cpu_temp,
            dsl_metrics=dsl,
            wlan_statistics=wlan,
            host_traffic_statistics=host_traffic,
        )
        self._cached_capabilities = caps
        return caps


# --- Action-level permission probing ----------------------------------------
#
# CapabilityDetector above only checks whether a *service* is present in the
# SCPD. It does not tell you whether the logged-in user may *call* a given
# action. A least-privilege FRITZ!Box account (one without the "FRITZ!Box
# Settings" permission) receives ``401 Invalid Action`` for the actions that
# back mesh topology, per-client Wi-Fi association data and the device log.

# feature -> (service, action, kwargs, human description of what it unlocks)
_PERMISSION_PROBES: list[tuple[str, str, str, dict[str, Any], str]] = [
    (
        "mesh_topology",
        "Hosts1",
        "X_AVM-DE_GetMeshListPath",
        {},
        "mesh hierarchy, per-repeater backhaul link rates and per-client access-point attribution",
    ),
    (
        "wlan_associations",
        "WLANConfiguration1",
        "GetTotalAssociations",
        {},
        "per-client Wi-Fi signal strength and negotiated PHY rate",
    ),
    (
        "device_log",
        "DeviceInfo1",
        "GetDeviceLog",
        {},
        "the FRITZ!Box event log",
    ),
]

_PERMISSION_ERROR_MARKERS = (
    "401",
    "403",
    "unauthorized",
    "invalid action",
    "not authorized",
)


def _is_permission_error(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return any(marker in msg for marker in _PERMISSION_ERROR_MARKERS)


@dataclass
class PermissionReport:
    """Result of :func:`probe_permissions` / :meth:`FritzClient.probe_capabilities`."""

    #: feature name -> callable today
    available: dict[str, bool] = field(default_factory=dict)
    #: features that failed specifically because of account permissions
    permission_denied: list[str] = field(default_factory=list)
    #: feature -> one-line description of what it unlocks
    unlocks: dict[str, str] = field(default_factory=dict)

    def as_flags(self) -> dict[str, int]:
        """``{feature: 1|0}`` — convenient for exporting as metrics."""
        return {k: (1 if v else 0) for k, v in self.available.items()}


def probe_permissions(
    call_action: Callable[..., Any],
    probes: Optional[list[tuple[str, str, str, dict[str, Any], str]]] = None,
) -> PermissionReport:
    """Call each gated action once and classify the outcome.

    Args:
        call_action: ``FritzConnection.call_action`` (service, action, **kwargs).
        probes: override the default probe set (mainly for testing).
    """
    probe_list = probes if probes is not None else _PERMISSION_PROBES
    report = PermissionReport()
    for feature, service, action, kwargs, unlocks in probe_list:
        report.unlocks[feature] = unlocks
        try:
            call_action(service, action, **kwargs)
            report.available[feature] = True
        except Exception as exc:  # noqa: BLE001 - any failure means unavailable
            report.available[feature] = False
            if _is_permission_error(exc):
                report.permission_denied.append(feature)
    return report
