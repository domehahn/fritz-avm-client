"""Fritz!Box client facade with retry logic and modular sub-clients."""

from __future__ import annotations
import time
import random
from typing import Dict, Any, List, Optional, TypeVar, cast
from collections.abc import Callable
from fritzconnection import FritzConnection

from .config import Settings
from .capabilities import CapabilityDetector, FritzCapabilities, PermissionReport
from .router import RouterClient
from .hosts import HostsClient
from .wlan import WlanClient
from .admin import AdminClient
from .discovery import MeshDiscovery, _coerce_null_lists
from .models import WanStats, DslStats, WlanStats, MeshTopology
from .exceptions import (
    FritzConfigurationError,
    FritzConnectionError,
    FritzTimeoutError,
    FritzAuthenticationError,
)

T = TypeVar("T")


class FritzClient:
    """Production-ready client for AVM Fritz!Box routers and mesh networks."""

    def __init__(self, settings: Settings) -> None:
        """Initialize Fritz!Box client.

        Args:
            settings: Settings instance with host, auth, and timeout parameters.
        """
        self.settings = settings
        self.password = settings.resolved_password

        try:
            self.fc = FritzConnection(
                address=settings.fritz_host,
                port=settings.fritz_port,
                user=settings.fritz_username,
                password=self.password,
                timeout=settings.fritz_timeout,
                use_tls=settings.fritz_use_tls,
            )
        except Exception as exc:
            err_msg = str(exc).lower()
            if "unauthorized" in err_msg or "accessdenied" in err_msg or "401" in err_msg:
                raise FritzAuthenticationError(
                    f"Authentication failed for user {settings.fritz_username}"
                ) from exc
            elif "timeout" in err_msg:
                raise FritzTimeoutError(
                    f"Connection to {settings.fritz_host}:{settings.fritz_port} timed out"
                ) from exc
            else:
                raise FritzConnectionError(
                    f"Failed to connect to Fritz!Box at {settings.fritz_host}: {exc}"
                ) from exc

        self.capability_detector = CapabilityDetector()
        self.router_client = RouterClient(self.fc)
        self.hosts_client = HostsClient(self.fc)
        self.wlan_client = WlanClient(self.fc)
        self.admin = AdminClient(self.fc)
        self._mesh_discovery: Optional[MeshDiscovery] = None

    @property
    def capabilities(self) -> FritzCapabilities:
        """Get cached capabilities of the connected device."""
        return self.capability_detector.detect(self.fc)

    @property
    def mesh_discovery(self) -> MeshDiscovery:
        if self._mesh_discovery is None:
            self._mesh_discovery = MeshDiscovery(self)
        return self._mesh_discovery

    def __enter__(self) -> FritzClient:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()

    def close(self) -> None:
        """Close connection resources if supported."""
        if hasattr(self.fc, "close"):
            try:
                self.fc.close()
            except Exception:
                pass

    def _execute_with_retry(
        self, func: Callable[[], T], max_retries: int = 2, initial_backoff: float = 0.5
    ) -> T:
        """Execute a function with exponential backoff and jitter for transient errors."""
        last_exception = None
        for attempt in range(max_retries + 1):
            try:
                return func()
            except (FritzTimeoutError, FritzConnectionError) as exc:
                last_exception = exc
                if attempt < max_retries:
                    sleep_time = (initial_backoff * (2**attempt)) + random.uniform(0, 0.1)
                    time.sleep(sleep_time)
                else:
                    raise exc
            except (FritzAuthenticationError, FritzConfigurationError):
                raise
        if last_exception:
            raise last_exception
        raise FritzConnectionError("Execution failed without exception")

    def get_capabilities(self) -> FritzCapabilities:
        """Get detected device capabilities."""
        return self.capabilities

    def get_all_hosts(self) -> list[dict[str, Any]]:
        """Get all host entries from Fritz!Box hosts table."""
        res: list[dict[str, Any]] = self._execute_with_retry(self.hosts_client.get_hosts_info)
        return res

    def get_mesh_info(self) -> Optional[dict[str, Any]]:
        """Get raw mesh topology information.

        List-valued fields that some FRITZ!OS versions return as JSON ``null``
        are coerced to ``[]`` so callers can iterate safely.
        """
        try:
            res = self.hosts_client.hosts.get_mesh_topology()
            return cast(Optional[dict[str, Any]], _coerce_null_lists(res))
        except Exception:
            return None

    def get_device_stats(self, mac_address: str) -> Optional[dict[str, int]]:
        """Get traffic statistics for a specific MAC address or None if unavailable.

        Does NOT return fake 0 values when data is unknown or unsupported.
        """
        try:
            info = self.hosts_client.hosts.get_specific_host_entry(mac_address)
            if info:
                rx = info.get("X_AVM-DE_RxBytes")
                tx = info.get("X_AVM-DE_TxBytes")
                if rx is not None and tx is not None:
                    return {"rx_bytes": int(rx), "tx_bytes": int(tx)}
        except Exception:
            pass
        return None

    def get_wan_stats(self) -> dict[str, Any]:
        """Get WAN statistics preserving None values for missing metrics."""
        stats: WanStats = self._execute_with_retry(self.router_client.get_wan_stats)
        dsl: DslStats = self.router_client.get_dsl_stats()

        return {
            "total_bytes_sent": stats.total_bytes_sent,
            "total_bytes_received": stats.total_bytes_received,
            "bytes_sent": stats.total_bytes_sent,
            "bytes_received": stats.total_bytes_received,
            "max_upstream_rate": stats.max_upstream_rate,
            "max_downstream_rate": stats.max_downstream_rate,
            "max_byte_rate_up": stats.max_upstream_rate,
            "max_byte_rate_down": stats.max_downstream_rate,
            "current_download_rate": stats.current_download_rate,
            "current_upload_rate": stats.current_upload_rate,
            "device_uptime": stats.device_uptime,
            "uptime": stats.device_uptime,
            "connection_uptime": stats.connection_uptime,
            "is_connected": stats.is_connected,
            "external_ip": stats.external_ip,
            "attenuation": (dsl.downstream_attenuation, dsl.upstream_attenuation),
            "noise_margin": (dsl.downstream_noise_margin, dsl.upstream_noise_margin),
            "dsl_downstream_attenuation": dsl.downstream_attenuation,
            "dsl_upstream_attenuation": dsl.upstream_attenuation,
            "dsl_downstream_noise_margin": dsl.downstream_noise_margin,
            "dsl_upstream_noise_margin": dsl.upstream_noise_margin,
            "cpu_temperatures": stats.cpu_temperatures,
        }

    def get_wan_stats_typed(self) -> WanStats:
        """Get WAN statistics as a typed WanStats domain model."""
        return self._execute_with_retry(self.router_client.get_wan_stats)

    def get_cpu_temperatures(self) -> dict[str, float]:
        """Get CPU temperatures dict."""
        return self.router_client.get_cpu_temperatures()

    def get_wlan_traffic_stats(self) -> dict[str, Any]:
        """Get aggregated WLAN interface packet counts."""
        wlan_stats_list: list[WlanStats] = self._execute_with_retry(self.wlan_client.get_wlan_stats)
        clients_list = [
            s.connected_clients for s in wlan_stats_list if s.connected_clients is not None
        ]
        sent_list = [
            s.total_packets_sent for s in wlan_stats_list if s.total_packets_sent is not None
        ]
        recv_list = [
            s.total_packets_received
            for s in wlan_stats_list
            if s.total_packets_received is not None
        ]

        return {
            "total_packets_sent": sum(sent_list) if sent_list else None,
            "total_packets_received": sum(recv_list) if recv_list else None,
            "connected_clients": sum(clients_list) if clients_list else None,
        }

    def get_wlan_devices(self) -> list[dict[str, Any]]:
        """Associated WLAN stations across all radio bands (not just 2.4 GHz)."""
        return self.wlan_client.get_all_associated_devices()

    def probe_capabilities(self) -> PermissionReport:
        """Actively test the permission-gated TR-064 actions once.

        The SCPD-based :class:`CapabilityDetector` only reports whether a
        *service* exists, not whether the logged-in user may call a given
        *action*. A least-privilege FRITZ!Box account gets ``401`` for the
        actions backing mesh topology, per-client Wi-Fi and the device log.
        """
        from .capabilities import probe_permissions

        return probe_permissions(self.fc.call_action)

    def discover_mesh(self) -> MeshTopology:
        """Discover mesh topology returning typed MeshTopology (nodes, devices)."""
        nodes, devices = self.mesh_discovery.discover()
        return MeshTopology(nodes=tuple(nodes), devices=tuple(devices))
