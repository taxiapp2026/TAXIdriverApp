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
APP_LOGO = ROOT.parent / "meta" / "logo-app.png"
ICON = ROOT.parent / "meta" / "logo-icon.png"
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
    "art": Path("/opt/cursor/artifacts/taxi_and_fly_arga_kathara_el.mp4"),
    "vo": BUILD / "vo_simple_el",
    "voice": "el-GR-NestorasNeural",
    "rate": "-14%",
    "spoken": (
        "Taxi and Fly. Μια τόσο απλή εφαρμογή για μετακινήσεις. "
        "Από και προς το αεροδρόμιο. Χωρίς login. Δοκιμασέ την."
    ),
    "slides": [
        "Taxi and Fly",
        "Μια τόσο απλή εφαρμογή για μετακινήσεις",
        "Από και προς το αεροδρόμιο",
        "Χωρίς login",
        "Δοκίμασέ την",
    ],
}

EN = {
    "out": ROOT / "taxi-and-fly-athens-to-airport-en.mp4",
    "art": Path("/opt/cursor/artifacts/taxi_and_fly_simple_nat_en.mp4"),
    "vo": BUILD / "vo_simple_en",
    "voice": "en-US-AndrewNeural",
    "rate": "-10%",
    "spoken": "Taxi and Fly. Such a simple app for your trips. To and from the airport. No login. Try it.",
    "slides": [
        "Taxi and Fly",
        "Such a simple app for your trips",
        "To and from the airport",
        "No login",
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


def _knockout_light(src: Image.Image) -> Image.Image:
    im = src.convert("RGBA")
    px = list(im.getdata())
    cleaned = []
    for r, g, b, a in px:
        if r > 220 and g > 220 and b > 220:
            cleaned.append((0, 0, 0, 0))
        else:
            cleaned.append((r, g, b, a))
    im.putdata(cleaned)
    bbox = im.getbbox()
    return im.crop(bbox) if bbox else im


def icon_lettering() -> Image.Image:
    """Just the Taxi and Fly lettering — the rounded-square frame stripped off."""
    src = Image.open(ICON).convert("RGB")
    w, h = src.size
    art = src.crop((14, 14, w - 14, h - 14)).convert("RGBA")
    px = []
    for r, g, b, a in art.getdata():
        lit = max(r, g, b)
        # Keep gold and white glyphs; drop the dark plate behind them.
        px.append((r, g, b, 255) if lit > 110 else (0, 0, 0, 0))
    art.putdata(px)
    bbox = art.getbbox()
    return art.crop(bbox) if bbox else art


def brand_badge() -> Image.Image:
    """Smaller yellow ring with the lettering inside — no square frame."""
    size = 720
    badge = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(badge)
    pad = 120
    draw.ellipse((pad, pad, size - pad, size - pad), outline=GOLD + (255,), width=24)
    letters = icon_lettering()
    inner = size - 2 * pad - 130
    scale = min(inner / letters.width, inner / letters.height)
    letters = letters.resize(
        (max(1, int(letters.width * scale)), max(1, int(letters.height * scale))),
        Image.Resampling.LANCZOS,
    )
    badge.alpha_composite(letters, ((size - letters.width) // 2, (size - letters.height) // 2))
    return badge


def brand_slide(phrase: str, dst: Path) -> None:
    """9:16 card — square logo in a smaller ring + one line of copy."""
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    badge = brand_badge()
    img.paste(badge, ((W - badge.width) // 2, 360), badge)
    f_t = ImageFont.truetype(FONT, 50)
    if phrase and phrase != "Taxi and Fly":
        _wrapped(draw, phrase, 1160, f_t, WHITE)
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


def space_out(vo: Path, marks: list[dict], gap: float, dst: Path) -> list[dict]:
    """Re-cut the take with a breath between sentences so it lands slower."""
    total = duration(vo)
    bounds = [m["t"] for m in marks] + [total]
    parts = []
    for i in range(len(marks)):
        seg = BUILD / f"{dst.stem}_seg{i}.wav"
        ff(
            "-i", str(vo), "-ss", f"{bounds[i]:.3f}", "-to", f"{bounds[i + 1]:.3f}",
            "-ac", "1", "-ar", "44100", str(seg),
        )
        parts.append(seg)
    pause = BUILD / f"{dst.stem}_pause.wav"
    ff("-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", f"{gap:.3f}", str(pause))
    lst = BUILD / f"{dst.stem}_join.txt"
    joined: list[Path] = []
    for i, seg in enumerate(parts):
        joined.append(seg)
        if i < len(parts) - 1:
            joined.append(pause)
    lst.write_text("".join(f"file '{p.resolve()}'\n" for p in joined))
    ff("-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(dst))
    spaced: list[dict] = []
    acc = 0.0
    for i, m in enumerate(marks):
        seg_len = duration(parts[i])
        spaced.append({"t": acc, "dur": seg_len, "text": m["text"]})
        acc += seg_len + (gap if i < len(parts) - 1 else 0.0)
    return spaced


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
    spaced_vo = vodir / "story_spaced.wav"
    marks = space_out(mp3, marks, cfg.get("gap", 0.55), spaced_vo)
    mp3 = spaced_vo
    print("marks", marks)
    vo_sec = duration(mp3)
    starts = [0.0]
    for mark in marks[1:]:
        starts.append(max(mark["t"], starts[-1] + 0.4))
    ends = starts[1:] + [vo_sec + 0.9]
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
    # Re-encode the joined cards: stream-copied concats stutter on some phones.
    ff(
        "-f", "concat", "-safe", "0", "-i", str(lst),
        "-vf", f"fps={FPS},format=yuv420p,setsar=1",
        "-fps_mode", "cfr", "-r", str(FPS),
        "-c:v", "libx264", "-preset", "medium", "-crf", "19",
        "-profile:v", "high", "-level", "4.0",
        "-g", str(FPS * 2), "-keyint_min", str(FPS), "-sc_threshold", "0",
        "-an", str(silent),
    )
    total = duration(silent)
    bed = BUILD / f"brand_{cfg['out'].stem}_bed.wav"
    pretty_music(total + 0.4, bed)
    mix_a = BUILD / f"brand_{cfg['out'].stem}_mix.m4a"
    mix_vo(mp3, bed, total + 0.05, mix_a)
    tmp = BUILD / f"brand_{cfg['out'].stem}_tmp.mp4"
    mix(silent, mix_a, tmp)
    ff(
        "-i", str(tmp),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.0",
        "-preset", "medium", "-crf", "19",
        "-fps_mode", "cfr", "-r", str(FPS),
        "-g", str(FPS * 2), "-keyint_min", str(FPS), "-sc_threshold", "0",
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
