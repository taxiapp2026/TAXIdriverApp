#!/usr/bin/env python3
"""Taxi and Fly — "Κλείσε ραντεβού" spot.

She books her airport pickup two days ahead, forgets about it, and on the day
the driver is at her door on time. Three voices: a narrator, the driver and the
traveller. Reggae bed that stops dead when the logo lands.
"""

from __future__ import annotations

import asyncio
import hashlib
import shutil
import sys
import time
from pathlib import Path

import edge_tts
from PIL import Image

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / "build"
STILLS = ROOT / "rantevou"
ART = Path("/opt/cursor/artifacts")
OUT = ROOT / "taxi-and-fly-rantevou.mp4"

sys.path.insert(0, str(ROOT))
from build_video import duration, ff, mix, xfade_concat  # noqa: E402
from make_story_spot import caption_png, end_card  # noqa: E402
from make_tagline_spots import VOICE_FX, trim_edges  # noqa: E402
from spot_audio import logo_sting, reggae_music  # noqa: E402

W, H, FPS = 1080, 1920, 30
FADE = 0.35
LEAD = 0.35          # beat of picture before a line starts
TAIL = 0.40          # beat of picture after it ends
LINE_GAP = 0.32      # pause between two lines inside one shot

# Only two Greek neural voices exist, so the driver is the narrator's voice
# pitched down — next to the pictures the three read as three people.
NARR = ("el-GR-NestorasNeural", "-8%", "+0Hz")
DRIVER = ("el-GR-NestorasNeural", "-2%", "-14Hz")
WOMAN = ("el-GR-AthinaNeural", "-4%", "+0Hz")

# image, pan, zoom, minimum seconds, lines spoken over it, hard cut from previous
#
# Shots inside a scene cut straight. Dissolving two photographs of the same
# person makes the faces and hands morph into each other, so the only
# cross-fades left are the jumps between scenes.
SHOTS = [
    ("ap_01_living.png", "center", 1.08, 2.2, [(NARR, "Δύο μέρες πριν το ταξίδι.")], False),
    ("ap_02_coffee.png", "left", 1.10, 1.4, [], True),
    ("ap_03_suitcase_empty.png", "down", 1.07, 1.4, [], True),
    ("ap_04_phone.png", "center", 1.09, 2.2, [(NARR, "Ανοίγει την εφαρμογή και κλείνει ραντεβού.")], False),
    ("ap_05_phone_down.png", "right", 1.10, 1.9, [(NARR, "Χωρίς εγγραφή, χωρίς κωδικούς.")], True),
    ("ap_06_looking_out.png", "up", 1.08, 1.8, [], True),
    # Locked-off trio: the same corner as two days go by.
    ("ap_03_suitcase_empty.png", "still", 1.02, 1.1, [], False),
    ("ap_07_suitcase_half.png", "still", 1.02, 1.1, [], True),
    ("ap_08_suitcase_ready.png", "still", 1.02, 1.3, [], True),
    ("ap_09_door_taxi.png", "center", 1.09, 1.8, [], False),
    ("ap_10_driver.png", "center", 1.08, 2.2, [(DRIVER, "Καλημέρα σας! Taxi and Fly, για το αεροδρόμιο.")], True),
    ("ap_11_luggage.png", "center", 1.08, 2.2, [
        (WOMAN, "Καλημέρα. Ακριβώς στην ώρα σας."),
        (DRIVER, "Όπως το κλείσατε."),
    ], True),
    ("ap_12_road.png", "left", 1.07, 1.9, [(NARR, "Τιμή ταξιμέτρου.")], False),
    ("ap_13_backseat.png", "center", 1.09, 2.3, [(NARR, "Αποσκευές και διόδια δώρο.")], True),
    ("ap_14_departures.png", "right", 1.07, 1.5, [], False),
    ("ap_15_wave.png", "center", 1.09, 1.8, [(DRIVER, "Καλό ταξίδι!")], True),
]

# first shot, last shot, greek, english
CAPTIONS = [
    (0, 2, "Δύο μέρες πριν το ταξίδι", "Two days before the trip"),
    (3, 5, "Χωρίς εγγραφή, χωρίς κωδικούς", "No sign-up, no passwords"),
    (6, 8, "Δύο μέρες μετά", "Two days later"),
    (9, 11, "Στην ώρα του, όπως το κλείσατε", "On time, exactly as booked"),
    (12, 13, "Τιμή ταξιμέτρου, αποσκευές και διόδια δώρο", "Taximeter price, luggage and tolls included"),
    (14, 15, "Καλό ταξίδι", "Have a good trip"),
]

BRAND_LINE = "Taxi and Fly. Κλείσε ραντεβού, πέτα ήσυχος."
TICKS = 10_000_000.0


async def say(voice: tuple[str, str, str], text: str, dst: Path) -> None:
    name, rate, pitch = voice
    last: Exception | None = None
    for attempt in range(8):
        try:
            comm = edge_tts.Communicate(text, name, rate=rate, pitch=pitch)
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
            print("retry", dst.name, exc)
            time.sleep(1.1 + attempt * 0.5)
    raise RuntimeError(last)


def kenburns(name: str, dst: Path, seconds: float, zoom_end: float, pan: str) -> None:
    """The stills are 720x1280, so upscale with lanczos before the move."""
    src = STILLS / name
    big = BUILD / f"ap_big_{src.stem}.png"
    if not big.exists():
        Image.open(src).convert("RGB").resize((1620, 2880), Image.Resampling.LANCZOS).save(big)
    frames = int(round(seconds * FPS))
    if pan == "up":
        x_expr, y_expr = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)-on*0.30"
    elif pan == "down":
        x_expr, y_expr = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)+on*0.30"
    elif pan == "left":
        x_expr, y_expr = "iw/2-(iw/zoom/2)-on*0.26", "ih/2-(ih/zoom/2)"
    elif pan == "right":
        x_expr, y_expr = "iw/2-(iw/zoom/2)+on*0.26", "ih/2-(ih/zoom/2)"
    else:
        x_expr, y_expr = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    if pan == "still":
        z_expr = f"{zoom_end}"
    else:
        z_expr = f"1.02+{zoom_end - 1.02}*on/{frames}"
    vf = (
        f"zoompan=z='{z_expr}':x='{x_expr}':y='{y_expr}':d={frames}:s={W}x{H}:fps={FPS},"
        f"format=yuv420p,setsar=1"
    )
    ff("-loop", "1", "-i", str(big), "-vf", vf, "-frames:v", str(frames),
       "-r", str(FPS), "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18", str(dst))


def overlay_captions(src: Path, caps: list[tuple[Path, float, float]], dst: Path) -> None:
    """Captions span whole scenes, so they ride over the cuts instead of each shot."""
    total = duration(src)
    args = ["-i", str(src)]
    for png, _, _ in caps:
        args += ["-loop", "1", "-t", f"{total:.3f}", "-i", str(png)]
    parts = []
    last = "[0:v]"
    for i, (_, start, end) in enumerate(caps, start=1):
        parts.append(
            f"[{i}:v]format=rgba,fade=t=in:st={start:.2f}:d=0.35:alpha=1,"
            f"fade=t=out:st={max(end - 0.35, start + 0.4):.2f}:d=0.35:alpha=1[c{i}]"
        )
        parts.append(f"{last}[c{i}]overlay=0:0:format=auto[o{i}]")
        last = f"[o{i}]"
    parts.append(f"{last}format=yuv420p[v]")
    ff(*args, "-filter_complex", ";".join(parts), "-map", "[v]", "-t", f"{total:.3f}",
       "-r", str(FPS), "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "18", str(dst))


def hard_concat(clips: list[Path], dst: Path) -> None:
    """Straight cuts, no dissolve — same encoder settings everywhere, so copy."""
    lst = dst.with_suffix(".txt")
    lst.write_text("".join(f"file '{p.resolve()}'\n" for p in clips))
    ff("-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(dst))


async def take(voice: tuple[str, str, str], text: str) -> Path:
    """Cached by voice and wording, so re-cuts do not re-synthesise everything."""
    key = hashlib.sha1(f"{voice}|{text}".encode()).hexdigest()[:10]
    wav = BUILD / f"ap_vo_{key}.wav"
    if not wav.exists():
        print("TTS", text)
        mp3 = BUILD / f"ap_vo_{key}.mp3"
        await say(voice, text, mp3)
        trim_edges(mp3, wav)
    return wav


async def voices() -> tuple[list[list[Path]], Path]:
    takes: list[list[Path]] = []
    for _, _, _, _, lines, _ in SHOTS:
        takes.append([await take(voice, text) for voice, text in lines])
    return takes, await take(NARR, BRAND_LINE)


async def main() -> int:
    BUILD.mkdir(parents=True, exist_ok=True)
    takes, brand = await voices()

    # A shot lasts as long as its own lines need, never less than the script says.
    durs: list[float] = []
    for (_, _, _, base, _, _), lines in zip(SHOTS, takes):
        spoken = sum(duration(w) for w in lines) + LINE_GAP * max(len(lines) - 1, 0)
        durs.append(round(max(base, spoken + LEAD + TAIL), 3))

    clips: list[Path] = []
    for i, (name, pan, zoom, _, _, _) in enumerate(SHOTS):
        if not (STILLS / name).exists():
            raise SystemExit(f"missing still {STILLS / name}")
        clip = BUILD / f"ap_shot_{i:02d}.mp4"
        kenburns(name, clip, durs[i], zoom, pan)
        clips.append(clip)

    end_sec = max(3.0, duration(brand) + 1.5)
    end = BUILD / "ap_end.mp4"
    end_card(end, end_sec)

    # Shots that cut hard belong to the same group; only groups dissolve.
    groups: list[list[Path]] = []
    for i, clip in enumerate(clips):
        if i and SHOTS[i][5]:
            groups[-1].append(clip)
        else:
            groups.append([clip])

    starts: list[float] = []
    acc = 0.0
    for i, d in enumerate(durs):
        starts.append(acc)
        next_is_cut = i + 1 < len(SHOTS) and SHOTS[i + 1][5]
        acc += d - (0.0 if next_is_cut else FADE)
    end_start = acc

    joined: list[Path] = []
    for gi, group in enumerate(groups):
        if len(group) == 1:
            joined.append(group[0])
            continue
        merged = BUILD / f"ap_group_{gi:02d}.mp4"
        hard_concat(group, merged)
        joined.append(merged)

    silent = BUILD / "ap_silent.mp4"
    xfade_concat(joined + [end], silent, fade=FADE)
    total = duration(silent)

    caps: list[tuple[Path, float, float]] = []
    for ci, (a, b, el, en) in enumerate(CAPTIONS):
        png = BUILD / f"ap_cap_{ci}.png"
        caption_png(el, en, png)
        caps.append((png, starts[a] + 0.30, starts[b] + durs[b] - 0.45))
    captioned = BUILD / "ap_captioned.mp4"
    overlay_captions(silent, caps, captioned)

    bed = BUILD / "ap_reggae.wav"
    reggae_music(total + 0.4, bed)
    sting = BUILD / "ap_sting.wav"
    logo_sting(total + 0.4, end_start + 0.3, sting)

    # Every take gets its own delay, so lines land on their own shot.
    vo_files: list[Path] = []
    delays: list[int] = []
    for i, lines in enumerate(takes):
        at = starts[i] + LEAD
        for wav in lines:
            vo_files.append(wav)
            delays.append(int(at * 1000))
            at += duration(wav) + LINE_GAP
    vo_files.append(brand)
    delays.append(int((end_start + 0.75) * 1000))

    args: list[str] = ["-i", str(bed), "-i", str(sting)]
    for wav in vo_files:
        args += ["-i", str(wav)]

    parts = [
        f"[0:a]volume=0.62,afade=t=out:st={end_start - 0.35:.3f}:d=0.50,"
        "aformat=sample_rates=44100:channel_layouts=stereo[m]",
        "[1:a]volume=0.55,aformat=sample_rates=44100:channel_layouts=stereo[s]",
    ]
    labels = []
    for k, d in enumerate(delays):
        parts.append(
            f"[{k + 2}:a]adelay={d}|{d},aformat=sample_rates=44100:channel_layouts=stereo[v{k}]"
        )
        labels.append(f"[v{k}]")
    parts.append(
        "".join(labels) + f"amix=inputs={len(labels)}:duration=longest:dropout_transition=0:normalize=0,"
        f"{VOICE_FX},asplit=2[vv][vk]"
    )
    parts.append("[m][vk]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=350[md]")
    parts.append(
        "[md][s][vv]amix=inputs=3:duration=longest:dropout_transition=0:normalize=0,"
        "loudnorm=I=-16:TP=-1.5:LRA=11,"
        f"alimiter=limit=0.95,atrim=0:{total:.3f},asetpts=PTS-STARTPTS[a]"
    )

    audio = BUILD / "ap_mix.m4a"
    ff(*args, "-filter_complex", ";".join(parts), "-map", "[a]", "-t", f"{total:.3f}",
       "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "160k", str(audio))

    tmp = BUILD / "ap_tmp.mp4"
    mix(captioned, audio, tmp)
    ff(
        "-i", str(tmp),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.0",
        "-preset", "medium", "-crf", "20",
        "-fps_mode", "cfr", "-r", str(FPS),
        "-g", str(FPS * 2), "-keyint_min", str(FPS), "-sc_threshold", "0",
        "-c:a", "aac", "-ar", "44100", "-ac", "2", "-b:a", "160k",
        "-movflags", "+faststart", str(OUT),
    )
    tmp.unlink(missing_ok=True)
    ART.mkdir(parents=True, exist_ok=True)
    (ART / "taxi_and_fly_rantevou.mp4").write_bytes(OUT.read_bytes())
    print("Wrote", OUT, round(duration(OUT), 2), "s")
    return 0


if __name__ == "__main__":
    shutil.rmtree(BUILD / "ap_frames", ignore_errors=True)
    raise SystemExit(asyncio.run(main()))
