# GIF Assets

Source animations and conversion tool for GeekMagic SmallTV-Ultra (240×240 px).

## Source videos (`*.mov`)

| File | Used as |
|------|---------|
| `start.mov` | `starting.gif` — session start |
| `request.mov` | `requesting.gif` — tool call in progress |
| `working.mov` | `working.gif` — post-tool, still working |
| `waiting.mov` | `waiting.gif` — waiting for user permission |
| `standby.mov` | `rate_limit.gif` — rate-limited |
| `subagent.mov` | `subagent.gif` — subagent finished |
| `compacting.mov` | `compacting.gif` — context compaction |
| `working2.mov` | alternative working animation |
| `control.mov` | alternative animation |
| `report.mov` | alternative animation |
| `setting.mov` | alternative animation |

## Converting videos to GIFs

### Requirements

```bash
pip install "imageio[pyav]" Pillow
```

### Usage

```bash
# Convert all videos in current directory → ./output/
python3 convert_to_gif.py

# Custom input directory
python3 convert_to_gif.py -i ./my_videos

# Single file with custom output dir
python3 convert_to_gif.py -i working.mov -o ./my_theme
```

Output specs: **240×240 px**, 8 fps, 64 colors (optimized for small display).

## Creating a custom theme

1. Record short screen captures or animations (any length, any resolution)
2. Convert with `convert_to_gif.py`
3. Name the output files to match the state names:
   - `starting.gif`
   - `requesting.gif`
   - `working.gif`
   - `waiting.gif`
   - `rate_limit.gif`
   - `subagent.gif` *(optional)*
4. Upload via `geekmagic_hook theme upload <output_dir>`

## GIF requirements

| Property | Value |
|----------|-------|
| Size | 240 × 240 px |
| Format | GIF (animated) |
| Loop | infinite (loop=0) |
| Max file size | ~300 KB recommended |
