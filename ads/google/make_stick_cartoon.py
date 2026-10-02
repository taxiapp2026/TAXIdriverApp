#!/usr/bin/env python3
"""Simple black stick-figure cartoon: home → Taxi and Fly → airport → brand."""

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
BUILD = ROOT / "build" / "stick"
ART = Path("/opt/cursor/artifacts")
OUT = ROOT / "taxi-and-fly-stick-cartoon.mp4"

sys.path.insert(0, str(ROOT))
from add_pretty_music import pretty_music  # noqa: E402
from build_video import FONT, FONT_REG, duration, ff, mix  # noqa: E402
from rebuild_brand_process import icon_lettering  # noqa: E402
from spot_audio import logo_sting  # noqa: E402

W, H, FPS = 1080, 1920, 30
GOLD = (255, 210, 40)
WHITE = (245, 245, 245)
INK = (22, 22, 22)
TAXI = (255, 210, 40)
ROAD = (55, 58, 65)
SKY = (214, 228, 240)
ROOM = (236, 232, 224)
GRASS = (170, 196, 150)
VOICE = "el-GR-NestorasNeural"
RATE = "-6%"

SPOKEN = (
    "Σπίτι. Πατάς Taxi and Fly. "
    "Έρχεται το ταξί. Σε αφήνει χαρούμενο στο αεροδρόμιο. "
    "Taxi and Fly. Από και προς το αεροδρόμιο Ελ Βενιζέλος, Αθήνα. "
    "Εφαρμογή με επαγγελματίες οδηγούς ταξί."
)


def ease(k: float) -> float:
    k = max(0.0, min(k, 1.0))
    return 1 - (1 - k) ** 3


def stick(draw: ImageDraw.ImageDraw, cx: float, cy: float, scale: float = 1.0, wave: float = 0.0, smile: bool = False) -> None:
    """Black stick person. cy is feet. wave: arm angle offset."""
    s = scale
    head_r = 28 * s
    body = 95 * s
    arm = 70 * s
    leg = 80 * s
    thick = max(6, int(8 * s))
    head_y = cy - leg - body - head_r
    hip_y = cy - leg
    shoulder_y = hip_y - body

    draw.ellipse(
        (cx - head_r, head_y - head_r, cx + head_r, head_y + head_r),
        outline=INK,
        width=thick,
    )
    if smile:
        draw.arc(
            (cx - 14 * s, head_y - 4 * s, cx + 14 * s, head_y + 16 * s),
            20,
            160,
            fill=INK,
            width=max(3, int(4 * s)),
        )
    draw.line((cx, head_y + head_r, cx, hip_y), fill=INK, width=thick)
    # arms
    draw.line(
        (cx, shoulder_y + 10 * s, cx - arm * 0.85, shoulder_y + arm * 0.7),
        fill=INK,
        width=thick,
    )
    ax = cx + arm * math.cos(math.radians(-25 + wave * 50))
    ay = shoulder_y + 10 * s + arm * math.sin(math.radians(55 - wave * 35))
    draw.line((cx, shoulder_y + 10 * s, ax, ay), fill=INK, width=thick)
    # legs
    draw.line((cx, hip_y, cx - 28 * s, cy), fill=INK, width=thick)
    draw.line((cx, hip_y, cx + 28 * s, cy), fill=INK, width=thick)


def house(draw: ImageDraw.ImageDraw, x: float, y: float, w: float = 340, h: float = 280) -> None:
    roof_h = h * 0.45
    draw.rectangle((x, y, x + w, y + h), outline=INK, width=8, fill=(250, 248, 242))
    draw.polygon(
        [(x - 20, y), (x + w / 2, y - roof_h), (x + w + 20, y)],
        outline=INK,
        fill=(230, 90, 80),
    )
    draw.line([(x - 20, y), (x + w / 2, y - roof_h), (x + w + 20, y)], fill=INK, width=8)
    # door + window
    dw, dh = 70, 120
    dx = x + w / 2 - dw / 2
    draw.rectangle((dx, y + h - dh, dx + dw, y + h), outline=INK, width=6, fill=(210, 180, 140))
    wx, wy, ww = x + 40, y + 50, 70
    draw.rectangle((wx, wy, wx + ww, wy + ww), outline=INK, width=6, fill=(180, 215, 235))
    draw.line((wx + ww / 2, wy, wx + ww / 2, wy + ww), fill=INK, width=4)
    draw.line((wx, wy + ww / 2, wx + ww, wy + ww / 2), fill=INK, width=4)


def phone(draw: ImageDraw.ImageDraw, cx: float, cy: float, lit: bool = True) -> None:
    pw, ph = 120, 210
    x0, y0 = cx - pw / 2, cy - ph / 2
    draw.rounded_rectangle((x0, y0, x0 + pw, y0 + ph), radius=22, fill=INK)
    screen = GOLD if lit else (40, 40, 40)
    draw.rounded_rectangle((x0 + 10, y0 + 22, x0 + pw - 10, y0 + ph - 28), radius=12, fill=screen)
    if lit:
        f = ImageFont.truetype(FONT, 18)
        t = "Taxi and Fly"
        tw = draw.textlength(t, font=f)
        draw.text((cx - tw / 2, cy - 10), t, font=f, fill=INK)


def taxi_car(draw: ImageDraw.ImageDraw, cx: float, cy: float, scale: float = 1.0) -> None:
    s = scale
    body_w, body_h = 220 * s, 70 * s
    cabin_w, cabin_h = 130 * s, 55 * s
    x0 = cx - body_w / 2
    y0 = cy - body_h
    draw.rounded_rectangle((x0, y0, x0 + body_w, y0 + body_h), radius=18, fill=TAXI, outline=INK, width=6)
    draw.rounded_rectangle(
        (cx - cabin_w / 2, y0 - cabin_h + 10, cx + cabin_w / 2, y0 + 10),
        radius=14,
        fill=TAXI,
        outline=INK,
        width=6,
    )
    # windows
    draw.rectangle(
        (cx - cabin_w / 2 + 12, y0 - cabin_h + 22, cx - 8, y0 - 4),
        fill=(170, 210, 230),
        outline=INK,
        width=3,
    )
    draw.rectangle(
        (cx + 8, y0 - cabin_h + 22, cx + cabin_w / 2 - 12, y0 - 4),
        fill=(170, 210, 230),
        outline=INK,
        width=3,
    )
    # wheels
    for wx in (cx - 70 * s, cx + 70 * s):
        draw.ellipse((wx - 22 * s, cy - 22 * s, wx + 22 * s, cy + 22 * s), fill=INK)
        draw.ellipse((wx - 10 * s, cy - 10 * s, wx + 10 * s, cy + 10 * s), fill=(200, 200, 200))
    # roof sign
    draw.rectangle((cx - 28 * s, y0 - cabin_h - 18 * s, cx + 28 * s, y0 - cabin_h + 4), fill=WHITE, outline=INK, width=4)
    f = ImageFont.truetype(FONT, max(14, int(16 * s)))
    tw = draw.textlength("TAXI", font=f)
    draw.text((cx - tw / 2, y0 - cabin_h - 16 * s), "TAXI", font=f, fill=INK)


def suitcase(draw: ImageDraw.ImageDraw, x: float, y: float) -> None:
    draw.rounded_rectangle((x, y, x + 55, y + 70), radius=8, outline=INK, width=5, fill=(90, 110, 140))
    draw.line((x + 12, y - 18, x + 43, y - 18), fill=INK, width=5)
    draw.line((x + 12, y - 18, x + 12, y), fill=INK, width=5)
    draw.line((x + 43, y - 18, x + 43, y), fill=INK, width=5)


def airport(draw: ImageDraw.ImageDraw) -> None:
    # terminal block
    draw.rectangle((80, 980, 1000, 1280), fill=(235, 238, 242), outline=INK, width=8)
    draw.polygon([(60, 980), (540, 820), (1020, 980)], fill=(200, 210, 220), outline=INK)
    draw.line([(60, 980), (540, 820), (1020, 980)], fill=INK, width=8)
    # glass doors
    for i in range(3):
        x = 220 + i * 200
        draw.rectangle((x, 1080, x + 140, 1280), outline=INK, width=5, fill=(160, 200, 225))
    # plane silhouette
    px, py = 780, 700
    draw.ellipse((px, py, px + 160, py + 40), fill=INK)
    draw.polygon([(px + 40, py + 10), (px + 10, py - 35), (px + 70, py + 10)], fill=INK)
    draw.polygon([(px + 100, py + 15), (px + 150, py + 55), (px + 90, py + 25)], fill=INK)
    f = ImageFont.truetype(FONT, 36)
    t = "ΑΕΡΟΔΡΟΜΙΟ"
    tw = draw.textlength(t, font=f)
    draw.text(((W - tw) / 2, 900), t, font=f, fill=INK)


def caption(draw: ImageDraw.ImageDraw, text: str, y: int = 160) -> None:
    f = ImageFont.truetype(FONT, 52)
    tw = draw.textlength(text, font=f)
    pad = 28
    draw.rounded_rectangle(
        ((W - tw) / 2 - pad, y - 18, (W + tw) / 2 + pad, y + 70),
        radius=20,
        fill=(255, 255, 255, 220) if False else (255, 255, 255),
        outline=INK,
        width=4,
    )
    draw.text(((W - tw) / 2, y), text, font=f, fill=INK)


def badge() -> Image.Image:
    size = 520
    mark = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(mark)
    d.ellipse((10, 10, size - 10, size - 10), outline=GOLD + (255,), width=16)
    letters = icon_lettering()
    inner = int(size * 0.58)
    sc = min(inner / letters.width, inner / letters.height)
    letters = letters.resize(
        (max(1, int(letters.width * sc)), max(1, int(letters.height * sc))),
        Image.Resampling.LANCZOS,
    )
    mark.alpha_composite(letters, ((size - letters.width) // 2, (size - letters.height) // 2))
    return mark


BADGE = None


def brand_end(t: float, start: float) -> Image.Image:
    global BADGE
    if BADGE is None:
        BADGE = badge()
    img = Image.new("RGBA", (W, H), (8, 8, 8, 255))
    draw = ImageDraw.Draw(img)
    # soft gold glow
    yy, xx = np.mgrid[0:H, 0:W]
    d = np.sqrt(((xx - W / 2) / 520.0) ** 2 + ((yy - 820) / 700.0) ** 2)
    a = np.clip(1.0 - d, 0.0, 1.0) ** 2.2 * 70
    glow = np.zeros((H, W, 4), dtype=np.uint8)
    glow[..., 0], glow[..., 1], glow[..., 2] = GOLD
    glow[..., 3] = a.astype(np.uint8)
    img.alpha_composite(Image.fromarray(glow, "RGBA"))

    since = max(t - start, 0.0)
    k = ease(min(since / 0.6, 1.0))
    mark = BADGE.resize((int(520 * (0.88 + 0.12 * k)), int(520 * (0.88 + 0.12 * k))), Image.Resampling.LANCZOS)
    img.alpha_composite(mark, ((W - mark.width) // 2, 420))

    f_brand = ImageFont.truetype(FONT, 78)
    f_line = ImageFont.truetype(FONT_REG, 42)
    f_url = ImageFont.truetype(FONT_REG, 30)
    fade = ease(min(max((since - 0.25) / 0.45, 0.0), 1.0))
    bw = draw.textlength("Taxi and Fly", font=f_brand)
    draw.text(((W - bw) / 2, 980), "Taxi and Fly", font=f_brand, fill=GOLD + (255,))
    lines = [
        "Από και προς αεροδρόμιο",
        "Ελ. Βενιζέλος · Αθήνα",
        "Επαγγελματίες οδηγοί ταξί",
    ]
    y = 1100
    for line in lines:
        tw = draw.textlength(line, font=f_line)
        draw.text(((W - tw) / 2, y), line, font=f_line, fill=WHITE + (int(245 * fade),))
        y += 58
    uw = draw.textlength("taxiapp2026.github.io/taxi-client-app", font=f_url)
    draw.text(((W - uw) / 2, y + 30), "taxiapp2026.github.io/taxi-client-app", font=f_url, fill=(160, 160, 160, int(230 * fade)))
    return img


def scene_home(t: float, local: float) -> Image.Image:
    img = Image.new("RGBA", (W, H), SKY + (255,))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 1200, W, H), fill=GRASS)
    house(draw, 200, 780)
    # figure walks a little toward door then stops with phone
    x = 720 + min(local, 1.0) * 20
    stick(draw, x, 1280, scale=1.15)
    suitcase(draw, x + 55, 1210)
    if local > 0.8:
        caption(draw, "Σπίτι")
    return img


def scene_call(t: float, local: float) -> Image.Image:
    img = Image.new("RGBA", (W, H), ROOM + (255,))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 1400, W, H), fill=(210, 205, 195))
    # big phone in center
    bob = math.sin(local * 6) * 8
    phone(draw, W / 2, 780 + bob, lit=True)
    # small figure below looking up
    stick(draw, W / 2, 1500, scale=1.05)
    pulse = 0.5 + 0.5 * math.sin(local * 10)
    f = ImageFont.truetype(FONT, 48)
    msg = "Κλήση Taxi and Fly"
    tw = draw.textlength(msg, font=f)
    draw.text(((W - tw) / 2, 1080), msg, font=f, fill=(int(40 + 80 * pulse),) * 2 + (40, 255))
    caption(draw, "Πατάς. Κλείνεις.")
    return img


def scene_pickup(t: float, local: float) -> Image.Image:
    img = Image.new("RGBA", (W, H), SKY + (255,))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 1250, W, H), fill=ROAD)
    draw.rectangle((0, 1250, W, 1270), fill=GOLD)
    # dashed road line
    for i in range(12):
        x = (i * 120 - int(local * 400) % 120)
        draw.rectangle((x, 1550, x + 60, 1570), fill=WHITE)

    car_x = -200 + ease(min(local / 0.55, 1.0)) * 740
    taxi_car(draw, car_x, 1480, scale=1.2)
    # figure waits then disappears into car
    if local < 0.7:
        stick(draw, 820, 1480, scale=1.1)
        suitcase(draw, 875, 1410)
    caption(draw, "Έρχεται το ταξί")
    return img


def scene_drive(t: float, local: float) -> Image.Image:
    img = Image.new("RGBA", (W, H), SKY + (255,))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 1200, W, H), fill=ROAD)
    # scrolling dashes
    for i in range(14):
        x = (i * 110 - int(local * 700) % 110)
        draw.rectangle((x, 1520, x + 55, 1540), fill=WHITE)
    # hills
    draw.ellipse((-100, 900, 500, 1400), fill=GRASS)
    draw.ellipse((600, 950, 1200, 1450), fill=(150, 180, 130))
    bounce = math.sin(local * 18) * 6
    taxi_car(draw, 540, 1450 + bounce, scale=1.35)
    # tiny head in window hint
    draw.ellipse((500, 1320 + bounce, 540, 1360 + bounce), outline=INK, width=5)
    caption(draw, "Προς αεροδρόμιο")
    return img


def scene_airport(t: float, local: float) -> Image.Image:
    img = Image.new("RGBA", (W, H), SKY + (255,))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 1280, W, H), fill=(190, 195, 200))
    airport(draw)
    # car arrives left, figure hops out happy
    car_x = 280 + (1 - ease(min(local / 0.4, 1.0))) * 200
    if local < 0.85:
        taxi_car(draw, car_x, 1550, scale=1.05)
    fig_x = 560 + ease(max((local - 0.35) / 0.5, 0.0)) * 120
    wave = ease(max((local - 0.45), 0.0))
    stick(draw, fig_x, 1550, scale=1.2, wave=wave, smile=local > 0.4)
    suitcase(draw, fig_x + 60, 1480)
    caption(draw, "Χαρούμενη άφιξη!")
    return img


# timeline: (name, seconds, renderer)
TIMELINE = [
    ("home", 2.2, scene_home),
    ("call", 2.4, scene_call),
    ("pickup", 2.3, scene_pickup),
    ("drive", 2.2, scene_drive),
    ("airport", 2.6, scene_airport),
    ("brand", 4.0, None),
]


async def speak(text: str, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    last: Exception | None = None
    for attempt in range(8):
        try:
            comm = edge_tts.Communicate(text, VOICE, rate=RATE, pitch="+0Hz")
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
        "[0:a]volume=0.22,afade=t=in:st=0:d=0.6,aformat=sample_rates=44100:channel_layouts=stereo[m];"
        "[1:a]volume=0.52,aformat=sample_rates=44100:channel_layouts=stereo[s];"
        "[2:a]highpass=f=80,equalizer=f=180:t=q:w=1:g=1.5,equalizer=f=2500:t=q:w=1:g=1.1,"
        "acompressor=threshold=-18dB:ratio=1.7:attack=12:release=120,"
        "aformat=sample_rates=44100:channel_layouts=stereo,volume=1.15[v];"
        "[m][s][v]amix=inputs=3:duration=longest:dropout_transition=0:normalize=0,"
        "loudnorm=I=-15:TP=-1.2:LRA=11,"
        f"alimiter=limit=0.95,atrim=0:{total:.3f},asetpts=PTS-STARTPTS[a]",
        "-map", "[a]", "-t", f"{total:.3f}",
        "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "192k", str(dst),
    )


async def main() -> int:
    BUILD.mkdir(parents=True, exist_ok=True)
    total = sum(s for _, s, _ in TIMELINE)
    print("total", total, "s")

    frames_dir = BUILD / "frames"
    shutil.rmtree(frames_dir, ignore_errors=True)
    frames_dir.mkdir(parents=True)

    brand_start = sum(s for _, s, fn in TIMELINE if fn is not None)
    t = 0.0
    idx = 0
    for name, seconds, fn in TIMELINE:
        n = int(round(seconds * FPS))
        for i in range(n):
            local = i / FPS
            abs_t = t + local
            if fn is None:
                img = brand_end(abs_t, brand_start)
            else:
                img = fn(abs_t, local)
            img.convert("RGB").save(frames_dir / f"{idx:05d}.png")
            idx += 1
        t += seconds
        print("scene", name, "done")

    silent = BUILD / "silent.mp4"
    ff(
        "-framerate", str(FPS), "-i", str(frames_dir / "%05d.png"),
        "-vf", "format=yuv420p,setsar=1",
        "-fps_mode", "cfr", "-r", str(FPS),
        "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-profile:v", "high", "-level", "4.0",
        "-g", str(FPS * 2), "-keyint_min", str(FPS), "-sc_threshold", "0",
        "-an", str(silent),
    )

    vo_mp3 = BUILD / "vo.mp3"
    await speak(SPOKEN, vo_mp3)
    vo_wav = BUILD / "vo.wav"
    ff("-i", str(vo_mp3), "-ac", "1", "-ar", "44100", str(vo_wav))

    vlen = duration(silent)
    # If VO is longer, pad video end a touch by freezing last frames via audio trim to video
    bed = BUILD / "bed.wav"
    pretty_music(vlen + 0.5, bed)
    sting = BUILD / "sting.wav"
    logo_sting(vlen + 0.5, brand_start + 0.15, sting)

    audio = BUILD / "mix.m4a"
    mix_audio(vo_wav, bed, sting, vlen + 0.05, audio)

    tmp = BUILD / "tmp.mp4"
    mix(silent, audio, tmp)
    ff(
        "-i", str(tmp),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.0",
        "-preset", "medium", "-crf", "18",
        "-fps_mode", "cfr", "-r", str(FPS),
        "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "192k",
        "-movflags", "+faststart", str(OUT),
    )
    ART.mkdir(parents=True, exist_ok=True)
    (ART / "taxi_and_fly_stick_cartoon.mp4").write_bytes(OUT.read_bytes())
    (ART / "downloads").mkdir(exist_ok=True)
    (ART / "downloads" / "stick-cartoon-taxi-and-fly.mp4").write_bytes(OUT.read_bytes())
    shutil.rmtree(frames_dir, ignore_errors=True)
    print("Wrote", OUT, round(duration(OUT), 2), "s")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
