#!/usr/bin/env python3
"""Original audio for the short spots: a logo sting and a second music bed."""

from __future__ import annotations

import math
import wave
from pathlib import Path

import numpy as np

SR = 44100


def write_wav(path: Path, audio: np.ndarray) -> None:
    pcm = (np.clip(audio, -0.97, 0.97) * 32767).astype(np.int16)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(pcm.tobytes())


def read_wav(path: Path) -> np.ndarray:
    with wave.open(str(path)) as wf:
        raw = wf.readframes(wf.getnframes())
    return np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32767.0


def logo_sting(seconds: float, hit: float, dst: Path) -> None:
    """Warm bell that lands with the logo, with a short breath of air before it."""
    n = int(SR * seconds)
    out = np.zeros(n)

    # Rising air just ahead of the logo.
    rise = 0.42
    i0 = max(int((hit - rise) * SR), 0)
    leng = min(int(rise * SR), n - i0)
    if leng > 0:
        tt = np.linspace(0, 1, leng, False)
        noise = np.random.default_rng(7).normal(0, 1, leng)
        smooth = np.convolve(noise, np.ones(90) / 90, mode="same")
        out[i0 : i0 + leng] += 0.16 * smooth * (tt ** 2.2)

    # D major bell: D5, F#5, A5, with the octave on top.
    for freq, amp, delay, decay in (
        (587.33, 0.30, 0.00, 2.2),
        (739.99, 0.20, 0.045, 2.4),
        (880.00, 0.16, 0.090, 2.6),
        (1174.66, 0.08, 0.135, 3.2),
    ):
        j0 = int((hit + delay) * SR)
        if j0 >= n:
            continue
        leng = min(int(2.6 * SR), n - j0)
        tt = np.linspace(0, leng / SR, leng, False)
        tone = amp * np.sin(2 * math.pi * freq * tt) * np.exp(-decay * tt)
        tone += 0.28 * amp * np.sin(2 * math.pi * freq * 2.004 * tt) * np.exp(-decay * 1.8 * tt)
        out[j0 : j0 + leng] += tone

    # Soft low body so the bell has weight on a phone speaker.
    j0 = int(hit * SR)
    leng = min(int(0.7 * SR), n - j0)
    if leng > 0:
        tt = np.linspace(0, leng / SR, leng, False)
        out[j0 : j0 + leng] += 0.22 * np.sin(2 * math.pi * 110.0 * tt) * np.exp(-5.0 * tt)

    write_wav(dst, out)


def reggae_music(seconds: float, dst: Path) -> None:
    """Sunny original reggae: one-drop drums, offbeat skank, round bass."""
    n = int(SR * seconds)
    out = np.zeros(n)
    bpm = 76.0
    beat = 60.0 / bpm
    bar = beat * 4

    def place(buf: np.ndarray, at: float, sound: np.ndarray) -> None:
        j0 = int(at * SR)
        if j0 >= len(buf) or j0 < 0:
            return
        leng = min(len(sound), len(buf) - j0)
        buf[j0 : j0 + leng] += sound[:leng]

    def env(length: float, decay: float) -> tuple[np.ndarray, np.ndarray]:
        leng = int(length * SR)
        tt = np.linspace(0, length, leng, False)
        return tt, np.exp(-decay * tt)

    # A – E – F#m – D, one bar each.
    progression = [
        (110.00, (440.00, 554.37, 659.25)),
        (82.41, (415.30, 493.88, 659.25)),
        (92.50, (440.00, 554.37, 739.99)),
        (73.42, (440.00, 587.33, 739.99)),
    ]

    bars = int(seconds / bar) + 1
    for b in range(bars):
        t0 = b * bar
        if t0 >= seconds:
            break
        root, chord = progression[b % len(progression)]

        # Warm organ held across the bar, so the groove never falls silent.
        hold = min(bar * 1.02, seconds - t0)
        if hold > 0.05:
            tt = np.linspace(0, hold, int(hold * SR), False)
            shape = np.minimum(tt / 0.12, 1.0) * np.minimum((hold - tt) / 0.20, 1.0)
            organ = sum(0.030 * np.sin(2 * math.pi * f * 0.5 * tt) for f in chord)
            organ += 0.020 * np.sin(2 * math.pi * root * 2 * tt)
            place(out, t0, organ * np.clip(shape, 0, 1))

        # Offbeat skank on the "and" of every beat — the reggae chop.
        for k in range(4):
            at = t0 + k * beat + beat / 2
            tt, e = env(0.30, 16.0)
            stab = sum(0.05 * np.sin(2 * math.pi * f * tt) for f in chord)
            stab += 0.018 * np.sin(2 * math.pi * chord[0] * 0.5 * tt)
            place(out, at, stab * e)

        # Bass riff: root, root, fifth, root — round and dry.
        for off, ratio in ((0.0, 1.0), (1.0, 2.0), (1.5, 1.0), (2.5, 1.5), (3.0, 1.0)):
            tt, e = env(0.52, 5.2)
            f = root * ratio
            tone = (0.34 * np.sin(2 * math.pi * f * tt) + 0.07 * np.sin(2 * math.pi * f * 2 * tt))
            place(out, t0 + off * beat, tone * e * np.minimum(tt / 0.012, 1.0))

        # One drop: kick and snare land together on beat three.
        tt, e = env(0.42, 13.0)
        kick = 0.42 * np.sin(2 * math.pi * (58 + 70 * np.exp(-42 * tt)) * tt) * e
        place(out, t0 + 2 * beat, kick)

        rng = np.random.default_rng(100 + b)
        tt, e = env(0.20, 26.0)
        noise = rng.normal(0, 1, len(tt))
        snare = 0.13 * (noise - np.convolve(noise, np.ones(12) / 12, mode="same")) * e
        place(out, t0 + 2 * beat, snare)

        # Hats on the eighths, softer on the downbeats.
        for k in range(8):
            tt, e = env(0.07, 70.0)
            hn = rng.normal(0, 1, len(tt))
            hat = 0.035 * (hn - np.convolve(hn, np.ones(4) / 4, mode="same")) * e
            place(out, t0 + k * beat / 2, hat * (1.0 if k % 2 else 0.6))

    t = np.linspace(0, seconds, n, False)
    fade = np.minimum(np.minimum(t / 1.2, 1.0), np.minimum((seconds - t) / 2.0, 1.0))
    write_wav(dst, out * np.clip(fade, 0, 1) * 0.72)


def drive_music(seconds: float, dst: Path) -> None:
    """Upbeat original drive bed: pulse, kick, bright stabs. Not a known song."""
    n = int(SR * seconds)
    out = np.zeros(n)
    bpm = 112.0
    beat = 60.0 / bpm
    rng = np.random.default_rng(21)

    def place(buf: np.ndarray, at: float, sound: np.ndarray) -> None:
        j0 = int(at * SR)
        if j0 >= len(buf) or j0 < 0:
            return
        leng = min(len(sound), len(buf) - j0)
        buf[j0 : j0 + leng] += sound[:leng]

    # Bright major lift: C – G – Am – F
    chords = [
        (130.81, (261.63, 329.63, 392.00)),
        (98.00, (196.00, 246.94, 392.00)),
        (110.00, (220.00, 261.63, 329.63)),
        (87.31, (174.61, 220.00, 261.63)),
    ]
    bars = int(seconds / (beat * 4)) + 2
    for b in range(bars):
        t0 = b * beat * 4
        if t0 >= seconds:
            break
        root, chord = chords[b % len(chords)]

        # Soft pad across the bar.
        hold = min(beat * 4.05, seconds - t0 + 0.05)
        if hold > 0.05:
            tt = np.linspace(0, hold, int(hold * SR), False)
            shape = np.minimum(tt / 0.08, 1.0) * np.minimum((hold - tt) / 0.18, 1.0)
            pad = sum(0.028 * np.sin(2 * math.pi * f * tt) for f in chord)
            pad += 0.022 * np.sin(2 * math.pi * root * tt)
            place(out, t0, pad * np.clip(shape, 0, 1))

        # Four-on-the-floor kick + offbeat clap energy.
        for k in range(4):
            at = t0 + k * beat
            tt = np.linspace(0, 0.28, int(0.28 * SR), False)
            kick = 0.38 * np.sin(2 * math.pi * (70 + 90 * np.exp(-35 * tt)) * tt) * np.exp(-10 * tt)
            place(out, at, kick)

            # snappy hat on every eighth
            for h in (0.0, 0.5):
                ht = np.linspace(0, 0.06, int(0.06 * SR), False)
                noise = rng.normal(0, 1, len(ht))
                hat = 0.045 * (noise - np.convolve(noise, np.ones(5) / 5, mode="same"))
                hat *= np.exp(-55 * ht)
                place(out, at + h * beat, hat * (1.0 if h else 0.7))

            # bright stab on the offbeat
            st = np.linspace(0, 0.22, int(0.22 * SR), False)
            stab = sum(0.055 * np.sin(2 * math.pi * f * st) for f in chord)
            stab *= np.exp(-14 * st) * np.minimum(st / 0.01, 1.0)
            place(out, at + beat * 0.5, stab)

        # short bass walk
        for off, ratio in ((0.0, 1.0), (1.0, 1.0), (2.0, 1.5), (3.0, 1.0)):
            tt = np.linspace(0, 0.36, int(0.36 * SR), False)
            f = root * ratio
            bass = (0.30 * np.sin(2 * math.pi * f * tt) + 0.08 * np.sin(2 * math.pi * f * 2 * tt))
            bass *= np.exp(-4.8 * tt) * np.minimum(tt / 0.01, 1.0)
            place(out, t0 + off * beat, bass)

    t = np.linspace(0, seconds, n, False)
    fade = np.minimum(np.minimum(t / 0.35, 1.0), np.minimum((seconds - t) / 1.2, 1.0))
    write_wav(dst, out * np.clip(fade, 0, 1) * 0.78)


def hope_music(seconds: float, dst: Path) -> None:
    """Warm hopeful bed: soft piano pulses + airy melody. Not reggae/drive."""
    n = int(SR * seconds)
    out = np.zeros(n)
    bpm = 96.0
    beat = 60.0 / bpm
    rng = np.random.default_rng(77)

    def place(buf: np.ndarray, at: float, sound: np.ndarray) -> None:
        j0 = int(at * SR)
        if j0 >= len(buf) or j0 < 0:
            return
        leng = min(len(sound), len(buf) - j0)
        buf[j0 : j0 + leng] += sound[:leng]

    # F – C – Dm – Bb (warm major lift)
    chords = [
        (174.61, (349.23, 440.00, 523.25)),
        (130.81, (261.63, 329.63, 392.00)),
        (146.83, (293.66, 349.23, 440.00)),
        (116.54, (233.08, 293.66, 349.23)),
    ]
    bars = int(seconds / (beat * 4)) + 2
    for b in range(bars):
        t0 = b * beat * 4
        if t0 >= seconds:
            break
        root, chord = chords[b % len(chords)]

        # soft string pad
        hold = min(beat * 4.1, seconds - t0 + 0.05)
        if hold > 0.05:
            tt = np.linspace(0, hold, int(hold * SR), False)
            shape = np.minimum(tt / 0.25, 1.0) * np.minimum((hold - tt) / 0.35, 1.0)
            pad = sum(0.034 * np.sin(2 * math.pi * f * tt) for f in chord)
            pad += 0.020 * np.sin(2 * math.pi * root * tt)
            place(out, t0, pad * np.clip(shape, 0, 1))

        # piano-like pulses on beats 1 and 3
        for k in (0, 2):
            at = t0 + k * beat
            tt = np.linspace(0, 0.55, int(0.55 * SR), False)
            tone = sum(0.07 * np.sin(2 * math.pi * f * tt) for f in chord)
            tone += 0.03 * np.sin(2 * math.pi * chord[0] * 2 * tt)
            tone *= np.exp(-3.8 * tt) * np.minimum(tt / 0.008, 1.0)
            place(out, at, tone)

        # light high sparkle every half bar
        for k in range(4):
            at = t0 + k * beat + beat * 0.5
            tt = np.linspace(0, 0.18, int(0.18 * SR), False)
            spark = 0.028 * np.sin(2 * math.pi * chord[2] * 2 * tt) * np.exp(-18 * tt)
            place(out, at, spark)

        # soft kick (quiet, not clubby)
        tt = np.linspace(0, 0.25, int(0.25 * SR), False)
        kick = 0.16 * np.sin(2 * math.pi * (55 + 40 * np.exp(-28 * tt)) * tt) * np.exp(-9 * tt)
        place(out, t0, kick)
        place(out, t0 + 2 * beat, kick * 0.85)

        # airy hats
        for k in range(8):
            tt = np.linspace(0, 0.05, int(0.05 * SR), False)
            noise = rng.normal(0, 1, len(tt))
            hat = 0.022 * (noise - np.convolve(noise, np.ones(6) / 6, mode="same")) * np.exp(-60 * tt)
            place(out, t0 + k * beat / 2, hat * (0.55 if k % 2 == 0 else 1.0))

    # floating melody line
    melody = [399.23, 440.00, 523.25, 440.00, 349.23, 392.00, 440.00, 523.25]
    step = beat
    for i, f0 in enumerate(melody * (int(seconds / (step * len(melody))) + 1)):
        t0 = 0.6 + i * step
        if t0 >= seconds - 0.3:
            break
        leng = int(0.7 * SR)
        j0 = int(t0 * SR)
        if j0 >= n:
            break
        tt = np.linspace(0, 0.7, leng, False)
        mel = 0.045 * np.sin(2 * math.pi * f0 * tt) * np.exp(-2.2 * tt)
        mel += 0.015 * np.sin(2 * math.pi * f0 * 2 * tt) * np.exp(-3.5 * tt)
        sl = slice(j0, min(j0 + leng, n))
        out[sl] += mel[: sl.stop - sl.start]

    t = np.linspace(0, seconds, n, False)
    fade = np.minimum(np.minimum(t / 1.0, 1.0), np.minimum((seconds - t) / 1.8, 1.0))
    write_wav(dst, out * np.clip(fade, 0, 1) * 0.82)


def plain_music(seconds: float, dst: Path) -> None:
    """Brighter plucked bed for the versions with no voice. Not a known song."""
    n = int(SR * seconds)
    t = np.linspace(0, seconds, n, False)
    out = np.zeros(n)

    # Gentle plucked arpeggio in A major.
    arp = [220.00, 277.18, 329.63, 440.00, 329.63, 277.18]
    step = 0.32
    for i in range(int(seconds / step) + 1):
        t0 = i * step
        if t0 >= seconds - 0.1:
            break
        f0 = arp[i % len(arp)]
        j0 = int(t0 * SR)
        leng = min(int(0.85 * SR), n - j0)
        if leng <= 0:
            continue
        tt = np.linspace(0, leng / SR, leng, False)
        pluck = (
            0.085 * np.sin(2 * math.pi * f0 * tt)
            + 0.034 * np.sin(2 * math.pi * f0 * 2 * tt)
            + 0.016 * np.sin(2 * math.pi * f0 * 3 * tt)
        ) * np.exp(-3.4 * tt)
        out[j0 : j0 + leng] += pluck

    # Low sustain underneath so it never sounds thin.
    out += (
        0.055 * np.sin(2 * math.pi * 110.0 * t)
        + 0.030 * np.sin(2 * math.pi * 164.81 * t)
        + 0.018 * np.sin(2 * math.pi * 220.0 * t)
    ) * (0.9 + 0.1 * np.sin(2 * math.pi * 0.16 * t))

    env = np.minimum(np.minimum(t / 0.9, 1.0), np.minimum((seconds - t) / 1.6, 1.0))
    write_wav(dst, out * np.clip(env, 0, 1) * 0.9)
