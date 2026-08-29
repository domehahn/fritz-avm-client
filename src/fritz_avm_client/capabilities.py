"""Capabilities detection and caching for Fritz!Box devices."""
from dataclasses import dataclass
from typing import Optional


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

    def __init__(self, fc=None) -> None:
        self._cached_capabilities: Optional[FritzCapabilities] = None

    def detect(self, fc) -> FritzCapabilities:
        """Detect capabilities from FritzConnection instance."""
        if self._cached_capabilities is not None:
            return self._cached_capabilities

        mesh = False
        cpu_temp = False
        dsl = False
        wlan = False
        host_traffic = False

        if fc is not None:
            services = getattr(fc, 'services', {})
            # Mesh support
            if 'Hosts1' in services and hasattr(fc, 'call_action'):
                mesh = True

            # CPU Temperature (Status service check)
            try:
                if hasattr(fc, 'call_action') and 'DeviceInfo1' in services:
                    cpu_temp = True
            except Exception:
                cpu_temp = False

            # DSL Metrics
            if 'WANIPConnection1' in services or 'WANPPPConnection1' in services or 'WANDSLInterfaceConfig1' in services:
                dsl = True

            # WLAN Statistics
            if 'WLANConfiguration1' in services:
                wlan = True

            # Host Traffic Statistics
            if 'Hosts1' in services:
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

