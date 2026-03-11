#!/usr/bin/env python3
"""
Test PDF Generation for All Languages.

Generates PDFs for every language in Translations.json and merges them
into a single PDF for easy review. Supports both legacy and fold modes.

Usage:
    python dev/test_all_languages.py
    python dev/test_all_languages.py --cards 6
    python dev/test_all_languages.py --mode fold --cards 4
    python dev/test_all_languages.py --mode fold --output fold_test.pdf
"""

import sys
from pathlib import Path
from io import BytesIO
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.translations_store import TranslationsStore
from app.pdf_renderer import render_print_sheet_pdf, render_fold_sheet_pdf
from app.layout import CardLayout
from app.back_content import get_back_content
from app.config import settings

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


def generate_all_pdfs(cards_per_page: int = 6, mode: str = "legacy") -> list:
    """
    Generate PDFs for all languages.

    Args:
        cards_per_page: Legacy: 4,6,8,12.  Fold: 4,5,6 (rows).
        mode: "legacy" (2-page front/back) or "fold" (single-page side-by-side).

    Returns:
        List of tuples: (language code, display name, stamped page)
    """
    json_path = settings.translations_json_path
    store = TranslationsStore(json_path)
    store.load()

    languages = store.list_languages()
    print(f"Found {len(languages)} languages")
    print(f"Using translations file: {json_path}")

    if mode == "fold":
        layout = CardLayout.from_fold_rows(rows=cards_per_page)
        print(f"Using FOLD layout: {cards_per_page} rows (front|back per row)")
    else:
        layout = CardLayout.from_cards_per_page(cards_per_page)
        print(f"Using LEGACY layout: {cards_per_page} cards/page")

    results = []
    failed = []

    for i, lang in enumerate(languages, 1):
        code = lang.get("code", "unknown")
        name = lang.get("name", code)

        try:
            lang_data = store.get_language(code)
            if not lang_data:
                print(f"  [{i}/{len(languages)}] {code}: No data found")
                failed.append((code, "No data"))
                continue

            payload = {
                "code": code,
                "name": name,
                "front": lang_data.get("front", {}),
                "back": get_back_content(code),
                "rtl": lang_data.get("rtl", False),
                "source": lang_data.get("source"),
            }

            if mode == "fold":
                pdf_bytes = render_fold_sheet_pdf(payload, layout)
            else:
                pdf_bytes = render_print_sheet_pdf(payload, layout)

            reader = PdfReader(BytesIO(pdf_bytes))
            page = reader.pages[0]
            overlay_bytes = _create_label_overlay(
                float(page.mediabox.width),
                float(page.mediabox.height),
                f"{code} ({name}) [{mode}]",
            )
            overlay_page = PdfReader(BytesIO(overlay_bytes)).pages[0]
            page.merge_page(overlay_page)

            results.append((code, name, page))

            print(f"  [{i}/{len(languages)}] {code} ({name}): OK ({len(pdf_bytes):,} bytes)")

        except Exception as e:
            print(f"  [{i}/{len(languages)}] {code} ({name}): FAILED - {e}")
            failed.append((code, str(e)))

    print(f"\nGenerated: {len(results)} pages ({mode} mode)")
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
    parser.add_argument("--cards", type=int, default=12, choices=[4, 5, 6, 8, 12],
                        help="Cards/rows per page (default: 12). Fold mode accepts 4,5,6.")
    parser.add_argument("--mode", type=str, default="legacy", choices=["legacy", "fold"],
                        help="Render mode: legacy (2-page) or fold (single-page side-by-side)")
    parser.add_argument("--output", type=str, default=None,
                        help="Output filename (default: all_languages_MODE_TIMESTAMP.pdf)")
    args = parser.parse_args()

    if args.mode == "fold" and args.cards not in (4, 5, 6):
        print(f"Fold mode only supports 4, 5, or 6 rows. Got {args.cards}, defaulting to 4.")
        args.cards = 4

    print("=" * 60)
    print(f"PDF Generation Test - All Languages ({args.mode.upper()} mode)")
    print("=" * 60)
    print()

    pages = generate_all_pdfs(cards_per_page=args.cards, mode=args.mode)

    if not pages:
        print("No pages generated!")
        return 1

    if args.output:
        output_path = Path(args.output)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(__file__).parent / f"all_languages_{args.mode}_{timestamp}.pdf"

    merge_pdfs(pages, output_path)

    print()
    print("=" * 60)
    print(f"Mode: {args.mode}")
    print(f"Total languages: {len(pages)}")
    print(f"Cards/rows per page: {args.cards}")
    print(f"Output: {output_path}")
    print(f"File size: {output_path.stat().st_size:,} bytes")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
