#!/usr/bin/env python3
"""Text-only Taxi and Fly spot — no comics, just words + VO + music."""

from __future__ import annotations

import asyncio
import math
import shutil
import sys
import time
from pathlib import Path

import edge_tts
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / "build" / "textspot"
ART = Path("/opt/cursor/artifacts")

sys.path.insert(0, str(ROOT))
from build_video import FONT, FONT_REG, duration, ff, mix  # noqa: E402
from rebuild_brand_process import icon_lettering  # noqa: E402
from spot_audio import hope_music, logo_sting  # noqa: E402

W, H, FPS = 1080, 1920, 30
GOLD = (255, 210, 40)
WHITE = (245, 245, 245)
SOFT = (190, 190, 190)
BG = (8, 8, 8, 255)
APP_URL = "taxiapp2026.github.io/taxi-client-app"
VOICE = "el-GR-NestorasNeural"
RATE = "-14%"
TAIL = 1.5
HOLD = 1.05

# On-screen text = spoken line.
VARIANTS = {
    "agapi": {
        "out": ROOT / "taxi-and-fly-text-agapi.mp4",
        "art": "taxi_and_fly_text_agapi.mp4",
        "download": "text-agapi.mp4",
        "brand_lines": ["Από και προς το αεροδρόμιο"],
        "lines": [
            "Είμαστε μια καινούργια ελληνική εφαρμογή",
            "Σκοπός μας είναι ο πελάτης να εξυπηρετηθεί\n"
            "με τον πιο επαγγελματικό και εύκολο τρόπο,\n"
            "για να χτιστεί μια καλή σχέση με την εφαρμογή",
            "Και η γνώμη του κάθε πελάτη\nθα βελτιώνει την εφαρμογή",
            "Ο επαγγελματίας οδηγός ταξί\nέχει μια εφαρμογή χωρίς μεσάζοντες",
            "Κανείς δεν αποφασίζει για εκείνον\nκανείς δεν παίρνει από το κομμάτι του",
            "Εδώ οι επαγγελματίες οδηγοί ταξί ενώνονται",
            "Γνωρίζοντας την εφαρμογή στον κόσμο\nο ένας δίνει δουλειά στον άλλον",
            "Αγάπη και για τον πελάτη\nκαι για τον οδηγό ταξί",
            "Για αυτό αξίζει η εφαρμογή",
        ],
    },
    # Short punch: love + worth it only
    "axizei": {
        "out": ROOT / "taxi-and-fly-text-axizei.mp4",
        "art": "taxi_and_fly_text_axizei.mp4",
        "download": "text-axizei.mp4",
        "brand_lines": ["Από και προς το αεροδρόμιο"],
        "lines": [
            "Αγάπη και για τον πελάτη\nκαι για τον οδηγό ταξί",
            "Για αυτό αξίζει η εφαρμογή",
        ],
    },
    # Fast clear 4-line spot
    "grigoro": {
        "out": ROOT / "taxi-and-fly-text-grigoro.mp4",
        "art": "taxi_and_fly_text_grigoro.mp4",
        "download": "text-grigoro.mp4",
        "brand_lines": ["Από και προς το αεροδρόμιο"],
        "hold": 0.55,
        "rate": "-6%",
        "lines": [
            "Καινούργια ελληνική εφαρμογή",
            "Εύκολη εξυπηρέτηση για τον πελάτη",
            "Χωρίς μεσάζοντες για τον οδηγό ταξί",
            "Αγάπη και για τους δύο\nΓια αυτό αξίζει",
        ],
    },
}


def ease(k: float) -> float:
    k = max(0.0, min(k, 1.0))
    return 1 - (1 - k) ** 3


def glow_layer() -> Image.Image:
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt(((xx - W / 2) / 540.0) ** 2 + ((yy - H * 0.42) / 720.0) ** 2)
    a = np.clip(1.0 - d, 0.0, 1.0) ** 2.2 * 90.0
    rgba = np.zeros((H, W, 4), dtype=np.uint8)
    rgba[..., 0], rgba[..., 1], rgba[..., 2] = GOLD
    rgba[..., 3] = a.astype(np.uint8)
    return Image.fromarray(rgba, "RGBA")


GLOW = glow_layer()
BADGE: Image.Image | None = None


def badge_image() -> Image.Image:
    global BADGE
    if BADGE is None:
        size = 560
        mark = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(mark)
        d.ellipse((12, 12, size - 12, size - 12), outline=GOLD + (255,), width=18)
        letters = icon_lettering()
        inner = int(size * 0.58)
        sc = min(inner / letters.width, inner / letters.height)
        letters = letters.resize(
            (max(1, int(letters.width * sc)), max(1, int(letters.height * sc))),
            Image.Resampling.LANCZOS,
        )
        mark.alpha_composite(letters, ((size - letters.width) // 2, (size - letters.height) // 2))
        BADGE = mark
    return BADGE


def background(t: float) -> Image.Image:
    img = Image.new("RGBA", (W, H), BG)
    drift = int(18 * math.sin(t * 0.45))
    img.alpha_composite(GLOW, (0, drift))
    # subtle vignette edge
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, W, 8), fill=(0, 0, 0, 80))
    return img


def fit_block(draw: ImageDraw.ImageDraw, text: str, max_w: float = 920) -> tuple[ImageFont.FreeTypeFont, list[str], int]:
    lines = [ln.strip() for ln in text.split("\n") if ln.strip()] or [text]
    for size in range(54, 28, -2):
        f = ImageFont.truetype(FONT, size)
        if all(draw.textlength(ln, font=f) <= max_w for ln in lines):
            return f, lines, int(size + 14)
    f = ImageFont.truetype(FONT, 28)
    return f, lines, 42


def text_frame(t: float, local: float, line: str, index: int, total_lines: int) -> Image.Image:
    img = background(t)
    draw = ImageDraw.Draw(img)

    # progress dots
    for i in range(total_lines):
        cx = W / 2 - (total_lines - 1) * 14 + i * 28
        r = 5 if i == index else 3
        fill = GOLD if i <= index else (70, 70, 70)
        draw.ellipse((cx - r, 160 - r, cx + r, 160 + r), fill=fill + (255,))

    fade = ease(min(local / 0.45, 1.0))
    rise = (1 - fade) * 28
    f, lines, line_h = fit_block(draw, line)
    block_h = len(lines) * line_h
    top = H / 2 - block_h / 2 - 40 + rise

    for i, ln in enumerate(lines):
        tw = draw.textlength(ln, font=f)
        draw.text(((W - tw) / 2, top + i * line_h), ln, font=f, fill=WHITE + (int(255 * fade),))

    # gold underline
    bar_w = 220 * fade
    bar_y = top + block_h + 36
    if bar_w > 2:
        draw.rounded_rectangle(
            (W / 2 - bar_w / 2, bar_y, W / 2 + bar_w / 2, bar_y + 6),
            radius=4,
            fill=GOLD + (int(230 * fade),),
        )
    return img


def brand_frame(t: float, start: float, lines: list[str]) -> Image.Image:
    img = background(t)
    draw = ImageDraw.Draw(img)
    since = max(t - start, 0.0)
    k = ease(min(since / 0.55, 1.0))
    mark = badge_image()
    size = int(560 * (0.90 + 0.10 * k))
    mark = mark.resize((size, size), Image.Resampling.LANCZOS)
    img.alpha_composite(mark, ((W - size) // 2, 380))

    f_brand = ImageFont.truetype(FONT, 78)
    f_line = ImageFont.truetype(FONT_REG, 40)
    f_url = ImageFont.truetype(FONT_REG, 28)
    fade = ease(min(max((since - 0.2) / 0.45, 0.0), 1.0))
    bw = draw.textlength("Taxi and Fly", font=f_brand)
    draw.text(((W - bw) / 2, 980), "Taxi and Fly", font=f_brand, fill=GOLD + (255,))
    y = 1100
    for line in lines:
        tw = draw.textlength(line, font=f_line)
        draw.text(((W - tw) / 2, y), line, font=f_line, fill=WHITE + (int(245 * fade),))
        y += 54
    uw = draw.textlength(APP_URL, font=f_url)
    draw.text(((W - uw) / 2, y + 30), APP_URL, font=f_url, fill=SOFT + (int(230 * fade),))
    return img


async def speak(text: str, dst: Path, rate: str = RATE) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    last: Exception | None = None
    for attempt in range(8):
        try:
            comm = edge_tts.Communicate(text, VOICE, rate=rate, pitch="+0Hz")
            audio = bytearray()
            async for chunk in comm.stream():
                if chunk["type"] == "audio":
                    audio.extend(chunk["data"])
            if len(audio) < 2000:
                raise RuntimeError("empty audio")
            dst.write_bytes(bytes(audio))
            return
        except Exception as exc:  # noqa: BLE001
            last = exc
            print("retry tts", exc)
            time.sleep(1.0 + attempt * 0.4)
    raise RuntimeError(last)


def mix_audio(vo: Path, bed: Path, sting: Path, total: float, dst: Path) -> None:
    ff(
        "-i", str(bed), "-i", str(sting), "-i", str(vo),
        "-filter_complex",
        "[0:a]volume=0.30,afade=t=in:st=0:d=0.8,"
        f"afade=t=out:st={max(total - 1.8, 0.5):.2f}:d=1.5,"
        "aformat=sample_rates=44100:channel_layouts=stereo[m];"
        "[1:a]volume=0.55,aformat=sample_rates=44100:channel_layouts=stereo[s];"
        "[2:a]highpass=f=80,equalizer=f=180:t=q:w=1:g=1.5,equalizer=f=2500:t=q:w=1:g=1.1,"
        "acompressor=threshold=-18dB:ratio=1.6:attack=12:release=120,"
        "aformat=sample_rates=44100:channel_layouts=stereo,volume=1.15,"
        f"apad=pad_dur={TAIL:.2f}[v];"
        "[m][s][v]amix=inputs=3:duration=longest:dropout_transition=0:normalize=0,"
        "loudnorm=I=-14:TP=-1.0:LRA=11,"
        f"alimiter=limit=0.96,atrim=0:{total:.3f},asetpts=PTS-STARTPTS[a]",
        "-map", "[a]", "-t", f"{total:.3f}",
        "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "192k", str(dst),
    )


async def build_one(slug: str, copy: dict) -> Path:
    work = BUILD / slug
    work.mkdir(parents=True, exist_ok=True)
    lines: list[str] = list(copy["lines"])
    out: Path = copy["out"]

    parts: list[Path] = []
    scene_durs: list[float] = []
    hold = float(copy.get("hold", HOLD))
    rate = str(copy.get("rate", RATE))
    for i, line in enumerate(lines):
        mp3 = work / f"line_{i}.mp3"
        wav = work / f"line_{i}.wav"
        await speak(line.replace("\n", " ") + ".", mp3, rate=rate)
        ff("-i", str(mp3), "-ac", "1", "-ar", "44100", str(wav))
        pad = work / f"line_{i}_pad.wav"
        ff("-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", f"{hold:.3f}", str(pad))
        d = duration(wav) + hold
        scene_durs.append(d)
        parts.extend([wav, pad])
        print(f"[text-{slug}] {i + 1}: «{line.replace(chr(10), ' ')}» {d:.2f}s")

    brand_mp3 = work / "brand.mp3"
    brand_wav = work / "brand.wav"
    await speak("Taxi and Fly. Από και προς το αεροδρόμιο.", brand_mp3, rate=rate)
    ff("-i", str(brand_mp3), "-ac", "1", "-ar", "44100", str(brand_wav))
    brand_pad = work / "brand_pad.wav"
    ff("-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", f"{TAIL:.3f}", str(brand_pad))
    brand_voice = duration(brand_wav)
    brand_dur = brand_voice + TAIL + 1.6
    parts.extend([brand_wav, brand_pad])

    lst = work / "vo_join.txt"
    lst.write_text("".join(f"file '{p.resolve()}'\n" for p in parts))
    vo_wav = work / "vo.wav"
    ff("-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(vo_wav))

    story_dur = sum(scene_durs)
    brand_start = story_dur
    total = story_dur + brand_dur
    print(f"[text-{slug}] total {total:.2f}s")

    frames = work / "frames"
    shutil.rmtree(frames, ignore_errors=True)
    frames.mkdir(parents=True)

    idx = 0
    t_abs = 0.0
    for i, (line, seconds) in enumerate(zip(lines, scene_durs)):
        n = int(round(seconds * FPS))
        for f_i in range(n):
            local = f_i / FPS
            img = text_frame(t_abs + local, local, line, i, len(lines))
            img.convert("RGB").save(frames / f"{idx:05d}.png")
            idx += 1
        t_abs += seconds

    need = int(round(total * FPS))
    while idx < need:
        t = idx / FPS
        img = brand_frame(t, brand_start, copy["brand_lines"])
        img.convert("RGB").save(frames / f"{idx:05d}.png")
        idx += 1

    silent = work / "silent.mp4"
    ff(
        "-framerate", str(FPS), "-i", str(frames / "%05d.png"),
        "-vf", "format=yuv420p,setsar=1",
        "-fps_mode", "cfr", "-r", str(FPS),
        "-frames:v", str(need),
        "-c:v", "libx264", "-preset", "medium", "-crf", "17",
        "-profile:v", "high", "-level", "4.0",
        "-g", str(FPS * 2), "-keyint_min", str(FPS), "-sc_threshold", "0",
        "-an", str(silent),
    )

    vlen = duration(silent)
    bed = work / "bed.wav"
    hope_music(vlen + 0.5, bed)
    sting = work / "sting.wav"
    logo_sting(vlen + 0.5, brand_start + 0.15, sting)
    audio = work / "mix.m4a"
    mix_audio(vo_wav, bed, sting, vlen, audio)

    tmp = work / "tmp.mp4"
    mix(silent, audio, tmp)
    ff(
        "-i", str(tmp),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.0",
        "-preset", "medium", "-crf", "17",
        "-fps_mode", "cfr", "-r", str(FPS),
        "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "192k",
        "-movflags", "+faststart", str(out),
    )

    ART.mkdir(parents=True, exist_ok=True)
    (ART / "downloads").mkdir(parents=True, exist_ok=True)
    data = out.read_bytes()
    (ART / copy["art"]).write_bytes(data)
    (ART / "downloads" / copy["download"]).write_bytes(data)
    shutil.rmtree(frames, ignore_errors=True)
    print("Wrote", out.name, round(duration(out), 2), "s")
    return out


async def main(argv: list[str] | None = None) -> int:
    wanted = set(sys.argv[1:] if argv is None else argv)
    items = [(k, v) for k, v in VARIANTS.items() if not wanted or k in wanted]
    if not items:
        print("Known:", ", ".join(VARIANTS))
        return 1
    for slug, copy in items:
        await build_one(slug, copy)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
