"""Test script to verify actual font coverage for all languages.

This script attempts to render a PDF for each language and reports:
- Which languages render successfully
- Which languages fail despite being marked as "supported"
- Detailed error messages for failures
"""

import sys
import io
from pathlib import Path

# Force UTF-8 encoding for Windows console
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.translations_store import TranslationsStore
from app.fonts import get_font_manager
from app.fonts.script_detector import detect_script
from app.pdf_renderer import render_print_sheet_pdf
from app.layout import CardLayout
from app.back_content import get_back_content
from app.config import TRANSLATIONS_JSON_PATH


def test_language_rendering(lang_item: dict) -> tuple[bool, str]:
    """
    Test if a language can actually render to PDF.

    Returns:
        (success, message) tuple
    """
    code = lang_item["code"]

    try:
        # Create a simple layout (4 cards per page)
        layout = CardLayout.from_cards_per_page(
            count=4,
            page_size="letter",
            margin_inches=0.5,
            gutter_inches=0.25,
            footer_height_inches=0.55,
        )

        # Attempt to render
        pdf_bytes = render_print_sheet_pdf(
            payload={
                "code": lang_item["code"],
                "name": lang_item["name"],
                "rtl": lang_item["rtl"],
                "official": True,
                "front": lang_item.get("front", {}),
                "back": get_back_content(lang_item["code"]),
            },
            layout=layout,
        )

        # Check if we got actual PDF data
        if pdf_bytes and len(pdf_bytes) > 1000:  # Valid PDFs are at least a few KB
            return True, "✓ Rendered successfully"
        else:
            return False, "✗ PDF too small (likely invalid)"

    except Exception as e:
        error_type = type(e).__name__
        return False, f"✗ {error_type}: {str(e)[:80]}"


def main():
    print("=" * 80)
    print("Font Coverage Test - Rendering All Languages")
    print("=" * 80)
    print()

    # Load translations
    print(f"Loading translations from {TRANSLATIONS_JSON_PATH}...")
    store = TranslationsStore(TRANSLATIONS_JSON_PATH)
    store.load()
    languages = store.list_languages()
    print(f"Loaded {len(languages)} languages\n")

    # Get font manager
    font_manager = get_font_manager()

    # Test each language
    results = {
        "success": [],
        "failed_supported": [],  # Marked as supported but failed to render
        "failed_unsupported": [],  # Expected to fail
    }

    print("Testing languages...")
    print("-" * 80)

    for lang in sorted(languages, key=lambda x: x["code"]):
        code = lang["code"]
        name = lang["name"]
        script = detect_script(code)
        font_supported = font_manager.is_script_supported(script)

        # Test rendering
        success, message = test_language_rendering(lang)

        # Categorize result
        status_icon = "✓" if success else "✗"
        font_icon = "🔤" if font_supported else "⚠️ "

        print(f"{status_icon} {font_icon} {code:8} {name:30} {message}")

        if success:
            results["success"].append((code, name, script.name))
        elif font_supported:
            results["failed_supported"].append((code, name, script.name, message))
        else:
            results["failed_unsupported"].append((code, name, script.name, message))

    # Print summary
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print()

    print(f"✓ Successfully rendered: {len(results['success'])} languages")
    print(f"✗ Failed (marked as supported): {len(results['failed_supported'])} languages")
    print(f"⚠  Failed (known unsupported): {len(results['failed_unsupported'])} languages")
    print()

    # Detail failed "supported" languages - these are the problematic ones
    if results["failed_supported"]:
        print("⚠️  ATTENTION: Languages marked as SUPPORTED but FAILED to render:")
        print("-" * 80)
        for code, name, script, message in results["failed_supported"]:
            print(f"  {code:8} - {name:30} (Script: {script})")
            print(f"           {message}")
        print()
        print("These languages may have:")
        print("  - Missing font files")
        print("  - Incomplete character coverage in installed fonts")
        print("  - Special rendering requirements not met")
        print()

    # Show expected failures
    if results["failed_unsupported"]:
        print("Expected failures (fonts not installed):")
        print("-" * 80)
        for code, name, script, _ in results["failed_unsupported"]:
            print(f"  {code:8} - {name:30} (Script: {script})")
        print()

    # Exit code based on results
    if results["failed_supported"]:
        print("❌ TEST FAILED: Some 'supported' languages cannot render!")
        sys.exit(1)
    else:
        print("✅ TEST PASSED: All supported languages render correctly!")
        sys.exit(0)


if __name__ == "__main__":
    main()
