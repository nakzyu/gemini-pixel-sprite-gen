---
name: gemini-pixel-sprite-gen
description: Generate chunky low-res pixel-art game sprites with consistent style across a roster (characters/monsters/bosses). Uses Google Gemini for generation + a deterministic snap pipeline. Use for game characters, monsters, sprite sheets, animation frames, pixel-art assets.
user-invocable: true
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
argument-hint: "[what to generate, or: list / delete / organize]"
---

# Pixel Sprite Generator

You generate and manage 2D game sprites via Google Gemini (browser cookie auth, `gemini_webapi`).
The Python script at `${CLAUDE_SKILL_DIR}/scripts/sprite_gen.py` is a dumb pipe — it sends your prompt to Gemini and saves the result. **You are the creative brain.**

All parameters (`--name`, `--category`, `--session`) are decided by you based on context. The user never needs to specify these directly.

## Prerequisites & Installation

- **Python**: 3.10+
- **Dependencies**: `pip install -r requirements.txt` (requires `gemini_webapi>=2.1.1`, `Pillow`, `numpy`, `scipy`, `curl_cffi`, `browser_cookie3`)
- **Authentication**: Logged into [gemini.google.com](https://gemini.google.com) in Google Chrome or Firefox on the local machine.
- **Multi-Account**: if several Google accounts are signed into Chrome, set `GEMINI_ACCOUNT=you@example.com` or put the email on the first line of `~/.config/gemini-pixel-sprite-gen/account` (local file, never committed). The script auto-routes requests and download URLs (`authuser=N`). Unset = browser's default account.
- **Auto-upgrade**: `scripts/sprite_gen.py` checks and automatically upgrades dependencies from `requirements.txt` if `gemini_webapi < 2.1.1`.

---


## Auto-Inference Rules

You must infer the following from the user's request. Never ask the user to specify these unless genuinely ambiguous.

### Category
Infer from the subject:
- **character**: people, monsters, creatures, NPCs, enemies, bosses
- **item**: weapons, potions, keys, coins, armor, accessories (equipment ICONS)
- **tile**: ground, walls, water, grass, floor, terrain
- **effect**: explosions, sparkles, fire, smoke, magic, particles
- **ui**: buttons, health bars, menus, ICONS (skill/element/status), cursors, frames
- **background**: full battle/scene backdrops, dungeon vistas, menu backgrounds

This skill does THREE asset families, each with its own post-process (see the
"Asset Types" section): **sprites** (characters/monsters), **icons**
(skill/element/status/item, square + transparent), and **backgrounds** (opaque,
fill the viewport). Pick the category, then follow that family's pipeline.

### Name
- Generate a short, descriptive snake_case name from the subject
- e.g. "cute green slime" → `green_slime`, "fire mage with staff" → `fire_mage`

### Background
- Transparent background is automatic — the script appends chromakey green instructions and removes the green in post-processing. Do NOT mention "transparent background" in your prompt.
- If the user explicitly wants a specific background color/scene, they'll say so.

### Session
- **New subject** (first time generating this character/thing) → start a new session, name it after the subject
- **Same subject as before** (user references previous sprite, asks for variations, adjustments, or related poses) → reuse the existing session
- **Different subject** → end the previous session, start a new one
- **Sprite sheets** → automatically use the sheet name as session
- When in doubt, check active sessions and the manifest to see what was generated recently

---

## Session Resume

When the user wants to continue previous work (e.g. "이전에 뭐했었지?", "resume", "continue", "list sessions"):

1. Run `sessions` command to get full history:
```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/sprite_gen.py" sessions --output-dir "<from config>"
```

2. Present the sessions naturally — show what was generated in each session, with thumbnail previews (Read the latest sprite image from each session)

3. When the user picks a session to resume, use that session name for the next `generate` call. Gemini will have the full conversation context restored.

Example flow:
- User: "이전에 뭐 하고 있었지?"
- You: fetch sessions, show list like:
  - **warrior** (3 sprites) — idle, walk, attack poses. Last: 2h ago
  - **slime** (1 sprite) — green bouncy slime. Last: 1h ago
- User: "전사 이어서 하자"
- You: resume the `warrior` session, generate the next sprite in that context

---

## Generation Workflow

### Phase 1: Understand

Read the user's request:

- **Clear enough** → go straight to Phase 3 (prompt crafting)
- **Vague** (missing critical details that would lead to a bad result) → ask 2-3 questions, conversationally. Pick from:
  - Art style: pixel art, 16bit retro, hand-drawn, anime, chibi, voxel…
  - View: front, side, top-down, isometric, 3/4…
  - Game context: RPG, platformer, roguelike, mobile…
  - Mood/palette: dark, colorful, pastel, limited palette…
  - Reference: any game or image to resemble?

Don't ask about things you can reasonably decide yourself. Only ask when the answer genuinely changes the output.

### Phase 2: Creative Brief (complex requests only)

Skip for simple, single-sprite requests.

For complex requests (sprite sheet, multiple variants, specific art direction), write a 2-3 line brief:

```
Brief: 16-bit JRPG warrior, front-facing idle pose. Dark steel armor with red cape.
       Limited 32-color palette, NES-inspired. Transparent background.
```

Show it, then proceed unless the user objects.

### Phase 3: Craft Prompt

Translate the user's intent into an English prompt for Gemini:

- Include ONLY what the user expressed (directly or through Q&A)
- Be specific and visual
- Add technical constraints at the end: single sprite, background type

**CRITICAL — When reference images are provided:**
- Keep the text prompt SHORT. The reference image already communicates the style — long text descriptions override and conflict with the visual reference.
- BAD: "Generate a HIGH QUALITY DETAILED chibi pixel art with smooth anti-aliased pixels, proper light/shadow shading, rich color palette, at least 128x128 pixels, long flowing blue hair with highlights..."
- GOOD: "Make this character (image 1) into a cute chibi pixel art like image 2. Must match image 2's style exactly. Transparent background."
- Only add text for things the image CAN'T communicate: background type, pose changes, specific corrections from user feedback.
- If the user provides a style reference, trust it. Don't re-describe the style in words.

For follow-ups in an existing session, reference the previous generation naturally:
- "same warrior but in a walking pose, left foot forward"
- "adjust the colors to be darker, keep everything else the same"

### Phase 3.5: Anchor check (HARD GATE)

**Before sending to Gemini for any brand-new subject (a character/item/asset
you have not generated before in this project), an anchor reference image is
REQUIRED.** If you do not have one, STOP and ask the user. Do NOT proceed.

What counts as "an anchor":
- A project-level canonical style reference the user has previously committed
  (saved in memory / repo `references/` dir / earlier in this conversation).
- An image the user pasted into this turn or named explicitly.
- For a *new action of an existing character*, the approved IDLE of that
  character (already in this project) — no asking needed.

What does NOT count:
- "Make it like Octopath Traveler" with no image.
- A vague style description.
- Re-using a different character's idle.

If no anchor is found, ask the user something concrete like:
"I need a style anchor image for this new character/asset. Should I use the
project canonical reference, or do you have a specific image to provide?"

This rule exists because generating without a style anchor produces drifty,
inconsistent output that fails to match the rest of the roster. User has
repeatedly enforced this — do not skip even if "you think you know the style."

### Phase 4: Generate

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/sprite_gen.py" generate "<your crafted prompt>" \
  --output-dir "<from config>" \
  --name <inferred_name> \
  --category <inferred_category> \
  --session <inferred_session> \
  [--files <comma-separated paths>]
```

Use `--files` when the user provides a reference image (e.g. "make this into pixel art", "use this as reference"). Gemini will see the image alongside the text prompt.

### Phase 5: Show Result

1. Display the image with Read tool
2. Present it naturally — describe what was generated
3. If it clearly doesn't match the intent, proactively offer to regenerate with an adjusted prompt
4. Otherwise, let the user respond naturally. Don't list a menu of options.

---

## Pixel Art Pipeline (chunky low-res game style)

When the user asks for **game-ready** pixel-art characters with multiple
actions (idle/attack/walk/hit/death/etc.) for any 2D engine, follow
`${CLAUDE_SKILL_DIR}/PIXEL_ART_PIPELINE.md`. It's the locked-in recipe:

1. **Existing unit?** Read `<project_root>/roster/<unit>.yaml` — pass its
   `anchor_idle` as `--files` and inject `design`+`distinctive` into the prompt.
   **New unit?** Pass the canonical style reference as `--files`.
2. Prompt = deltas only (style + locked design come from the references/roster);
   keep it short — long prose fights the reference image
3. **Gate** the raw output: `${CLAUDE_SKILL_DIR}/scripts/qc_frame.py <raw> --kind idle|action|swing`.
   Hard fail (clip / no transparency) → regenerate before snapping; never show a clipped frame
4. Snap with `${CLAUDE_SKILL_DIR}/scripts/snap_single.py` (default `--target-h 32`,
   lower for bent poses) — outline-preserving mode-downsample
5. Tool artifact is `<char>_<action>.png` in `sprites/sheets/` (no `_1x1`, no
   `_display`). Open via `open <path>` to preview; on approval, **deliver** it to
   the project's configured `delivery_root` (only if `sprite_spec.yaml` defines one)
6. `normalize_sheets.py` is OPTIONAL — run only when the user explicitly wants
   uniform cells; do NOT auto-run (it breaks idle uniformity across the roster)

**Trigger this pipeline when:** user wants pixel-art characters for a 2D
game (any engine — Godot, Unity, Pico-8, raylib, web, etc.), multiple poses
of one character, low-res / RPG-classic / chunky / Octopath / Dead-Cells
style, sprite-sheet animations.

**Skip this (character) pipeline when:** the asset is an ICON or a BACKGROUND
(use the dedicated flows below), a single static illustration, high-res pixel
art, or not for a game engine. Plain `generate` is fine.

Read `${CLAUDE_SKILL_DIR}/PIXEL_ART_PIPELINE.md` before starting the character
pipeline; it covers references, prompt template, h-tuning compare grid,
normalize, engine import, and known failure modes.

### Recommended character workflow (grid 1:1 — supersedes `snap_single.py` for characters)

Gemini draws on a fixed block grid, so the best downscale is no resampling at all:
find the grid and copy one source block → one output pixel. Everything below runs from
`${CLAUDE_SKILL_DIR}/scripts/`; every CLI prints usage when run without args.

1. **Idle = 2 reference images.** `--files base_ref.png,liked_12x.png` where image 1
   is the project's canonical style reference and image 2 is an already-approved
   sprite of the *same family/class* that the user likes, upscaled 12x nearest
   (`python3 -c "from PIL import Image; i=Image.open('a.png'); i.resize((i.width*12,i.height*12),Image.NEAREST).save('a_12x.png')"`).
   The prompt says: copy ONLY image 2's face (eye size/shape, eyebrow row, face width),
   pixel-block size, outline and shading — NOT its outfit, hair or weapon; and keep the
   figure EXACTLY as big as image 2 (state its block height). One reference only →
   the face comes out like a stranger's; `batch_gen.sh` refuses such idle jobs.
2. **Eye spec (right-facing 3/4 view)** — put it in the prompt and check it after:
   one dark eyebrow row directly above the eyes; each eye 2 rows tall; the eye on the
   VIEWER'S LEFT is 2 blocks wide, the VIEWER'S RIGHT eye 1 block wide; 2 skin blocks
   between them; tiny highlight; small eyes, not anime eyes.
3. **Downscale 1:1.** `snap_char.py RAW OUT [--idle] [--monster] [--target-h N --cell-h N]`
   picks the grid period whose block height is closest to the target (default 34
   blocks, monster 64) and runs `native_snap.py` (pass `--idle` so real green colors
   are not despilled; despill is for attack swing trails). `native_snap_half.py` is the
   fallback for raws drawn on a half-block grid (2×2 merge).
4. **Size gate.** Compare the snapped char height with the existing idle of that
   character: accept about **0.85x–1.5x**, regenerate outside that. Also run
   `qc_frame.py RAW --kind idle|action|swing` (clipping/transparency) before snapping.
5. **Zoom before showing.** `face_zoom.py 8 out.png new.png,ref.png` (face window, block
   grid) and `zoom_heads.py 8 14 out.png ...` (top N rows) — compare the face block by
   block against the eye spec before presenting a candidate to the user.
6. **Attacks reuse the idle head.** Generate the attack with `--files idle.png,base_ref.png`
   (pose change only, head front-facing), snap it, then
   `head_swap.py IDLE.png CAND.png OUT.png [--atk CUR_ATTACK.png]` pastes the idle head
   (aligned on face center + chin row) so the face is identical to idle, and recolors
   near-palette body pixels to the idle palette. Modes: default *tight* (clears only the
   pasted head + candidate face box — raised weapons/hair survive); `--box` (candidate
   head much bigger than idle); `--crown` (candidate crown sticks out above the pasted
   head — erases only head/outline colors there); `--imax X` (cut a staff tip etc. that
   is glued to the idle head at column X). Face detection uses the `skin()` color ranges
   at the top of `head_swap.py` — adjust them if your palette's skin tones differ.
7. **Face surgery helpers** (manual, rarely needed): `seam_carve.py` (remove one vertical
   seam, e.g. a 6-block face → 5 without block stamping), `rowdrop.py` (drop one row),
   `eye_transplant.py` (copy an eye block from a reference, remapping skin colors),
   `find_holes.py` / `fill_holes.py` (interior transparent holes).

**Gemini timing & limits.** A healthy generate finishes in ~1–2 min. Over **3 minutes**
= stuck: kill it and retry in a *fresh* session (never wait longer). If the reply
contains the image-limit message (`... limit resets ...`), stop — retries are useless.
Budget about **30–35 images per 5 hours** per account. `gen_retry.sh NAME FILES PROMPT_FILE`
implements both rules (prints `OK <raw>` / `LIMIT`).

**Batch.** `batch_gen.sh WORKDIR` runs `WORKDIR/jobs.json`
(`[{"name","files","kind":"idle|action|swing","monster":bool,"idle":bool}]`, prompt in
`WORKDIR/prompts/<name>.txt`): generate → `qc_frame` → `snap_char` → one row per job in
`WORKDIR/results.tsv` (`name raw qc snap`), snapped files in `WORKDIR/snap/`. Re-running
skips finished rows, so after an image limit just run it again later. Env: `OUT_DIR`
(raw output, default `WORKDIR/raw`), `TIMEOUT_S`, `ATTEMPTS`, `CATEGORY`.

---

## Asset Types

This skill makes three families. Same generator, different prompt framing +
post-process. **Stay in the SAME chunky pixel-art family across all three** —
that consistency is the whole point of using one skill. For sprites, pass the
project style anchor. For icons/backgrounds there is no character anchor, but
keep the chunky low-res, limited-palette, bold-outline language so they read as
the same game.

### A) Sprites (characters / monsters) — the default

Follow the Pixel Art Pipeline above (anchor required, `snap_single.py`,
bottom-center). Nothing changes.

### B) Icons (skill / element / status / item) — square, transparent

Small square pictograms. Transparent subject (do NOT use `--opaque`), so the
generator chromakeys the green out as usual.

1. **Prompt:** one bold, centered, iconic object on a flat green bg. Push
   "SINGLE centered icon, chunky pixel art, thick black outline, bold readable
   silhouette, limited palette, NO text, NO border frame". Element/status icons
   should be instantly legible at tiny size (fire = flame, freeze = ice crystal,
   poison = skull/bubble, bleed = blood drop). Keep it ONE concept — icons read
   by silhouette.
2. **Generate** (transparent, no `--opaque`):
   ```bash
   python3 "${CLAUDE_SKILL_DIR}/scripts/sprite_gen.py" generate "<icon prompt>" \
     --output-dir "<from config>" --name <icon_name> --category ui \
     --session icons   # reuse ONE session so a whole icon set stays consistent
   ```
   Use `--category item` for equipment icons. **Generate an icon SET in one
   session** ("same style, now a lightning bolt", "now an ice crystal") so the
   whole set matches — like a sprite sheet, the first icon is the style anchor.
3. **Snap to a square:**
   ```bash
   python3 "${CLAUDE_SKILL_DIR}/scripts/snap_icon.py" <raw.png> <icon_name> \
     --out-dir sprites/icons --size 32   # 48/64 for larger item icons
   ```
   Centers the art in a `size`×`size` transparent cell, fits the longer side,
   keeps all parts (use `--largest` for a clean single blob). Same
   mode-downsample as sprites → same pixel family.
4. Preview with `open`, then deliver to the project's icon dir
   (`<delivery_root>/icons/<group>/<name>.png`; common groups: `element`,
   `status`, `skill`, `item`). No eye-edit, no QC gate (icons aren't faces).

### C) Backgrounds — opaque, fills the viewport

Full scenes (battle backdrops, dungeon vistas, menu backgrounds). Keep the
generated background — pass `--opaque` so NO chromakey/transparency is applied.

1. **Prompt:** describe the SCENE + mood + palette, framed for the game's aspect
   (e.g. PORTRAIT 360×640 for a phone game). Push "chunky pixel-art background, wide
   establishing scene, atmospheric, cohesive limited palette, NO characters, NO
   UI, NO text". Theme it off the dungeon (forest / goblin camp / mine / swamp /
   abyss …) from the game's own level/zone data.
2. **Generate with `--opaque`:**
   ```bash
   python3 "${CLAUDE_SKILL_DIR}/scripts/sprite_gen.py" generate "<scene prompt>" \
     --output-dir "<from config>" --name <bg_name> --category background \
     --session backgrounds --opaque
   ```
3. **Snap to the viewport (cover-crop + chunk):**
   ```bash
   python3 "${CLAUDE_SKILL_DIR}/scripts/snap_bg.py" <raw.png> <bg_name> \
     --out-dir sprites/backgrounds --size 360x640 --block 2
   ```
   Cover-fits + center-crops to 360×640, then chunks pixels to `block`×`block`
   so it matches the chunky sprites (`--block 1` for smooth, 3-4 for coarser).
4. Preview with `open`, then deliver to `<delivery_root>/backgrounds/<name>.png`.

All three families' native sizes + delivery paths live in
`<project_root>/sprite_spec.yaml` — read it first; it's the source of truth.

## Sprite Sheet Workflow

When generating multiple frames (walk cycle, attack animation, etc.):

1. **Generate the anchor frame first** — this sets the style
2. Show it to the user for approval (this one is worth confirming before committing to multiple frames)
3. **Generate remaining frames in the same session** — Gemini remembers the style
4. Combine into a sheet:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/sprite_gen.py" sheet "<name>" \
  --output-dir "<from config>" \
  --category <category> \
  --frames '<json: [{"name":"idle","description":"..."},{"name":"walk1","description":"..."}]>'
```

The sheet command automatically uses the sheet name as the session.

Describe each frame relative to the anchor:
- Frame 1 (anchor): "16-bit warrior, front-facing idle, dark armor, red cape, pixel art"
- Frame 2: "same warrior, left foot forward, walking pose"
- Frame 3: "same warrior, right foot forward, walking pose"

---

## Management Commands

### List
```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/sprite_gen.py" list --output-dir "<from config>" [--category <cat>]
```
Format output as a readable table.

### Delete
```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/sprite_gen.py" delete "<name>" --output-dir "<from config>"
```

### Organize (remove orphaned manifest entries)
```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/sprite_gen.py" organize --output-dir "<from config>"
```

### Sessions
```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/sprite_gen.py" sessions --output-dir "<from config>"
python3 "${CLAUDE_SKILL_DIR}/scripts/sprite_gen.py" end-session "<name>" --output-dir "<from config>"
```

---

## First Run Setup

Before any command, check if config exists:
```bash
cat "${CLAUDE_PLUGIN_DATA}/config.json" 2>/dev/null
```

If it doesn't exist or fails, run setup:

1. `pip install -r "${CLAUDE_SKILL_DIR}/scripts/requirements.txt"`
2. Ask user: "Where should sprites be saved? (default: `./sprites`)"
3. **Pixel-art project setup (only if user mentioned a game / chunky pixel art / sprite roster)** — if the workflow will use the chunky pixel-art pipeline, also collect:
   a. **Canonical style anchor reference image**: ask "Do you have a reference image to anchor the art style for this project? Provide a path, or I can help you generate one. (This is mandatory — without it, generation drifts and `generate` will refuse to run for new characters/monsters.)" Save the path.
   b. **Project sprite spec**: check if `<project_root>/sprite_spec.yaml` exists. If not, ask "What sprite spec should I use? (defaults: characters target_h=32 cell_h=48, monsters target_h=64 cell_h=72)" and create the file with their values, or use defaults. If it exists, read it and use those values.
4. Save config:
```bash
mkdir -p "${CLAUDE_PLUGIN_DATA}"
cat > "${CLAUDE_PLUGIN_DATA}/config.json" << 'EOF'
{
  "output_dir": "<user's answer>",
  "canonical_anchor": "<path to anchor image, optional>",
  "project_root": "<cwd at setup time, optional>"
}
EOF
```
5. `python3 "${CLAUDE_SKILL_DIR}/scripts/sprite_gen.py" check`

If config exists, read `output_dir` (and `canonical_anchor`, `project_root` if present) from it and pass as args to all commands.

## Pipeline Config (sprite_spec.yaml)

**ALWAYS read `<project_root>/sprite_spec.yaml` BEFORE running snap or generate
for the chunky-pixel-art pipeline.** It defines per-project specs:
- `native.characters.target_h` / `cell_h` — chars
- `native.monsters.target_h` / `cell_h` — monsters
- `native.margin_bottom` — PAD

If `sprite_spec.yaml` is missing in the project root, fall back to defaults
documented in `PIXEL_ART_PIPELINE.md` (chars 32/48, monsters 64/72) AND offer
to create the file. Never proceed silently with defaults if the project has
git history or other sprite output that suggests a non-default spec.

Also verify the canonical anchor path (from `config.json` or
`sprite_spec.yaml`) exists before every `generate` call. If missing → STOP
and ask the user.
