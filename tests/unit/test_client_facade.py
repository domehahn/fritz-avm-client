"""Unit tests for FritzClient facade and retry logic."""
import pytest
from unittest.mock import MagicMock, patch

from fritz_avm_client import FritzClient, Settings
from fritz_avm_client.exceptions import FritzTimeoutError, FritzConnectionError, FritzAuthenticationError


def test_fritz_client_init_success():
    with patch("fritz_avm_client.client.FritzConnection") as mock_fc_cls:
        settings = Settings(fritz_password="password123")
        client = FritzClient(settings)
        assert client.fc is not None
        mock_fc_cls.assert_called_once_with(
            address="192.168.178.1",
            port=49000,
            user=None,
            password="password123",
            timeout=5.0,
            use_tls=False
        )


def test_fritz_client_init_auth_failure():
    with patch("fritz_avm_client.client.FritzConnection", side_effect=Exception("401 Unauthorized")):
        settings = Settings(fritz_username="admin", fritz_password="wrong")
        with pytest.raises(FritzAuthenticationError):
            FritzClient(settings)


def test_execute_with_retry():
    with patch("fritz_avm_client.client.FritzConnection"):
        client = FritzClient(Settings())

        mock_func = MagicMock()
        mock_func.side_effect = [FritzTimeoutError("Timeout 1"), "success"]

        result = client._execute_with_retry(mock_func, max_retries=2, initial_backoff=0.01)
        assert result == "success"
        assert mock_func.call_count == 2


def test_execute_with_retry_exhausted():
    with patch("fritz_avm_client.client.FritzConnection"):
        client = FritzClient(Settings())

        mock_func = MagicMock()
        mock_func.side_effect = FritzTimeoutError("Persistent timeout")

        with pytest.raises(FritzTimeoutError):
            client._execute_with_retry(mock_func, max_retries=1, initial_backoff=0.01)
        assert mock_func.call_count == 2

