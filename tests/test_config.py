from src.config import get_settings

def test_settings_loads():
    settings = get_settings()
    assert settings.app_name == "GermanDocAI"


def test_settings_default():
    settings = get_settings()
    assert settings.opensearch_port == 9200
    assert settings.postgres_port == 5432
    assert settings.opensearch_index == "german-docs"


def test_settings_environment():
    settings = get_settings()
    assert settings.environment in ["development", "Development","production","staging"]


def test_debug_is_bool():
    settings = get_settings()
    assert isinstance(settings.debug, bool)


def test_opensearch_port_is_int():
    settings = get_settings()
    assert isinstance(settings.opensearch_port, int)
