"""Administrative operations client for FRITZ!Box device management."""
from __future__ import annotations
import re
from typing import Any
from .exceptions import FritzConnectionError, FritzTimeoutError, FritzProtocolError

MAC_REGEX = re.compile(r"^[0-9A-Fa-f]{2}(:[0-9A-Fa-f]{2}){5}$")


class AdminClient:
    """Handles administrative operations on FRITZ!Box (host deletion, device management)."""

    def __init__(self, fc: Any) -> None:
        self.fc = fc

    def delete_host(self, mac_address: str) -> bool:
        """Delete a host entry by MAC address from FRITZ!Box.

        Args:
            mac_address: MAC address in XX:XX:XX:XX:XX:XX format.

        Returns:
            bool: True if deletion succeeded.

        Raises:
            ValueError: If MAC address format is invalid.
            FritzConnectionError: On network or SOAP communication errors.
        """
        mac_clean = mac_address.upper().strip()
        if not MAC_REGEX.match(mac_clean):
            raise ValueError(f"Invalid MAC address format: '{mac_address}'")

        try:
            self.fc.call_action("Hosts1", "X_AVM-DE_DeleteHostEntry", NewMACAddress=mac_clean)
            return True
        except TimeoutError as exc:
            raise FritzTimeoutError(f"Timeout deleting host {mac_clean}: {exc}") from exc
        except Exception as exc:
            err_str = str(exc).lower()
            if "nosuchnode" in err_str or "invalid" in err_str:
                raise FritzProtocolError(
                    f"Host {mac_clean} not found or deletion rejected: {exc}"
                ) from exc
            raise FritzConnectionError(f"Failed to delete host {mac_clean}: {exc}") from exc
