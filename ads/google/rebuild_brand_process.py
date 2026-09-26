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
from build_video import FONT, duration, ff, kenburns, mix  # noqa: E402

EL = {
    "out": ROOT / "taxi-and-fly-athens-to-airport-el.mp4",
    "art": Path("/opt/cursor/artifacts/taxi_and_fly_start_el.mp4"),
    "vo": BUILD / "vo_simple_el",
    "voice": "el-GR-NestorasNeural",
    "rate": "-6%",
    "spoken": "Taxi and Fly. Μια τόσο απλή εφαρμογή. Χωρίς login. Από και προς το αεροδρόμιο. Δοκίμασέ την.",
    "slides": [
        "Taxi and Fly",
        "Μια τόσο απλή εφαρμογή",
        "Χωρίς login",
        "Από και προς το αεροδρόμιο",
        "Δοκίμασέ την",
    ],
}

EN = {
    "out": ROOT / "taxi-and-fly-athens-to-airport-en.mp4",
    "art": Path("/opt/cursor/artifacts/taxi_and_fly_simple_nat_en.mp4"),
    "vo": BUILD / "vo_simple_en",
    "voice": "en-US-AndrewNeural",
    "rate": "-4%",
    "spoken": "Taxi and Fly. Such a simple app. No login. To and from the airport. Try it.",
    "slides": [
        "Taxi and Fly",
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
    # Yellow ring only — not the misspelled wordmark baked into the PNG.
    ring = src.crop((248, 155, 832, 500))
    return ring.resize((560, 330), Image.Resampling.LANCZOS)


def brand_slide(phrase: str, dst: Path) -> None:
    """9:16 Taxi and Fly card — yellow ring + words. Never a phone."""
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    ring = logo_ring()
    img.paste(ring, ((W - ring.width) // 2, 420))
    f_brand = ImageFont.truetype(FONT, 70)
    f_t = ImageFont.truetype(FONT, 50)
    _center(draw, "Taxi and Fly", 820, f_brand, GOLD)
    if phrase and phrase != "Taxi and Fly":
        _wrapped(draw, phrase, 960, f_t, WHITE)
    img.save(dst)


TICKS = 10_000_000.0


async def speak_story(text: str, dst: Path, voice: str, rate: str) -> list[dict]:
    """One natural take. Sentence timings drive the pictures."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    last_err: Exception | None = None
    for attempt in range(8):
        try:
            comm = edge_tts.Communicate(
                text, voice, rate=rate, pitch="+0Hz", boundary="SentenceBoundary"
            )
            audio = bytearray()
            marks: list[dict] = []
            async for chunk in comm.stream():
                if chunk["type"] == "audio":
                    audio.extend(chunk["data"])
                elif chunk["type"] == "SentenceBoundary":
                    marks.append({
                        "t": chunk["offset"] / TICKS,
                        "dur": chunk["duration"] / TICKS,
                        "text": chunk["text"],
                    })
            if len(audio) < 2000:
                raise RuntimeError("empty")
            dst.write_bytes(bytes(audio))
            return marks
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            print("retry", dst.name, exc)
            time.sleep(1.1 + attempt * 0.5)
    raise RuntimeError(last_err)


def mix_vo(vo: Path, bed: Path, total: float, dst: Path) -> None:
    ff(
        "-i", str(bed), "-i", str(vo),
        "-filter_complex",
        "[0:a]volume=0.16,aformat=sample_rates=44100:channel_layouts=stereo[bed];"
        "[1:a]highpass=f=80,equalizer=f=160:t=q:w=1:g=1.8,equalizer=f=2600:t=q:w=1:g=1.2,"
        "acompressor=threshold=-18dB:ratio=1.8:attack=15:release=140,"
        "aformat=sample_rates=44100:channel_layouts=stereo,volume=1.18[v];"
        f"[bed][v]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,"
        f"alimiter=limit=0.95,atrim=0:{total:.3f},asetpts=PTS-STARTPTS[a]",
        "-map", "[a]",
        "-t", f"{total:.3f}", "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "160k", str(dst),
    )


async def build(cfg: dict) -> None:
    vodir: Path = cfg["vo"]
    vodir.mkdir(parents=True, exist_ok=True)
    mp3 = vodir / "story.mp3"
    print("TTS", cfg["spoken"])
    marks = await speak_story(cfg["spoken"], mp3, cfg["voice"], cfg["rate"])
    print("marks", marks)
    vo_sec = duration(mp3)
    starts = [0.0]
    for mark in marks[1:]:
        starts.append(max(mark["t"], starts[-1] + 0.4))
    ends = starts[1:] + [vo_sec + 0.75]
    durs = [max(e - s, 1.2) for s, e in zip(starts, ends)]
    clips = []
    for i, (slide, sec) in enumerate(zip(cfg["slides"], durs)):
        png = BUILD / f"brand_{cfg['out'].stem}_{i}.png"
        brand_slide(slide, png)
        clip = BUILD / f"brand_{cfg['out'].stem}_{i}.mp4"
        kenburns(png, clip, sec, 1.05, "center")
        clips.append(clip)

    silent = BUILD / f"brand_{cfg['out'].stem}_silent.mp4"
    lst = BUILD / f"brand_{cfg['out'].stem}_concat.txt"
    lst.write_text("".join(f"file '{c.resolve()}'\n" for c in clips))
    ff("-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(silent))
    total = duration(silent)
    bed = BUILD / f"brand_{cfg['out'].stem}_bed.wav"
    pretty_music(total + 0.4, bed)
    mix_a = BUILD / f"brand_{cfg['out'].stem}_mix.m4a"
    mix_vo(mp3, bed, total + 0.05, mix_a)
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
