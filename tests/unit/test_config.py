"""Unit tests for configuration and password secret resolution."""
import pytest
from fritz_avm_client import Settings
from fritz_avm_client.exceptions import FritzConfigurationError


def test_settings_defaults():
    settings = Settings()
    assert settings.fritz_host == "192.168.178.1"
    assert settings.fritz_port == 49000
    assert settings.fritz_timeout == 5.0
    assert settings.resolved_password is None


def test_settings_password_direct():
    settings = Settings(fritz_password="mysecretpassword")
    assert settings.resolved_password == "mysecretpassword"
    assert "mysecretpassword" not in repr(settings)
    assert "***" in repr(settings)


def test_settings_password_file(tmp_path):
    secret_file = tmp_path / "fritz_pass.txt"
    secret_file.write_text("file_password_123\n")

    settings = Settings(
        fritz_password="direct_password",
        fritz_password_file=str(secret_file)
    )
    # File should take priority over direct password
    assert settings.resolved_password == "file_password_123"


def test_settings_password_file_missing():
    settings = Settings(fritz_password_file="/path/does/not/exist/pass.txt")
    with pytest.raises(FritzConfigurationError):
        _ = settings.resolved_password

