# Contributing to the Red Card API

Thank you for helping. This project produces "Know Your Rights" red cards in many languages, for people who may need them in a stressful moment. Accuracy matters more than anything else.

## Attribution (required)

The 56 translations come from the Immigrant Legal Resource Center (ILRC), who created the original red cards. Contributions that touch translation content must keep this attribution and must not misrepresent ILRC's role.

## Setup

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt   # Windows: .venv\Scripts\pip
```

Before opening a pull request:

```bash
ruff check .
python -m scripts.validate_translations
pytest
```

CI runs the same checks, plus `pip-audit` and a Docker build.

## Changing translations

All card text lives in `data/Translations_with_sources.json`. The API validates the file at startup, and refuses to start if it is malformed.

1. **Edit the language entry.** It needs `name` (English), `native` (the name in the language itself), `code`, `rtl`, `front.header`, `front.bullets[{id, text}]` and `source`.
2. **Copy the text, don't extract it.** Copy from an editable source, or retype it. Do not extract it from a PDF: extraction scrambles Arabic, Indic and Khmer text (see `scripts/known_issues.py`).
3. **Run `python -m scripts.validate_translations`.** It checks:
   - the schema;
   - that every character has a glyph in the language's font;
   - for signs of corrupted text.
4. **Map the script for a new language.** If the language uses a script other than Latin, add its code to `LANGUAGE_TO_SCRIPT` in `app/fonts/script_detector.py`. If that script is new, also add a Noto font pair (Regular + Bold) to `assets/fonts/` and to `app/fonts/font_config.py`.
5. **Look at the result.** Run `python -m scripts.render_review --mode fold <code>` and check `review.pdf`. Ideally a native speaker reviews it.
6. **Sync the frontend.** The frontend bundles the same file. Run `npm run sync:data` in `redcardapi-frontend`.

After fixing a language listed in `scripts/known_issues.py`, remove it from that list. The validator and tests point it out until you do.

## Changing rendering code

- Check Latin, right-to-left (ar, ur, he), CJK (zh-cn, ja), and shaped scripts (hi, ta, km, my) with `scripts.render_review`.
- Text that is drawn must be measured with `app.text.text_width` and drawn with `app.pdf.draw.draw_line`, so shaping and right-to-left handling stay correct.

## Style

- Ruff enforces the rules (`pyproject.toml`).
- Use type hints, and write short docstrings that explain why rather than restating the code.
- Commit messages use the imperative mood: Add, Fix, Update, Remove.
