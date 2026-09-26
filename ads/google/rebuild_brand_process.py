#!/usr/bin/env python3
"""Brand-only explainer: how Taxi and Fly works. No phone-on-table footage."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

import edge_tts
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / "build"
STILLS = ROOT / "stills"
LOGO = ROOT.parent / "meta" / "logo-taxi-and-fly.png"
W, H, FPS = 1080, 1920, 30

import sys

sys.path.insert(0, str(ROOT))
from build_video import FONT, FONT_REG, duration, ff, kenburns, make_audio, mix, xfade_concat  # noqa: E402

EL = {
    "out": ROOT / "taxi-and-fly-process-el.mp4",
    "art": Path("/opt/cursor/artifacts/taxi_and_fly_diadikasia.mp4"),
    "vo": BUILD / "vo_proc_el",
    "voice": "el-GR-NestorasNeural",
    "rate": "-10%",
    "lines": [
        "Ξεκινά το Taxi and Fly.",
        "Μια τόσο απλή εφαρμογή. Χωρίς login.",
        "Συμπληρώνεις τη φόρμα και κλείνει το ραντεβού.",
        "Το ραντεβού πάει στον φάκελο. Πατάς και μιλάς με τον οδηγό.",
        "Κλείνεις τόσο εύκολα, από και προς το αεροδρόμιο. Δοκίμασέ την.",
    ],
    "slides": [
        ("Taxi and Fly", "Ξεκινά"),
        ("Χωρίς login", "τόσο απλή εφαρμογή"),
        ("Συμπληρώνεις", "και κλείνει το ραντεβού"),
        ("Στον φάκελο", "πατάς και μιλάς με τον οδηγό"),
        ("Από και προς το αεροδρόμιο", "Δοκίμασέ την"),
    ],
}

EN = {
    "out": ROOT / "taxi-and-fly-process-en.mp4",
    "art": Path("/opt/cursor/artifacts/taxi_and_fly_how_it_works.mp4"),
    "vo": BUILD / "vo_proc_en",
    "voice": "en-US-AndrewNeural",
    "rate": "-8%",
    "lines": [
        "This is Taxi and Fly.",
        "Such a simple app. No login.",
        "You fill in the form and the appointment is booked.",
        "It goes in the folder. You tap it and talk to the driver.",
        "You book so easily, to and from the airport. Try it.",
    ],
    "slides": [
        ("Taxi and Fly", "Here we go"),
        ("No login", "such a simple app"),
        ("Fill in the form", "and you're booked"),
        ("In the folder", "tap and talk to the driver"),
        ("To and from the airport", "Try it"),
    ],
}


def brand_slide(title: str, sub: str, dst: Path) -> None:
    img = Image.new("RGB", (W, H), (8, 8, 8))
    draw = ImageDraw.Draw(img)
    if LOGO.exists():
        mark = Image.open(LOGO).convert("RGB").resize((280, 280))
        img.paste(mark, ((W - 280) // 2, 420))
    f_t = ImageFont.truetype(FONT, 64)
    f_s = ImageFont.truetype(FONT_REG, 40)

    def center(text: str, y: int, font, fill) -> None:
        bb = draw.textbbox((0, 0), text, font=font)
        draw.text(((W - (bb[2] - bb[0])) / 2, y), text, font=font, fill=fill)

    center(title, 760, f_t, (255, 210, 40))
    center(sub, 860, f_s, (240, 240, 240))
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
    parts = ["[0:a]volume=0.14,aformat=sample_rates=44100:channel_layouts=stereo[bed]"]
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
    photos = [
        STILLS / "05_taxi_pickup.png",
        STILLS / "04_athens_arrivals.png",
        STILLS / "06_in_taxi_athens.png",
        STILLS / "05b_getting_in.png",
        STILLS / "07_destination_athens.png",
    ]
    vo_files = []
    clips = []
    durs = []
    for i, (line, slide, photo) in enumerate(zip(cfg["lines"], cfg["slides"], photos)):
        mp3 = vodir / f"line_{i:02d}.mp3"
        print("TTS", line)
        await speak(line, mp3, cfg["voice"], cfg["rate"])
        vo_files.append(mp3)
        sec = duration(mp3) + 0.65
        durs.append(sec)
        png = BUILD / f"proc_{cfg['out'].stem}_{i}.png"
        brand_slide(slide[0], slide[1], png)
        # Brand slide over a Taxi and Fly still — not a phone on a table.
        still = BUILD / f"proc_still_{cfg['out'].stem}_{i}.mp4"
        slidev = BUILD / f"proc_slide_{cfg['out'].stem}_{i}.mp4"
        kenburns(photo, still, sec, 1.10, "center")
        kenburns(png, slidev, sec, 1.04, "center")
        # 55% photo, then fade to brand words
        half = max(sec * 0.45, 1.1)
        mixv = BUILD / f"proc_mix_{cfg['out'].stem}_{i}.mp4"
        ff(
            "-i", str(still), "-i", str(slidev),
            "-filter_complex",
            f"[0:v][1:v]xfade=transition=fade:duration=0.35:offset={half:.3f},format=yuv420p[v]",
            "-map", "[v]", "-t", f"{sec:.3f}", "-an",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-r", str(FPS), str(mixv),
        )
        clips.append(mixv)

    silent = BUILD / f"proc_{cfg['out'].stem}_silent.mp4"
    xfade_concat(clips, silent, fade=0.16)
    starts = [0.0]
    acc = durs[0]
    for d in durs[1:]:
        starts.append(max(acc - 0.16, 0.05))
        acc = acc + d - 0.16
    total = max(acc, duration(silent))
    bed = BUILD / f"proc_{cfg['out'].stem}_bed.wav"
    make_audio(total + 0.4, bed)
    mix_a = BUILD / f"proc_{cfg['out'].stem}_mix.m4a"
    mix_vo(starts, vo_files, bed, total + 0.05, mix_a)
    tmp = BUILD / f"proc_{cfg['out'].stem}_tmp.mp4"
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
    await build(EL)
    await build(EN)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
