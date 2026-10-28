# Red Card API

A FastAPI service that renders printable "Know Your Rights" red cards as PDFs in 59 languages. It also serves the card text and print options as JSON.

- **Frontend:** [redcardapi-frontend](https://github.com/pierre-projects/redcardapi-frontend). The frontend bundles the card text, so it can show cards without this API. The API is needed for PDF downloads.
- **Translations:** sourced from the Immigrant Legal Resource Center (ILRC), who created the original red cards.

## Quick start

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt          # Windows: .venv\Scripts\pip
.venv/bin/uvicorn app.main:app --reload            # http://localhost:8000/docs
```

With Docker:

```bash
docker build -t redcardapi .
docker run -p 8000:8000 -e CARD_ENVIRONMENT=production \
  -e CARD_CORS_ORIGINS='["https://cards.example.org"]' redcardapi
```

## API

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Liveness. Always 200 while the process is up: `{ok, languages_loaded}` |
| `GET /api/ready` | Readiness. 503 until fonts are registered (about 1–3 s after start), then 200 |
| `GET /api/config` | Print options: `valid_layouts`, `fold_layouts`, defaults, `page_size`, `render_modes` (`grid`, `fold`) |
| `GET /api/languages` | `[{code, name, native, rtl, official, fontSupported, source}]`. `native` is the language's own name, e.g. "Español". Returns 503 while starting. |
| `GET /api/card/{code}` | `{code, name, native, rtl, official, front: {header, bullets: [{id, text}]}, source}` |
| `GET /api/render/{code}?mode=grid\|fold&cards_per_page=N` | PDF download (see below) |

Codes are case-insensitive (`zh-CN` = `zh-cn`).

**Render modes:**
- `grid` puts 4, 6, 8 or 12 cards per page: fronts on page 1, backs on page 2, for duplex printing.
- `fold` puts 4, 5 or 6 rows on one page, each row front | back, to fold down the middle.

An invalid `mode` or `cards_per_page` returns 422.

**Errors** always have the shape `{detail, code}`:

| Status | `code` | Notes |
|---|---|---|
| 404 | `language_not_found` | |
| 422 | `invalid_request` | |
| 400 | `font_not_available` | Also includes `error_type`, `script` and `language` |
| 429 | `rate_limited` | Sent with a `Retry-After` header |
| 503 | `not_ready` / `render_timeout` | |
| 500 | `render_failed` / `internal_error` | Internal details are logged, never returned |

**Caching:** JSON responses send `Cache-Control: public, max-age=300`, and PDFs `max-age=3600`. Rendered PDFs are also cached in memory, and cached PDFs don't count toward the rate limit.

## Configuration

All settings are `CARD_*` environment variables, or a `.env` file in the project root. `.env.example` lists every setting with its default. The ones that matter in production:

- `CARD_ENVIRONMENT=production`: refuses to start if `CARD_CORS_ORIGINS` only allows localhost or `*`.
- `CARD_CORS_ORIGINS`: a JSON list, e.g. `'["https://cards.example.org"]'`.
- `CARD_RENDER_RATE_LIMIT_PER_MINUTE` (default 20), `CARD_RENDER_TIMEOUT_SECONDS` (30), `CARD_RENDER_WORKERS` (2).

## Deployment notes

- **Run behind a proxy with `--proxy-headers --forwarded-allow-ips=...`.** The Dockerfile and Procfile already do. Without it, every client appears as the proxy's address and shares one rate-limit bucket.
- **Use one worker per container.** Fonts take about 150 MB, and the PDF cache and rate limiter are in memory per process. Scale by adding containers. PDFs are deterministic and cacheable, so a CDN in front absorbs repeat downloads.
- **Point the container healthcheck at `/api/ready`.** Use `/api/health` for liveness.

## How rendering works

```text
app/
  main.py            create_app(): settings checks, data load, middleware, error handlers
  config.py          Settings (CARD_* variables)
  data.py            Translations schema and TranslationStore (validated at startup)
  exceptions.py      domain errors → HTTP status and {detail, code}
  layout.py          sheet geometry; GRID_LAYOUTS and FOLD_ROWS are the only list of valid layouts
  api/               routes, response schemas, per-app state, PDF cache and rate limiter
  fonts/             language → script → Noto font; registration at startup
  text/              shaping (HarfBuzz), right-to-left run ordering, line wrapping
  pdf/               plan text once per sheet, draw it into every card, page guides
scripts/             validate_translations, render_review
tests/               API, data, fonts (glyph coverage), text, rendering, data quality
```

A render goes through four steps:

1. **Pick the font.** The language code maps to a script, and the script to a Noto font (`app/fonts`).
2. **Plan the front and back once per sheet.** Wrapping is tried at different text scales, and a binary search finds the largest that fits the card (`app/pdf/fitting.py`).
3. **Shape and wrap the text.**
   - Arabic-script text (Arabic, Farsi, Dari, Pashto, Urdu), Devanagari, Bengali, Tamil, Gurmukhi, Thai, Lao, Khmer and Myanmar are shaped with HarfBuzz (`uharfbuzz`), and their widths are measured from the shaped glyphs.
   - Right-to-left text is wrapped in logical order; each line's runs are then laid out right to left (Hebrew lines are reordered with python-bidi).
   - Lines break at spaces, or between characters for CJK, and never inside a letter cluster.
4. **Draw the planned lines** into every card position.

## Development

```bash
pip install -r requirements.txt -r requirements-dev.txt
ruff check .
pytest                                     # ~100 tests, ~20 s; renders every language
python -m scripts.validate_translations    # schema, glyph coverage, corruption heuristics
python -m scripts.render_review --mode fold hi ar km   # visual check → review.pdf
```

Dependencies are pinned in `requirements.txt`, compiled from `requirements.in` with `pip-compile`. Edit the `.in` files, then recompile. See `CONTRIBUTING.md` for how to change translations.

## Known issues

- **Four translations need native-speaker review.** Khmer, Tamil and Pashto were reconstructed from ILRC artwork that is itself badly typeset (the Khmer card is also cut off at the end; the Pashto card omits two words). Sudanese Arabic was transcribed by eye because its PDF text layer is scrambled, and the artwork's header is missing its first letter. They are marked `"verified": false` with a `review_note` in the data, the API returns that note, and `python -m scripts.validate_translations` lists them. Arabic, Farsi, Dari and Marshallese were corrected against clean ILRC artwork.
- **The font files are large.** `assets/fonts` is about 60 MB, 58 MB of it CJK fonts used by five languages. Subsetting those fonts to the characters the cards use would cut this to a few MB. If the repo grows, Git LFS is the other option. Either way, check that the deploy platform fetches the real font files.

## License

MIT. See `LICENSE`. The translations are from ILRC (https://www.ilrc.org/red-cards).
