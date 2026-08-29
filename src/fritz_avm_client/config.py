"""Configuration management for Fritz!Box client."""
import os
from functools import cached_property
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

from .exceptions import FritzConfigurationError


class Settings(BaseSettings):
    """Settings for Fritz!Box connection and authentication.

    Attributes:
        fritz_host: Fritz!Box IP address or hostname
        fritz_port: TR-064 port (default: 49000)
        fritz_username: Username for authentication
        fritz_password: Password string for authentication
        fritz_password_file: Path to a file containing the password
        fritz_use_tls: Use TLS for TR-064 connection (default: False)
        fritz_timeout: Connection and read timeout in seconds (default: 5.0)
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        env_prefix="",
        extra="ignore"
    )

    fritz_host: str = Field(default="192.168.178.1")
    fritz_port: int = Field(default=49000)
    fritz_username: Optional[str] = Field(default=None)
    fritz_password: Optional[str] = Field(default=None)
    fritz_password_file: Optional[str] = Field(default=None)
    fritz_use_tls: bool = Field(default=False)
    fritz_timeout: float = Field(default=5.0)

    @property
    def resolved_password(self) -> Optional[str]:
        """Resolve password prioritizing FRITZ_PASSWORD_FILE over FRITZ_PASSWORD."""
        if self.fritz_password_file:
            path = self.fritz_password_file.strip()
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        return f.read().strip()
                except Exception as exc:
                    raise FritzConfigurationError(f"Failed to read password from file '{path}': {exc}") from exc
            else:
                raise FritzConfigurationError(f"Password file '{path}' does not exist")
        return self.fritz_password

    @cached_property
    def fritz_base_url(self) -> str:
        """Get base URL for Fritz!Box connection."""
        protocol = "https" if self.fritz_use_tls else "http"
        return f"{protocol}://{self.fritz_host}:{self.fritz_port}"

    def __repr__(self) -> str:
        """String representation with password scrubbed."""
        return (
            f"Settings(fritz_host={self.fritz_host!r}, fritz_port={self.fritz_port!r}, "
            f"fritz_username={self.fritz_username!r}, fritz_password='***', "
            f"fritz_password_file={self.fritz_password_file!r}, fritz_use_tls={self.fritz_use_tls!r}, "
            f"fritz_timeout={self.fritz_timeout!r})"
        )
