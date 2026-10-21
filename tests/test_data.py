import json

import pytest

from app.data import DatasetError, TranslationStore


def test_loads_every_language(store):
    assert len(store.languages()) == 56
    assert store.get("ZH-CN").display_code == "zh-CN"
    assert store.get("nope") is None
    assert len(store.back.paragraphs) == 5
    assert store.back.paragraphs[-1].startswith("These cards are available")


def _write(tmp_path, data) -> str:
    path = tmp_path / "translations.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _minimal(**language_overrides):
    language = {
        "name": "Spanish", "native": "Español", "code": "es", "rtl": False,
        "front": {"header": "Derechos:", "bullets": [{"id": "b1", "text": "Uno"}]},
        "source": {"type": "official", "origin": "ILRC", "verified": True},
    }
    language.update(language_overrides)
    return {
        "version": "1.0.0",
        "languages": {"es": language},
        "back": {"statements": [{"id": "s1", "text": "Statement"}], "footer": "Footer"},
    }


def test_minimal_file_loads(tmp_path):
    store = TranslationStore.load(_write(tmp_path, _minimal()))
    assert store.get("es").native == "Español"


@pytest.mark.parametrize("override", [
    {"native": ""},
    {"front": {"header": "x", "bullets": []}},
    {"code": "fr"},  # key/code mismatch
])
def test_invalid_language_fails_at_load(tmp_path, override):
    with pytest.raises(DatasetError):
        TranslationStore.load(_write(tmp_path, _minimal(**override)))


def test_missing_file(tmp_path):
    with pytest.raises(DatasetError, match="not found"):
        TranslationStore.load(tmp_path / "missing.json")
