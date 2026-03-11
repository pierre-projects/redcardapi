#!/usr/bin/env python3
"""
Validate app font configuration against Google Fonts support metadata.

Inputs:
  - dev/noto_font_language_support.json
  - data/Translations_with_sources.json (default scope)

Statuses:
  - PASS_PRIMARY: first configured font candidate supports script
  - PASS_FALLBACK: first candidate does not, but a later candidate does
  - FAIL_NO_SUPPORT: no configured candidate provides script support

Outputs:
  - Console summary
  - dev/font_support_audit.json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.fonts.font_config import FONT_FAMILIES, SCRIPT_TO_FONTS
from app.fonts.script_detector import LANGUAGE_TO_SCRIPT, Script


SUPPORT_JSON = ROOT / "dev" / "noto_font_language_support.json"
AUDIT_JSON = ROOT / "dev" / "font_support_audit.json"
TRANSLATIONS_JSON = ROOT / "data" / "Translations_with_sources.json"
FONTS_DIR = ROOT / "assets" / "fonts"


SCRIPT_TO_BCP47 = {
    Script.LATIN: "Latn",
    Script.CYRILLIC: "Cyrl",
    Script.ARABIC: "Arab",
    Script.HEBREW: "Hebr",
    Script.CJK_SIMPLIFIED: "Hans",
    Script.CJK_TRADITIONAL: "Hant",
    Script.JAPANESE: "Jpan",
    Script.KOREAN: "Kore",
    Script.DEVANAGARI: "Deva",
    Script.BENGALI: "Beng",
    Script.TAMIL: "Taml",
    Script.GURMUKHI: "Guru",
    Script.THAI: "Thai",
    Script.LAO: "Laoo",
    Script.KHMER: "Khmr",
    Script.MYANMAR: "Mymr",
    Script.ETHIOPIC: "Ethi",
    Script.ARMENIAN: "Armn",
    Script.GEORGIAN: "Geor",
    Script.VIETNAMESE: "Latn",
    Script.GREEK: "Grek",
    Script.MONGOLIAN: "Cyrl",
}


@dataclass
class FontSupport:
    font: str
    local_family_id: str
    primary_script: str
    language_tags: Set[str]
    scripts_from_tags: Set[str]


def load_support() -> Dict[str, FontSupport]:
    raw = json.loads(SUPPORT_JSON.read_text(encoding="utf-8"))
    out: Dict[str, FontSupport] = {}
    for item in raw.get("fonts", []):
        local_id = item.get("local_family_id")
        if not local_id:
            continue
        tags = {entry.get("tag", "") for entry in item.get("languages", []) if entry.get("tag")}
        scripts = {
            tag.split("_", 1)[1]
            for tag in tags
            if "_" in tag and len(tag.split("_", 1)[1]) == 4
        }
        out[local_id] = FontSupport(
            font=item.get("font", local_id),
            local_family_id=local_id,
            primary_script=item.get("primary_script", ""),
            language_tags=tags,
            scripts_from_tags=scripts,
        )
    return out


def base_lang(code: str) -> str:
    return (code or "").replace("_", "-").split("-", 1)[0].lower()


def family_files_exist(family_id: str) -> bool:
    family = FONT_FAMILIES.get(family_id)
    if not family:
        return False
    return (FONTS_DIR / family.regular_file).exists() and (FONTS_DIR / family.bold_file).exists()


def supports_script(meta: FontSupport, expected_script: str) -> bool:
    return expected_script in {meta.primary_script, *meta.scripts_from_tags}


def get_active_language_codes(use_all_mapped: bool) -> Tuple[List[str], List[str]]:
    if use_all_mapped:
        return sorted(LANGUAGE_TO_SCRIPT.keys()), []

    if not TRANSLATIONS_JSON.exists():
        raise FileNotFoundError(f"Translations file not found: {TRANSLATIONS_JSON}")

    raw = json.loads(TRANSLATIONS_JSON.read_text(encoding="utf-8"))
    langs = raw.get("languages")

    codes: List[str] = []
    if isinstance(langs, dict):
        codes = sorted(str(k) for k in langs.keys())
    elif isinstance(langs, list):
        codes = sorted(str(item.get("code")) for item in langs if isinstance(item, dict) and item.get("code"))
    else:
        raise ValueError("Unexpected translations JSON structure for 'languages'")

    unmapped = sorted([code for code in codes if code not in LANGUAGE_TO_SCRIPT])
    mapped = sorted([code for code in codes if code in LANGUAGE_TO_SCRIPT])
    return mapped, unmapped


def evaluate_language_support(
    code: str,
    script: Script,
    candidates: List[str],
    support: Dict[str, FontSupport],
) -> dict:
    expected_script = SCRIPT_TO_BCP47.get(script, "")
    lang = base_lang(code)

    candidate_checks: List[dict] = []
    for idx, family_id in enumerate(candidates):
        meta = support.get(family_id)
        files_ok = family_files_exist(family_id)
        has_meta = meta is not None

        if not has_meta or not files_ok:
            candidate_checks.append(
                {
                    "font": family_id,
                    "has_metadata": has_meta,
                    "files_present": files_ok,
                    "script_supported": False,
                    "exact_language_tag": False,
                }
            )
            continue

        script_ok = supports_script(meta, expected_script)
        exact = any(tag.lower().startswith(f"{lang}_") for tag in meta.language_tags)
        candidate_checks.append(
            {
                "font": family_id,
                "has_metadata": has_meta,
                "files_present": files_ok,
                "script_supported": script_ok,
                "exact_language_tag": exact,
            }
        )

        if script_ok:
            status = "PASS_PRIMARY" if idx == 0 else "PASS_FALLBACK"
            reason = "primary_font_supports_script" if idx == 0 else "fallback_font_supports_script"
            return {
                "code": code,
                "script": script.name,
                "status": status,
                "reason": reason,
                "selected_font": family_id,
                "exact_language_tag": exact,
                "expected_script": expected_script,
                "candidate_checks": candidate_checks,
            }

    return {
        "code": code,
        "script": script.name,
        "status": "FAIL_NO_SUPPORT",
        "reason": "no_candidate_supports_script",
        "selected_font": None,
        "exact_language_tag": False,
        "expected_script": expected_script,
        "candidate_checks": candidate_checks,
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audit app font support using Google metadata JSON")
    parser.add_argument(
        "--all-mapped",
        action="store_true",
        help="Audit all language codes in script_detector mapping (not just active translations file).",
    )
    return parser


def main() -> int:
    args = build_arg_parser().parse_args()

    if not SUPPORT_JSON.exists():
        print(f"Missing support file: {SUPPORT_JSON}")
        print("Generate it first (noto_font_language_support.json).")
        return 1

    support = load_support()
    active_codes, unmapped_codes = get_active_language_codes(args.all_mapped)

    family_issues: List[str] = []
    script_issues: List[str] = []

    for family_id in sorted(FONT_FAMILIES.keys()):
        if family_id not in support:
            family_issues.append(f"Missing Google metadata entry for family: {family_id}")
        if not family_files_exist(family_id):
            family_issues.append(f"Missing local font files for family: {family_id}")

    # Script-level chain check: any candidate should support expected script.
    for script in Script:
        candidates = SCRIPT_TO_FONTS.get(script, [])
        if not candidates:
            script_issues.append(f"No configured font candidates for script: {script.name}")
            continue

        expected_script = SCRIPT_TO_BCP47.get(script, "")
        if not expected_script:
            script_issues.append(f"{script.name}: no expected BCP47 script mapping")
            continue

        found = False
        for family_id in candidates:
            meta = support.get(family_id)
            if not meta or not family_files_exist(family_id):
                continue
            if supports_script(meta, expected_script):
                found = True
                break

        if not found:
            script_issues.append(
                f"{script.name}: no configured candidate provides expected script {expected_script}"
            )

    language_results: List[dict] = []
    for code in active_codes:
        script = LANGUAGE_TO_SCRIPT.get(code)
        if script is None:
            continue
        candidates = SCRIPT_TO_FONTS.get(script, [])
        if not candidates:
            language_results.append(
                {
                    "code": code,
                    "script": script.name,
                    "status": "FAIL_NO_SUPPORT",
                    "reason": "no_candidates",
                    "selected_font": None,
                    "exact_language_tag": False,
                    "expected_script": SCRIPT_TO_BCP47.get(script, ""),
                    "candidate_checks": [],
                }
            )
            continue
        language_results.append(evaluate_language_support(code, script, candidates, support))

    pass_primary = [r for r in language_results if r["status"] == "PASS_PRIMARY"]
    pass_fallback = [r for r in language_results if r["status"] == "PASS_FALLBACK"]
    fail_no_support = [r for r in language_results if r["status"] == "FAIL_NO_SUPPORT"]
    exact_matches = [r for r in language_results if r["exact_language_tag"]]

    report = {
        "source_file": str(SUPPORT_JSON),
        "scope": "all_mapped" if args.all_mapped else "active_translations",
        "translations_file": str(TRANSLATIONS_JSON),
        "summary": {
            "families_in_config": len(FONT_FAMILIES),
            "languages_evaluated": len(language_results),
            "unmapped_translation_languages": len(unmapped_codes),
            "family_issues": len(family_issues),
            "script_issues": len(script_issues),
            "pass_primary": len(pass_primary),
            "pass_fallback": len(pass_fallback),
            "fail_no_support": len(fail_no_support),
            "exact_language_tag_matches": len(exact_matches),
        },
        "family_issues": family_issues,
        "script_issues": script_issues,
        "unmapped_translation_languages": unmapped_codes,
        "language_results": language_results,
    }

    AUDIT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print("=" * 72)
    print("Font Support Audit")
    print("=" * 72)
    print(f"Scope: {report['scope']}")
    print(f"Languages evaluated: {report['summary']['languages_evaluated']}")
    print(f"Family issues: {report['summary']['family_issues']}")
    print(f"Script issues: {report['summary']['script_issues']}")
    print(f"PASS_PRIMARY: {report['summary']['pass_primary']}")
    print(f"PASS_FALLBACK: {report['summary']['pass_fallback']}")
    print(f"FAIL_NO_SUPPORT: {report['summary']['fail_no_support']}")
    print(f"Exact language-tag matches: {report['summary']['exact_language_tag_matches']}")
    if unmapped_codes:
        print(f"Unmapped translation languages: {len(unmapped_codes)}")
    print(f"Report: {AUDIT_JSON}")
    print("=" * 72)

    if fail_no_support:
        print("Top FAIL_NO_SUPPORT:")
        for issue in fail_no_support[:10]:
            print(f"  - {issue['code']} ({issue['script']}): {issue['reason']}")

    if pass_fallback:
        print("Top PASS_FALLBACK:")
        for issue in pass_fallback[:10]:
            print(f"  - {issue['code']} ({issue['script']}): using {issue['selected_font']}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

