"""
Translations Store - Flexible JSON parser for multi-language card content.

=============================================================================
MODULE OVERVIEW
=============================================================================

This module handles loading and parsing the Translations.json file, which
contains card content in multiple languages. The parser is designed to be
FLEXIBLE and handle various JSON structures that might be exported from
different sources (spreadsheets, CMS, manual editing, etc.).

=============================================================================
SUPPORTED JSON STRUCTURES
=============================================================================

The parser can handle all of these formats:

1. TOP-LEVEL LIST:
   [
       {"code": "en", "name": "English", "front": {...}},
       {"code": "es", "name": "Spanish", "front": {...}}
   ]

2. DICT WITH "languages" KEY (list):
   {
       "languages": [
           {"code": "en", "name": "English", "front": {...}},
           {"code": "es", "name": "Spanish", "front": {...}}
       ]
   }

3. DICT WITH "languages" KEY (dict/map):
   {
       "languages": {
           "en": {"name": "English", "front": {...}},
           "es": {"name": "Spanish", "front": {...}}
       }
   }

4. NESTED STRUCTURES:
   The parser will recursively search for language data up to 6 levels deep.

=============================================================================
FIELD NAME FLEXIBILITY
=============================================================================

The parser accepts multiple variations of field names:

- Language code: "code", "lang", "lang_code", "languageCode", "language_code"
- Language name: "name", "language", "languageName", "language_name", "label"
- RTL flag: "rtl", "is_rtl", "rightToLeft", "right_to_left"
- Front content: "front", "Front", "content", "Content", "card_front", etc.

=============================================================================
DATA FLOW
=============================================================================

1. TranslationsStore.__init__(path)  -> Store path, initialize empty state
2. TranslationsStore.load()          -> Read JSON file from disk
3. TranslationsStore._normalize()    -> Parse and normalize all entries
4. TranslationsStore.list_languages() -> Return all languages as list
5. TranslationsStore.get_language(code) -> Look up single language by code

=============================================================================
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple


# =============================================================================
# FLEXIBLE FIELD NAME MAPPINGS
# =============================================================================
# These tuples define the various field names we'll accept for each concept.
# This allows the parser to work with JSON exported from different sources.

# Keys that indicate a container of languages (for nested structures)
KNOWN_LANG_KEYS = {"languages", "language", "langs", "translations", "cards"}

# Possible field names for the language code (e.g., "en", "es", "zh-CN")
CODE_KEYS = ("code", "lang", "lang_code", "languageCode", "language_code")

# Possible field names for the display name (e.g., "English", "Spanish")
NAME_KEYS = ("name", "language", "languageName", "language_name", "label")

# Possible field names for right-to-left flag
RTL_KEYS = ("rtl", "is_rtl", "rightToLeft", "right_to_left")

# Possible field names for front card content
FRONT_KEYS = ("front", "Front", "content", "Content", "card_front", "cardFront", "text")

# Possible field names for source/attribution information
SOURCE_KEYS = ("source", "Source", "attribution", "Attribution", "origin", "Origin")


# =============================================================================
# HELPER FUNCTIONS FOR FLEXIBLE FIELD ACCESS
# =============================================================================

def _first_str(d: Dict[str, Any], keys: Tuple[str, ...]) -> str:
    """
    Find the first non-empty string value from a dict using multiple possible keys.

    This allows us to accept various field names for the same concept.

    EXAMPLE:
        d = {"languageCode": "en", "label": "English"}
        _first_str(d, CODE_KEYS)  # Returns "en"
        _first_str(d, NAME_KEYS)  # Returns "English"

    PARAMETERS:
        d: Dictionary to search
        keys: Tuple of possible key names to try, in order

    RETURNS:
        First non-empty string found, or empty string if none found
    """
    for k in keys:
        v = d.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def _first_bool(d: Dict[str, Any], keys: Tuple[str, ...], default: bool = False) -> bool:
    """
    Find the first boolean value from a dict using multiple possible keys.

    Handles both actual booleans and string representations like "true"/"false".

    EXAMPLE:
        d = {"is_rtl": True}
        _first_bool(d, RTL_KEYS)  # Returns True

        d = {"rtl": "yes"}
        _first_bool(d, RTL_KEYS)  # Returns True

    PARAMETERS:
        d: Dictionary to search
        keys: Tuple of possible key names to try
        default: Value to return if no match found

    RETURNS:
        Boolean value, or default if not found
    """
    for k in keys:
        v = d.get(k)
        # Direct boolean
        if isinstance(v, bool):
            return v
        # String representation
        if isinstance(v, str):
            s = v.strip().lower()
            if s in ("true", "1", "yes"):
                return True
            if s in ("false", "0", "no"):
                return False
    return default


def _first_obj(d: Dict[str, Any], keys: Tuple[str, ...]) -> Any:
    """
    Find the first object/dict value from a dict using multiple possible keys.

    Used to find the front content, which might be under different key names.

    EXAMPLE:
        d = {"content": {"header": "KNOW YOUR RIGHTS", "bullets": [...]}}
        _first_obj(d, FRONT_KEYS)  # Returns the content dict

    PARAMETERS:
        d: Dictionary to search
        keys: Tuple of possible key names to try

    RETURNS:
        First found value (any type), or empty dict if not found
    """
    for k in keys:
        if k in d:
            return d[k]
    return {}


def _looks_like_lang_item(x: Any) -> bool:
    """
    Heuristic check: Does this dict look like a language entry?

    Used during recursive search to identify candidate language lists.
    An item "looks like" a language if it has:
    - A language code, AND
    - Either a name OR front content

    EXAMPLE:
        _looks_like_lang_item({"code": "en", "name": "English"})  # True
        _looks_like_lang_item({"foo": "bar"})  # False

    PARAMETERS:
        x: Any value to check

    RETURNS:
        True if this looks like a language entry
    """
    if not isinstance(x, dict):
        return False

    code = _first_str(x, CODE_KEYS)
    name = _first_str(x, NAME_KEYS)
    front = _first_obj(x, FRONT_KEYS)

    # Must have a code, and either a name or front content
    return bool(code) and (bool(name) or isinstance(front, (dict, str, list)))


def _flatten_lang_map(m: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Convert a dict-based language map to a list format.

    Some JSON exports use the language code as the key:
        {"en": {"name": "English"}, "es": {"name": "Spanish"}}

    This converts it to our standard list format:
        [{"code": "en", "name": "English"}, {"code": "es", "name": "Spanish"}]

    PARAMETERS:
        m: Dictionary where keys are language codes

    RETURNS:
        List of dicts with "code" field added
    """
    out = []
    for k, v in m.items():
        if isinstance(v, dict):
            # Copy the dict and add the code if not present
            item = dict(v)
            item.setdefault("code", k)
            out.append(item)
    return out


def _find_candidate_lists(obj: Any, max_depth: int = 6) -> List[List[Dict[str, Any]]]:
    """
    Recursively search for lists of dicts that look like language entries.

    This is the fallback parser for unusual JSON structures. It walks the
    entire JSON tree looking for arrays that contain language-like objects.

    ALGORITHM:
    1. Walk the JSON tree recursively (up to max_depth)
    2. When we find a list of dicts, score it by how many items look like languages
    3. If enough items match (at least 2, or 1/3 of the list), add to candidates
    4. Prioritize known keys ("languages", "translations", etc.) when walking

    PARAMETERS:
        obj: The JSON object to search
        max_depth: Maximum recursion depth (prevents infinite loops)

    RETURNS:
        List of candidate language lists found
    """
    found: List[List[Dict[str, Any]]] = []

    def walk(o: Any, depth: int):
        """Recursive walker function."""
        if depth > max_depth:
            return

        if isinstance(o, list):
            # Check if this list contains language-like dicts
            dicts = [x for x in o if isinstance(x, dict)]
            if dicts:
                # Score: how many items look like language entries?
                score = sum(1 for x in dicts if _looks_like_lang_item(x))
                # Threshold: at least 2 matches, or at least 1/3 of the list
                if score >= max(2, len(dicts) // 3):
                    found.append(dicts)

            # Continue searching within list items
            for x in o:
                walk(x, depth + 1)

        elif isinstance(o, dict):
            # Prioritize known language container keys first
            for k, v in o.items():
                if isinstance(k, str) and k.strip().lower() in KNOWN_LANG_KEYS:
                    walk(v, depth + 1)

            # Then walk all other values
            for v in o.values():
                walk(v, depth + 1)

    walk(obj, 0)
    return found


# =============================================================================
# TRANSLATIONS STORE CLASS
# =============================================================================

class TranslationsStore:
    """
    Loads and provides access to multi-language card translations.

    This class handles:
    - Loading JSON from disk
    - Parsing various JSON structures (see module docstring)
    - Normalizing field names to a consistent format
    - Providing lookup by language code

    USAGE:
        store = TranslationsStore(Path("Translations.json"))
        store.load()

        # Get all languages
        for lang in store.list_languages():
            print(f"{lang['code']}: {lang['name']}")

        # Look up single language
        spanish = store.get_language("es")
        print(spanish["front"]["header"])

    NORMALIZED FORMAT:
        Each language item is normalized to:
        {
            "code": "en",           # ISO language code (lowercase)
            "name": "English",      # Display name
            "rtl": false,           # Right-to-left flag
            "official": true,       # Official translation flag
            "front": {              # Front card content
                "header": "KNOW YOUR RIGHTS",
                "bullets": ["Point 1", "Point 2", ...]
            },
            "source": {             # Optional source/attribution info
                "type": "official",
                "origin": "ILRC",
                "url": "https://...",
                "verified": true
            }
        }
    """

    def __init__(self, json_path: Path):
        """
        Initialize the store with path to JSON file.

        Does NOT load the file - call load() separately.

        PARAMETERS:
            json_path: Path to Translations.json file
        """
        self.json_path = json_path

        # Raw JSON data (set by load())
        self._raw: Any = None

        # Normalized list of all languages
        self._languages: List[Dict[str, Any]] = []

        # Lookup dict: lowercase code -> language dict
        self._by_code: Dict[str, Dict[str, Any]] = {}

    def load(self) -> None:
        """
        Load and parse the JSON file.

        FLOW:
        1. Check if file exists (raise FileNotFoundError if not)
        2. Read and parse JSON
        3. Call _normalize() to parse into standard format

        RAISES:
            FileNotFoundError: If JSON file doesn't exist
            json.JSONDecodeError: If JSON is invalid
            ValueError: If no languages could be parsed
        """
        # Check file exists
        if not self.json_path.exists():
            raise FileNotFoundError(f"Translations JSON not found at: {self.json_path}")

        # Read and parse JSON
        self._raw = json.loads(self.json_path.read_text(encoding="utf-8"))

        # Normalize into standard format
        self._normalize()

    def _normalize(self) -> None:
        """
        Parse raw JSON into normalized language list.

        This is the main parsing logic that handles various JSON structures.

        PARSING STRATEGY (in order of priority):

        1. TOP-LEVEL LIST
           If raw JSON is a list, use it directly

        2. KNOWN CONTAINER KEY
           Look for keys like "languages", "translations", etc.
           Handle both list and dict values

        3. RECURSIVE SEARCH
           Walk the entire tree looking for language-like arrays
           Pick the best candidate based on scoring

        After finding the raw list, each item is normalized to our standard
        format with consistent field names.

        RAISES:
            ValueError: If no languages found or no valid codes
        """
        raw = self._raw
        langs: Optional[List[Dict[str, Any]]] = None

        # === STRATEGY 1: Top-level list ===
        if isinstance(raw, list):
            langs = [x for x in raw if isinstance(x, dict)]

        # === STRATEGY 2: Known container key ===
        if langs is None and isinstance(raw, dict):
            # Look for known keys (case-insensitive)
            for k in list(raw.keys()):
                if isinstance(k, str) and k.strip().lower() in KNOWN_LANG_KEYS:
                    v = raw[k]
                    if isinstance(v, list):
                        # List of language objects
                        langs = [x for x in v if isinstance(x, dict)]
                        break
                    if isinstance(v, dict):
                        # Dict with code as key: {"en": {...}, "es": {...}}
                        langs = _flatten_lang_map(v)
                        break

            # Also try exact "languages" key if not found above
            if langs is None and "languages" in raw:
                v = raw["languages"]
                if isinstance(v, list):
                    langs = [x for x in v if isinstance(x, dict)]
                elif isinstance(v, dict):
                    langs = _flatten_lang_map(v)

        # === STRATEGY 3: Recursive search fallback ===
        if langs is None:
            candidates = _find_candidate_lists(raw)
            if candidates:
                # Pick best candidate by scoring
                # Score = (matching items, total items)
                def rank(lst: List[Dict[str, Any]]) -> Tuple[int, int]:
                    return (
                        sum(1 for x in lst if _looks_like_lang_item(x)),
                        len(lst),
                    )
                candidates.sort(key=rank, reverse=True)
                langs = candidates[0]

        # === Validate we found something ===
        if not langs:
            # Provide helpful error message
            top_keys = list(raw.keys()) if isinstance(raw, dict) else f"type={type(raw)}"
            raise ValueError(
                "Could not locate a languages list in Translations.json. "
                f"Top-level keys/type seen: {top_keys}"
            )

        # === Normalize each language item ===
        normalized: List[Dict[str, Any]] = []

        for item in langs:
            if not isinstance(item, dict):
                continue

            # Extract fields using flexible key matching
            code = _first_str(item, CODE_KEYS)
            name = _first_str(item, NAME_KEYS) or code  # Fall back to code if no name
            rtl = _first_bool(item, RTL_KEYS, default=False)
            front = _first_obj(item, FRONT_KEYS)
            source = _first_obj(item, SOURCE_KEYS)

            # Normalize front content to dict format
            if isinstance(front, str):
                # Plain string -> wrap in dict
                front_obj: Dict[str, Any] = {"text": front}
            elif isinstance(front, dict):
                # Already a dict -> use as-is
                front_obj = front
            else:
                # Other type -> wrap in dict
                front_obj = {"value": front}

            # Normalize source to dict format (or None if not present)
            source_obj: Optional[Dict[str, Any]] = None
            if isinstance(source, dict) and source:
                source_obj = {
                    "type": source.get("type", "unknown"),
                    "origin": source.get("origin", "unknown"),
                    "url": source.get("url"),
                    "verified": bool(source.get("verified", False)),
                }

            # Skip items without a code
            if not code:
                continue

            # Add normalized item
            normalized.append({
                "code": code,
                "name": name,
                "rtl": rtl,
                "official": True,  # Assume all loaded translations are official
                "front": front_obj,
                "source": source_obj,
            })

        # === Validate we got at least one valid language ===
        if not normalized:
            raise ValueError(
                "Found a candidate languages list, but none of the items contained "
                "a usable language 'code'. Check Translations.json structure."
            )

        # === Store normalized data ===
        self._languages = normalized

        # Build lookup dict with lowercase codes for case-insensitive matching
        self._by_code = {x["code"].lower(): x for x in normalized}

    def list_languages(self) -> List[Dict[str, Any]]:
        """
        Get all available languages.

        RETURNS:
            List of language dicts (copies, safe to modify)

        EXAMPLE:
            for lang in store.list_languages():
                print(f"{lang['code']}: {lang['name']}")
        """
        return list(self._languages)

    def get_language(self, code: str) -> Optional[Dict[str, Any]]:
        """
        Look up a language by its code.

        Lookup is case-insensitive: "EN", "en", "En" all match.

        PARAMETERS:
            code: Language code (e.g., "en", "es", "zh-CN")

        RETURNS:
            Language dict if found, None if not found

        EXAMPLE:
            spanish = store.get_language("es")
            if spanish:
                print(spanish["front"]["header"])
        """
        return self._by_code.get((code or "").lower())
