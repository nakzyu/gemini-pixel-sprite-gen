# gemini-sprite-gen

Claude Code plugin that provides a `/gemini-sprite-gen` skill for generating and managing 2D game sprites using Google Gemini.

Uses Gemini's image generation via browser cookie authentication ([`gemini_webapi`](https://github.com/HanaokaYuzu/Gemini-API)), not API keys. Install the plugin and the skill handles everything — prompt crafting, session management, and image processing.

## Requirements

- Python 3.10+
- Google Gemini subscription (logged in to gemini.google.com in Chrome or Firefox)

## Installation

```bash
/plugin marketplace add nakzyu/gemini-sprite-gen
/plugin install gemini-sprite-gen@gemini-sprite-gen
```

Or for local development:

```bash
git clone https://github.com/nakzyu/gemini-sprite-gen.git
claude --plugin-dir ./gemini-sprite-gen
```

Dependencies are auto-installed on first run via `requirements.txt`.

## Usage

### Generate a sprite

```
/gemini-sprite-gen warrior character
```

If detailed enough, it generates immediately. If vague, it asks 2-3 questions first.

```
/gemini-sprite-gen 16-bit RPG warrior, front-facing, Final Fantasy style
```

### Style consistency (multi-turn sessions)

The plugin uses Gemini's multi-turn conversation to keep sprites consistent. Each subject gets its own session — Gemini remembers the art style, palette, and design from previous turns, so follow-up requests produce visually coherent results without re-describing everything.

```
/gemini-sprite-gen cute slime character for a platformer
```
→ generates slime, starts a new session

```
/gemini-sprite-gen make the same slime but jumping
```
→ same session — Gemini already knows the slime's style

### Resume previous work

Sessions persist across conversations. You can pick up where you left off:

```
/gemini-sprite-gen what was I working on?     ← shows previous sessions
/gemini-sprite-gen continue the warrior       ← resumes with full Gemini context
```

### Sprite sheets

```
/gemini-sprite-gen warrior walk cycle, 4 frames, sprite sheet
```

Generates an anchor frame first for approval, then remaining frames in the same session.

### Reference images

Attach reference images to guide generation — useful for style matching or character conversion:

```
/gemini-sprite-gen convert this character to chibi pixel art [attach image]
/gemini-sprite-gen make this into a 16-bit RPG sprite [attach image]
```

Multiple references work too (e.g. character design + target art style).

### Management

```
/gemini-sprite-gen list
/gemini-sprite-gen list --category character
/gemini-sprite-gen delete warrior
/gemini-sprite-gen organize
```

## Features

- **Gemini Pro model** — uses `gemini-3-pro` (Nano Banana 2) for higher quality image generation
- **Real transparent backgrounds** — Gemini can't output alpha channels natively, so the plugin auto-generates on chromakey green (#00FF00) and removes it via HSV-based detection with despill for clean edges
- **Reference image support** — attach images to guide style, character design, or art direction. When references are provided, prompt text is kept minimal to let the image communicate the style
- **Auto cookie refresh** — detects expired Gemini sessions and reloads cookies from browser automatically
- **Watermark removal** — removes the Gemini sparkle watermark via reverse alpha blending, restoring original pixels with zero artifacts
- **Portable manifest** — sprite paths stored as relative paths for cross-machine compatibility

## How transparency works

Gemini's image generation model always outputs opaque images — it cannot produce PNG alpha channels. When you ask for a "transparent background", it draws a checkerboard pattern instead.

This plugin works around that limitation using the chromakey green screen technique:

1. Every prompt automatically gets a green screen instruction appended (`#00FF00` background)
2. After the image is saved, HSV-based color detection identifies and removes the green background
3. Edge pixels are despilled to remove green color bleed
4. The result is a clean PNG with real transparency

## License

MIT
