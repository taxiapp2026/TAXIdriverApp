#!/usr/bin/env python3
"""Rebuild the 9:16 ad with a natural male Greek voice (Nestoras)."""

from __future__ import annotations

import asyncio
import re
import subprocess
import sys
import time
from pathlib import Path

import edge_tts
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / "build"
OUT = ROOT / "taxi-and-fly-google-ads-9x16.mp4"
VO_DIR = BUILD / "vo_nestoras"
ARTIFACT = Path("/opt/cursor/artifacts/taxi_and_fly_arxi_logia.mp4")

sys.path.insert(0, str(ROOT))
from build_video import FONT, FONT_REG, duration, ff, kenburns, make_audio, mix, xfade_concat  # noqa: E402

LINES = [
    "Από όπου κι αν βρίσκεσαι, έρχεσαι στην Αθήνα.",
    "Συμπληρώνεις τη φόρμα.",
    "Βάζεις τον προορισμό που θέλεις.",
    "Κλείνεις ραντεβού με έναν οδηγό.",
    "Όταν φτάσεις στο αεροδρόμιο,",
    "πατάς το κουμπί να έρθει ο οδηγός να σε πάρει.",
    "Ο οδηγός ενημερώνεται από σένα σε ποιον αριθμό στις αφίξεις είσαι.",
    "Έρχεται και σε παίρνει.",
    "Σε πάει με ασφάλεια στον προορισμό σου.",
    "Μπορείς να γράψεις πώς ήταν η διαδρομή σου και ο οδηγός, για να βελτιωνόμαστε συνέχεια.",
    "END",
]

AIRPORT_SENTENCE = (
    "Όταν φτάσεις στο αεροδρόμιο, πατάς το κουμπί να έρθει ο οδηγός να σε πάρει."
)

# Picture order: abroad, form, destination, book, arrivals, button, exits, taxi, dest, thanks, end
PICTURES = [
    BUILD / "n0.mp4",
    BUILD / "n2.mp4",
    BUILD / "n1.mp4",
    BUILD / "n3.mp4",
    BUILD / "n4.mp4",
    BUILD / "n5.mp4",
    BUILD / "n6.mp4",
    BUILD / "n7.mp4",
    BUILD / "n8.mp4",
    BUILD / "n9.mp4",
    BUILD / "n10.mp4",
]

VOICE = "el-GR-NestorasNeural"
RATE = "-10%"
PITCH = "-2Hz"
# Extra pause after booking so the airport line starts a new sentence.
HOLDS = [0.50, 0.50, 0.50, 1.15, 0.85, 0.50, 0.50, 0.50, 0.50, 0.50, 0.70]
FADE = 0.18
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


def silence_wav(dst: Path, seconds: float) -> None:
    ff("-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", f"{seconds:.3f}", str(dst))


def concat_audio(parts: list[Path], dst: Path) -> None:
    lst = dst.with_suffix(".txt")
    lst.write_text("".join(f"file '{p}'\n" for p in parts))
    ff("-f", "concat", "-safe", "0", "-i", str(lst), "-ar", "44100", "-ac", "1", str(dst))


def split_on_pause(src: Path, left: Path, right: Path) -> None:
    wav = BUILD / "split_src.wav"
    ff("-i", str(src), "-ar", "44100", "-ac", "1", str(wav))
    proc = subprocess.run(
        [
            "ffmpeg", "-hide_banner", "-i", str(wav),
            "-af", "silencedetect=noise=-32dB:d=0.07", "-f", "null", "-",
        ],
        capture_output=True, text=True, check=False,
    )
    d = duration(wav)
    starts = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", proc.stderr)]
    cut = next((s for s in starts if 0.65 < s < d * 0.62), None)
    if cut is None:
        cut = min(max(d * 0.40, 0.85), d - 0.45)
    print(f"airport split at {cut:.2f}s of {d:.2f}s")
    ff("-i", str(wav), "-t", f"{cut:.3f}", "-ar", "44100", "-ac", "1", str(left))
    ff("-ss", f"{cut:.3f}", "-i", str(wav), "-ar", "44100", "-ac", "1", str(right))


def make_end_card_png(dst: Path) -> None:
    img = Image.new("RGB", (W, H), (8, 8, 8))
    draw = ImageDraw.Draw(img)
    f_brand = ImageFont.truetype(FONT, 92)
    f_hero = ImageFont.truetype(FONT, 56)
    f_sub = ImageFont.truetype(FONT_REG, 42)

    def center(text: str, y: int, font, fill) -> None:
        bbox = draw.textbbox((0, 0), text, font=font)
        tw = bbox[2] - bbox[0]
        draw.text(((W - tw) / 2, y), text, font=font, fill=fill)

    center("Taxi and Fly", 700, f_brand, (255, 210, 40))
    center("Από και προς το αεροδρόμιο", 860, f_hero, (255, 255, 255))
    center("με επαγγελματίες οδηγούς ταξί", 960, f_sub, (255, 210, 40))
    img.save(dst)


def fit_clip(src: Path, dst: Path, seconds: float) -> None:
    cur = duration(src)
    vf = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps={FPS},format=yuv420p"
    if cur > seconds + 0.04:
        ff(
            "-i", str(src), "-t", f"{seconds:.3f}",
            "-vf", vf, "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-r", str(FPS), str(dst),
        )
        return
    pad = max(seconds - cur, 0)
    if pad < 0.05:
        ff(
            "-i", str(src), "-t", f"{seconds:.3f}",
            "-vf", vf, "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-r", str(FPS), str(dst),
        )
        return
    ff(
        "-i", str(src),
        "-vf", f"{vf},tpad=stop_mode=clone:stop_duration={pad:.3f}",
        "-t", f"{seconds:.3f}",
        "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-r", str(FPS), str(dst),
    )


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
        *args,
        "-filter_complex", ";".join(parts),
        "-map", "[a]",
        "-t", f"{total:.3f}",
        "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "160k",
        str(dst),
    )


async def main() -> int:
    VO_DIR.mkdir(parents=True, exist_ok=True)
    vo_files: list[Path] = []
    durs: list[float] = []

    png = BUILD / "end_drivers.png"
    make_end_card_png(png)

    for i, line in enumerate(LINES):
        mp3 = VO_DIR / f"line_{i:02d}.mp3"
        if i == 4:
            full = VO_DIR / "airport_full.mp3"
            print("TTS airport sentence")
            await speak(AIRPORT_SENTENCE, full)
            split_on_pause(full, VO_DIR / "line_04.wav", VO_DIR / "line_05.wav")
            vo_files.append(VO_DIR / "line_04.wav")
            durs.append(duration(vo_files[-1]) + HOLDS[4])
            print("  airport start", f"{durs[-1]:.2f}s")
            continue
        if i == 5:
            vo_files.append(VO_DIR / "line_05.wav")
            durs.append(duration(vo_files[-1]) + HOLDS[5])
            print("  airport rest", f"{durs[-1]:.2f}s")
            continue
        if i == 10:
            a = VO_DIR / "end_a.mp3"
            b = VO_DIR / "end_b.mp3"
            c = VO_DIR / "end_c.mp3"
            gap = VO_DIR / "end_gap.wav"
            await speak("Taxi and Fly.", a, rate="-8%")
            await speak("Από και προς το αεροδρόμιο.", b, rate="-18%")
            await speak("Με επαγγελματίες οδηγούς ταξί.", c, rate="-10%")
            silence_wav(gap, 0.28)
            a_wav = VO_DIR / "end_a.wav"
            b_wav = VO_DIR / "end_b.wav"
            c_wav = VO_DIR / "end_c.wav"
            ff("-i", str(a), "-ar", "44100", "-ac", "1", str(a_wav))
            ff("-i", str(b), "-ar", "44100", "-ac", "1", str(b_wav))
            ff("-i", str(c), "-ar", "44100", "-ac", "1", str(c_wav))
            concat_audio([a_wav, gap, b_wav, gap, c_wav], VO_DIR / "line_10.wav")
            mp3 = VO_DIR / "line_10.wav"
            vo_files.append(mp3)
            durs.append(duration(mp3) + HOLDS[10])
            print("TTS end", f"{durs[-1]:.2f}s")
            continue
        print("TTS", i, line)
        await speak(line, mp3)
        vo_files.append(mp3)
        durs.append(duration(mp3) + HOLDS[i])
        print(f"  {durs[-1]:.2f}s")

    n10 = BUILD / "n10.mp4"
    print("end card clip", f"{durs[-1]:.2f}s")
    kenburns(png, n10, durs[-1], 1.08, "center")

    fitted: list[Path] = []
    for i, (pic, sec) in enumerate(zip(PICTURES, durs)):
        dst = BUILD / f"nat_{i:02d}.mp4"
        print("fit", pic.name, f"{sec:.2f}s")
        fit_clip(pic, dst, sec)
        fitted.append(dst)

    silent = BUILD / "nat_silent.mp4"
    print("concat")
    xfade_concat(fitted, silent, fade=FADE)
    starts, total = clip_starts(durs, FADE)
    video_dur = duration(silent)
    total = max(total, video_dur)
    print("timeline", [round(s, 2) for s in starts], "total", round(total, 2), "video", round(video_dur, 2))

    bed = BUILD / "nat_bed.wav"
    make_audio(total + 0.5, bed)
    mix_a = BUILD / "nat_mix.m4a"
    mix_vo(starts, vo_files, bed, total + 0.05, mix_a)

    tmp = BUILD / "nat_out.mp4"
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
