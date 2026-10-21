import time

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.data import TranslationStore
from app.fonts import init_font_manager
from app.main import create_app


def make_settings(**overrides) -> Settings:
    defaults = dict(render_rate_limit_per_minute=0, pdf_cache_size=0, log_level="WARNING")
    return Settings(**{**defaults, **overrides})


def start(settings: Settings) -> TestClient:
    client = TestClient(create_app(settings))
    client.__enter__()
    deadline = time.monotonic() + 30
    while client.get("/api/ready").status_code != 200:
        assert time.monotonic() < deadline, "fonts did not load"
        time.sleep(0.05)
    return client


@pytest.fixture
def client_factory():
    clients = []

    def factory(**overrides) -> TestClient:
        client = start(make_settings(**overrides))
        clients.append(client)
        return client

    yield factory
    for client in clients:
        client.__exit__(None, None, None)


@pytest.fixture
def client(client_factory) -> TestClient:
    return client_factory()


@pytest.fixture(scope="session")
def store() -> TranslationStore:
    return TranslationStore.load(Settings().translations_json_path)


@pytest.fixture(scope="session")
def fonts():
    return init_font_manager(Settings().fonts_dir)
