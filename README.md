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
- **Flexible Layouts**: 4, 6, 8, or 12 cards per page
- **Font Availability Checking**: API reports which languages have fonts installed
- **Flexible JSON Parsing**: Accepts multiple translation file formats

## Architecture

```
Request Flow:
─────────────

1. GET /api/languages
   └── TranslationsStore.list_languages()
       └── FontManager.is_script_supported() → fontSupported flag

2. GET /api/render/{code}
   └── TranslationsStore.get_language(code)
       └── script_detector.detect_script(code) → Script enum
           └── FontManager.get_font_for_script(script)
               └── pdf_renderer.render_print_sheet_pdf()
                   └── ReportLab canvas → PDF bytes
```

## Installation

### Prerequisites

- Python 3.10+
- pip

### Setup

```bash
# Navigate to backend directory
cd Backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

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
2. Place TTF files in `Backend/assets/fonts/`
3. Required files per font family:
   - `NotoSans{Script}-Regular.ttf`
   - `NotoSans{Script}-Bold.ttf`

### Font Selection Flow

```
Language Code → Script Detection → Font Family → Font Files
     "ar"     →   Script.ARABIC  → NotoSansArabic → NotoSansArabic-*.ttf
```

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

3. Place font files in `Backend/assets/fonts/`

## Testing

### Run Font Coverage Test

Tests that all languages can actually render PDFs:

```bash
cd Backend
python test_font_coverage.py
```

This will:
- Attempt to render a PDF for each language
- Report which languages succeed/fail
- Identify "supported but failed" issues (font mapping bugs)

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
│   ├── pdf_renderer.py         # ReportLab PDF generation
│   ├── layout.py               # Card positioning calculations
│   ├── back_content.py         # English back card content
│   ├── logging_config.py       # Logging configuration
│   └── fonts/
│       ├── __init__.py         # Font module exports
│       ├── font_manager.py     # Font registration & lookup singleton
│       ├── font_config.py      # Font family definitions
│       └── script_detector.py  # Language → Unicode script detection
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

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]
