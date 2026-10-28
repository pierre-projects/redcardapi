import json

import pytest

from app.data import DatasetError, TranslationStore


def test_loads_every_language(store):
    assert len(store.languages()) == 59
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


MACHINE_SOURCE = {"type": "machine", "engine": "Google Translate", "translated_on": "2026-10-28",
                  "translated_from": "English, ILRC card text"}


def test_machine_translation_loads_with_provenance(tmp_path):
    store = TranslationStore.load(_write(tmp_path, _minimal(source=MACHINE_SOURCE)))
    source = store.get("es").source
    assert not store.get("es").official
    assert source.translated_on.isoformat() == "2026-10-28"
    assert source.machine_notice == (
        "Machine translation (Google Translate), not yet checked by a native speaker.")


@pytest.mark.parametrize("missing", ["engine", "translated_on"])
def test_machine_translation_without_provenance_fails(tmp_path, missing):
    source = {k: v for k, v in MACHINE_SOURCE.items() if k != missing}
    with pytest.raises(DatasetError, match="engine"):
        TranslationStore.load(_write(tmp_path, _minimal(source=source)))


def test_unknown_source_type_fails(tmp_path):
    with pytest.raises(DatasetError):
        TranslationStore.load(_write(tmp_path, _minimal(source={"type": "app"})))


def test_only_machine_translations_carry_a_notice(store):
    assert all(lang.source.machine_notice is None for lang in store.languages() if lang.official)
