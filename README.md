# RedCardGenerator Backend

A FastAPI backend for generating multi-language "Know Your Rights" PDF cards with support for 56+ languages and 22 Unicode scripts.

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

```
┌─────────────────────┐    ┌─────────────────────┐
│       FRONT         │    │        BACK         │
│                     │    │                     │
│   KNOW YOUR RIGHTS  │    │  I do not wish to   │
│   (Translated)      │    │  speak with you...  │
│                     │    │  (English)          │
│   • Right 1         │    │                     │
│   • Right 2         │    │  Based on my 4th    │
│   • Right 3         │    │  Amendment rights...│
│                     │    │                     │
└─────────────────────┘    └─────────────────────┘
```

## Features

- **56+ Languages**: Support for Latin, Cyrillic, Arabic, Hebrew, CJK, South Asian, Southeast Asian, and more
- **22 Unicode Scripts**: Each script uses optimized Noto Sans fonts
- **RTL Support**: Full right-to-left rendering for Arabic and Hebrew with proper text reshaping
- **No-Space Script Wrapping**: Character-safe wrapping for CJK, Thai, Lao, Khmer, and Myanmar scripts
- **Flexible Layouts**: 4, 6, 8, or 12 cards per page
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
└── TranslationsStore.list_languages()
    └── FontManager.is_script_supported() → fontSupported flag per language

GET /api/render/{code}?cards_per_page=4
│
├── 1. VALIDATION
│   ├── Check store initialized (503 if not)
│   ├── Look up language by code (404 if not found)
│   └── Validate cards_per_page (defaults to 4 if invalid)
│
├── 2. LAYOUT CALCULATION
│   └── CardLayout.from_cards_per_page()
│       ├── Determine grid (2x2, 2x3, 2x4, or 3x4)
│       ├── Calculate card dimensions (width/height in points)
│       ├── Calculate font_scale based on card area ratio
│       └── Generate positions list [(x, y, w, h), ...]
│
├── 3. CONTENT PREPARATION
│   ├── Front content from TranslationsStore (translated)
│   └── Back content from back_content.py (English)
│
├── 4. PDF RENDERING — render_print_sheet_pdf()
│   ├── Detect script from language code
│   ├── Select font via FontManager.pick()
│   ├── PAGE 1 (Front):
│   │   ├── Draw fold guides (dashed lines)
│   │   ├── For each card position:
│   │   │   ├── Draw cut lines (dotted border)
│   │   │   └── _draw_front()
│   │   │       ├── Find optimal font scale (adaptive sizing)
│   │   │       ├── Wrap text (script-aware + overflow-safe)
│   │   │       ├── Process RTL text (Arabic/Hebrew reshaping)
│   │   │       └── Draw header + bullets
│   │   └── Draw footer (printing instructions)
│   ├── PAGE 2 (Back):
│   │   ├── Draw fold guides
│   │   ├── For each card position:
│   │   │   ├── Draw cut lines
│   │   │   └── _draw_back() (English paragraphs)
│   │   └── Draw footer
│   └── Return PDF bytes
│
└── 5. RESPONSE
    └── Content-Type: application/pdf
        Filename: know-your-rights-{code}-{count}up.pdf
```

### Text Wrapping Flow

The text wrapping system handles different scripts intelligently:

```
Text Input
    │
    ├─→ Has lang_code? ─YES─→ detect_script(lang_code) → Script enum
    │                         │
    │                         └─→ is_no_space_script()? ─YES─→ character-wrap
    │                                                     │
    │                                                     └─NO─→ simpleSplit()
    │
    ├─→ No lang_code ──→ is_cjk_text()? ─YES─→ character-wrap
    │                    │
    │                    └─NO─→ simpleSplit()
    │
    └─→ Final safety pass: any over-width line ─→ character-wrap fallback
```

### Font Scaling Flow

Two-level scaling ensures text fits within card boundaries:

```
1. Layout-level scale: font_scale = sqrt(card_area / base_card_area)
   └── Clamped between 0.6 and 1.0

2. Adaptive content scale: _find_optimal_font_scale()
   └── Start at layout's base font_scale
       └── Measure content height → too tall? → reduce by 0.05 → repeat
           └── Stops at 50% of base scale or 6pt minimum
```

## Installation

### Prerequisites

- Python 3.10+
- pip

### Setup

```bash
# Clone the repository
git clone https://github.com/pierre-projects/redcardapi.git
cd redcardapi

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
| `CARD_LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `CARD_PAGE_SIZE` | `letter` | Page size (`letter` or `a4`) |
| `CARD_DEFAULT_CARDS_PER_PAGE` | `4` | Default layout (4, 6, 8, or 12) |
| `CARD_CORS_ORIGINS` | `localhost:5173` | Comma-separated allowed origins |

Example `.env` file:
```env
CARD_LOG_LEVEL=DEBUG
CARD_PAGE_SIZE=letter
CARD_CORS_ORIGINS=http://localhost:5173,http://localhost:3000
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
  "page_size": "letter"
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
    "fontSupported": true
  }
]
```

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
  }
}
```

### Render PDF
```
GET /api/render/{code}?cards_per_page=4
```
Generates and downloads a printable PDF.

**Parameters:**
- `code`: Language code (e.g., `en`, `es`, `zh-cn`)
- `cards_per_page`: Optional, one of 4, 6, 8, or 12 (default: 4)

**Response:**
- Content-Type: `application/pdf`
- Filename: `know-your-rights-{code}-{count}up.pdf`

**Error Responses:**
- `400`: Font not available for requested language
- `404`: Language code not found
- `500`: PDF generation failed

## Font System

### Supported Scripts

| Script | Languages | Font |
|--------|-----------|------|
| Latin | English, Spanish, French, etc. (39) | NotoSans |
| Cyrillic | Russian, Ukrainian, etc. (5) | NotoSans |
| Arabic | Arabic, Persian, Urdu, etc. (6) | NotoSansArabic |
| Hebrew | Hebrew (1) | NotoSansHebrew |
| CJK Simplified | Chinese Simplified (1) | NotoSansSC |
| CJK Traditional | Chinese Traditional, Cantonese (2) | NotoSansTC |
| Japanese | Japanese (1) | NotoSansJP |
| Korean | Korean (1) | NotoSansKR |
| Devanagari | Hindi, Nepali, Marathi (3) | NotoSansDevanagari |
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

### Installing Fonts

1. Download Noto Sans fonts from [Google Fonts](https://fonts.google.com/noto)
2. Place TTF files in `assets/fonts/`
3. Required files per font family:
   - `NotoSans{Script}-Regular.ttf`
   - `NotoSans{Script}-Bold.ttf`

### Font Selection Flow

```
Language Code → Script Detection → Font Family → Font Files
     "ar"     →   Script.ARABIC  → NotoSansArabic → NotoSansArabic-*.ttf
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
lines = wrap_text("你好世界", font_name, font_size, max_width)
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

Add the language to `Translations.json`:
```json
{
  "code": "new",
  "name": "New Language",
  "rtl": false,
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

### Generate Visual QA PDF (All Languages, Front Only)

Generate one merged PDF with a labeled **front page** per language (back pages skipped):

```bash
python dev/test_all_languages.py --cards 12
```

This will:
- Render all language front sides
- Add `Language: <code> (<name>)` label to each output page
- Merge pages into a single review PDF in `dev/`

### Run API Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run tests
pytest tests/
```

## Project Structure

```
redcard-backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app, endpoints, lifespan
│   ├── config.py               # Settings & path management (pydantic-settings)
│   ├── schemas.py              # Pydantic models for API validation
│   ├── exceptions.py           # Custom exception classes
│   ├── translations_store.py   # Translation JSON loader/parser
│   ├── pdf_renderer.py         # Compatibility facade (legacy imports)
│   ├── pdf/
│   │   ├── __init__.py         # PDF package exports
│   │   ├── renderer.py         # Main PDF orchestration
│   │   ├── front.py            # Front card rendering + adaptive sizing
│   │   ├── back.py             # Back card rendering
│   │   ├── guides.py           # Cut lines, fold guides, footer, text helpers
│   │   ├── wrapping.py         # RTL-aware line wrapping adapter
│   │   ├── rtl.py              # RTL shaping/reordering support
│   │   ├── fonts.py            # Font pick/registration helpers
│   │   └── constants.py        # Shared typography/scaling constants
│   ├── layout.py               # Card positioning calculations
│   ├── back_content.py         # English back card content
│   ├── logging_config.py       # Logging configuration
│   ├── fonts/
│   │   ├── __init__.py         # Font module exports
│   │   ├── font_manager.py     # Font registration & lookup singleton
│   │   ├── font_config.py      # Font family definitions
│   │   └── script_detector.py  # Language → Unicode script detection
│   └── text/
│       ├── __init__.py         # Text module exports
│       └── text_wrapper.py     # Script-aware + overflow-safe text wrapping
├── assets/
│   └── fonts/                  # TTF font files (Noto Sans families)
├── data/
│   ├── Translations.json
│   └── Translations_with_sources.json
├── .env.example                # Environment variable template
├── .gitignore
├── requirements.txt            # Python dependencies
├── test_font_coverage.py       # Font coverage validation script
└── README.md                   # Project documentation

```

## Dependencies

| Package | Purpose |
|---------|---------|
| `fastapi` | Web framework |
| `uvicorn` | ASGI server |
| `pydantic` | Data validation |
| `pydantic-settings` | Configuration management |
| `reportlab` | PDF generation |
| `arabic-reshaper` | Arabic text shaping |
| `python-bidi` | Bidirectional text support |

## Known Issues / In Progress

### Font File Naming Is Strict

Font loading is based on exact filenames defined in `app/fonts/font_config.py`.  
For each configured family, both files must exist in `assets/fonts/`:

- `NotoSans{Script}-Regular.ttf`
- `NotoSans{Script}-Bold.ttf`

If names do not match exactly, the renderer may fall back to another font (or fail for scripts with no usable fallback).

### Card Size Scaling Does Not Scale Up

The adaptive font scaling in `app/pdf/front.py` currently only **shrinks** text to fit within card boundaries — it does not **scale up** to maximize the use of available card space.

- **Current behavior:** If the translated text is short (e.g., a language with brief bullet points), the font stays at the base size even when there is significant empty space on the card. The text appears small relative to the cut-out area.
- **Desired behavior:** The renderer should also attempt to scale text *up* (beyond the base `font_scale`) when there is room, so that shorter content fills more of the card and is easier to read.
- **Where:** `_find_optimal_font_scale()` in `app/pdf/front.py` — the loop currently only reduces scale; it needs a complementary upward pass.

## License

This project is licensed under the MIT License. See `LICENSE` for details.

Attribution: The 56 language translations were sourced from the Immigration
Legal Resource Center (ILRC), who created the original red cards.

## Contributing

See `CONTRIBUTING.md` for guidelines.
