# Contributing to RedCardGenerator Backend

Thank you for your interest in contributing! This project generates "Know Your
Rights" red cards in multiple languages to help people understand their rights.

## Attribution (Required)

The 56 language translations were sourced from the Immigration Legal Resource
Center (ILRC), who created the original red cards. Any contributions that
touch translation content must preserve this attribution and may not
misrepresent ILRC's role.

## How to Contribute

### Reporting Issues

- Bug reports: Steps to reproduce, expected vs actual behavior, environment
- Feature requests: Use case, why it matters, expected impact
- Translation issues: Language code, exact text, and the correction

### Pull Requests

1. Fork the repo and create a feature branch
2. Make your changes following the guidelines below
3. Run tests and include results in the PR description
4. Update documentation if behavior changes
5. Submit a PR with a clear description of what and why

## Project-Specific Guidelines

### Translations (ILRC-sourced)

- Do not remove ILRC attribution
- Ensure legal meaning is preserved
- Keep formatting consistent (header + bullet list)
- If adding a new language, include translation source in
  `Translations_with_sources.json`

### Fonts

- If a language renders blank/broken, add the required Noto Sans font files
  to `assets/fonts/` (Regular + Bold)
- Update `app/fonts/font_config.py` and `app/fonts/script_detector.py` as needed

### PDF Rendering

- Verify changes across multiple scripts (Latin, RTL, CJK)
- Run `python dev/test_all_languages.py` and check the output PDF

## Testing

- `pytest tests/`
- `python test_font_coverage.py`
- `python dev/test_all_languages.py`

## Code Style

- PEP 8, type hints, and clear docstrings
- Avoid non-ASCII unless required for translation content

## Commit Messages

- Use imperative verbs: Add, Fix, Update, Remove
- Reference issues if relevant
