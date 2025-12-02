"""Configuration for Fritz!Box client."""
from pydantic_settings import BaseSettings
from functools import cached_property
from typing import Optional


class Settings(BaseSettings):
    """Settings for Fritz!Box connection.
    
    Attributes:
        fritz_host: Fritz!Box IP address or hostname
        fritz_port: TR-064 port (default: 49000)
        fritz_username: Username for authentication
        fritz_password: Password for authentication
        fritz_use_tls: Use TLS for connection (default: False)
    
    Example:
        >>> settings = Settings(
        ...     fritz_host="192.168.178.1",
        ...     fritz_username="admin",
        ...     fritz_password="secret"
        ... )
    """
    fritz_host: str = "192.168.178.1"
    fritz_port: int = 49000
    fritz_username: Optional[str] = None
    fritz_password: Optional[str] = None
    fritz_use_tls: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = False
        env_prefix = ""

    @cached_property
    def fritz_base_url(self) -> str:
        """Get base URL for Fritz!Box."""
        protocol = "https" if self.fritz_use_tls else "http"
        return f"{protocol}://{self.fritz_host}:{self.fritz_port}"
