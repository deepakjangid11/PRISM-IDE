
from prism.config.settings import Settings


def test_settings_default_values() -> None:
    settings = Settings()

    assert settings.app_name == "PRISM IDE"
    assert settings.environment == "development"
    assert settings.debug is True


def test_settings_custom_values() -> None:
    settings = Settings(
        app_name="PRISM Test",
        environment="testing",
        debug=False,
    )

    assert settings.app_name == "PRISM Test"
    assert settings.environment == "testing"
    assert settings.debug is False
