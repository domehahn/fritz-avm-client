"""WLAN client for wireless access point and associated station statistics."""
from __future__ import annotations
from typing import List, Dict, Any, cast
from fritzconnection.lib.fritzwlan import FritzWLAN

from .models import WlanStats
from .exceptions import FritzConnectionError, FritzTimeoutError


class WlanClient:
    """Handles WLAN configuration, SSIDs, and connected station statistics."""

    def __init__(self, fc: Any) -> None:
        self.fc = fc

    def get_wlan_stats(self) -> List[WlanStats]:
        """Get WLAN statistics across all available radio bands (2.4GHz, 5GHz, 6GHz)."""
        stats_list: List[WlanStats] = []
        try:
            # Query up to 4 potential WLAN instances
            for i in range(1, 5):
                try:
                    wlan = FritzWLAN(self.fc, service=i)
                    ssid = getattr(wlan, 'ssid', None)
                    channel = getattr(wlan, 'channel', None)
                    num_clients = len(wlan.get_associated_devices()) if hasattr(wlan, 'get_associated_devices') else 0
                    stats_list.append(
                        WlanStats(
                            service_index=i,
                            ssid=ssid,
                            channel=channel,
                            connected_clients=num_clients,
                        )
                    )
                except Exception:
                    # Service instance i does not exist or is inactive
                    break
        except TimeoutError as exc:
            raise FritzTimeoutError(f"Timeout fetching WLAN stats: {exc}") from exc
        except Exception as exc:
            raise FritzConnectionError(f"Error fetching WLAN stats: {exc}") from exc

        return stats_list

    def get_associated_devices(self, service_index: int = 1) -> List[Dict[str, Any]]:
        """Get list of associated wireless stations for a given WLAN service index."""
        try:
            wlan = FritzWLAN(self.fc, service=service_index)
            devices = wlan.get_associated_devices()
            return cast(List[Dict[str, Any]], devices)
        except Exception:
            return []
