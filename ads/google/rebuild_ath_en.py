#!/usr/bin/env python3
"""English 9:16 ad: you're in Athens, you easily book a taxi to the airport."""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

import edge_tts
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / "build"
OUT = ROOT / "taxi-and-fly-athens-to-airport-en.mp4"
VO_DIR = BUILD / "vo_ath_en"
ARTIFACT = Path("/opt/cursor/artifacts/taxi_and_fly_athens_to_airport_en.mp4")
SRC = Path("/home/ubuntu/.cursor/projects/workspace/uploads/VID-20260926-WA0005_3361.mp4")

sys.path.insert(0, str(ROOT))
from build_video import FONT, FONT_REG, duration, ff, kenburns, make_audio, mix, xfade_concat  # noqa: E402

LINES = [
    "You're in Athens. You easily book a taxi for the airport.",
    "You open Taxi and Fly and fill in the form.",
    "Pickup in Athens. Destination: the airport.",
    "You pick the date and time.",
    "You see the price before you confirm.",
    "The driver accepts. Your booking is done.",
    "Taxi and Fly. Athens to the airport. With professional taxi drivers.",
]

# Raw phone footage: skip calendar and driver-app screens.
RAW = [
    (0.40, 5.20),   # open the app
    (7.60, 8.50),   # form
    (21.80, 6.40),  # pickup airport
    (46.20, 5.80),  # date + price button, no calendar
    (61.80, 6.20),  # fare on screen
    (70.40, 8.20),  # booking saved
    None,           # end card
]

VOICE = "en-US-AndrewNeural"
RATE = "-8%"
PITCH = "-1Hz"
HOLD = 0.45
FADE = 0.16
W, H, FPS = 1080, 1920, 30


async def speak(text: str, dst: Path, rate: str = RATE) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    last_err: Exception | None = None
    for attempt in range(8):
        try:
            comm = edge_tts.Communicate(text, VOICE, rate=rate, pitch=PITCH)
            await comm.save(str(dst))
            if dst.exists() and dst.stat().st_size > 2000:
                return
            raise RuntimeError(f"empty audio for {dst.name}")
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            print(f"retry {attempt + 1} {dst.name}: {exc}")
            time.sleep(1.2 + attempt * 0.6)
    raise RuntimeError(f"TTS failed for {text!r}: {last_err}")


def phone_clip(ss: float, take: float, dst: Path) -> None:
    vf = (
        f"crop=iw*0.78:ih*0.78:(iw-ow)/2:(ih-oh)/2,"
        f"scale={W}:{H}:force_original_aspect_ratio=increase,"
        f"crop={W}:{H},setsar=1,fps={FPS},eq=brightness=0.04:contrast=1.08,"
        f"format=yuv420p"
    )
    ff(
        "-i", str(SRC), "-ss", f"{ss:.3f}", "-t", f"{take:.3f}",
        "-vf", vf, "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-r", str(FPS), str(dst),
    )


def fit_clip(src: Path, dst: Path, seconds: float) -> None:
    cur = duration(src)
    vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps={FPS},format=yuv420p"
    if cur > seconds + 0.04:
        ff("-i", str(src), "-t", f"{seconds:.3f}", "-vf", vf, "-an",
           "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-r", str(FPS), str(dst))
        return
    pad = max(seconds - cur, 0)
    ff(
        "-i", str(src),
        "-vf", f"{vf},tpad=stop_mode=clone:stop_duration={pad:.3f}",
        "-t", f"{seconds:.3f}", "-an", "-c:v", "libx264", "-preset", "fast",
        "-crf", "18", "-r", str(FPS), str(dst),
    )


def make_end_card_png(dst: Path) -> None:
    img = Image.new("RGB", (W, H), (8, 8, 8))
    draw = ImageDraw.Draw(img)
    f_brand = ImageFont.truetype(FONT, 92)
    f_hero = ImageFont.truetype(FONT, 54)
    f_sub = ImageFont.truetype(FONT_REG, 40)

    def center(text: str, y: int, font, fill) -> None:
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        draw.text(((W - tw) / 2, y), text, font=font, fill=fill)

    center("Taxi and Fly", 700, f_brand, (255, 210, 40))
    center("Athens to the airport", 860, f_hero, (255, 255, 255))
    center("with professional taxi drivers", 960, f_sub, (255, 210, 40))
    img.save(dst)


def clip_starts(durs: list[float], fade: float) -> tuple[list[float], float]:
    starts = [0.0]
    acc = durs[0]
    for d in durs[1:]:
        starts.append(max(acc - fade, 0.05))
        acc = acc + d - fade
    return starts, acc


def mix_vo(starts: list[float], vo_files: list[Path], bed: Path, total: float, dst: Path) -> None:
    args: list[str] = ["-i", str(bed)]
    for p in vo_files:
        args += ["-i", str(p)]
    parts = ["[0:a]volume=0.16,aformat=sample_rates=44100:channel_layouts=stereo[bed]"]
    mix_in = "[bed]"
    n = 1 + len(vo_files)
    for i, start in enumerate(starts, start=1):
        delay_ms = int(round(start * 1000))
        parts.append(
            f"[{i}:a]aformat=sample_rates=44100:channel_layouts=stereo,"
            f"adelay={delay_ms}|{delay_ms},volume=1.35[v{i}]"
        )
        mix_in += f"[v{i}]"
    parts.append(
        f"{mix_in}amix=inputs={n}:duration=first:dropout_transition=0:normalize=0,"
        f"alimiter=limit=0.95,atrim=0:{total:.3f},asetpts=PTS-STARTPTS[a]"
    )
    ff(
        *args, "-filter_complex", ";".join(parts), "-map", "[a]",
        "-t", f"{total:.3f}", "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "160k",
        str(dst),
    )


async def main() -> int:
    if not SRC.exists():
        print("missing source", SRC)
        return 1
    VO_DIR.mkdir(parents=True, exist_ok=True)
    vo_files: list[Path] = []
    durs: list[float] = []
    for i, line in enumerate(LINES):
        mp3 = VO_DIR / f"line_{i:02d}.mp3"
        print("TTS", i, line)
        await speak(line, mp3)
        vo_files.append(mp3)
        durs.append(duration(mp3) + HOLD)
        print(f"  {durs[-1]:.2f}s")

    png = BUILD / "end_ath_en.png"
    make_end_card_png(png)
    end_raw = BUILD / "ath_end_raw.mp4"
    kenburns(png, end_raw, durs[-1], 1.08, "center")

    raws: list[Path] = []
    for i, spec in enumerate(RAW):
        dst = BUILD / f"ath_raw_{i:02d}.mp4"
        if spec is None:
            raws.append(end_raw)
            continue
        ss, take = spec
        print("cut", ss, take)
        phone_clip(ss, take, dst)
        raws.append(dst)

    fitted: list[Path] = []
    for i, (src, sec) in enumerate(zip(raws, durs)):
        dst = BUILD / f"ath_fit_{i:02d}.mp4"
        print("fit", src.name, f"{sec:.2f}s")
        fit_clip(src, dst, sec)
        fitted.append(dst)

    silent = BUILD / "ath_silent.mp4"
    xfade_concat(fitted, silent, fade=FADE)
    starts, total = clip_starts(durs, FADE)
    total = max(total, duration(silent))
    print("timeline", [round(s, 2) for s in starts], "total", round(total, 2))

    bed = BUILD / "ath_bed.wav"
    make_audio(total + 0.5, bed)
    mix_a = BUILD / "ath_mix.m4a"
    mix_vo(starts, vo_files, bed, total + 0.05, mix_a)
    tmp = BUILD / "ath_out.mp4"
    mix(silent, mix_a, tmp)
    ff(
        "-i", str(tmp),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "high",
        "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "160k",
        "-movflags", "+faststart", str(OUT),
    )
    ARTIFACT.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT.write_bytes(OUT.read_bytes())
    print("Wrote", OUT, round(duration(OUT), 2), OUT.stat().st_size)
    print("Artifact", ARTIFACT)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
