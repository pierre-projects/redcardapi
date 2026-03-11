"""
Configuration Management for RedCardGenerator Application.

=============================================================================
MODULE OVERVIEW
=============================================================================

This module provides centralized configuration management using Pydantic's
settings management. It handles:

1. PATH RESOLUTION - Automatic detection of project and backend directories
2. ENVIRONMENT VARIABLES - Load settings from .env file or environment
3. PDF DEFAULTS - Default layout, margins, and page size settings
4. CORS SETTINGS - Allowed origins for cross-origin requests

=============================================================================
CONFIGURATION SOURCES (in priority order)
=============================================================================

1. Environment variables (prefixed with CARD_)
   Example: CARD_LOG_LEVEL=DEBUG

2. .env file in the current directory
   Example: CARD_CORS_ORIGINS=http://localhost:3000,http://localhost:5173

3. Default values defined in the Settings class

=============================================================================
DIRECTORY STRUCTURE
=============================================================================


Project root (PROJECT_ROOT):
├── app/                     <- Application package
│   ├── config.py            <- This file
│   ├── main.py
│   └── ...
├── assets/
│   └── fonts/               <- Font files directory (TTF/OTF)
├── data/
│   ├── Translations.json
│   └── Translations_with_sources.json
├── .env.example
├── requirements.txt
└── README.md

=============================================================================
USAGE
=============================================================================

Import the singleton settings instance:

    from app.config import settings

    # Access settings
    page_size = settings.page_size
    margins = settings.margin_inches

    # Validate user input
    cards = settings.validate_cards_per_page(user_input)

    # Get valid options for UI
    layouts = settings.get_valid_layouts()  # [4, 6, 8, 12]

=============================================================================
"""

import os
from pathlib import Path
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


# =============================================================================
# PATH CONSTANTS
# =============================================================================
# These are resolved at module load time based on this file's location.
# File path: Backend/app/config.py
# parents[0] = Backend/app/
# parents[1] = Backend/
# parents[2] = Project root/

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT =  PROJECT_ROOT 


# =============================================================================
# SETTINGS CLASS
# =============================================================================

class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Uses pydantic-settings for automatic environment variable parsing with
    the CARD_ prefix. For example:
    - CARD_LOG_LEVEL=DEBUG sets log_level
    - CARD_PAGE_SIZE=a4 sets page_size

    All settings have sensible defaults for development.

    ATTRIBUTES:
        translations_json_path: Path to Translations.json file
        fonts_dir: Directory containing TTF font files
        cors_origins: List of allowed CORS origins
        default_cards_per_page: Default layout (4, 6, 8, or 12)
        page_size: Page size ("letter" or "a4")
        margin_inches: Page margin in inches
        gutter_inches: Space between cards in inches
        footer_height_inches: Reserved space for footer
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """

    # Pydantic settings configuration
    model_config = SettingsConfigDict(
        env_prefix="CARD_",           # Environment variables prefixed with CARD_
        env_file=".env",              # Load from .env file if present
        env_file_encoding="utf-8",    # UTF-8 encoding for .env file
        extra="ignore",               # Ignore unknown environment variables
    )

    # -------------------------------------------------------------------------
    # PATH SETTINGS
    # -------------------------------------------------------------------------
    # Configurable paths for data files and assets.
    # Defaults point to standard locations relative to project root.

    translations_json_path: Path = (
    PROJECT_ROOT / "data" / "Translations_with_sources.json"
        )

    fonts_dir: Path = PROJECT_ROOT / "assets" / "fonts"


    # -------------------------------------------------------------------------
    # CORS SETTINGS
    # -------------------------------------------------------------------------
    # Cross-Origin Resource Sharing configuration.
    # Defaults allow Vite dev server (localhost:5173).
    # In production, add your domain to this list.

    cors_origins: List[str] = [
        "http://localhost:5173",    # Vite dev server
        "http://127.0.0.1:5173",    # Alternative localhost
    ]

    # -------------------------------------------------------------------------
    # PDF LAYOUT DEFAULTS
    # -------------------------------------------------------------------------
    # These settings control the default PDF generation behavior.
    # Users can override cards_per_page via query parameter.

    default_cards_per_page: int = 4   # Valid values: 4, 6, 8, or 12
    default_fold_cards_per_page: int = 4  # Valid values for fold mode: 4, 5, or 6
    page_size: str = "letter"         # "letter" (8.5x11") or "a4" (210x297mm)

    # -------------------------------------------------------------------------
    # MARGIN AND SPACING SETTINGS (in inches)
    # -------------------------------------------------------------------------
    # These control the whitespace around and between cards.
    # Values are in inches for compatibility with ReportLab.

    margin_inches: float = 0.5        # Page margin (all sides)
    gutter_inches: float = 0.25       # Space between cards
    footer_height_inches: float = 0.55  # Reserved for footer text

    # -------------------------------------------------------------------------
    # LOGGING SETTINGS
    # -------------------------------------------------------------------------

    log_level: str = "INFO"           # DEBUG, INFO, WARNING, ERROR, CRITICAL

    # -------------------------------------------------------------------------
    # METHODS
    # -------------------------------------------------------------------------

    def get_valid_layouts(self) -> List[int]:
        """
        Return list of valid cards-per-page options.

        These values correspond to the grid layouts supported by CardLayout:
        - 4: 2x2 grid (largest cards)
        - 6: 2x3 grid
        - 8: 2x4 grid
        - 12: 3x4 grid (smallest cards)

        RETURNS:
            List of valid layout options: [4, 6, 8, 12]

        USAGE:
            Used by /api/config endpoint to populate frontend dropdown.
        """
        return [4, 6, 8, 12]

    def get_valid_fold_layouts(self) -> List[int]:
        """
        Return list of valid rows-per-page options for fold mode.

        In fold mode each row contains a front|back pair (2 columns),
        so rows = number of distinct cards on the sheet.

        RETURNS:
            List of valid fold row options: [4, 5, 6]
        """
        return [4, 5, 6]

    def validate_cards_per_page(self, count: int) -> int:
        """
        Validate and normalize cards-per-page value.

        If the provided count is not in the valid layouts list,
        returns the default value instead.

        PARAMETERS:
            count: User-provided cards per page value

        RETURNS:
            Validated count (4, 6, 8, or 12)

        EXAMPLE:
            settings.validate_cards_per_page(4)   # Returns 4
            settings.validate_cards_per_page(5)   # Returns 4 (default)
            settings.validate_cards_per_page(12)  # Returns 12
        """
        valid = self.get_valid_layouts()
        if count in valid:
            return count
        return self.default_cards_per_page

    def validate_fold_rows(self, count: int) -> int:
        """
        Validate and normalize fold-mode rows value.

        PARAMETERS:
            count: User-provided rows per page value

        RETURNS:
            Validated count (4, 5, or 6)
        """
        valid = self.get_valid_fold_layouts()
        if count in valid:
            return count
        return self.default_fold_cards_per_page


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================
# Create a single Settings instance that is shared across the application.
# This is the recommended way to access configuration.

settings = Settings()


# =============================================================================
# LEGACY EXPORTS
# =============================================================================
# These exports maintain backward compatibility with older code that
# imports TRANSLATIONS_JSON_PATH directly.

TRANSLATIONS_JSON_PATH = settings.translations_json_path
