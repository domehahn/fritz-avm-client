"""WLAN client for interface stats and device AP associations."""
from typing import List, Dict, Any, Optional
from fritzconnection.lib.fritzwlan import FritzWLAN

from .models import WlanStats
from .exceptions import FritzConnectionError, FritzTimeoutError


class WlanClient:
    """Handles WLAN statistics and client AP mappings."""

    def __init__(self, fc) -> None:
        self.fc = fc
        self._wlan: Optional[FritzWLAN] = None

    @property
    def wlan(self) -> FritzWLAN:
        if self._wlan is None:
            self._wlan = FritzWLAN(self.fc)
        return self._wlan

    def get_wlan_traffic_stats(self) -> WlanStats:
        """Get aggregated WiFi interface traffic statistics across all bands."""
        total_sent = 0
        total_received = 0
        try:
            for service_id in range(1, 5):
                try:
                    service_name = f'WLANConfiguration{service_id}'
                    result = self.fc.call_action(service_name, 'GetStatistics')
                    total_sent += result.get('NewTotalPacketsSent', 0) or 0
                    total_received += result.get('NewTotalPacketsReceived', 0) or 0
                except Exception:
                    continue
        except TimeoutError as exc:
            raise FritzTimeoutError(f"Timeout fetching WLAN stats: {exc}") from exc
        except Exception as exc:
            raise FritzConnectionError(f"Error fetching WLAN stats: {exc}") from exc

        return WlanStats(
            total_packets_sent=total_sent,
            total_packets_received=total_received,
        )

    def get_wlan_devices(self) -> List[Dict[str, Any]]:
        """Get all devices connected via WLAN with associated AP MAC."""
        wlan_devices = []
        try:
            for service_id in range(1, 5):
                try:
                    service_name = f'WLANConfiguration{service_id}'
                    result = self.fc.call_action(service_name, 'GetTotalAssociations')
                    total = result.get('NewTotalAssociations', 0) or 0

                    bssid_result = self.fc.call_action(service_name, 'GetInfo')
                    ap_mac = bssid_result.get('NewBSSID', '')

                    for i in range(total):
                        try:
                            device_info = self.fc.call_action(
                                service_name,
                                'GetGenericAssociatedDeviceInfo',
                                NewAssociatedDeviceIndex=i
                            )
                            device_mac = device_info.get('NewAssociatedDeviceMACAddress', '')
                            if device_mac:
                                wlan_devices.append({
                                    'device_mac': device_mac,
                                    'ap_mac': ap_mac,
                                    'service': service_name,
                                    'ip': device_info.get('NewAssociatedDeviceIPAddress', ''),
                                    'signal_strength': device_info.get('NewX_AVM-DE_SignalStrength', 0),
                                    'speed': device_info.get('NewX_AVM-DE_Speed', 0),
                                })
                        except Exception:
                            continue
                except Exception:
                    continue
        except TimeoutError as exc:
            raise FritzTimeoutError(f"Timeout fetching WLAN devices: {exc}") from exc
        except Exception as exc:
            raise FritzConnectionError(f"Error fetching WLAN devices: {exc}") from exc

        return wlan_devices

