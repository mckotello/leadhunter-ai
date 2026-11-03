from app.config import settings


def test_cors_origins_are_explicit():
    origins = settings.cors_origins_list()
    assert origins
    assert "*" not in origins
    assert settings.cors_allow_credentials is True
