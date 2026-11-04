from urllib.parse import quote_plus

from prism.config.settings import Settings


def test_database_url_generation() -> None:
    s = Settings(
        db_host="localhost",
        db_port=3306,
        db_user="prism_user",
        db_password="secret_password",
        db_name="prism_prod",
    )
    expected = "mysql+pymysql://prism_user:secret_password@localhost:3306/prism_prod?charset=utf8mb4"
    assert s.database_url == expected


def test_test_database_url_generation() -> None:
    s = Settings(
        test_db_host="127.0.0.1",
        test_db_port=3307,
        test_db_user="test_runner",
        test_db_password="test_secret",
        test_db_name="prism_test_suite",
    )
    expected = "mysql+pymysql://test_runner:test_secret@127.0.0.1:3307/prism_test_suite?charset=utf8mb4"
    assert s.test_database_url == expected


def test_password_url_escaping() -> None:
    complex_password = "p@ssword#with$special%chars&and=slash/test"
    s = Settings(
        db_host="mysql.internal",
        db_port=3306,
        db_user="app_user",
        db_password=complex_password,
        db_name="app_db",
    )
    escaped = quote_plus(complex_password)
    assert escaped in s.database_url
    assert "@" not in s.database_url.split("app_user:")[1].split("@mysql.internal")[0]


def test_pool_configuration_defaults() -> None:
    s = Settings()
    assert s.db_pool_size == 10
    assert s.db_max_overflow == 20
    assert s.db_pool_recycle == 1800
    assert s.db_echo is False
