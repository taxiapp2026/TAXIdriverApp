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

EL = {
    "out": OUT / "taxi-and-fly-card-el.png",
    "art": ART / "taxi_and_fly_karta_el.png",
    "title": "Taxi and Fly",
    "subtitle": "Η εφαρμογή για ταξί από και προς το αεροδρόμιο Αθηνών",
    "bullets": [
        "Κλείνεις εύκολα ταξί",
        "Χωρίς login, χωρίς εγγραφή",
        "Καλές τιμές",
    ],
    "cta": "Σκάναρε με την κάμερα",
    "pill": "Κλείσε το ταξί σου τώρα",
}

EN = {
    "out": OUT / "taxi-and-fly-card-en.png",
    "art": ART / "taxi_and_fly_card_en.png",
    "title": "Taxi and Fly",
    "subtitle": "The app for taxis to and from Athens Airport",
    "bullets": [
        "Book a taxi easily",
        "No login, no sign-up",
        "Good prices",
    ],
    "cta": "Scan with your camera",
    "pill": "Book your taxi now",
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

    f_title = ImageFont.truetype(FONT_BOLD, 56)
    f_sub = ImageFont.truetype(FONT_REG, 25)
    f_bullet = ImageFont.truetype(FONT_REG, 26)
    f_cta = ImageFont.truetype(FONT_BOLD, 24)
    f_url = ImageFont.truetype(FONT_REG, 22)

    # Right column: QR on a white plate so it scans off dark card stock.
    qr_size = 290
    qr_x, qr_y = W - qr_size - 54, 62
    card.paste(Image.new("RGB", (qr_size + 28, qr_size + 28), (255, 255, 255)), (qr_x - 14, qr_y - 14))
    card.paste(qr_image(qr_size), (qr_x, qr_y))
    cta_w = draw.textlength(cfg["cta"], font=f_cta)
    draw.text((qr_x + (qr_size - cta_w) / 2, qr_y + qr_size + 30), cfg["cta"], font=f_cta, fill=GOLD)

    # Left column: brand, then what the app actually does.
    left = 58
    col_w = qr_x - 46 - left
    mark = badge(132)
    card.paste(mark, (left, 58), mark)
    draw.text((left + 152, 74), cfg["title"], font=f_title, fill=GOLD)

    y = 214
    for line in wrap(draw, cfg["subtitle"], f_sub, col_w):
        draw.text((left, y), line, font=f_sub, fill=GREY)
        y += 34
    y += 30

    for bullet in cfg["bullets"]:
        rows = wrap(draw, bullet, f_bullet, col_w - 34)
        draw.ellipse((left + 4, y + 12, left + 16, y + 24), fill=GOLD)
        for row in rows:
            draw.text((left + 34, y), row, font=f_bullet, fill=WHITE)
            y += 34
        y += 20

    f_pill = ImageFont.truetype(FONT_BOLD, 26)
    pill_w = draw.textlength(cfg["pill"], font=f_pill) + 56
    pill_y = H - 168
    draw.rounded_rectangle((left, pill_y, left + pill_w, pill_y + 66), radius=33, fill=GOLD)
    draw.text((left + 28, pill_y + 17), cfg["pill"], font=f_pill, fill=(12, 12, 12))

    url_w = draw.textlength(APP_URL, font=f_url)
    draw.text(((W - url_w) / 2, H - 58), APP_URL, font=f_url, fill=GREY)

    cfg["out"].parent.mkdir(parents=True, exist_ok=True)
    card.save(cfg["out"], dpi=(300, 300))
    cfg["art"].parent.mkdir(parents=True, exist_ok=True)
    card.save(cfg["art"], dpi=(300, 300))
    print("Wrote", cfg["out"])


def main() -> int:
    if not LOGO.exists():
        raise SystemExit(f"missing logo {LOGO}")
    build(EL)
    build(EN)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
