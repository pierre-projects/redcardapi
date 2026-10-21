import pytest

from app.api import routes
from app.main import check_production_settings
from tests.conftest import make_settings


def test_health_and_ready(client):
    assert client.get("/api/health").json() == {"ok": True, "languages_loaded": 56}
    ready = client.get("/api/ready")
    assert ready.status_code == 200
    assert ready.json()["fonts_loaded"] is True


def test_config_lists_layouts(client):
    body = client.get("/api/config").json()
    assert body["valid_layouts"] == [4, 6, 8, 12]
    assert body["fold_layouts"] == [4, 5, 6]
    assert body["render_modes"] == ["grid", "fold"]


def test_languages_include_native_names_and_font_support(client):
    response = client.get("/api/languages")
    assert response.headers["cache-control"].startswith("public, max-age=")
    languages = {lang["code"]: lang for lang in response.json()}
    assert len(languages) == 56
    assert languages["es"]["native"] == "Español"
    assert languages["ar"]["rtl"] is True
    assert languages["zh-cn"]["name"] == "Chinese (Simplified)"
    assert all(lang["fontSupported"] for lang in languages.values())


def test_card_lookup_is_case_insensitive(client):
    body = client.get("/api/card/ZH-cn").json()
    assert body["code"] == "zh-cn"
    assert body["native"] == "中文（简体）"
    assert body["front"]["bullets"][0]["id"] == "bullet_1"


def test_unknown_language_is_404_with_code(client):
    response = client.get("/api/card/xx")
    assert response.status_code == 404
    assert response.json() == {"detail": "Language not found: xx", "code": "language_not_found"}


@pytest.mark.parametrize("mode,count,suffix", [
    ("grid", 4, "4up.pdf"),
    ("grid", 12, "12up.pdf"),
    ("fold", 5, "5up-fold.pdf"),
])
def test_render_pdf(client, mode, count, suffix):
    response = client.get("/api/render/es", params={"mode": mode, "cards_per_page": count})
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.headers["content-disposition"].endswith(f'-spanish-{suffix}"')
    assert response.headers["cache-control"].startswith("public, max-age=")
    assert response.content.startswith(b"%PDF")


def test_render_filename_keeps_display_code(client):
    response = client.get("/api/render/zh-cn")
    assert 'know-your-rights-zh-CN-chinese-simplified-4up.pdf' in response.headers["content-disposition"]


@pytest.mark.parametrize("params", [
    {"mode": "poster"},
    {"mode": "legacy"},
    {"cards_per_page": 5},
    {"mode": "fold", "cards_per_page": 8},
])
def test_invalid_render_options_are_rejected(client, params):
    response = client.get("/api/render/es", params=params)
    assert response.status_code == 422
    assert response.json()["code"] == "invalid_request"


def test_cached_pdf_is_reused_and_not_rate_limited(client_factory):
    client = client_factory(pdf_cache_size=8, render_rate_limit_per_minute=1)
    first = client.get("/api/render/fr")
    second = client.get("/api/render/fr")
    assert first.status_code == second.status_code == 200
    assert first.content == second.content


def test_rate_limit(client_factory):
    client = client_factory(render_rate_limit_per_minute=2)
    statuses = [client.get(f"/api/render/{code}").status_code for code in ("fr", "de", "pt", "vi")]
    # "de" is not a card language, so it 404s before counting against the limit.
    assert statuses == [200, 404, 200, 429]
    limited = client.get("/api/render/ru")
    assert limited.json()["code"] == "rate_limited"
    assert 1 <= int(limited.headers["retry-after"]) <= 60


def test_render_failure_does_not_leak_internals(client, monkeypatch):
    def broken(*args, **kwargs):
        raise ValueError("secret internal detail")

    monkeypatch.setattr(routes, "render_pdf", broken)
    response = client.get("/api/render/es")
    assert response.status_code == 500
    assert response.json() == {"detail": "PDF generation failed.", "code": "render_failed"}


def test_production_requires_real_cors_origins():
    with pytest.raises(RuntimeError, match="only allows localhost"):
        check_production_settings(make_settings(environment="production"))
    with pytest.raises(RuntimeError, match="not '\\*'"):
        check_production_settings(make_settings(environment="production", cors_origins=["*"]))
    check_production_settings(make_settings(environment="production",
                                            cors_origins=["https://cards.example.org"]))
