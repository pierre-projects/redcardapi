#!/usr/bin/env python3
"""
Test PDF Generation for All Languages.

Generates PDFs for every language in Translations.json and merges them
into a single PDF for easy review.

Usage:
    python dev/test_all_languages.py
    python dev/test_all_languages.py --cards 6
    python dev/test_all_languages.py --output my_test.pdf
"""

import sys
from pathlib import Path
from io import BytesIO
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.translations_store import TranslationsStore
from app.pdf_renderer import render_print_sheet_pdf
from app.layout import CardLayout
from app.back_content import get_back_content

# For merging/stamping PDFs
from PyPDF2 import PdfReader, PdfWriter
from reportlab.pdfgen import canvas


def _create_label_overlay(page_width: float, page_height: float, label: str) -> bytes:
    """Create a one-page PDF overlay with a language label."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=(page_width, page_height))

    # Place label in top-left margin area for easy visual scan.
    c.setFont("Helvetica-Bold", 11)
    c.drawString(24, page_height - 20, f"Language: {label}")
    c.save()
    return buf.getvalue()


def generate_all_pdfs(cards_per_page: int = 6) -> list:
    """
    Generate PDFs for all languages.

    Returns:
        List of tuples: (language code, display name, stamped front page)
    """
    # Load translations
    json_path = Path(__file__).parent.parent / "data" / "Translations.json"
    store = TranslationsStore(json_path)
    store.load()

    languages = store.list_languages()
    print(f"Found {len(languages)} languages")

    layout = CardLayout.from_cards_per_page(cards_per_page)
    print(f"Using {cards_per_page}-card layout")

    results = []
    failed = []

    for i, lang in enumerate(languages, 1):
        code = lang.get("code", "unknown")
        name = lang.get("name", code)

        try:
            # Get full language data
            lang_data = store.get_language(code)
            if not lang_data:
                print(f"  [{i}/{len(languages)}] {code}: No data found")
                failed.append((code, "No data"))
                continue

            # Build payload
            payload = {
                "code": code,
                "front": lang_data.get("front", {}),
                "back": get_back_content(code),
                "rtl": lang_data.get("rtl", False),
            }

            # Generate full PDF (front + back)
            pdf_bytes = render_print_sheet_pdf(payload, layout)

            # Keep only the front page, then stamp with language label.
            reader = PdfReader(BytesIO(pdf_bytes))
            front_page = reader.pages[0]
            overlay_bytes = _create_label_overlay(
                float(front_page.mediabox.width),
                float(front_page.mediabox.height),
                f"{code} ({name})",
            )
            overlay_page = PdfReader(BytesIO(overlay_bytes)).pages[0]
            front_page.merge_page(overlay_page)

            results.append((code, name, front_page))

            print(f"  [{i}/{len(languages)}] {code} ({name}): OK ({len(pdf_bytes):,} bytes)")

        except Exception as e:
            print(f"  [{i}/{len(languages)}] {code} ({name}): FAILED - {e}")
            failed.append((code, str(e)))

    print(f"\nGenerated: {len(results)} front pages")
    if failed:
        print(f"Failed: {len(failed)} languages")
        for code, error in failed:
            print(f"  - {code}: {error}")

    return results


def merge_pdfs(pages: list, output_path: Path) -> None:
    """
    Merge front pages into a single PDF.

    Args:
        pages: List of tuples: (language code, display name, stamped front page)
        output_path: Output file path
    """
    writer = PdfWriter()

    for _, _, page in pages:
        writer.add_page(page)

    with open(output_path, "wb") as f:
        writer.write(f)
    print(f"\nMerged PDF saved to: {output_path}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Test PDF generation for all languages")
    parser.add_argument("--cards", type=int, default=12, choices=[4, 6, 8, 12],
                        help="Cards per page (default: 12)")
    parser.add_argument("--output", type=str, default=None,
                        help="Output filename (default: all_languages_TIMESTAMP.pdf)")
    args = parser.parse_args()

    print("=" * 60)
    print("PDF Generation Test - All Languages")
    print("=" * 60)
    print()

    # Generate all PDFs
    pages = generate_all_pdfs(cards_per_page=args.cards)

    if not pages:
        print("No front pages generated!")
        return 1

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(__file__).parent / f"all_languages_{timestamp}.pdf"

    # Merge PDFs
    merge_pdfs(pages, output_path)

    # Summary
    print()
    print("=" * 60)
    print(f"Total languages: {len(pages)}")
    print(f"Cards per page: {args.cards}")
    print(f"Output: {output_path}")
    print(f"File size: {output_path.stat().st_size:,} bytes")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
