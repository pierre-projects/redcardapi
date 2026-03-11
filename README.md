# RedCardGenerator Backend

A FastAPI backend for generating multi-language "Know Your Rights" PDF cards with support for 56 languages and 22 Unicode scripts.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [API Endpoints](#api-endpoints)
- [Font System](#font-system)
- [Adding New Languages](#adding-new-languages)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [Known Issues / In Progress](#known-issues--in-progress)

## Overview

This backend generates printable PDF cards that display constitutional rights information. The front of each card is translated into the user's language, while the back contains English text explaining 4th and 5th Amendment rights.

Card intent (applies to all render modes):

```
+--------------------+--------------------+
|       FRONT        |        BACK        |
|   (Translated)     |      (English)     |
|  Know Your Rights  |  4th/5th Amendment |
+--------------------+--------------------+
```

Legacy and fold modes only change how these front/back sides are arranged on a printable sheet.

Two render modes are available:

**Legacy mode** (default) -- Two-page PDF with separate front and back grids:

```
  Page 1 (Front)              Page 2 (Back)
+----------+----------+    +----------+----------+
| FRONT 1  | FRONT 2  |    | BACK 1   | BACK 2   |
|Translated|          |    | English  | English  |
+----------+----------+    +----------+----------+
| FRONT 3  | FRONT 4  |    | BACK 3   | BACK 4   |
+----------+----------+    +----------+----------+
```

**Fold mode** -- Single-page official fold format with front and back side-by-side per row:

```
  Instructions header          Cut / Fold legend
  ----------------------------------------------
  +--------------+--------------+  Row 1
  |    FRONT     |     BACK     |
  | (Translated) |   (English)  |
  +--------------+--------------+
  |    FRONT     |     BACK     |  Row 2
  +--------------+--------------+
  |    FRONT     |     BACK     |  Row 3
  +--------------+--------------+
  |    FRONT     |     BACK     |  Row 4
  +--------------+--------------+
              fold line
```

## Features

- **56 Languages**: Support for Latin, Cyrillic, Arabic, Hebrew, CJK, South Asian, Southeast Asian, and more
- **22 Unicode Scripts**: Each script uses optimized Noto Sans fonts
- **RTL Support**: Full right-to-left rendering for Arabic and Hebrew with proper text reshaping
- **No-Space Script Wrapping**: Character-safe wrapping for CJK, Thai, Lao, Khmer, and Myanmar scripts
- **Two Render Modes**: Legacy (2-page front/back grids) and fold (single-page front|back side-by-side per row)
- **Official Fold Format**: Matches the ILRC red card fold sheet layout with max 2 columns, cut/fold guides, and instruction header
- **Flexible Layouts**: Legacy supports 4, 6, 8, or 12 cards per page; fold supports 4, 5, or 6 rows
- **Font Availability Checking**: API reports which languages have fonts installed
- **Flexible JSON Parsing**: Accepts multiple translation file formats

## Architecture

### Startup

```
1. FastAPI app starts via lifespan context manager
2. TranslationsStore loads Translations_with_sources.json
3. TranslationsStore._normalize() parses & normalizes language entries
4. FontManager initializes lazily on first use (registers fonts from assets/fonts/)
```

### Request Flow

```
GET /api/languages
`->` TranslationsStore.list_languages()
    `->` FontManager.is_script_supported() -> fontSupported flag per language

GET /api/render/{code}?cards_per_page=4&mode=legacy

1. VALIDATION
   - Check store initialized (503 if not)
   - Validate mode ("legacy" or "fold")
   - Look up language by code (404 if not found)
   - Validate cards_per_page per mode

2. LAYOUT CALCULATION
   - Legacy: CardLayout.from_cards_per_page()
     - Determine grid (2x2, 2x3, 2x4, or 3x4)
     - Generate positions list
   - Fold: CardLayout.from_fold_rows()
     - Always 2 columns (front|back)
     - N rows (4, 5, or 6)
     - Positions as front/back pairs per row

3. CONTENT PREPARATION
   - Front content from TranslationsStore (translated)
   - Back content from back_content.py (English)

4. PDF RENDERING
   - Legacy: render_print_sheet_pdf()
     - PAGE 1 (Front): grid of translated cards
     - PAGE 2 (Back): grid of English cards
   - Fold: render_fold_sheet_pdf()
     - HEADER: instructions + cut/fold legend
     - For each row:
       - Left cell: draw_front() (translated, RTL-aware)
       - Right cell: draw_back() (English, LTR)
     - Cut borders around each cell
     - Center fold guide line

5. RESPONSE
   - Content-Type: application/pdf
     Filename: know-your-rights-{code}-{count}up.pdf
```

### Text Wrapping Flow

The text wrapping system handles different scripts intelligently:

```
Text Input
  -> Has lang_code?
     -> YES: detect_script(lang_code) -> Script enum
        -> is_no_space_script()?
           -> YES: character-wrap
           -> NO: simpleSplit()

  -> No lang_code
     -> is_cjk_text()?
        -> YES: character-wrap
        -> NO: simpleSplit()

  -> Final safety pass:
     any over-width line -> character-wrap fallback
```

### Font Scaling Flow

Two-level scaling ensures text fits within card boundaries:

```
1. Layout-level scale: font_scale = sqrt(card_area / base_card_area)
   - Clamped between 0.6 and 1.0

2. Adaptive content fit (front + back): find_best_fit_scale()
   - Start at layout's base font_scale
   - If content fits, search upward for larger readable text
   - If content overflows, search downward for largest fitting scale
   - Bounded by min/max scale factors + absolute font-size caps
```

## Installation

### Prerequisites

- Python 3.10+
- pip

### Setup

```bash
# Clone the repository
git clone https://github.com/pierre-projects/redcardapi.git
cd redcardapi/redcard-backend

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Server

```bash
# Development mode with auto-reload
uvicorn app.main:app --reload --port 8000

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

## Configuration

Configuration is managed via environment variables or a `.env` file. All variables use the `CARD_` prefix.

| Variable | Default | Description |
|----------|---------|-------------|
| `CARD_TRANSLATIONS_JSON_PATH` | `data/Translations_with_sources.json` | Path to translations JSON file |
| `CARD_FONTS_DIR` | `assets/fonts` | Directory containing font files |
| `CARD_LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `CARD_PAGE_SIZE` | `letter` | Page size (`letter` or `a4`) |
| `CARD_DEFAULT_CARDS_PER_PAGE` | `4` | Default legacy layout (4, 6, 8, or 12) |
| `CARD_DEFAULT_FOLD_CARDS_PER_PAGE` | `4` | Default fold mode rows (4, 5, or 6) |
| `CARD_MARGIN_INCHES` | `0.5` | Page margin in inches |
| `CARD_GUTTER_INCHES` | `0.25` | Space between cards in inches |
| `CARD_FOOTER_HEIGHT_INCHES` | `0.55` | Reserved footer height in inches |
| `CARD_CORS_ORIGINS` | `["http://localhost:5173","http://127.0.0.1:5173"]` | Allowed origins as a JSON string array |

Example `.env` file:
```env
CARD_LOG_LEVEL=DEBUG
CARD_PAGE_SIZE=letter
CARD_CORS_ORIGINS=["http://localhost:5173","http://127.0.0.1:5173","http://localhost:3000"]
```

## API Endpoints

### Health Check
```
GET /api/health
```
Returns service status and loaded language count.

**Response:**
```json
{
  "ok": true,
  "languages_loaded": 56
}
```

### Get Configuration
```
GET /api/config
```
Returns valid layout options for the frontend.

**Response:**
```json
{
  "valid_layouts": [4, 6, 8, 12],
  "default_cards_per_page": 4,
  "page_size": "letter",
  "render_modes": ["legacy", "fold"],
  "fold_layouts": [4, 5, 6],
  "default_fold_cards_per_page": 4
}
```

### List Languages
```
GET /api/languages
```
Returns all available languages with font support status.

**Response:**
```json
[
  {
    "code": "en",
    "name": "English",
    "rtl": false,
    "official": true,
    "fontSupported": true
  },
  {
    "code": "ar",
    "name": "Arabic",
    "rtl": true,
    "official": true,
    "fontSupported": true,
    "source": {
      "type": "official",
      "origin": "ILRC",
      "url": "https://www.ilrc.org/red-cards",
      "verified": true
    }
  }
]
```

**Error Responses:**
- `503`: Service not ready (translations store not initialized)

### Get Card Content
```
GET /api/card/{code}
```
Returns card content for preview.

**Parameters:**
- `code`: Language code (e.g., `en`, `es`, `zh-cn`)

**Response:**
```json
{
  "code": "es",
  "name": "Spanish",
  "rtl": false,
  "official": true,
  "front": {
    "header": "CONOZCA SUS DERECHOS",
    "bullets": ["Punto 1", "Punto 2", "..."]
  },
  "source": {
    "type": "official",
    "origin": "ILRC",
    "url": "https://www.ilrc.org/red-cards",
    "verified": true
  }
}
```

**Error Responses:**
- `404`: Language code not found
- `503`: Service not ready (translations store not initialized)

### Render PDF
```
GET /api/render/{code}?cards_per_page=4&mode=legacy
```
Generates and downloads a printable PDF.

**Parameters:**
- `code`: Language code (e.g., `en`, `es`, `zh-cn`)
- `cards_per_page`: Optional layout count
  - Legacy mode: one of 4, 6, 8, or 12 (default: 4)
  - Fold mode: one of 4, 5, or 6 rows (default: 4)
  - Fold mode normalization: if `cards_per_page` is within query bounds (`4-12`) but not in `{4,5,6}` (e.g., `8`), it is normalized to the fold default.
- `mode`: Optional render mode (default: `legacy`)
  - `legacy` -- Two-page PDF. Page 1 = translated front grid, Page 2 = English back grid.
  - `fold` -- Single-page official fold format. Each row has front (left) and back (right) side-by-side, max 2 columns. Matches the official red card sheet layout.

**Response:**
- Content-Type: `application/pdf`
- Legacy filename: `know-your-rights-{code}-{language-name-slug}-{count}up.pdf`
- Fold filename: `know-your-rights-{code}-{language-name-slug}-{count}up-fold.pdf`

**Error Responses:**
- `400`: Invalid mode or font not available for requested language
- `404`: Language code not found
- `500`: PDF generation failed
- `503`: Service not ready (translations store not initialized)

## Font System

### Supported Scripts

| Script | Languages | Font |
|--------|-----------|------|
| Latin | English, Spanish, French, etc. (26) | NotoSans |
| Cyrillic | Russian, Ukrainian, etc. (2) | NotoSans |
| Arabic | Arabic, Persian, Urdu, etc. (5) | NotoSansArabic |
| Hebrew | Hebrew (1) | NotoSansHebrew |
| CJK Simplified | Chinese Simplified (1) | NotoSansSC |
| CJK Traditional | Chinese Traditional, Cantonese (2) | NotoSansTC |
| Japanese | Japanese (1) | NotoSansJP |
| Korean | Korean (1) | NotoSansKR |
| Devanagari | Hindi, Nepali (2) | NotoSans (fallback when NotoSansDevanagari files are absent) |
| Bengali | Bengali (1) | NotoSansBengali |
| Tamil | Tamil (1) | NotoSansTamil |
| Gurmukhi | Punjabi (1) | NotoSansGurmukhi |
| Thai | Thai (1) | NotoSansThai |
| Lao | Lao (1) | NotoSansLao |
| Khmer | Khmer (1) | NotoSansKhmer |
| Myanmar | Burmese, Karen (2) | NotoSansMyanmar |
| Ethiopic | Amharic, Tigrinya (2) | NotoSansEthiopic |
| Armenian | Armenian (1) | NotoSansArmenian |
| Georgian | Georgian (1) | NotoSansGeorgian |
| Greek | Greek (1) | NotoSans |
| Vietnamese | Vietnamese (1) | NotoSans |
| Mongolian | Mongolian (1) | NotoSans |

Current script distribution in `data/Translations_with_sources.json`: LATIN (26), ARABIC (5), CYRILLIC (2), DEVANAGARI (2), ETHIOPIC (2), CJK_TRADITIONAL (2), MYANMAR (2), and 1 each for ARMENIAN, BENGALI, CJK_SIMPLIFIED, GEORGIAN, GREEK, GURMUKHI, HEBREW, JAPANESE, KHMER, KOREAN, LAO, MONGOLIAN, TAMIL, THAI, and VIETNAMESE.

### Installing Fonts

1. Download Noto Sans fonts from [Google Fonts](https://fonts.google.com/noto)
2. Place TTF files in `assets/fonts/`
3. Required files per font family:
   - `NotoSans{Script}-Regular.ttf`
   - `NotoSans{Script}-Bold.ttf`

### Font Selection Flow

```
Language Code -> Script Detection -> Font Family -> Font Files
     "ar"     ->   Script.ARABIC  -> NotoSansArabic -> NotoSansArabic-*.ttf
```

## Text Wrapping (No-Space Script Support)

### The Problem

Several scripts do not reliably use spaces as word boundaries for line wrapping.  
If wrapping is done only with whitespace-based splitting (like ReportLab's `simpleSplit()`), long runs can overflow card boundaries.

### The Solution

The `app/text/` module now uses a two-stage strategy:

1. **Script-aware primary wrapping**
   - Character-level wrapping for: CJK, Thai, Lao, Khmer, Myanmar
   - Word-boundary wrapping for: Latin/Cyrillic/Arabic/Hebrew/etc.
2. **Overflow safety pass**
   - Any line still wider than `max_width` is re-wrapped character-by-character.

| Script Type | Primary Wrapping | Overflow Safety |
|-------------|------------------|-----------------|
| Latin/Cyrillic/Greek/Vietnamese | Word-boundary (`simpleSplit`) | Character fallback if needed |
| Arabic/Hebrew (RTL) | Word-boundary + RTL processing | Character fallback if needed |
| CJK | Character-by-character | Built-in |
| Thai/Lao/Khmer/Myanmar | Character-by-character | Built-in |

### How It Works

```python
from app.text import wrap_text

# With language hint (recommended, uses script mapping)
lines = wrap_text(text, font_name, font_size, max_width, lang_code="km")

# Without language hint (falls back to CJK character detection)
lines = wrap_text("\u4f60\u597d\u4e16\u754c", font_name, font_size, max_width)
```

### Unicode Ranges Auto-Detected (No `lang_code`)

When `lang_code` is not provided, the wrapper can still auto-detect CJK text via Unicode ranges:
- `0x4E00-0x9FFF`: CJK Unified Ideographs (Chinese characters)
- `0x3400-0x4DBF`: CJK Extension A
- `0x3000-0x303F`: CJK Punctuation
- `0xFF00-0xFFEF`: Fullwidth Forms
- `0x3040-0x309F`: Hiragana (Japanese)
- `0x30A0-0x30FF`: Katakana (Japanese)
- `0xAC00-0xD7AF`: Hangul Syllables (Korean)

## Adding New Languages

### 1. Add Translation Data

Add the language to `Translations_with_sources.json` (or the file configured by `CARD_TRANSLATIONS_JSON_PATH`):
```json
{
  "code": "new",
  "name": "New Language",
  "rtl": false,
  "source": {
    "type": "official",
    "origin": "ILRC",
    "url": "https://www.ilrc.org/red-cards",
    "verified": true
  },
  "front": {
    "header": "TRANSLATED HEADER",
    "bullets": ["Bullet 1", "Bullet 2"]
  }
}
```

### 2. Add Script Mapping

In `app/fonts/script_detector.py`, add the language code:
```python
LANGUAGE_TO_SCRIPT: Dict[str, Script] = {
    # ... existing mappings ...
    "new": Script.LATIN,  # or appropriate script
}
```

### 3. Add Font (if new script)

If the language uses a new script:

1. Add Script enum value in `script_detector.py`:
   ```python
   class Script(Enum):
       # ... existing scripts ...
       NEW_SCRIPT = auto()
   ```

2. Add font family in `font_config.py`:
   ```python
   FONT_FAMILIES["NotoSansNew"] = FontFamily(
       name="NotoSansNew",
       regular_file="NotoSansNew-Regular.ttf",
       bold_file="NotoSansNew-Bold.ttf",
       scripts=[Script.NEW_SCRIPT],
   )

   SCRIPT_TO_FONTS[Script.NEW_SCRIPT] = ["NotoSansNew", "NotoSans"]
   ```

3. Place font files in `assets/fonts/`

## Testing

### Run Font Coverage Test

Tests that all languages can actually render PDFs:

```bash
python test_font_coverage.py
```

This will:
- Attempt to render a PDF for each language
- Report which languages succeed/fail
- Identify "supported but failed" issues (font mapping bugs)

### Generate Visual QA PDF (All Languages)

Generate one merged PDF with a labeled page per language for visual review:

Install optional dev dependency first (required by `dev/test_all_languages.py`):

```bash
pip install PyPDF2
```

```bash
# Legacy mode (default) -- front page only per language
python dev/test_all_languages.py --cards 12

# Fold mode -- full fold sheet (front|back side-by-side) per language
python dev/test_all_languages.py --mode fold --cards 4

# Custom output path
python dev/test_all_languages.py --mode fold --cards 6 --output fold_review.pdf
```

This will:
- Render all languages in the selected mode
- Add `Language: <code> (<name>) [mode]` label to each output page
- Use `settings.translations_json_path` (default: `data/Translations_with_sources.json`)
- Include per-language `source` metadata in fold header rendering
- Merge pages into a single review PDF in `dev/`

### API Tests

Automated API tests are not currently checked into this repository (`tests/` does not exist yet).  
If tests are added later, document and run them from this section.

## Project Structure

```
redcard-backend/
|- app/
|  |- __init__.py
|  |- main.py                 # FastAPI app, endpoints, lifespan (legacy + fold routing)
|  |- config.py               # Settings and path management (includes fold defaults)
|  |- schemas.py              # Pydantic models for API validation
|  |- exceptions.py           # Custom exception classes
|  |- translations_store.py   # Translation JSON loader/parser
|  |- pdf_renderer.py         # Compatibility facade (legacy + fold exports)
|  |- pdf/
|  |  |- __init__.py          # PDF package exports
|  |  |- renderer.py          # PDF orchestration (render_print_sheet_pdf + render_fold_sheet_pdf)
|  |  |- front.py             # Front card rendering + adaptive sizing
|  |  |- back.py              # Back card rendering
|  |  |- guides.py            # Cut lines, fold guides, fold header, footer, text helpers
|  |  |- wrapping.py          # RTL-aware line wrapping adapter
|  |  |- rtl.py               # RTL shaping/reordering support
|  |  |- fonts.py             # Font pick/registration helpers
|  |  `- constants.py         # Shared typography/scaling constants
|  |- layout.py               # Card positioning (legacy grids + fold rows)
|  |- back_content.py         # English back card content
|  |- logging_config.py       # Logging configuration
|  |- fonts/
|  |  |- __init__.py          # Font module exports
|  |  |- font_manager.py      # Font registration and lookup singleton
|  |  |- font_config.py       # Font family definitions
|  |  `- script_detector.py   # Language -> Unicode script detection
|  `- text/
|     |- __init__.py          # Text module exports
|     `- text_wrapper.py      # Script-aware + overflow-safe text wrapping
|- assets/
|  `- fonts/                  # TTF font files (Noto Sans families)
|- data/
|  |- Translations.json
|  `- Translations_with_sources.json
|- dev/
|  `- test_all_languages.py   # Visual QA: all languages in legacy or fold mode
|- .env.example               # Environment variable template
|- .gitignore
|- requirements.txt           # Python dependencies
|- test_font_coverage.py      # Font coverage validation script
`- README.md                  # Project documentation
```

## Dependencies

| Package | Purpose |
|---------|---------|
| `fastapi` | Web framework |
| `uvicorn` | ASGI server |
| `pydantic-settings` | Configuration management |
| `reportlab` | PDF generation |
| `pillow` | Image processing support used by PDF tooling |
| `arabic-reshaper` | Arabic text shaping |
| `python-bidi` | Bidirectional text support |
| `charset-normalizer` | Text encoding normalization utilities |

## Known Issues / In Progress

### Font File Naming Is Strict

Font loading is based on exact filenames defined in `app/fonts/font_config.py`.  
For each configured family, both files must exist in `assets/fonts/`:

- `NotoSans{Script}-Regular.ttf`
- `NotoSans{Script}-Bold.ttf`

If names do not match exactly, the renderer may fall back to another font (or fail for scripts with no usable fallback).

### Adaptive Text Fill

Card text now uses bidirectional adaptive fitting:

- **Scale down** when content is dense and would overflow.
- **Scale up** when content is short and there is room, improving readability.
- **Applied to both sides:** translated front and English back.
- **Safety caps:** fitting is bounded by min/max scale factors and absolute font-size limits.

Fold header behavior in `mode=fold`:

- Metadata includes `Language`, `Code`, and `Source`.
- Source resolution prefers per-language `source`, then top-level `metadata.source`, then `unknown`.
- Source formatting includes origin/type plus verification flag and compact domain when available.
- Instruction copy is split into explicit lines to avoid truncation in the header text area.

## License

This project is licensed under the MIT License. See `LICENSE` for details.

Attribution: The 56 language translations were sourced from the Immigration
Legal Resource Center (ILRC), who created the original red cards.

## Contributing

See `CONTRIBUTING.md` for guidelines.
