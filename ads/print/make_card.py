#!/usr/bin/env python3
"""Printable Taxi and Fly hand-out card: logo, QR code, and the app link.

Drop the real artwork in ads/meta/ and re-run:
  logo-icon.png  — the app logo
  qr-code.png    — the QR the client app hands out (optional; generated if absent)
"""

from __future__ import annotations

from pathlib import Path

import qrcode
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
META = ROOT.parent / "meta"
OUT = ROOT
ART = Path("/opt/cursor/artifacts")

LOGO = META / "logo-icon.png"
QR_FILE = META / "qr-code.png"
APP_URL = "https://taxiapp2026.github.io/taxi-client-app/"

FONT_BOLD = "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"
FONT_REG = "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"

# 85 x 55 mm business card at 300 dpi, with 3 mm bleed already inside the margins.
W, H = 1004, 650
BG = (10, 10, 10)
GOLD = (255, 210, 40)
WHITE = (242, 242, 242)
GREY = (170, 170, 170)

# One-sided card, so every line carries both languages: Greek first, English under it.
CARD = {
    "out": OUT / "taxi-and-fly-card.png",
    "art": ART / "taxi_and_fly_karta.png",
    "title": "Taxi and Fly",
    "tagline": (
        "Η πτήση σου ξεκινάει από την πόρτα σου",
        "Your flight starts at your front door",
    ),
    "bullets": [
        ("Κλείνεις εύκολα ταξί από και προς το αεροδρόμιο", "Book a taxi to and from the airport"),
        ("Χωρίς login, χωρίς εγγραφή", "No login, no sign-up"),
        ("Καλές τιμές", "Good prices"),
    ],
    "cta": ("Σκάναρε με την κάμερα", "Scan with your camera"),
    "pill": ("Κλείσε τώρα, πέτα ήσυχος", "Book now, fly relaxed"),
}


def qr_image(size: int) -> Image.Image:
    if QR_FILE.exists():
        return Image.open(QR_FILE).convert("RGB").resize((size, size), Image.Resampling.LANCZOS)
    code = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=2)
    code.add_data(APP_URL)
    code.make(fit=True)
    img = code.make_image(fill_color="black", back_color="white").convert("RGB")
    return img.resize((size, size), Image.Resampling.LANCZOS)


def logo_lettering() -> Image.Image:
    """The Taxi and Fly lettering with its dark plate knocked out."""
    src = Image.open(LOGO).convert("RGB")
    w, h = src.size
    art = src.crop((14, 14, w - 14, h - 14)).convert("RGBA")
    art.putdata([
        (r, g, b, 255) if max(r, g, b) > 110 else (0, 0, 0, 0)
        for r, g, b, a in art.getdata()
    ])
    bbox = art.getbbox()
    return art.crop(bbox) if bbox else art


def badge(size: int) -> Image.Image:
    mark = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(mark)
    draw.ellipse((6, 6, size - 6, size - 6), outline=GOLD + (255,), width=max(6, size // 34))
    letters = logo_lettering()
    inner = int(size * 0.62)
    scale = min(inner / letters.width, inner / letters.height)
    letters = letters.resize(
        (max(1, int(letters.width * scale)), max(1, int(letters.height * scale))),
        Image.Resampling.LANCZOS,
    )
    mark.alpha_composite(letters, ((size - letters.width) // 2, (size - letters.height) // 2))
    return mark


def wrap(draw: ImageDraw.ImageDraw, text: str, font, max_w: int) -> list[str]:
    lines: list[str] = []
    cur = ""
    for word in text.split():
        trial = f"{cur} {word}".strip()
        if draw.textlength(trial, font=font) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def build(cfg: dict) -> None:
    card = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(card)
    draw.rounded_rectangle((10, 10, W - 11, H - 11), radius=34, outline=GOLD, width=4)

    f_title = ImageFont.truetype(FONT_BOLD, 50)
    f_tag_el = ImageFont.truetype(FONT_REG, 24)
    f_tag_en = ImageFont.truetype(FONT_REG, 19)
    f_el = ImageFont.truetype(FONT_REG, 24)
    f_en = ImageFont.truetype(FONT_REG, 18)
    f_cta = ImageFont.truetype(FONT_BOLD, 19)
    f_cta_en = ImageFont.truetype(FONT_REG, 16)
    f_pill = ImageFont.truetype(FONT_BOLD, 24)
    f_url = ImageFont.truetype(FONT_REG, 21)

    # Right column: QR on a white plate so it scans off dark card stock.
    qr_size = 250
    qr_x, qr_y = W - qr_size - 56, 92
    card.paste(Image.new("RGB", (qr_size + 26, qr_size + 26), (255, 255, 255)), (qr_x - 13, qr_y - 13))
    card.paste(qr_image(qr_size), (qr_x, qr_y))
    cta_el, cta_en = cfg["cta"]
    mid = qr_x + qr_size / 2
    draw.text((mid - draw.textlength(cta_el, font=f_cta) / 2, qr_y + qr_size + 26), cta_el, font=f_cta, fill=GOLD)
    draw.text((mid - draw.textlength(cta_en, font=f_cta_en) / 2, qr_y + qr_size + 54), cta_en, font=f_cta_en, fill=GREY)

    # Left column: brand, then what the app does, each line in both languages.
    left = 58
    col_w = qr_x - 46 - left
    mark = badge(116)
    card.paste(mark, (left, 42), mark)
    tag_el, tag_en = cfg["tagline"]
    draw.text((left + 134, 44), cfg["title"], font=f_title, fill=GOLD)
    draw.text((left + 136, 112), tag_el, font=f_tag_el, fill=WHITE)
    draw.text((left + 136, 146), tag_en, font=f_tag_en, fill=GREY)

    y = 216
    for bullet_el, bullet_en in cfg["bullets"]:
        draw.ellipse((left + 4, y + 11, left + 16, y + 23), fill=GOLD)
        for row in wrap(draw, bullet_el, f_el, col_w - 34):
            draw.text((left + 34, y), row, font=f_el, fill=WHITE)
            y += 31
        for row in wrap(draw, bullet_en, f_en, col_w - 34):
            draw.text((left + 34, y), row, font=f_en, fill=GREY)
            y += 24
        y += 16

    pill_el, pill_en = cfg["pill"]
    pill_w = draw.textlength(pill_el, font=f_pill) + 52
    pill_y = 498
    draw.rounded_rectangle((left, pill_y, left + pill_w, pill_y + 60), radius=30, fill=GOLD)
    draw.text((left + 26, pill_y + 15), pill_el, font=f_pill, fill=(12, 12, 12))
    draw.text((left + pill_w + 22, pill_y + 20), pill_en, font=f_en, fill=GREY)

    url_w = draw.textlength(APP_URL, font=f_url)
    draw.text(((W - url_w) / 2, H - 56), APP_URL, font=f_url, fill=GREY)

    cfg["out"].parent.mkdir(parents=True, exist_ok=True)
    card.save(cfg["out"], dpi=(300, 300))
    cfg["art"].parent.mkdir(parents=True, exist_ok=True)
    card.save(cfg["art"], dpi=(300, 300))
    print("Wrote", cfg["out"])


def main() -> int:
    if not LOGO.exists():
        raise SystemExit(f"missing logo {LOGO}")
    build(CARD)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
