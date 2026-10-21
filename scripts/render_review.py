"""Render one review PDF with a sheet for every language, for visual checks.

Usage: python -m scripts.render_review [--mode grid|fold] [--count N] [--out review.pdf] [codes...]
"""

import argparse
import io
from pathlib import Path

from pypdf import PdfReader, PdfWriter

from app.config import settings
from app.data import TranslationStore
from app.fonts import init_font_manager
from app.layout import FOLD_ROWS, GRID_LAYOUTS, CardLayout
from app.pdf import render_pdf


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["grid", "fold"], default="fold")
    parser.add_argument("--count", type=int, default=4, choices=sorted(set(GRID_LAYOUTS) | set(FOLD_ROWS)))
    parser.add_argument("--out", type=Path, default=Path("review.pdf"))
    parser.add_argument("codes", nargs="*", help="language codes (default: all)")
    args = parser.parse_args()

    store = TranslationStore.load(settings.translations_json_path)
    fonts = init_font_manager(settings.fonts_dir)
    make_layout = CardLayout.fold if args.mode == "fold" else CardLayout.grid
    layout = make_layout(args.count, page_size=settings.page_size)
    languages = [store.get(c) for c in args.codes] if args.codes else store.languages()

    writer = PdfWriter()
    for language in languages:
        if language is None:
            continue
        for page in PdfReader(io.BytesIO(render_pdf(language, store.back, layout, fonts))).pages:
            writer.add_page(page)
    with args.out.open("wb") as handle:
        writer.write(handle)
    print(f"Wrote {len(languages)} languages to {args.out}")


if __name__ == "__main__":
    main()
