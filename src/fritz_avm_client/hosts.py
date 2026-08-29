"""Hosts client for host list and per-host traffic stats."""
from __future__ import annotations
from typing import List, Dict, Optional, Any, cast
from fritzconnection.lib.fritzhosts import FritzHosts

from .exceptions import FritzConnectionError, FritzTimeoutError


class HostsClient:
    """Handles FRITZ!Box host management and device query operations."""

    def __init__(self, fc: Any) -> None:
        self.fc = fc
        self._hosts: Optional[FritzHosts] = None

    @property
    def hosts(self) -> FritzHosts:
        if self._hosts is None:
            self._hosts = FritzHosts(self.fc)
        return self._hosts

    def get_hosts_info(self) -> List[Dict[str, Any]]:
        """Get list of all host entries from FRITZ!Box."""
        try:
            res = self.hosts.get_hosts_info()
            return cast(List[Dict[str, Any]], res)
        except TimeoutError as exc:
            raise FritzTimeoutError(f"Timeout fetching hosts info: {exc}") from exc
        except Exception as exc:
            raise FritzConnectionError(f"Error fetching hosts info: {exc}") from exc

    def get_host_details(self, index: int) -> Dict[str, Any]:
        """Get detailed host info by index."""
        try:
            res = self.hosts.get_generic_host_entry(index)
            return cast(Dict[str, Any], res)
        except Exception:
            return {}

    def get_host_number(self) -> int:
        """Get count of registered hosts."""
        try:
            num = self.hosts.host_number
            return int(num)
        except Exception:
            return 0
