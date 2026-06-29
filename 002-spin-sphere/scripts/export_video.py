from __future__ import annotations

import argparse
import hashlib
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


WIDTH = 1080
HEIGHT = 1920
FPS = 30
OUTPUT_SECONDS = 24.0
FRAME_COUNT = int(OUTPUT_SECONDS * FPS)
SOURCE_LOOP_SECONDS = 16.0
POINT_COUNT = 96
FRUSTUM_HEIGHT = 4.35
DOT_COLOR = np.array([160, 232, 255], dtype=np.float32)
TEXT = "它是在向左转，还是向右转？"


def smoothstep(edge0: float, edge1: float, value: np.ndarray) -> np.ndarray:
    t = np.clip((value - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def hex_color(value: str) -> np.ndarray:
    return np.array(
        [int(value[1:3], 16), int(value[3:5], 16), int(value[5:7], 16)],
        dtype=np.float32,
    )


def create_fibonacci_sphere(count: int = POINT_COUNT) -> np.ndarray:
    golden_angle = math.pi * (3.0 - math.sqrt(5.0))
    points = np.empty((count, 3), dtype=np.float32)

    for index in range(count):
        y = 1.0 - ((index + 0.5) / count) * 2.0
        radius = math.sqrt(1.0 - y * y)
        angle = index * golden_angle
        points[index] = [math.cos(angle) * radius, y, math.sin(angle) * radius]

    return points


def create_background() -> Image.Image:
    y, x = np.mgrid[0:HEIGHT, 0:WIDTH].astype(np.float32)
    x_norm = x / WIDTH
    y_norm = y / HEIGHT

    center = hex_color("#1a1a2e")
    mid = hex_color("#111126")
    edge = hex_color("#0a0a1a")
    cyan = hex_color("#a0e8ff")
    vignette_color = hex_color("#04040e")

    radial = np.sqrt(((x_norm - 0.5) * 1.72) ** 2 + (y_norm - 0.54) ** 2)
    first_mix = smoothstep(0.0, 0.56, radial)[..., None]
    second_mix = smoothstep(0.56, 0.96, radial)[..., None]
    background = center * (1.0 - first_mix) + mid * first_mix
    background = background * (1.0 - second_mix) + edge * second_mix

    cyan_radial = np.sqrt(((x_norm - 0.5) * 1.72) ** 2 + (y_norm - 0.42) ** 2)
    cyan_alpha = (1.0 - smoothstep(0.0, 0.34, cyan_radial))[..., None] * 0.055
    background = background * (1.0 - cyan_alpha) + cyan * cyan_alpha

    vignette = smoothstep(0.48, 1.0, radial)[..., None] * 0.42
    background = background * (1.0 - vignette) + vignette_color * vignette

    alpha = np.full((HEIGHT, WIDTH, 1), 255, dtype=np.uint8)
    rgb = np.clip(background, 0, 255).astype(np.uint8)
    return Image.fromarray(np.concatenate([rgb, alpha], axis=2), "RGBA")


def create_dot_sprite(scale: float) -> Image.Image:
    size = int(round(18 * scale))
    if size % 2 == 0:
        size += 1

    y, x = np.mgrid[0:size, 0:size].astype(np.float32)
    point = np.stack([(x + 0.5) / size - 0.5, (y + 0.5) / size - 0.5], axis=-1)
    radius = np.linalg.norm(point, axis=-1) * 2.0

    core = smoothstep(0.48, 0.38, radius)
    halo = smoothstep(1.0, 0.16, radius) * 0.34
    alpha = np.maximum(core * 0.86, halo)
    alpha[radius > 1.0] = 0.0

    rgba = np.zeros((size, size, 4), dtype=np.uint8)
    rgba[..., :3] = DOT_COLOR.astype(np.uint8)
    rgba[..., 3] = np.clip(alpha * 255, 0, 255).astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


def find_font() -> Path:
    candidates = [
        Path("C:/Windows/Fonts/NotoSansSC-VF.ttf"),
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/msyhbd.ttc"),
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    raise FileNotFoundError("No suitable Chinese font found")


def draw_text(frame: Image.Image, scale: float, source_time: float) -> None:
    font_size = int(round(20.68 * scale))
    font = ImageFont.truetype(str(find_font()), font_size)
    overlay = Image.new("RGBA", frame.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    bbox = draw.textbbox((0, 0), TEXT, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    bottom = 84.4 * scale
    x = (WIDTH - text_width) / 2
    y = HEIGHT - bottom - text_height
    phase = (source_time % 4.0) / 4.0
    opacity = 0.4 + 0.4 * (0.5 - 0.5 * math.cos(phase * math.tau))

    draw.text((x, y), TEXT, fill=(255, 255, 255, int(round(opacity * 255))), font=font)
    frame.alpha_composite(overlay)


def render_frame(
    background: Image.Image,
    dot_sprite: Image.Image,
    points: np.ndarray,
    frame_index: int,
) -> tuple[Image.Image, bytes, float]:
    progress = frame_index / (FRAME_COUNT - 1)
    source_time = progress * SOURCE_LOOP_SECONDS
    angle = source_time * math.tau / SOURCE_LOOP_SECONDS
    cos_angle = math.cos(angle)
    sin_angle = math.sin(angle)
    world_scale = HEIGHT / FRUSTUM_HEIGHT
    half_dot = dot_sprite.width // 2

    frame = background.copy()

    for x, y, z in points:
        rotated_x = cos_angle * x + sin_angle * z
        screen_x = int(round(WIDTH / 2 + rotated_x * world_scale))
        screen_y = int(round(HEIGHT / 2 - y * world_scale))
        frame.alpha_composite(dot_sprite, (screen_x - half_dot, screen_y - half_dot))

    draw_text(frame, WIDTH / 390.0, source_time)
    rgb = frame.convert("RGB").tobytes()
    return frame, rgb, source_time


def export_video(output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    scale = WIDTH / 390.0
    background = create_background()
    dot_sprite = create_dot_sprite(scale)
    points = create_fibonacci_sphere()
    first_hash: str | None = None
    last_hash = ""

    command = [
        "ffmpeg",
        "-y",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{WIDTH}x{HEIGHT}",
        "-r",
        str(FPS),
        "-i",
        "-",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(output_path),
    ]

    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    if process.stdin is None:
        raise RuntimeError("ffmpeg stdin is unavailable")

    try:
        for frame_index in range(FRAME_COUNT):
            _frame, rgb, _source_time = render_frame(background, dot_sprite, points, frame_index)
            frame_hash = hashlib.sha256(rgb).hexdigest()
            if frame_index == 0:
                first_hash = frame_hash
            if frame_index == FRAME_COUNT - 1:
                last_hash = frame_hash

            process.stdin.write(rgb)
            if frame_index % FPS == 0:
                print(f"rendered {frame_index // FPS:02d}s / {int(OUTPUT_SECONDS)}s", flush=True)
    finally:
        process.stdin.close()

    exit_code = process.wait()
    if exit_code != 0:
        raise RuntimeError(f"ffmpeg exited with {exit_code}")

    if first_hash != last_hash:
        raise RuntimeError("first and last raw frames are not identical")

    print(f"wrote {output_path}")
    print(f"raw first/last sha256 {first_hash}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("002-spin-sphere/exports/spin-sphere-loop-24s.mp4"),
    )
    args = parser.parse_args()

    export_video(args.output)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(error, file=sys.stderr)
        raise
