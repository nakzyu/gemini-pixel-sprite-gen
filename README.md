# sprite-gen

Claude Code plugin for generating and managing 2D game sprites using Google Gemini.

Uses Gemini's image generation via subscription-based browser cookie authentication (`gemini_webapi`), not API keys.

## Requirements

- Python 3.10+
- Google Gemini subscription (must be logged in to gemini.google.com in your browser)
- Chrome or Firefox

## Installation

```bash
/plugin marketplace add nakzyu/sprite-gen
/plugin install sprite-gen@sprite-gen
```

Or for local development:

```bash
git clone https://github.com/nakzyu/sprite-gen.git
claude --plugin-dir ./sprite-gen
```

Dependencies (`gemini_webapi[browser]`, `Pillow`) are auto-installed on first run.

## Usage

### Generate a sprite

```
/sprite-gen warrior character 32px
```

If the request is vague, it will ask about style, view angle, purpose, etc.
If detailed enough, it generates immediately.

```
/sprite-gen 16-bit RPG warrior, front-facing, Final Fantasy style, 32px
```

### Style consistency (multi-turn sessions)

When generating related sprites (same character, variations, iterations), the plugin automatically maintains a Gemini conversation session. This means Gemini remembers the art style, palette, and design from previous generations.

```
/sprite-gen cute slime character for a platformer
```
→ (generates slime, asks if you like it)

```
/sprite-gen make the same slime but jumping
```
→ (generates in the same session — consistent style)

```
/sprite-gen now a walking animation version
```
→ (still same session — same slime design)

No manual session management needed. Claude automatically detects when requests are related and maintains context.

### Resume previous work

Come back later and pick up where you left off:

```
/sprite-gen what was I working on?
```
→ (shows list of previous sessions with sprites generated in each)

```
/sprite-gen continue the warrior
```
→ (resumes the warrior session with full Gemini context — style stays consistent)

### Generate a sprite sheet

```
/sprite-gen warrior walk cycle, 4 frames, sprite sheet
```

Uses an anchor-frame method: generates the first frame, gets approval, then generates remaining frames in the same Gemini session for style consistency.

### List sprites

```
/sprite-gen list
/sprite-gen list --category character
```

### Delete a sprite

```
/sprite-gen delete warrior
```

### Organize (remove orphaned manifest entries)

```
/sprite-gen organize
```

## Workflow

```
Request → (if vague) Questions → Creative brief → Gemini prompt → Generate → Validate → Iterate
```

1. **Understand**: Analyze the request. Ask 2-3 questions if key details are missing
2. **Brief**: For complex requests, write a 2-3 line creative brief
3. **Prompt**: Translate user intent into an English prompt for Gemini (constructed by Claude)
4. **Generate**: Send prompt to Gemini, save the image
5. **Validate**: Display result, suggest regeneration if it doesn't match intent
6. **Iterate**: Apply adjustments based on user feedback (using same session for consistency)

## Options

| Option | Values | Default |
|--------|--------|---------|
| size | 16, 32, 64, 128 | 32 |
| category | character, item, tile, effect, ui | character |

## Project Structure

```
sprite-gen/
├── .claude-plugin/
│   └── marketplace.json        # Plugin manifest
├── skills/
│   └── sprite-gen/
│       ├── SKILL.md            # Skill definition (workflow)
│       └── scripts/
│           └── sprite_gen.py   # Gemini call script
├── .gitignore
├── LICENSE
└── README.md
```

## How It Works

- **SKILL.md**: Claude's workflow instructions. All logic for questioning, prompt construction, session management, and validation lives here
- **sprite_gen.py**: A dumb pipe — calls Gemini API, saves images, manages the manifest and sessions
- **Prompt construction**: Claude interprets user intent and crafts the Gemini prompt directly. The script adds nothing to the prompt
- **Multi-turn sessions**: When generating related sprites, the script maintains Gemini conversation context via `gemini_webapi`'s ChatSession. Claude automatically decides when to use the same session for style consistency

## License

MIT
