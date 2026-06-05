# Chunky low-res pixel art pipeline

The locked-in recipe for game-ready sprites: **generate → snap**.
Output: `<char>_<action>.png` (and only that — no `_1x1`, no `_display`).
Engine-agnostic — drop into any 2D engine (Godot, Unity, Pico-8, raylib, web canvas, etc.) with NEAREST texture filter.

Use this pipeline whenever the user wants:
- Chunky low-res pixel art (RPG-classic, Octopath/Dead-Cells scale)
- Multiple actions (idle / attack / walk / hit / death / victory) of the same
  character to swap cleanly in an animation
- Engine-agnostic sheets ready for any 2D pipeline (Godot/Unity/Pico-8/etc.)

## Where knowledge lives (so we stop re-litigating the same things)

Three kinds of knowledge, three homes — when you learn something new, put it in
the RIGHT one instead of piling more prose into prompts:

1. **Style law** (universal, rarely changes — chunky / chibi / eyes-only face /
   female-only / horizontal attacks) → the prompt templates below + the `rules`
   block in `sprite_spec.yaml`. Mostly settled; don't keep re-adding it.
2. **Project numbers** (target_h, cell_h, PAD, paths, gate thresholds) →
   `sprite_spec.yaml`. One source of truth.
3. **Per-unit locked design** (a character's locked colors, hair, weapon,
   silhouette) → an OPTIONAL per-project roster (`<project_root>/roster/<unit>.yaml`).
   **Never re-derive a character from chat — read its roster spec.**

And two mechanisms, instead of "tell Gemini harder" (which fails — Gemini is
non-deterministic, and long prose actively fights an attached reference):

- **SHOW, don't tell.** Pass approved frames as references (`anchor_idle`, plus
  an action `exemplar` for new actions). A reference image carries proportions,
  pose, and composition far better than words. Use prose ONLY for the *delta*
  from the reference.
- **VALIDATE, don't pray.** `scripts/qc_frame.py` catches clipping / missing
  transparency / bad size mechanically, BEFORE you see the frame — so you stop
  being the manual QA for the same failure every session.

## Step 0 — Read project config (ALWAYS)

Before any snap/generate, **check for `<project_root>/sprite_spec.yaml`**:

```bash
cat ./sprite_spec.yaml 2>/dev/null
```

If present → use its values for `target_h`, `cell_h`, `canonical_anchor`,
etc. They override the defaults below.

If absent → use defaults (chars 32/48, monsters 64/72) AND offer to create
the file so the project has an explicit spec going forward.

The canonical anchor referenced in `sprite_spec.yaml` (or in `config.json`)
must exist on disk before any `generate` call — verify, and STOP+ask if
missing.

## Step 0.5 — Read the roster (if the project keeps one)

A roster is an OPTIONAL per-project memory of locked character designs under
`<project_root>/roster/`, so you never re-derive a character from chat. If the
project has one, check its index (`roster/_index.yaml`) before generating:

- **Existing unit** (it's listed) → read `roster/<unit>.yaml`. Pass its
  `anchor_idle` as `--files`, and inject `design` + `distinctive` (and the
  action's `pose`, if listed) into the prompt verbatim. Do NOT re-describe the
  character from memory or chat — that's exactly the loop the roster removes.
- **New unit** → design it (Step 1 templates). Once it's APPROVED and delivered,
  write `roster/<unit>.yaml` capturing the final locked design, and add it to
  `roster/_index.yaml`. The roster grows by one entry per approved character.

## Output spec (defaults — overridable via sprite_spec.yaml)

- **Characters**: native char height = 32 px, cell height = 48, cell width
  16-multiple auto-grown to fit feet_extent×2 + PAD×2.
- **Monsters**: native char height = 64 px, cell height = 72, cell width
  same auto-grow rule. Bigger than chars on screen at same render scale →
  natural visual threat hierarchy without runtime scaling.
- **Alignment**: feet bottom-aligned (PAD=4 from cell bottom), feet x-centered.
- **Alpha**: binary (0 or 255), no AA.
- **Filename**: `<char>_<action>.png` only. The script does NOT produce a
  display/preview PNG — preview by `open <path>` in Preview.app (auto-zoom).

## Style + aesthetic split

- **Characters** = clean Octopath chibi feel (modest detail, friendly readable
  proportions, minimalist face = eyes only).
- **Monsters** = grotesque/vile (irregular asymmetric forms, dripping ooze,
  visible innards, multiple uneven eyes, drooling fanged mouths, scars,
  dark sickly palettes — see `feedback_monster_aesthetic.md`).
- **Backgrounds** = ordinary scenes (grassland, forest) but with darkened
  palette overall.

## Combat orientation: HORIZONTAL ATTACKS

Game is left↔right side-view battle. **Every attack pose extends
horizontally toward the opponent (right or left side of the canvas), NOT
downward, NOT toward the viewer.** Weapons / lunges / strikes / projectiles
travel along the X axis. See `feedback_horizontal_attacks.md`.

## Step 1 — Generate (Gemini)

Call `sprite_gen.py generate` per frame.

**References (--files): ALWAYS THE CANONICAL ANCHOR.**

The single style anchor `sprites/references/female_ref_3x.png` is the default
for every character generation, full stop. The user locked this in 2026-05-28:
"앵커는 그냥 무조건 그 첫캐릭터 그거로해라.. 다른건 다 너무 이상하다" — anchoring on
other approved units (knight, cleric, a mage, the acolyte, etc.) consistently
produced off-looking characters; the canonical alone produces clean ones.

| Frame                                | --files                                              |
|--------------------------------------|------------------------------------------------------|
| Character IDLE (NEW or re-roll)      | canonical ALONE: `sprites/references/female_ref_3x.png` |
| Character ATTACK / non-idle          | TWO refs: that character's approved IDLE **+** canonical |
| First frame of a NEW monster         | Canonical style ref (chunkiness anchor)              |
| Subsequent frames same monster       | Approved IDLE of THAT monster (only)                 |
| Family-of-monster (e.g. giant_slime from slime) | Canonical + the related monster's idle (2 refs) |

Refinement locked-in 2026-05-28: idle = canonical alone (locks the style cleanly);
attack = idle + canonical together (idle carries the character's identity, canonical
keeps the style from drifting). The old rule of "attack = just the idle alone" was
weaker — adding the canonical alongside is what the user wants.

(Monsters are different — the canonical is human-shaped, so reusing the
monster's own idle still wins for repeat monster frames.)

For an existing unit, the roster spec names the exact reference: pass its
`anchor_idle` (the approved idle). When generating a NEW ACTION you haven't done
for this unit yet, ALSO pass an **exemplar** — the cleanest already-approved
frame of that action (the roster can record which) — as a second reference. It
shows Gemini the composition (e.g. a wide swing) so you don't have to spell it
out in prose. Show, don't tell.

**Generation timing & stall recovery (3-minute rule).** A healthy `generate`
finishes in ~50s–2min. It HANGS when the log reaches `StreamGenerate [200]` then
goes silent (cookie flicker or image-gen quota — see the gemini-gen-stalls
memory). **Rule: if a single generate exceeds 3 MINUTES with no `"success"`,
KILL it and retry with a FRESH unique session name.** Never wait longer than 3
min on one attempt. Don't pipe the gen through `tail` in the background (it
buffers and hides the live log) — redirect to a file and watch it.

For unattended runs use an **auto-retry-until-success loop**: each iteration
starts the gen in the background with a fresh session, polls the log every 15s,
and after **180s (3 min)** without success kills it, `end-session`s, and retries.
Stop on the first `"success": true`. This punches through the intermittent
quota/cookie stalls without babysitting. (Pattern used for the whole mage +
cleric batch; the script lived at /tmp/*_retry.sh.)

**HARD GATE — never call `sprite_gen.py generate` for a brand-new subject
without an anchor in `--files`.** If the project has no canonical reference
yet, STOP and ask the user. Anchor-less output drifts heavily.

**Prompt structure (deltas only, style comes from references):**

For a CHARACTER first frame:
```
Match image 1 EXACTLY — same chunky thick pixel blocks, same CHIBI
PROPORTIONS (head is HUGE relative to body, head ≈ 40% of total figure
height; torso + legs short and stubby; feet small and close together),
same minimalist face style (eyes only, no nose, no mouth).
Female [class]. [outfit colors + items short list].
Idle pose, calm ready stance, feet close together (NOT a wide combat
stance).
VIEW — 3/4 FRONT VIEW (NOT a flat dead-on front, NOT a pure side profile):
the body is angled slightly toward the viewer's RIGHT, the face turned the
same way. Apply this EVEN IF the anchor image looks flat-front — 3/4 is the
house style for idles, not "copy the anchor's angle". (Several approved idles
came out flat-front; do not propagate that.)
Eyes: match the mage/acolyte reference — an EYEBROW above the eye, a tiny bright
HIGHLIGHT in each, FOLLOWING the 3/4 turn: NEAR eye (on the viewer's right) FULLY
visible, FAR eye (on the viewer's left) only HALF visible (partly hidden by the
face turn / nose-bridge / hair). NOT both eyes equal & symmetric — that's a flat
cross-eyed mugshot. Reads as brow(1)+eye(2)=3 rows at native res. Let the
REFERENCE carry the eye style; describe in words, never literal pixel coordinates.
Exactly 2 arms, exactly N weapon(s).
```

The explicit chibi-ratio language matters: "same proportions" alone lets
Gemini drift toward adult/realistic RPG-hero builds. Spelling out
head ≈ 40%, stubby limbs, feet-close keeps the silhouette anchored to the
canonical chibi reference. For eyes, LEAN ON THE REFERENCE — the mage/acolyte have
the eyes we want, so anchoring a new unit on them (or any approved pretty unit)
carries the eye style. In words, add only: an EYEBROW above the eye, a tiny
HIGHLIGHT, near eye full / far eye half (→ brow(1)+eye(2)=3 rows). Do NOT pile on
eye-size adjectives like "small" (that was an invented over-spec and it backfired),
and never give literal pixel coordinates (those garble).

For a CHARACTER non-idle frame:
```
CRITICAL CANVAS RULE — output canvas size must NOT be limited to the
reference image's aspect ratio. The reference is a portrait (tall/narrow).
This is an ACTION pose with limbs/weapons/hair/cape extending outward —
the figure needs HORIZONTAL ROOM. USE A WIDE CANVAS — width should be
roughly 1.5× to 2× the height. Output a wide rectangular image. Character
sits center; weapon extends out one side with margin, hair/cape extend
out the other side with margin. NOTHING gets clipped at the edges.

Match image 1 EXACTLY (locked character) — same chunky pixels, same chibi
proportions (head HUGE ≈ 40% of figure height, stubby body, feet small),
same outfit (preserve all colors), same hair (color + style), same face
style (eyes only, no nose, no mouth — eyebrow above the eye, a tiny highlight;
brow(1)+eye(2)=3 rows, near full / far half, like the mage/acolyte).

Pose change ONLY: [pose description, side-view battle, attack to the RIGHT].
For dynamic action: weapon held in motion (NOT static "ready" stance), body
torqued into the swing, hair (braid/ponytail/loose) WHIPPED BACK in the
direction opposite the swing, cape billowing the same direction. BUT keep the
HEAD fairly FRONT-FACING — do NOT turn the face away into the swing, and don't
let hair sweep over the face. At 32px a turned action head collapses the eyes to
a messy 1px in the snap, and NO snap tweak (pad/phase/crop sweeps all tried)
recovers it — only re-rolling with a front head, or transplanting the idle's eyes,
fixes it (the mercenary attack burned a long fight here). Head front + eyes clear;
let only the body / weapon / hair do the swinging. Add a
SHORT compact motion swoosh trail behind the weapon arc — semi-transparent
white/silver, small (NOT spanning the canvas), single arc (NOT a second
ghost weapon).

Weapon constraints (must read at small size):
- Blade/shaft rendered as THICK CHUNKY pixel blocks, no thin lines.
- Weapon tip leaves at least 10-15% margin from canvas edges.

Same chunky pixels everywhere. Exactly 2 arms, exactly 1 weapon.
```

The template above is for a MELEE swing (sword/spear). A **CASTER attack**
(mage/cleric channeling a spell) is different — do NOT use the wide-canvas /
swoosh-trail melee template for casters. A caster who got the wide canvas +
fireball + turned head ended up stretched and smear-eyed; one clean roll with
the rules below won instead. For a CASTER non-idle frame, swap these blocks:
```
CANVAS: keep it COMPACT / portrait — this is a CASTING pose, NOT a wide melee
swing. Do NOT stretch the canvas wide (casters don't fling limbs/weapons
sideways the way a swordsman does). Figure centered, small even margins,
nothing clipped. (Expected snap aspect ~0.62–0.88, like the idle.)

Pose change ONLY: side-view battle, casting a spell to the RIGHT. Hold the
staff DIAGONALLY ACROSS the body (gripped in two hands, ONE thick continuous
diagonal from the lower-LEFT up to the UPPER-RIGHT, the glowing focus tip
leading at the upper-right) — a braced casting stance. Body leaning slightly
into the cast, feet apart. Keep the HEAD DEAD FRONT-FACING (same eye rule as
every frame). Do NOT thrust the staff straight overhead, and do NOT turn the
face toward the staff.

DO NOT add: any projectile / fireball / orb / bolt leaving the staff or hand;
any elemental energy emanating from the character or robe; any large glow
spanning the canvas. ONLY the focus's own small tip glow (element-colored).
The game animates the projectile separately — the sprite is just the caster.
```
(Why no projectile: the user cut it explicitly — "파이어볼은 삭제". Effects are
the engine's job; the unit sprite is the figure only. Pyromancer attack was the
first caster done this way — see roster/pyromancer.yaml `frames.attack.notes`.)

Two snap-survival rules learned on the cryomancer attack (see
roster/cryomancer.yaml `frames.attack.notes`):
- **Staff = ONE thick continuous diagonal across the body.** A raised/overhead
  or thin diagonal staff snaps to a BROKEN dotted line at 32px. The across-body
  diagonal (the pyro/cryo composition) is the only one that holds. Passing an
  approved caster-attack frame as a 2nd `--files` exemplar reproduces it cleanly,
  but two-file gens HANG more often and can turn the head — weigh that.
- **Head DEAD front or the eyes die.** Any head turn collapses the eyes to mush
  at 32px and no snap tweak recovers it. Re-roll front-headed. If the eyes are
  still imperfect on an otherwise-good front-headed frame, TRANSPLANT the idle's
  eye patch (heads aligned by skin-centroid) — guaranteed idle-identical eyes.
  This is the one allowed pixel edit (copying a real eye patch, NOT hand-drawing).

For a MONSTER first frame:
```
Match the CHUNKY THICK PIXEL ART STYLE of image 1 — same large pixel blocks.
NOT a humanoid character — the SUBJECT is a [monster type].
[Anatomy spec — clear silhouette readable at small size].
Grotesque details: [matted/rotting/dripping/multi-eyed/fanged/etc.].
Idle pose, menacing stance.
```

For a MONSTER non-idle frame: same as character non-idle pattern.

Do NOT add style adjectives ("mature/gritty/clean") when a reference is
attached — they fight the visual reference.

Eyes — LEAN ON THE REFERENCE. The mage/acolyte have the eyes we want; anchor a new
unit on an approved pretty unit and the eye style comes with it. In words add only:
an EYEBROW above the eye, a tiny HIGHLIGHT, near eye full / far eye half (→ a clean
brow(1)+eye(2)=3-row stack). Do NOT add eye-size adjectives ("small" was an invented
over-spec — it backfired), and never give literal pixel-grid coordinates ("2 cols ×
3 rows", those garble). If the raw eyes look right but the SNAP muddies them, that's
a downsample issue — a small `--top-crop` (more pixels on the face) usually fixes it.

If output drifts (face broken, outfit color wrong, etc.):
- Iterate in a FRESH session (`end-session` then new session). Sometimes
  session context decay is the issue, not the prompt.
- Emphasize the specific thing that broke ("OUTFIT COLORS must match image 1
  EXACTLY: [list colors]") in plain words — not pixel grids.

## Step 1.5 — Acceptance gate (BEFORE snapping or showing the user)

Run the raw Gemini output through the gate:

```
python3 scripts/qc_frame.py <raw.png> --kind idle|action|swing
```

- `idle` — portrait expected. `action` — generic (warns if no horizontal margin).
- `swing` — melee sword/spear; also warns if the pose isn't wide/horizontal.

**Hard fail (exit 1)** = clipped at a canvas edge, no transparent background
(chromakey failed), or empty/tiny subject. On a hard fail, **regenerate** with
the failure reason appended to the prompt — do NOT snap or show the user a
clipped frame. (Clipping otherwise costs blind re-roll after re-roll; the gate
flags it in one shot.)

**Soft warn (exit 0)** = minor edge contact, full-width subject, or a swing that
came out portrait. Surface these but use judgment — approved attacks legitimately
range from portrait casters to wide melee swings, so aspect is not a hard gate.

The gate runs on the RAW output (the 800–1400px Gemini frame), where clipping is
visible — not on the snapped result.

## Step 1.6 — Consistency check vs the idle (every non-idle frame)

The gate is mechanical only. Whether the frame is the SAME CHARACTER as the idle
is YOUR judgment — and the failure mode is cheerleading a frame that drifted. So
for every non-idle frame, before showing the user, run:

```
python3 scripts/compare_frames.py <idle.png> <frame_raw.png>
```

It places the idle and the new frame side by side at matched figure height with
quarter guide lines. Actually LOOK and compare, point by point:
- hair length & style (does short hair stay short?)
- head-to-body ratio (still chibi, or stretched by the action pose?)
- face / eyes (expression, shadowing, symmetry)
- palette

State any drift plainly and fix it BEFORE calling the frame good — do NOT
cheerlead just because it passed the gate. Recurring traps: motion words
("hair flying/tossed", "deep lunge") make Gemini grow short hair into a long
mane and stretch the chibi body; heavy action shading muddies the eyes/face.

## Step 2 — Snap

```
python3 scripts/snap_single.py <src.png> <char> <action> \
  --out-dir <sprites_dir>/sheets \
  [--target-h 32] [--cell-h 48] [--top-crop N]
```

- **Characters**: `--target-h 32 --cell-h 48` (default).
- **Monsters**: `--target-h 64 --cell-h 72`.
- For BENT poses (forward-stab attack, dive) where source character is
  shorter, h32 makes pixels too fine — try `--target-h 28-30` for chars,
  eyeball compare.
- `--top-crop N` trims N rows off the source's tight-bbox top before
  snapping. Use when overlong hair/halo/aura pushes face down so eyes/face
  details get averaged out at h32. Try 40-100 px first; verify face not cut.
- `--keep-all` keeps ALL connected components (dropping only tiny specks),
  instead of culling everything but the largest. Use it whenever the sprite
  has a DETACHED prop that must survive — a floating spellbook (arcanist), an
  orbiting orb/rune, a separate summoned creature (summoner), a thrown weapon.
  WITHOUT it the snap deletes the detached piece (it keeps only the biggest
  blob = the body). If a floating prop vanished from the snap, this is why.
  Prefer keeping the prop visually CONNECTED to the figure when you can (it
  also reads better at 32px); `--keep-all` is the fallback when it must float.

**Variation compare (when result looks off):** use the bundled
`scripts/snap_compare.py` to sweep h or top_crop and let the user pick:

```
# h sweep at fixed top_crop=0:
python3 scripts/snap_compare.py <src.png> --target-h-range 24 38 2

# top_crop sweep at fixed h32:
python3 scripts/snap_compare.py <src.png> --top-crop-range 0 200 20

# 2D grid: h × top_crop:
python3 scripts/snap_compare.py <src.png> \
  --target-h-range 28 36 2 --top-crop-range 0 100 20

# Monsters (bigger cell):
python3 scripts/snap_compare.py <src.png> --cell-h 72 \
  --target-h-range 56 70 2
```

Outputs a labeled grid PNG (default `/tmp/<src_stem>_compare.png`); `open`
it, the user picks the best (h, top_crop), then run `snap_single.py` with
those values for the final game file.

The pipeline inside snap_single.py:
1. Tight bbox of source figure (alpha > 10).
2. (Optional) trim top-crop rows.
3. Mode-downsample: each dest pixel = majority opaque color in its source
   block (opaque threshold alpha > 200, dest opaque if > 40% of block opaque).
4. Largest connected component cleanup (drops tiny isolated specks).
5. Outline pass: opaque dest pixels touching transparent are recolored
   with the darkest opaque color in their source block — preserves outlines
   that mode-color picks would dilute.
6. Bottom-center align with feet x-centering, cell_w = round_up_16(...),
   cell_h = `--cell-h`.

## Step 3 — Normalize (DEFAULT: skip)

**Default policy:** do NOT auto-run `normalize_sheets.py`. Each frame stays
at its native cell size from the snap.

- All character idle frames natively snap to **32×48** → uniform idle row
  across the roster.
- All monster idle frames natively snap to ~variable × **72** at h64 → also
  uniform within the monster tier.
- Attacks may be wider per creature (recruit attack with sword 80×48,
  giant_slime body-charge 96×72 etc.) — that's fine, no padding needed.

Run normalize only when the user explicitly asks for uniform cells:

| Mode                           | Command                                          |
|--------------------------------|--------------------------------------------------|
| Per-character max              | `normalize_sheets.py --sheets-dir DIR`           |
| Global max across roster       | `normalize_sheets.py --sheets-dir DIR --global`  |
| Forced exact cell (clip OK)    | `normalize_sheets.py --sheets-dir DIR --cell W H`|

## Step 4 — Show user

```
osascript -e 'tell application "Preview" to quit'
sleep 0.4
open -a Preview <sheets_dir>/<char>_idle.png <sheets_dir>/<char>_attack.png
```

Quit + reopen ensures both files load into ONE Preview window with a sidebar,
not separate windows. (Preview.app's automatic zoom-to-fit handles small
native PNGs — no need for upscaled `_display.png`.)

If the user says the snap is broken / weird:
1. Most common cause: wrong target_h. Run a compare grid (h26-h44 step 2).
2. Second cause: face details lost at h32 due to overlong hair → try
   `--top-crop 40-100`.
3. Third cause: source itself is bad → regenerate the source.

## Step 4.5 — Deliver (if the project configures a delivery target)

If `sprite_spec.yaml` defines `paths.delivery_root` (where the consuming project
keeps its final assets), copy the approved frame there after the user approves —
landing in that tree is the project's "approved" bar:

```
cp <sheets>/<unit>_<action>.png "<delivery_root>/<subpath>/<unit>_<action>.png"
```

The `<subpath>` (e.g. by class or family) is whatever the project's roster /
`sprite_spec.yaml` defines. If no `delivery_root` is configured, the snapped
frame in `<sheets>/` is the final artifact. After delivering a NEW unit's first
approved frame, record its locked design in the project's roster.

## Step 5 — Engine import

Engine-agnostic. The output PNGs work in any 2D pipeline; just respect:

- **NEAREST filter only** — never bilinear / smoothing. Otherwise pixel art blurs.
- **Feet anchor** — feet are at `(cell_w / 2, cell_h - PAD)` from texture top-left. Set the sprite origin / offset so the entity's logical position equals the feet position. (Godot 4: `AnimatedSprite2D.offset = (0, -PAD)`. Unity: pivot bottom-center. Pico-8: `spr` blits at top-left, so adjust by `cell_h`.)
- **Multi-frame actions** later follow `<char>_<action>_<N>x1.png` — N frames horizontally, hframes=N for engines that auto-split.
- **Different cell sizes per creature** are expected (chars 48 tall, monsters 72 tall by default). Group same-tier creatures into one atlas if your engine prefers uniform cells.

## What NOT to do

- Don't give literal pixel-GRID eye coordinates ("2 cols × 3 rows") — they
  garble. Don't pile on eye-size adjectives ("small" backfired). Lean on the
  reference (mage/acolyte) + words: eyebrow above, highlight, near full / far half.
- Don't add style adjectives when a reference is attached.
- Don't generate without a reference image — no style anchor, output drifts.
- Don't auto-derive target_h from a reference idle (tried; tiny output for
  bent poses).
- Don't combine multiple actions into one strip per character — each action
  stays in its own file.
- Don't snap chars at target_h ≥ 64 (too detailed, not chunky).
- Don't use LANCZOS or direct NEAREST resize — uneven pixels.
- Don't auto-run normalize_sheets.py — breaks idle uniformity across roster.
- Don't ship `_display.png` — we no longer create it; if you find one,
  delete it.
- Don't use 1.5× runtime scaling for monsters — non-integer pixel scaling
  produces uneven pixel chunks. Render natively bigger instead (h64).
- Don't aim attack poses downward or toward viewer — game is L↔R side-view,
  attacks must extend horizontally.
