"""Router client for WAN stats, DSL quality, and CPU temperatures."""
from __future__ import annotations
from typing import Dict, Optional, Any
from fritzconnection.lib.fritzstatus import FritzStatus

from .models import WanStats, DslStats
from .exceptions import FritzConnectionError, FritzTimeoutError, FritzAuthenticationError


class RouterClient:
    """Handles WAN status, DSL line quality, and CPU temperatures."""

    def __init__(self, fc: Any) -> None:
        self.fc = fc
        self._status: Optional[FritzStatus] = None

    @property
    def status(self) -> FritzStatus:
        if self._status is None:
            self._status = FritzStatus(self.fc)
        return self._status

    def get_cpu_temperatures(self) -> Dict[str, float]:
        """Get CPU temperature readings if supported."""
        try:
            temps = self.status.get_cpu_temperatures()
            if temps:
                result = {}
                for i, temp in enumerate(temps):
                    result[f"cpu{i}"] = float(temp)
                return result
        except TimeoutError as exc:
            raise FritzTimeoutError(f"Timeout reading CPU temperatures: {exc}") from exc
        except Exception as exc:
            err_str = str(exc).lower()
            if "unauthorized" in err_str or "401" in err_str:
                raise FritzAuthenticationError(
                    "Authentication failed reading CPU temperatures"
                ) from exc
            elif "nosuchservice" in err_str or "unsupported" in err_str:
                pass
            else:
                # Cable/Fiber or unsupported hardware without temperature sensors
                pass
        return {}

    def get_dsl_stats(self) -> DslStats:
        """Get DSL line quality statistics."""
        try:
            attenuation = self.status.attenuation
            noise_margin = self.status.noise_margin
            return DslStats(
                downstream_attenuation=float(attenuation[0])
                if attenuation and attenuation[0] is not None
                else None,
                upstream_attenuation=float(attenuation[1])
                if attenuation and len(attenuation) > 1 and attenuation[1] is not None
                else None,
                downstream_noise_margin=float(noise_margin[0])
                if noise_margin and noise_margin[0] is not None
                else None,
                upstream_noise_margin=float(noise_margin[1])
                if noise_margin and len(noise_margin) > 1 and noise_margin[1] is not None
                else None,
            )
        except TimeoutError as exc:
            raise FritzTimeoutError(f"Timeout fetching DSL stats: {exc}") from exc
        except Exception as exc:
            err_str = str(exc).lower()
            if "unauthorized" in err_str or "401" in err_str:
                raise FritzAuthenticationError("Authentication failed fetching DSL stats") from exc
            elif "nosuchservice" in err_str or "invalid" in err_str:
                # Cable, Fiber, or WAN Ethernet connection without DSL interface
                return DslStats()
            raise FritzConnectionError(f"Error fetching DSL stats: {exc}") from exc

    def get_wan_stats(self) -> WanStats:
        """Get WAN connection statistics and real-time rates."""
        try:
            current_rates = self.status.transmission_rate
            connection_uptime = getattr(self.status, "connection_uptime", None)
            external_ip = getattr(self.status, "external_ip", None)

            max_byte_rate = self.status.max_byte_rate
            max_down = max_byte_rate[0] if max_byte_rate else None
            max_up = max_byte_rate[1] if max_byte_rate and len(max_byte_rate) > 1 else None

            down_rate = current_rates[0] if current_rates else None
            up_rate = current_rates[1] if current_rates and len(current_rates) > 1 else None

            device_uptime = getattr(self.status, "device_uptime", None)

            return WanStats(
                total_bytes_received=self.status.bytes_received,
                total_bytes_sent=self.status.bytes_sent,
                current_download_rate=down_rate,
                current_upload_rate=up_rate,
                max_downstream_rate=max_down,
                max_upstream_rate=max_up,
                device_uptime=device_uptime,
                connection_uptime=connection_uptime,
                external_ip=external_ip or None,
                is_connected=self.status.is_connected,
                cpu_temperatures=self.get_cpu_temperatures(),
            )
        except TimeoutError as exc:
            raise FritzTimeoutError(f"Timeout fetching WAN stats: {exc}") from exc
        except Exception as exc:
            err_str = str(exc).lower()
            if "unauthorized" in err_str or "401" in err_str:
                raise FritzAuthenticationError("Authentication failed fetching WAN stats") from exc
            raise FritzConnectionError(f"Error fetching WAN stats: {exc}") from exc
