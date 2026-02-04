"""
Pydantic Schemas for API Request/Response Validation.

=============================================================================
MODULE OVERVIEW
=============================================================================

This module defines Pydantic models that validate and serialize data flowing
through the API. These schemas ensure:

1. DATA INTEGRITY - All required fields are present and valid
2. TYPE SAFETY - Fields are correctly typed and transformed
3. DOCUMENTATION - OpenAPI/Swagger docs are auto-generated from these models
4. SERIALIZATION - Consistent JSON output format

=============================================================================
SCHEMA HIERARCHY
=============================================================================

    BulletItem          <- Single bullet point with optional ID
         |
    FrontContent        <- Card front: header + list of bullets
         |
    CardPayload         <- Full card: metadata + front content
         |
    LanguageItem        <- Language listing with font support status

    BackContent         <- Card back: list of paragraphs (English rights)

=============================================================================
API ENDPOINT MAPPING
=============================================================================

    GET /api/languages     -> List[LanguageItem]
    GET /api/card/{code}   -> CardPayload
    GET /api/render/{code} -> (Uses CardPayload internally for validation)

=============================================================================
VALIDATION STRATEGY
=============================================================================

All validators use @field_validator with the following conventions:

1. STRIP WHITESPACE - All string fields are trimmed
2. EMPTY CHECK - Required strings cannot be empty after stripping
3. NORMALIZE - Language codes are lowercased for consistency
4. LENIENT PARSING - Accept multiple field name variations (header/title)

=============================================================================
"""

import re
from pydantic import BaseModel, field_validator
from typing import Optional, List, Dict, Any, Union


# =============================================================================
# CONSTANTS
# =============================================================================

# Language code validation pattern
# Matches: "en", "es", "zh-CN", "pt-BR" (2-3 letter code with optional region)
LANGUAGE_CODE_PATTERN = re.compile(r"^[a-z]{2,3}(-[A-Z]{2})?$")


# =============================================================================
# BULLET ITEM SCHEMA
# =============================================================================

class BulletItem(BaseModel):
    """
    A single bullet point in card content.

    Represents one item in the "Know Your Rights" bullet list.
    Supports both simple strings and objects with IDs for tracking.

    ATTRIBUTES:
        id: Optional identifier for the bullet (used by CMS/editing systems)
        text: The actual bullet point text (required, cannot be empty)

    JSON EXAMPLES:
        Simple: {"text": "You have the right to remain silent"}
        With ID: {"id": "right_1", "text": "You have the right to remain silent"}
    """

    id: Optional[str] = None
    text: str

    @field_validator("text")
    @classmethod
    def text_not_empty(cls, v: str) -> str:
        """
        Validate bullet text is not empty.

        FLOW:
        1. Check if value is None or empty string -> raise error
        2. Check if value is all whitespace -> raise error
        3. Strip whitespace and return

        RAISES:
            ValueError: If text is empty or whitespace-only
        """
        if not v or not v.strip():
            raise ValueError("Bullet text cannot be empty")
        return v.strip()


# =============================================================================
# FRONT CONTENT SCHEMA
# =============================================================================

class FrontContent(BaseModel):
    """
    Front side content of a Know Your Rights card.

    The front side displays the translated rights information with
    a header and bullet points in the target language.

    ATTRIBUTES:
        header: Main heading text (e.g., "KNOW YOUR RIGHTS" / "CONOZCA SUS DERECHOS")
        bullets: List of rights points (strings or BulletItem objects)

    JSON EXAMPLE:
        {
            "header": "CONOZCA SUS DERECHOS",
            "bullets": [
                "Tiene derecho a guardar silencio",
                {"id": "2", "text": "Tiene derecho a un abogado"}
            ]
        }

    RENDERING FLOW:
        1. Header is displayed at top in larger/bold font
        2. Bullets are rendered as a bulleted list below
        3. For RTL languages, text alignment is reversed
    """

    header: str
    bullets: List[Union[BulletItem, str]]  # Accept both string and object bullets

    @field_validator("header")
    @classmethod
    def header_not_empty(cls, v: str) -> str:
        """
        Validate header text is not empty.

        The header is required as it's the main title shown on the card.

        RAISES:
            ValueError: If header is empty or whitespace-only
        """
        if not v or not v.strip():
            raise ValueError("Header cannot be empty")
        return v.strip()

    @field_validator("bullets")
    @classmethod
    def bullets_not_empty(cls, v: List) -> List:
        """
        Validate bullets list is not empty.

        A card must have at least one bullet point to be useful.

        RAISES:
            ValueError: If bullets list is empty
        """
        if not v:
            raise ValueError("Bullets list cannot be empty")
        return v


# =============================================================================
# LANGUAGE ITEM SCHEMA
# =============================================================================

class LanguageItem(BaseModel):
    """
    Language metadata for the /api/languages endpoint.

    Represents a single language option in the language picker dropdown.
    Includes font support status to enable/disable PDF generation.

    ATTRIBUTES:
        code: ISO language code (e.g., "en", "es", "zh-cn")
        name: Display name (e.g., "English", "Español", "简体中文")
        rtl: True if language is right-to-left (Arabic, Hebrew)
        official: True if this is an official/verified translation
        fontSupported: True if fonts are available for PDF rendering

    JSON EXAMPLE:
        {
            "code": "ar",
            "name": "Arabic",
            "rtl": true,
            "official": true,
            "fontSupported": true
        }

    FRONTEND USAGE:
        - code: Used as dropdown value and API parameter
        - name: Displayed in dropdown
        - rtl: Shows "RTL" badge in dropdown
        - fontSupported: Shows warning icon if false, disables PDF button
    """

    code: str
    name: str
    rtl: bool = False
    official: bool = True
    fontSupported: bool = True  # Added to support font availability warnings

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        """
        Validate and normalize language code.

        FLOW:
        1. Strip whitespace and convert to lowercase
        2. Check if empty -> raise error
        3. Check length (2-10 chars) -> raise error if invalid
        4. Return normalized code

        NOTE: We are lenient with format (don't enforce strict ISO)
        to support various code styles (en, zh-CN, zh-cn, etc.)

        RAISES:
            ValueError: If code is empty or wrong length
        """
        v = v.strip().lower() if v else ""
        if not v:
            raise ValueError("Language code cannot be empty")
        if len(v) < 2 or len(v) > 10:
            raise ValueError("Language code must be 2-10 characters")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """
        Validate language display name.

        RAISES:
            ValueError: If name is empty or whitespace-only
        """
        if not v or not v.strip():
            raise ValueError("Language name cannot be empty")
        return v.strip()


# =============================================================================
# CARD PAYLOAD SCHEMA
# =============================================================================

class CardPayload(BaseModel):
    """
    Full card payload for preview and PDF rendering.

    This is the primary schema used when fetching card content for a
    specific language. It includes all metadata plus the front content.

    ATTRIBUTES:
        code: Language code (normalized to lowercase)
        name: Language display name
        rtl: Right-to-left flag
        official: Official translation flag
        front: Dictionary containing header and bullets

    JSON EXAMPLE:
        {
            "code": "es",
            "name": "Spanish",
            "rtl": false,
            "official": true,
            "front": {
                "header": "CONOZCA SUS DERECHOS",
                "bullets": ["Punto 1", "Punto 2"]
            }
        }

    USED BY:
        - GET /api/card/{code} - Returns this schema for preview
        - render_print_sheet_pdf() - Uses this format internally

    NOTE:
        The front field uses Dict[str, Any] instead of FrontContent to
        maintain flexibility with various JSON structures from different
        translation sources.
    """

    code: str
    name: str
    rtl: bool = False
    official: bool = True
    front: Dict[str, Any]  # Flexible dict to handle various JSON structures

    @field_validator("code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        """
        Validate and normalize language code.

        Same validation as LanguageItem for consistency.

        RAISES:
            ValueError: If code is empty or wrong length
        """
        v = v.strip().lower() if v else ""
        if not v:
            raise ValueError("Language code cannot be empty")
        if len(v) < 2 or len(v) > 10:
            raise ValueError("Language code must be 2-10 characters")
        return v

    @field_validator("front")
    @classmethod
    def validate_front(cls, v: Dict) -> Dict:
        """
        Validate front content structure.

        Checks that required content fields are present. Accepts multiple
        field name variations for flexibility with different JSON sources:
        - "header" or "title" for the main heading
        - "bullets" or "points" for the list items

        FLOW:
        1. Check if dict is empty -> raise error
        2. Check for header/title key -> raise error if missing
        3. Check for bullets/points key -> raise error if missing
        4. Return original dict

        RAISES:
            ValueError: If front content is empty or missing required fields
        """
        if not v:
            raise ValueError("Front content cannot be empty")

        # Check for required keys (accept multiple field name variations)
        has_header = bool(v.get("header") or v.get("title"))
        has_bullets = bool(v.get("bullets") or v.get("points"))

        if not has_header:
            raise ValueError("Front content must have 'header' or 'title'")
        if not has_bullets:
            raise ValueError("Front content must have 'bullets' or 'points'")

        return v


# =============================================================================
# BACK CONTENT SCHEMA
# =============================================================================

class BackContent(BaseModel):
    """
    Back side content of a Know Your Rights card.

    The back side contains constitutional rights information in English.
    Currently, this is not translated - all cards use the same English
    back content regardless of the front language.

    ATTRIBUTES:
        paragraphs: List of paragraph strings explaining constitutional rights

    JSON EXAMPLE:
        {
            "paragraphs": [
                "I do not wish to speak with you...",
                "I do not give you permission to enter...",
                "I choose to exercise my constitutional rights."
            ]
        }

    RENDERING:
        - Paragraphs are displayed as separate blocks of text
        - Font size is smaller than front to fit all content
        - Always rendered in English (LTR) even for RTL languages

    SEE ALSO:
        back_content.py - Provides the default English content
    """

    paragraphs: List[str]

    @field_validator("paragraphs")
    @classmethod
    def paragraphs_not_empty(cls, v: List[str]) -> List[str]:
        """
        Validate and clean paragraphs list.

        FLOW:
        1. Check if list is empty -> raise error
        2. Strip whitespace from each paragraph
        3. Filter out empty paragraphs
        4. Return cleaned list

        RAISES:
            ValueError: If paragraphs list is empty
        """
        if not v:
            raise ValueError("Paragraphs list cannot be empty")
        return [p.strip() for p in v if p and p.strip()]
