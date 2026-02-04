# backend/app/dev_diagnose_pages.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.layout import CardLayout, get_default_layout
from app.pdf_renderer import _draw_front, _draw_back, _register_fonts


def _project_root() -> Path:
    """
    backend/app/dev_diagnose_pages.py
    parents[0] = app/
    parents[1] = backend/
    parents[2] = project root/
    """
    return Path(__file__).resolve().parents[2]


def load_translations(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def safe_front_payload(lang_data: Dict[str, Any]) -> Dict[str, Any]:
    front = lang_data.get("front") or {}
    header = front.get("header") or front.get("title") or ""

    raw_bullets = front.get("bullets") or front.get("points") or []
    bullets: list[str] = []
    for b in raw_bullets:
        if isinstance(b, dict):
            t = b.get("text") or ""
            if t:
                bullets.append(str(t))
        elif isinstance(b, str) and b.strip():
            bullets.append(b)

    return {"header": header, "bullets": bullets}


def safe_back_payload(lang_data: Dict[str, Any]) -> Dict[str, Any]:
    back = lang_data.get("back") or {}
    header = back.get("header") or back.get("title") or ""

    raw_bullets = back.get("bullets") or back.get("points") or []
    bullets: list[str] = []
    for b in raw_bullets:
        if isinstance(b, dict):
            t = b.get("text") or ""
            if t:
                bullets.append(str(t))
        elif isinstance(b, str) and b.strip():
            bullets.append(b)

    return {"header": header, "bullets": bullets}



def main():
    project_root = _project_root()
    backend_dir = project_root / "backend"
    translations_json = project_root / "Translations.json"

    out_path = backend_dir / "diagnostic_languages.pdf"

    data = load_translations(translations_json)

    # Ensure fonts are registered (your module also registers on import, but this is explicit)
    _register_fonts()

    # Use your normal layout sizing/scaling logic
    layout: CardLayout = get_default_layout()

    c = canvas.Canvas(str(out_path), pagesize=letter)
    page_w, page_h = letter

    # We'll draw one card centered per page, using the same card size your real print sheet uses
    card_w = layout.card_width
    card_h = layout.card_height
    x = (page_w - card_w) / 2
    y = (page_h - card_h) / 2

    data = load_translations(translations_json)
    languages = data.get("languages", {})

    for lang_code in sorted(languages.keys()):
        lang_data = languages.get(lang_code) or {}

        RTL_FALLBACK = {"ar", "he", "fa", "ur", "ps", "dv", "ku", "yi"}

        rtl = bool(lang_data.get("rtl")) or (lang_code in RTL_FALLBACK)

        # ---- FRONT ----
        c.setFont("Helvetica", 11)
        c.drawString(36, page_h - 36, f"FRONT  lang={lang_code}   rtl={rtl}")
        front = safe_front_payload(lang_data)
        _draw_front(c, x, y, card_w, card_h, front, layout, rtl=rtl)
        c.showPage()

        # ---- BACK ----
        c.setFont("Helvetica", 11)
        c.drawString(36, page_h - 36, f"BACK   lang={lang_code}   rtl(stored)={rtl}")
        back = safe_back_payload(lang_data)

        # For diagnostics, draw back with rtl=rtl to catch bidi/double-reversal issues too.
        _draw_back(c, x, y, card_w, card_h, back, layout, rtl=rtl)
        c.showPage()

    c.save()
    print(f"OK: wrote {out_path.resolve()}")


if __name__ == "__main__":
    main()
