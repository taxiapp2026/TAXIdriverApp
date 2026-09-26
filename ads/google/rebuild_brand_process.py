#!/usr/bin/env python3
"""Brand-only explainer: Taxi and Fly logo and words. No phone, no filmed footage."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

import edge_tts
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / "build"
LOGO = ROOT.parent / "meta" / "logo-taxi-and-fly.png"
W, H, FPS = 1080, 1920, 30
GOLD = (255, 210, 40)
WHITE = (240, 240, 240)
MUTED = (180, 180, 180)
BG = (8, 8, 8)

import sys

sys.path.insert(0, str(ROOT))
from add_pretty_music import pretty_music  # noqa: E402
from build_video import FONT, FONT_REG, duration, ff, kenburns, mix, xfade_concat  # noqa: E402

EL = {
    "out": ROOT / "taxi-and-fly-athens-to-airport-el.mp4",
    "art": Path("/opt/cursor/artifacts/taxi_and_fly_aplo_el.mp4"),
    "vo": BUILD / "vo_simple_el",
    "voice": "el-GR-NestorasNeural",
    "lines": [
        ("Μια τόσο απλή εφαρμογή.", "-14%"),
        ("Χωρίς login.", "-14%"),
        ("Από και προς το αεροδρόμιο.", "-20%"),
        ("Δοκίμασέ την.", "-12%"),
    ],
    "slides": [
        "Μια τόσο απλή εφαρμογή",
        "Χωρίς login",
        "Από και προς το αεροδρόμιο",
        "Δοκίμασέ την",
    ],
}

EN = {
    "out": ROOT / "taxi-and-fly-athens-to-airport-en.mp4",
    "art": Path("/opt/cursor/artifacts/taxi_and_fly_aplo_en.mp4"),
    "vo": BUILD / "vo_simple_en",
    "voice": "en-US-AndrewNeural",
    "lines": [
        ("Such a simple app.", "-12%"),
        ("No login.", "-12%"),
        ("To and from the airport.", "-16%"),
        ("Try it.", "-10%"),
    ],
    "slides": [
        "Such a simple app",
        "No login",
        "To and from the airport",
        "Try it",
    ],
}


def _center(draw: ImageDraw.ImageDraw, text: str, y: int, font, fill) -> int:
    bb = draw.textbbox((0, 0), text, font=font)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    draw.text(((W - tw) / 2, y), text, font=font, fill=fill)
    return th


def _wrapped(draw: ImageDraw.ImageDraw, text: str, y: int, font, fill, max_w: int = 960) -> int:
    words = text.split()
    lines: list[str] = []
    cur = ""
    for word in words:
        trial = f"{cur} {word}".strip()
        bb = draw.textbbox((0, 0), trial, font=font)
        if bb[2] - bb[0] <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    top = y
    for line in lines:
        th = _center(draw, line, top, font, fill)
        top += th + 16
    return top - y


def logo_ring() -> Image.Image:
    src = Image.open(LOGO).convert("RGB")
    ring = src.crop((220, 140, 860, 720))
    return ring.resize((520, 470), Image.Resampling.LANCZOS)


def brand_slide(phrase: str, dst: Path) -> None:
    """9:16 Taxi and Fly card — yellow ring + words. Never a phone."""
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    ring = logo_ring()
    img.paste(ring, ((W - ring.width) // 2, 340))
    f_brand = ImageFont.truetype(FONT, 70)
    f_t = ImageFont.truetype(FONT, 50)
    _center(draw, "Taxi and Fly", 880, f_brand, GOLD)
    if phrase and phrase != "Taxi and Fly":
        _wrapped(draw, phrase, 1020, f_t, WHITE)
    img.save(dst)


async def speak(text: str, dst: Path, voice: str, rate: str) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    last_err: Exception | None = None
    for attempt in range(8):
        try:
            comm = edge_tts.Communicate(text, voice, rate=rate, pitch="-1Hz")
            await comm.save(str(dst))
            if dst.exists() and dst.stat().st_size > 2000:
                return
            raise RuntimeError("empty")
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            print("retry", dst.name, exc)
            time.sleep(1.1 + attempt * 0.5)
    raise RuntimeError(last_err)


def mix_vo(starts: list[float], vo_files: list[Path], bed: Path, total: float, dst: Path) -> None:
    args: list[str] = ["-i", str(bed)]
    for p in vo_files:
        args += ["-i", str(p)]
    parts = ["[0:a]volume=0.20,aformat=sample_rates=44100:channel_layouts=stereo[bed]"]
    mix_in = "[bed]"
    for i, start in enumerate(starts, start=1):
        ms = int(round(start * 1000))
        parts.append(
            f"[{i}:a]aformat=sample_rates=44100:channel_layouts=stereo,"
            f"adelay={ms}|{ms},volume=1.35[v{i}]"
        )
        mix_in += f"[v{i}]"
    n = 1 + len(vo_files)
    parts.append(
        f"{mix_in}amix=inputs={n}:duration=first:dropout_transition=0:normalize=0,"
        f"alimiter=limit=0.95,atrim=0:{total:.3f},asetpts=PTS-STARTPTS[a]"
    )
    ff(
        *args, "-filter_complex", ";".join(parts), "-map", "[a]",
        "-t", f"{total:.3f}", "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "160k", str(dst),
    )


async def build(cfg: dict) -> None:
    vodir: Path = cfg["vo"]
    vodir.mkdir(parents=True, exist_ok=True)
    vo_files = []
    clips = []
    durs = []
    for i, (line, slide) in enumerate(zip(cfg["lines"], cfg["slides"])):
        text, rate = line
        mp3 = vodir / f"line_{i:02d}.mp3"
        print("TTS", text)

        await speak(text, mp3, cfg["voice"], rate)
        vo_files.append(mp3)
        sec = duration(mp3) + 0.85
        durs.append(sec)
        png = BUILD / f"brand_{cfg['out'].stem}_{i}.png"
        brand_slide(slide, png)
        clip = BUILD / f"brand_{cfg['out'].stem}_{i}.mp4"
        kenburns(png, clip, sec, 1.06, "center")
        clips.append(clip)

    silent = BUILD / f"brand_{cfg['out'].stem}_silent.mp4"
    xfade_concat(clips, silent, fade=0.18)
    starts = [0.0]
    acc = durs[0]
    for d in durs[1:]:
        starts.append(max(acc - 0.18, 0.05))
        acc = acc + d - 0.18
    total = max(acc, duration(silent))
    bed = BUILD / f"brand_{cfg['out'].stem}_bed.wav"
    pretty_music(total + 0.4, bed)
    mix_a = BUILD / f"brand_{cfg['out'].stem}_mix.m4a"
    mix_vo(starts, vo_files, bed, total + 0.05, mix_a)
    tmp = BUILD / f"brand_{cfg['out'].stem}_tmp.mp4"
    mix(silent, mix_a, tmp)
    ff(
        "-i", str(tmp),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "high",
        "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "160k",
        "-movflags", "+faststart", str(cfg["out"]),
    )
    cfg["art"].parent.mkdir(parents=True, exist_ok=True)
    cfg["art"].write_bytes(cfg["out"].read_bytes())
    print("Wrote", cfg["out"], round(duration(cfg["out"]), 2))


async def main() -> int:
    BUILD.mkdir(parents=True, exist_ok=True)
    if not LOGO.exists():
        raise SystemExit(f"missing logo {LOGO}")
    await build(EL)
    await build(EN)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
