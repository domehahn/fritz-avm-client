"""Unit tests for exception hierarchy."""
import pytest
from fritz_avm_client.exceptions import (
    FritzError,
    FritzConfigurationError,
    FritzConnectionError,
    FritzTimeoutError,
    FritzAuthenticationError,
    FritzProtocolError,
    FritzServiceUnavailableError,
    FritzUnsupportedFeatureError,
)


def test_exception_inheritance():
    """Verify exception inheritance tree."""
    assert issubclass(FritzConfigurationError, FritzError)
    assert issubclass(FritzConnectionError, FritzError)
    assert issubclass(FritzTimeoutError, FritzConnectionError)
    assert issubclass(FritzAuthenticationError, FritzError)
    assert issubclass(FritzProtocolError, FritzError)
    assert issubclass(FritzServiceUnavailableError, FritzError)
    assert issubclass(FritzUnsupportedFeatureError, FritzError)


def test_exception_raising():
    """Verify raising and catching base FritzError."""
    with pytest.raises(FritzError):
        raise FritzTimeoutError("Connection timed out")

