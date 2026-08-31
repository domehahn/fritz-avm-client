"""WLAN client for wireless access point and associated station statistics."""

from __future__ import annotations
from typing import List, Dict, Any, cast
from fritzconnection.lib.fritzwlan import FritzWLAN
from fritzconnection.core.exceptions import FritzServiceError, FritzActionError

from .models import WlanStats
from .exceptions import FritzConnectionError, FritzTimeoutError, FritzAuthenticationError


class WlanClient:
    """Handles WLAN configuration, SSIDs, and connected station statistics."""

    def __init__(self, fc: Any) -> None:
        self.fc = fc

    def get_wlan_stats(self) -> list[WlanStats]:
        """Get WLAN statistics across all available radio bands (2.4GHz, 5GHz, 6GHz)."""
        stats_list: list[WlanStats] = []
        try:
            for i in range(1, 5):
                try:
                    wlan = FritzWLAN(self.fc, service=i)
                    ssid = getattr(wlan, "ssid", None)
                    channel = getattr(wlan, "channel", None)
                    devices = (
                        wlan.get_associated_devices()
                        if hasattr(wlan, "get_associated_devices")
                        else (wlan.get_hosts_info() if hasattr(wlan, "get_hosts_info") else [])
                    )
                    num_clients = (
                        len(devices)
                        if devices is not None
                        else (getattr(wlan, "total_host_number", 0) or 0)
                    )
                    stats_list.append(
                        WlanStats(
                            service_index=i,
                            ssid=ssid,
                            channel=channel,
                            connected_clients=num_clients,
                        )
                    )
                except (FritzServiceError, FritzActionError):
                    # Service instance i does not exist on this device (e.g. only 2 bands exist)
                    break
                except TimeoutError as exc:
                    raise FritzTimeoutError(f"Timeout querying WLAN service {i}: {exc}") from exc
                except Exception as exc:
                    err_str = str(exc).lower()
                    if "unauthorized" in err_str or "401" in err_str:
                        raise FritzAuthenticationError(
                            f"Authentication failed querying WLAN service {i}"
                        ) from exc
                    elif "nosuchservice" in err_str or "713" in err_str or "714" in err_str:
                        break
                    raise FritzConnectionError(
                        f"Connection error querying WLAN service {i}: {exc}"
                    ) from exc
        except (FritzTimeoutError, FritzAuthenticationError, FritzConnectionError):
            raise
        except TimeoutError as exc:
            raise FritzTimeoutError(f"Timeout fetching WLAN stats: {exc}") from exc
        except Exception as exc:
            raise FritzConnectionError(f"Error fetching WLAN stats: {exc}") from exc

        return stats_list

    def get_associated_devices(self, service_index: int = 1) -> list[dict[str, Any]]:
        """Associated wireless stations for one WLAN service index.

        Rows follow fritzconnection's ``FritzWLAN.get_hosts_info()`` shape:
        ``service``, ``index``, ``status``, ``mac``, ``ip``, ``signal``,
        ``speed``. Returns ``[]`` if the service is absent or access is
        restricted.
        """
        try:
            wlan = FritzWLAN(self.fc, service=service_index)
            devices = (
                wlan.get_associated_devices()
                if hasattr(wlan, "get_associated_devices")
                else (wlan.get_hosts_info() if hasattr(wlan, "get_hosts_info") else [])
            )
            return cast(list[dict[str, Any]], devices or [])
        except TimeoutError as exc:
            raise FritzTimeoutError(
                f"Timeout fetching associated devices for WLAN {service_index}: {exc}"
            ) from exc
        except Exception:
            # Service not available, 401 restricted, or unsupported
            return []

    def get_all_associated_devices(self, max_service_index: int = 4) -> list[dict[str, Any]]:
        """Associated stations across every radio band (2.4/5/6 GHz + guest).

        ``get_associated_devices(1)`` alone only sees the 2.4 GHz band. This
        merges services ``1..max_service_index`` and de-duplicates by MAC,
        keeping the row with the strongest signal.
        """
        best: dict[str, dict[str, Any]] = {}
        for idx in range(1, max_service_index + 1):
            rows = self.get_associated_devices(idx)
            if not rows:
                continue
            for row in rows:
                if not isinstance(row, dict):
                    continue
                mac = (
                    row.get("mac")
                    or row.get("device_mac")
                    or row.get("MACAddress")
                    or row.get("NewAssociatedDeviceMACAddress")
                    or ""
                ).upper()
                if not mac:
                    continue
                sig = row.get("signal", row.get("signal_strength", 0)) or 0
                prev = best.get(mac)
                prev_sig = prev.get("signal", prev.get("signal_strength", 0)) or 0 if prev else -1
                if prev is None or sig >= prev_sig:
                    best[mac] = row
        return list(best.values())
