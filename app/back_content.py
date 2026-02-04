"""
Back Side Content for Know Your Rights Cards.

=============================================================================
MODULE OVERVIEW
=============================================================================

This module provides the content for the BACK side of Know Your Rights cards.
The back side contains constitutional rights information in English that
explains how to exercise 4th and 5th Amendment rights.

=============================================================================
DESIGN DECISION: WHY ENGLISH ONLY?
=============================================================================

The back side content is intentionally kept in English because:

1. LEGAL ACCURACY - Constitutional rights language must be precise
2. OFFICER UNDERSTANDING - Law enforcement reads English
3. DUAL-LANGUAGE DESIGN - Front is translated, back is universal
4. SIMPLICITY - Avoiding translation of legal terminology

The card design is:
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

=============================================================================
CONTENT SOURCE
=============================================================================

The back content is based on standard "Know Your Rights" card text that
explains constitutional protections:

- 5th Amendment: Right to remain silent
- 4th Amendment: Protection against unreasonable search/entry
- Universal applicability: Citizens and non-citizens

=============================================================================
USAGE IN PDF RENDERING
=============================================================================

The content is used by:

    main.py render_pdf():
        payload = {
            "front": item.get("front", {}),        # Translated content
            "back": get_back_content(item["code"]) # English content
        }
        pdf_bytes = render_print_sheet_pdf(payload, layout)

    pdf_renderer.py:
        _draw_back_card(canvas, payload["back"]["paragraphs"], ...)

=============================================================================
FUTURE ENHANCEMENT
=============================================================================

The language_code parameter is included for future support of:
- Localized back content for specific languages
- Multiple back content variants (detailed vs. concise)
- Region-specific legal information

=============================================================================
"""

from typing import Dict, List, Any


# =============================================================================
# DEFAULT BACK CONTENT
# =============================================================================
# These paragraphs appear on the back of every card, in English.
# They explain the constitutional rights the cardholder wishes to exercise.

DEFAULT_BACK_PARAGRAPHS = [
    # Paragraph 1: 5th Amendment - Right to remain silent
    "I do not wish to speak with you, answer your questions, or sign or hand "
    "you any documents based on my 5th Amendment rights under the United "
    "States Constitution.",

    # Paragraph 2: 4th Amendment - Home entry protection
    "I do not give you permission to enter my home based on my 4th Amendment "
    "rights under the United States Constitution unless you have a warrant to "
    "enter, signed by a judge or magistrate with my name on it that you slide "
    "under the door.",

    # Paragraph 3: 4th Amendment - Search protection
    "I do not give you permission to search any of my belongings based on my "
    "4th Amendment rights.",

    # Paragraph 4: Rights assertion statement
    "I choose to exercise my constitutional rights.",

    # Paragraph 5: Universal applicability notice
    "These cards are available to citizens and noncitizens alike."
]


# =============================================================================
# PUBLIC API
# =============================================================================

def get_back_content(language_code: str = None) -> Dict[str, Any]:
    """
    Get back-side content for cards as a dictionary.

    Returns the constitutional rights paragraphs in a format suitable
    for the CardPayload and PDF renderer.

    PARAMETERS:
        language_code: Optional language code (reserved for future use)
                       Currently ignored - always returns English content

    RETURNS:
        Dictionary with structure:
        {
            "paragraphs": [
                "I do not wish to speak with you...",
                "I do not give you permission to enter...",
                ...
            ]
        }

    USAGE:
        # In main.py render_pdf():
        payload = {
            "front": item.get("front", {}),
            "back": get_back_content(item["code"])
        }

    NOTE:
        Returns a copy of the list to prevent accidental modification
        of the module-level constant.
    """
    # TODO: Add support for localized back content in the future
    # Could check language_code and return translated content if available
    return {
        "paragraphs": DEFAULT_BACK_PARAGRAPHS.copy()
    }


def get_back_paragraphs(language_code: str = None) -> List[str]:
    """
    Get back-side paragraphs as a simple list.

    Convenience function that returns just the paragraph strings
    without the dictionary wrapper.

    PARAMETERS:
        language_code: Optional language code (reserved for future use)
                       Currently ignored - always returns English content

    RETURNS:
        List of paragraph strings:
        [
            "I do not wish to speak with you...",
            "I do not give you permission to enter...",
            ...
        ]

    USAGE:
        paragraphs = get_back_paragraphs()
        for p in paragraphs:
            canvas.drawString(x, y, p)
            y -= line_height

    NOTE:
        Returns a copy of the list to prevent accidental modification
        of the module-level constant.
    """
    return DEFAULT_BACK_PARAGRAPHS.copy()
