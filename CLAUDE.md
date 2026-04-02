# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Claude Code plugin that generates 2D game sprites via Google Gemini's image generation. Uses browser cookie authentication (`gemini_webapi`), not API keys. Requires an active Google Gemini subscription.

## Development

```bash
# Test the plugin locally
claude --plugin-dir ./

# Then invoke with
/sprite-gen <prompt>

# Install dependencies manually (normally auto-installed on first run)
pip install -r skills/sprite-gen/scripts/requirements.txt
```

No build step. No tests. Single Python script.

## Architecture

**SKILL.md is the brain, sprite_gen.py is a dumb pipe.** Claude reads SKILL.md for workflow instructions, constructs all prompts, and makes all creative decisions. The Python script only: sends prompts to Gemini, saves images, manages manifest/sessions. This split is intentional — don't move prompt logic into the script.

### Key flows in sprite_gen.py

- **Cookie auth**: `GeminiClient()` auto-extracts cookies from Chrome/Firefox. `create_client()` detects `UNAUTHENTICATED` status and auto-clears cached cookies (`/tmp/gemini_webapi/.cached_cookies_*.json`) to retry with fresh ones.
- **Multi-turn sessions**: `client.start_chat(metadata=saved["metadata"])` restores Gemini conversation context. Sessions are stored as JSON in `<output_dir>/.sessions/`. This is how style consistency works across multiple sprite generations.
- **Image URL fallback**: When `gemini_webapi` fails to parse the image from the response, regex extracts `googleusercontent.com` URLs from response text and downloads directly via `curl_cffi`.
- **Watermark removal**: Reverse alpha blending using pre-extracted alpha maps in `watermark_alpha.json`. Not inpainting, not flat fill — mathematically restores original pixels. Two sizes: 48x48 (images <= 1024px) and 96x96 (images > 1024px).
- **DELAY_FACTOR monkey-patch**: `gemini_webapi.utils.decorators.DELAY_FACTOR = 3` reduces stream reconnection delays during image generation (default 5 wastes ~75s on retries).

### Data layout (at runtime, in user's output_dir)

- `<category>/<category>_<name>_<timestamp>.png` — generated sprites
- `manifest.json` — index of all sprites
- `.sessions/<name>.json` — Gemini chat session metadata + history

## Conventions

- Keep `sprite_gen.py` as a single file — no splitting into modules
- kebab-case for plugin/skill names, snake_case for Python
- All data serialization is JSON
- Dependencies in `skills/sprite-gen/scripts/requirements.txt` (auto-installed via `_ensure_dependencies()`)
- `gemini_webapi` must be installed from GitHub master branch (not PyPI) for native curl-cffi support
