#!/usr/bin/env python3
"""
Convert video files to 240x240 optimized GIFs for GeekMagic SmallTV-Ultra.

Requirements:
    pip install imageio[pyav] Pillow

Usage:
    python3 convert_to_gif.py <input_folder_or_file> [-o ./out]
    python3 convert_to_gif.py .                      # convert current dir → ./output/
    python3 convert_to_gif.py ./my_videos           # custom input dir
"""

import argparse
import glob
import os

import imageio.v3 as iio
from PIL import Image

VIDEO_EXTENSIONS = ('.mov', '.mp4', '.avi', '.mkv', '.m4v', '.webm')
OUTPUT_SIZE = (240, 240)
TARGET_FPS = 8
COLORS = 64


def resize_crop_square(img: Image.Image, size: tuple) -> Image.Image:
    w, h = img.size
    min_dim = min(w, h)
    left = (w - min_dim) // 2
    top = (h - min_dim) // 2
    img = img.crop((left, top, left + min_dim, top + min_dim))
    return img.resize(size, Image.LANCZOS)


def convert_video_to_gif(video_path: str, output_path: str) -> bool:
    name = os.path.basename(video_path)
    print(f"Converting: {name}")

    try:
        meta = iio.immeta(video_path, plugin="pyav")
        source_fps = meta.get("fps", 30) or 30
        step = max(1, round(source_fps / TARGET_FPS))

        all_frames = iio.imread(video_path, plugin="pyav", index=None)
        sampled = all_frames[::step]

        frames = []
        for raw in sampled:
            img = Image.fromarray(raw).convert("RGB")
            img = resize_crop_square(img, OUTPUT_SIZE)
            img = img.quantize(
                colors=COLORS,
                method=Image.Quantize.MEDIANCUT,
                dither=Image.Dither.FLOYDSTEINBERG,
            )
            frames.append(img)

        if not frames:
            print(f"  Warning: no frames found in {name}")
            return False

        duration_ms = int(1000 / TARGET_FPS)
        frames[0].save(
            output_path,
            format="GIF",
            save_all=True,
            append_images=frames[1:],
            optimize=True,
            duration=duration_ms,
            loop=0,
        )

        size_kb = os.path.getsize(output_path) / 1024
        print(f"  Done: {os.path.basename(output_path)} ({size_kb:.1f} KB, {len(frames)} frames)")
        return True

    except Exception as e:
        print(f"  Error ({name}): {e}")
        return False


def collect_videos(path: str) -> list[str]:
    if os.path.isfile(path):
        return [path]
    videos = []
    for ext in VIDEO_EXTENSIONS:
        videos.extend(glob.glob(os.path.join(path, f"*{ext}")))
        videos.extend(glob.glob(os.path.join(path, f"*{ext.upper()}")))
    return sorted(set(videos))


def main():
    parser = argparse.ArgumentParser(
        description="Convert videos to 240x240 GIFs for GeekMagic display"
    )
    parser.add_argument(
        "input",
        nargs="?",
        default=".",
        help="Input video file or directory (default: current directory)",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output directory (default: <input_dir>/output/)",
    )
    args = parser.parse_args()

    input_path = os.path.abspath(os.path.expanduser(args.input))
    if args.output:
        output_dir = os.path.abspath(os.path.expanduser(args.output))
    else:
        base = input_path if os.path.isdir(input_path) else os.path.dirname(input_path)
        output_dir = os.path.join(base, "output")

    os.makedirs(output_dir, exist_ok=True)

    videos = collect_videos(input_path)
    if not videos:
        print(f"No video files found in: {input_path}")
        return

    print(f"Converting {len(videos)} video(s) → {output_dir}")
    print(f"Settings: {OUTPUT_SIZE[0]}x{OUTPUT_SIZE[1]}px, {TARGET_FPS}fps, {COLORS} colors\n")

    success = 0
    for video_path in videos:
        base = os.path.splitext(os.path.basename(video_path))[0]
        output_path = os.path.join(output_dir, f"{base}.gif")
        if convert_video_to_gif(video_path, output_path):
            success += 1

    print(f"\nDone: {success}/{len(videos)} converted → {output_dir}")


if __name__ == "__main__":
    main()
