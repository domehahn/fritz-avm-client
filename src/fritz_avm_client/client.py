"""Fritz!Box client facade with retry logic and modular sub-clients."""
import time
import random
from typing import Dict, Any, List, Optional
from fritzconnection import FritzConnection

from .config import Settings
from .capabilities import CapabilityDetector, FritzCapabilities
from .router import RouterClient
from .hosts import HostsClient
from .wlan import WlanClient
from .discovery import MeshDiscovery
from .models import WanStats, DslStats, WlanStats, MeshTopology
from .exceptions import (
    FritzError,
    FritzConfigurationError,
    FritzConnectionError,
    FritzTimeoutError,
    FritzAuthenticationError,
)


class FritzClient:
    """Production-ready client for AVM Fritz!Box routers and mesh networks."""

    def __init__(self, settings: Settings):
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
            if 'unauthorized' in err_msg or 'accessdenied' in err_msg or '401' in err_msg:
                raise FritzAuthenticationError(f"Authentication failed for user {settings.fritz_username}") from exc
            elif 'timeout' in err_msg:
                raise FritzTimeoutError(f"Connection to {settings.fritz_host}:{settings.fritz_port} timed out") from exc
            else:
                raise FritzConnectionError(f"Failed to connect to Fritz!Box at {settings.fritz_host}: {exc}") from exc

        self.capability_detector = CapabilityDetector()
        self.router_client = RouterClient(self.fc)
        self.hosts_client = HostsClient(self.fc)
        self.wlan_client = WlanClient(self.fc)
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

    def _execute_with_retry(self, func, max_retries: int = 2, initial_backoff: float = 0.5):
        """Execute a function with exponential backoff and jitter for transient errors."""
        last_exception = None
        for attempt in range(max_retries + 1):
            try:
                return func()
            except (FritzTimeoutError, FritzConnectionError) as exc:
                last_exception = exc
                if attempt < max_retries:
                    sleep_time = (initial_backoff * (2 ** attempt)) + random.uniform(0, 0.1)
                    time.sleep(sleep_time)
                else:
                    raise exc
            except (FritzAuthenticationError, FritzConfigurationError):
                raise
        if last_exception:
            raise last_exception

    def get_capabilities(self) -> FritzCapabilities:
        """Get detected device capabilities."""
        return self.capabilities

    def get_all_hosts(self) -> List[Dict[str, Any]]:
        """Get all host entries from Fritz!Box hosts table."""
        return self._execute_with_retry(self.hosts_client.get_all_hosts)

    def get_mesh_info(self) -> Optional[Dict[str, Any]]:
        """Get raw mesh topology information."""
        try:
            return self.hosts_client.hosts.get_mesh_topology()
        except Exception:
            return None

    def get_device_stats(self, mac_address: str) -> Dict[str, int]:
        """Get traffic statistics for a specific MAC address."""
        return self.hosts_client.get_device_stats(mac_address)

    def get_wan_stats(self) -> Dict[str, Any]:
        """Get WAN statistics as a dictionary (compatible with legacy callers and typed WAN model)."""
        stats: WanStats = self._execute_with_retry(self.router_client.get_wan_stats)
        dsl: DslStats = self.router_client.get_dsl_stats()

        down_atten = dsl.downstream_attenuation or 0.0
        up_atten = dsl.upstream_attenuation or 0.0
        down_noise = dsl.downstream_noise_margin or 0.0
        up_noise = dsl.upstream_noise_margin or 0.0

        return {
            'total_bytes_sent': stats.total_bytes_sent or 0,
            'total_bytes_received': stats.total_bytes_received or 0,
            'bytes_sent': stats.total_bytes_sent or 0,
            'bytes_received': stats.total_bytes_received or 0,
            'max_upstream_rate': stats.max_upstream_rate or 0,
            'max_downstream_rate': stats.max_downstream_rate or 0,
            'max_byte_rate_up': stats.max_upstream_rate or 0,
            'max_byte_rate_down': stats.max_downstream_rate or 0,
            'current_download_rate': stats.current_download_rate or 0,
            'current_upload_rate': stats.current_upload_rate or 0,
            'device_uptime': stats.device_uptime or 0,
            'uptime': stats.device_uptime or 0,
            'connection_uptime': stats.connection_uptime or 0,
            'is_connected': bool(stats.is_connected),
            'external_ip': stats.external_ip or '',
            'attenuation': (down_atten, up_atten),
            'noise_margin': (down_noise, up_noise),
            'dsl_downstream_attenuation': down_atten,
            'dsl_upstream_attenuation': up_atten,
            'dsl_downstream_noise_margin': down_noise,
            'dsl_upstream_noise_margin': up_noise,
            'cpu_temperatures': stats.cpu_temperatures,
        }

    def get_wan_stats_typed(self) -> WanStats:
        """Get WAN statistics as a typed WanStats domain model."""
        return self._execute_with_retry(self.router_client.get_wan_stats)

    def get_cpu_temperatures(self) -> Dict[str, float]:
        """Get CPU temperatures dict."""
        return self.router_client.get_cpu_temperatures()

    def get_wlan_traffic_stats(self) -> Dict[str, int]:
        """Get aggregated WLAN interface packet counts."""
        stats: WlanStats = self._execute_with_retry(self.wlan_client.get_wlan_traffic_stats)
        return {
            'total_packets_sent': stats.total_packets_sent,
            'total_packets_received': stats.total_packets_received,
        }

    def get_wlan_devices(self) -> List[Dict[str, Any]]:
        """Get associated WLAN devices list."""
        return self._execute_with_retry(self.wlan_client.get_wlan_devices)

    def discover_mesh(self) -> MeshTopology:
        """Discover mesh topology returning typed MeshTopology (nodes, devices)."""
        nodes, devices = self.mesh_discovery.discover()
        return MeshTopology(nodes=tuple(nodes), devices=tuple(devices))
