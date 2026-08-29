"""Hosts client for device queries and host entries."""
from typing import List, Dict, Any, Optional
from fritzconnection.lib.fritzhosts import FritzHosts

from .exceptions import FritzConnectionError, FritzTimeoutError


class HostsClient:
    """Handles host entries, device lookup, and MAC traffic queries."""

    def __init__(self, fc) -> None:
        self.fc = fc
        self._hosts: Optional[FritzHosts] = None

    @property
    def hosts(self) -> FritzHosts:
        if self._hosts is None:
            self._hosts = FritzHosts(self.fc)
        return self._hosts

    def get_all_hosts(self) -> List[Dict[str, Any]]:
        """Get all host entries from Fritz!Box."""
        try:
            return self.hosts.get_hosts_info()
        except TimeoutError as exc:
            raise FritzTimeoutError(f"Timeout fetching hosts: {exc}") from exc
        except Exception as exc:
            raise FritzConnectionError(f"Error fetching hosts: {exc}") from exc

    def get_device_stats(self, mac_address: str) -> Dict[str, int]:
        """Get traffic statistics for a specific MAC address."""
        if not mac_address:
            return {'rx_bytes': 0, 'tx_bytes': 0}
        try:
            result = self.fc.call_action(
                'Hosts1',
                'GetSpecificHostEntry',
                NewMACAddress=mac_address
            )
            return {
                'rx_bytes': result.get('NewX_AVM-DE_RxBytes', 0) or 0,
                'tx_bytes': result.get('NewX_AVM-DE_TxBytes', 0) or 0,
            }
        except Exception:
            return {'rx_bytes': 0, 'tx_bytes': 0}

