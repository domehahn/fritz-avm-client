"""Exception hierarchy for fritz-avm-client."""


class FritzError(Exception):
    """Base exception for all Fritz!Box client errors."""
    pass


class FritzConfigurationError(FritzError):
    """Raised when client configuration is invalid or missing."""
    pass


class FritzConnectionError(FritzError):
    """Raised when a network or transport-level error occurs."""
    pass


class FritzTimeoutError(FritzConnectionError):
    """Raised when a request to Fritz!Box times out."""
    pass


class FritzAuthenticationError(FritzError):
    """Raised when Fritz!Box authentication fails or credentials are invalid."""
    pass


class FritzProtocolError(FritzError):
    """Raised when an unexpected or malformed response is received from TR-064/HTTP."""
    pass


class FritzServiceUnavailableError(FritzError):
    """Raised when TR-064 service or action is temporarily unavailable."""
    pass


class FritzUnsupportedFeatureError(FritzError):
    """Raised when a requested feature or metric is not supported by the device."""
    pass

