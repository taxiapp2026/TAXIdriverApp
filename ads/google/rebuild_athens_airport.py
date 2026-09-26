#!/usr/bin/env python3
"""Athens → airport ad. Few pictures, voice carries the story."""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

import edge_tts
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / "build"
SRC = Path("/home/ubuntu/.cursor/projects/workspace/uploads/VID-20260926-WA0005_3361.mp4")
W, H, FPS = 1080, 1920, 30

sys.path.insert(0, str(ROOT))
from build_video import FONT, FONT_REG, duration, ff, kenburns, make_audio, mix, xfade_concat  # noqa: E402

# Long-ish chunks. Do not cut on every tap.
BEATS = [
    (5.2, 8.5),     # fill the form
    (62.5, 8.5),    # appointment is booked
    (76.5, 8.0),    # appointment is in the folder
    (84.0, 10.0),   # tap it → contact the driver
]

EL = {
    "out": ROOT / "taxi-and-fly-athens-to-airport-el.mp4",
    "art": Path("/opt/cursor/artifacts/taxi_and_fly_athina_aerodromio.mp4"),
    "vo": BUILD / "vo_ath_el",
    "voice": "el-GR-NestorasNeural",
    "rate": "-10%",
    "lines": [
        "Ανοίγεις την εφαρμογή.",
        "Συμπληρώνεις τη φόρμα. Κλείνει το ραντεβού.",
        "Το ραντεβού πάει στον φάκελο.",
        "Πατάς το ραντεβού και μιλάς με τον οδηγό.",
    ],
    "end": [
        ("Taxi and Fly.", "-8%"),
        ("Από την Αθήνα προς το αεροδρόμιο.", "-16%"),
        ("Με επαγγελματίες οδηγούς ταξί.", "-10%"),
    ],
    "card": ("Από την Αθήνα", "προς το αεροδρόμιο"),
    "card_sub": "με επαγγελματίες οδηγούς ταξί",
}

EN = {
    "out": ROOT / "taxi-and-fly-athens-to-airport-en.mp4",
    "art": Path("/opt/cursor/artifacts/taxi_and_fly_athens_to_airport_en.mp4"),
    "vo": BUILD / "vo_ath_en",
    "voice": "en-US-AndrewNeural",
    "rate": "-8%",
    "lines": [
        "You open the app.",
        "You fill in the form. The appointment is booked.",
        "The appointment goes into the folder.",
        "You tap the appointment and you talk to the driver.",
    ],
    "end": [
        ("Taxi and Fly.", "-6%"),
        ("From Athens to the airport.", "-14%"),
        ("With professional taxi drivers.", "-8%"),
    ],
    "card": ("From Athens", "to the airport"),
    "card_sub": "with professional taxi drivers",
}


async def speak(text: str, dst: Path, voice: str, rate: str) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    last_err: Exception | None = None
    for attempt in range(8):
        try:
            comm = edge_tts.Communicate(text, voice, rate=rate, pitch="-1Hz")
            await comm.save(str(dst))
            if dst.exists() and dst.stat().st_size > 2000:
                return
            raise RuntimeError(f"empty {dst.name}")
        except Exception as exc:  # noqa: BLE001
            last_err = exc
            print("retry", dst.name, exc)
            time.sleep(1.1 + attempt * 0.5)
    raise RuntimeError(last_err)


def phone_clip(ss: float, dur: float, dst: Path) -> None:
    """Put the table-phone shot on a 9:16 board. No aggressive crop."""
    vf = (
        f"scale=1080:-2,setsar=1,"
        f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:black,"
        f"fps={FPS},format=yuv420p"
    )
    ff(
        "-ss", f"{ss:.3f}", "-i", str(SRC), "-t", f"{dur:.3f}",
        "-vf", vf, "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-r", str(FPS), str(dst),
    )


def fit(src: Path, dst: Path, seconds: float) -> None:
    cur = duration(src)
    vf = f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:black,fps={FPS},format=yuv420p"
    if cur >= seconds - 0.04:
        ff("-i", str(src), "-t", f"{seconds:.3f}", "-vf", vf, "-an",
           "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-r", str(FPS), str(dst))
        return
    pad = seconds - cur
    ff("-i", str(src), "-vf", f"{vf},tpad=stop_mode=clone:stop_duration={pad:.3f}",
       "-t", f"{seconds:.3f}", "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18",
       "-r", str(FPS), str(dst))


def end_card(dst: Path, line1: str, line2: str, sub: str) -> Path:
    img = Image.new("RGB", (W, H), (8, 8, 8))
    draw = ImageDraw.Draw(img)
    brand = ImageFont.truetype(FONT, 88)
    hero = ImageFont.truetype(FONT, 52)
    subf = ImageFont.truetype(FONT_REG, 40)

    def center(text: str, y: int, font, fill) -> None:
        bb = draw.textbbox((0, 0), text, font=font)
        draw.text(((W - (bb[2] - bb[0])) / 2, y), text, font=font, fill=fill)

    center("Taxi and Fly", 720, brand, (255, 210, 40))
    center(line1, 860, hero, (255, 255, 255))
    center(line2, 930, hero, (255, 255, 255))
    center(sub, 1040, subf, (255, 210, 40))
    png = dst.with_suffix(".png")
    img.save(png)
    return png


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
    ff(*args, "-filter_complex", ";".join(parts), "-map", "[a]",
       "-t", f"{total:.3f}", "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "160k", str(dst))


async def build_lang(cfg: dict, raws: list[Path]) -> None:
    vodir: Path = cfg["vo"]
    vodir.mkdir(parents=True, exist_ok=True)
    vo_files: list[Path] = []
    durs: list[float] = []
    for i, line in enumerate(cfg["lines"]):
        mp3 = vodir / f"line_{i:02d}.mp3"
        print("TTS", cfg["voice"], line)
        await speak(line, mp3, cfg["voice"], cfg["rate"])
        vo_files.append(mp3)
        durs.append(max(duration(mp3) + 0.55, 3.2))

    a = vodir / "end_a.mp3"
    b = vodir / "end_b.mp3"
    c = vodir / "end_c.mp3"
    await speak(cfg["end"][0][0], a, cfg["voice"], cfg["end"][0][1])
    await speak(cfg["end"][1][0], b, cfg["voice"], cfg["end"][1][1])
    await speak(cfg["end"][2][0], c, cfg["voice"], cfg["end"][2][1])
    gap = vodir / "gap.wav"
    ff("-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "0.22", str(gap))
    aw, bw, cw = vodir / "a.wav", vodir / "b.wav", vodir / "c.wav"
    ff("-i", str(a), "-ar", "44100", "-ac", "1", str(aw))
    ff("-i", str(b), "-ar", "44100", "-ac", "1", str(bw))
    ff("-i", str(c), "-ar", "44100", "-ac", "1", str(cw))
    lst = vodir / "end.txt"
    lst.write_text("".join(f"file '{p}'\n" for p in (aw, gap, bw, gap, cw)))
    end_wav = vodir / "end.wav"
    ff("-f", "concat", "-safe", "0", "-i", str(lst), "-ar", "44100", "-ac", "1", str(end_wav))
    vo_files.append(end_wav)
    durs.append(duration(end_wav) + 0.6)

    png = end_card(BUILD / f"end_ath_{cfg['out'].stem}", *cfg["card"], cfg["card_sub"])
    card_vid = BUILD / f"end_ath_{cfg['out'].stem}.mp4"
    kenburns(png, card_vid, durs[-1], 1.06, "center")

    fitted = []
    for i, (raw, sec) in enumerate(zip(raws + [card_vid], durs)):
        dst = BUILD / f"ath_{cfg['out'].stem}_{i:02d}.mp4"
        fit(raw, dst, sec)
        fitted.append(dst)

    silent = BUILD / f"ath_{cfg['out'].stem}_silent.mp4"
    xfade_concat(fitted, silent, fade=0.16)
    starts = [0.0]
    acc = durs[0]
    for d in durs[1:]:
        starts.append(max(acc - 0.16, 0.05))
        acc = acc + d - 0.16
    total = max(acc, duration(silent))
    bed = BUILD / f"ath_{cfg['out'].stem}_bed.wav"
    make_audio(total + 0.4, bed)
    mix_a = BUILD / f"ath_{cfg['out'].stem}_mix.m4a"
    mix_vo(starts, vo_files, bed, total + 0.05, mix_a)
    tmp = BUILD / f"ath_{cfg['out'].stem}_tmp.mp4"
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
    if not SRC.exists():
        print("missing source", SRC)
        return 1
    BUILD.mkdir(parents=True, exist_ok=True)
    raws = []
    for i, (ss, dur) in enumerate(BEATS):
        p = BUILD / f"ath_raw_{i}.mp4"
        print("clip", ss, dur)
        phone_clip(ss, dur, p)
        raws.append(p)
    await build_lang(EL, raws)
    await build_lang(EN, raws)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
