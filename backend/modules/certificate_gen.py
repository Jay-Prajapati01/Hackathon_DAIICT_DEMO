"""
REC Guard — Certificate Generator
Renders the human-readable REC certificate as a PNG (Pillow) or PDF (reportlab).

The PNG produced here is the *cover image* for LSB steganography: the issuer
renders it, then hides the signed payload inside its pixels. The visual layout
is deliberately large (1400 x 1000 px → ~525 KB of LSB capacity) so the payload
always fits with a huge margin.
"""

import os
from datetime import datetime, timezone
from typing import Optional, Tuple

import structlog
from PIL import Image, ImageDraw, ImageFont

log = structlog.get_logger()

CANVAS_W, CANVAS_H = 1400, 1000

# Palette (matches the frontend design tokens)
NAVY = (13, 17, 23)
NAVY_2 = (22, 27, 34)
GREEN = (46, 160, 67)
GREEN_LIGHT = (63, 185, 80)
CREAM = (247, 245, 238)
INK = (30, 36, 44)
MUTED = (110, 118, 129)
LINE = (208, 212, 216)

SOURCE_GLYPH = {
    "Wind": "WIND",
    "Solar": "SOLAR",
    "Hydro": "HYDRO",
    "Biomass": "BIOMASS",
    "Geothermal": "GEOTHERMAL",
    "Tidal": "TIDAL",
    "Other": "RENEWABLE",
}

_FONT_CANDIDATES = {
    "regular": [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ],
    "bold": [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ],
    "mono": [
        "/System/Library/Fonts/Supplemental/Courier New Bold.ttf",
        "/System/Library/Fonts/Menlo.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
        "C:/Windows/Fonts/courbd.ttf",
    ],
}


def _font(kind: str, size: int) -> ImageFont.ImageFont:
    for path in _FONT_CANDIDATES.get(kind, []):
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    try:
        return ImageFont.load_default(size=size)  # Pillow ≥ 10.1
    except TypeError:
        return ImageFont.load_default()


def _text_width(draw: ImageDraw.ImageDraw, text: str, font) -> int:
    left, _, right, _ = draw.textbbox((0, 0), text, font=font)
    return right - left


def _fmt_kwh(value: float) -> str:
    v = float(value)
    return f"{v:,.3f}".rstrip("0").rstrip(".") if v != int(v) else f"{int(v):,}"


def generate_certificate_png(
    cert_id: str,
    generator_id: str,
    source_type: str,
    energy_kwh: float,
    generation_date: str,
    issuer_id: str,
    output_path: str,
    issued_at: Optional[str] = None,
    size: Tuple[int, int] = (CANVAS_W, CANVAS_H),
) -> str:
    """Render the certificate artwork to a PNG file and return its path."""
    W, H = size
    img = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(img)

    # ── Frame ─────────────────────────────────────────────────
    d.rectangle([0, 0, W - 1, H - 1], outline=NAVY, width=14)
    d.rectangle([24, 24, W - 25, H - 25], outline=GREEN, width=3)
    d.rectangle([0, 0, W, 120], fill=NAVY)  # header band
    d.rectangle([0, 120, W, 128], fill=GREEN)  # accent stripe

    # ── Header ────────────────────────────────────────────────
    f_brand = _font("bold", 40)
    f_sub = _font("regular", 20)
    d.text((60, 32), "REC GUARD", font=f_brand, fill=(255, 255, 255))
    d.text((60, 80), "Tamper-evident Renewable Energy Certificate Registry", font=f_sub, fill=(180, 190, 200))
    badge = SOURCE_GLYPH.get(source_type, "RENEWABLE")
    f_badge = _font("bold", 22)
    bw = _text_width(d, badge, f_badge) + 40
    d.rounded_rectangle([W - 60 - bw, 40, W - 60, 88], radius=8, fill=GREEN)
    d.text((W - 60 - bw + 20, 50), badge, font=f_badge, fill=(255, 255, 255))

    # ── Title ─────────────────────────────────────────────────
    f_title = _font("bold", 54)
    title = "RENEWABLE ENERGY CERTIFICATE"
    d.text(((W - _text_width(d, title, f_title)) // 2, 180), title, font=f_title, fill=INK)
    f_tag = _font("regular", 22)
    tag = "This certifies that the electricity described below was generated from a renewable source."
    d.text(((W - _text_width(d, tag, f_tag)) // 2, 250), tag, font=f_tag, fill=MUTED)

    # ── Certificate ID ───────────────────────────────────────
    f_label = _font("bold", 18)
    f_mono = _font("mono", 44)
    d.text(((W - _text_width(d, "CERTIFICATE ID", f_label)) // 2, 315), "CERTIFICATE ID", font=f_label, fill=MUTED)
    d.text(((W - _text_width(d, cert_id, f_mono)) // 2, 345), cert_id, font=f_mono, fill=NAVY)
    d.line([(200, 420), (W - 200, 420)], fill=LINE, width=2)

    # ── Energy figure ────────────────────────────────────────
    f_big = _font("bold", 96)
    f_unit = _font("bold", 36)
    energy_txt = _fmt_kwh(energy_kwh)
    ew = _text_width(d, energy_txt, f_big)
    uw = _text_width(d, "kWh", f_unit)
    x0 = (W - (ew + 20 + uw)) // 2
    d.text((x0, 440), energy_txt, font=f_big, fill=GREEN)
    d.text((x0 + ew + 20, 500), "kWh", font=f_unit, fill=INK)

    # ── Detail grid ──────────────────────────────────────────
    f_val = _font("bold", 28)
    fields = [
        ("GENERATOR / FACILITY", generator_id),
        ("ENERGY SOURCE", source_type),
        ("GENERATION DATE", generation_date),
        ("ISSUING BODY", issuer_id),
    ]
    col_w = (W - 240) // 2
    for i, (label, value) in enumerate(fields):
        cx = 120 + (i % 2) * col_w
        cy = 600 + (i // 2) * 120
        d.rounded_rectangle([cx, cy, cx + col_w - 40, cy + 96], radius=10, fill=(255, 255, 255), outline=LINE)
        d.text((cx + 24, cy + 16), label, font=f_label, fill=MUTED)
        d.text((cx + 24, cy + 46), str(value), font=f_val, fill=INK)

    # ── Footer ───────────────────────────────────────────────
    issued_str = issued_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    d.rectangle([0, H - 110, W, H], fill=NAVY_2)
    f_foot = _font("regular", 18)
    f_foot_b = _font("bold", 18)
    d.text((60, H - 84), "Issued (UTC)", font=f_foot, fill=(150, 160, 170))
    d.text((60, H - 56), issued_str, font=f_foot_b, fill=(230, 237, 243))
    right = "Cryptographically signed (RSA-2048 / SHA-256) and registered in the shared REC ledger."
    d.text((W - 60 - _text_width(d, right, f_foot), H - 84), right, font=f_foot, fill=(150, 160, 170))
    right2 = "Verify this file at any REC Guard verifier - no contact with the issuer required."
    d.text((W - 60 - _text_width(d, right2, f_foot_b), H - 56), right2, font=f_foot_b, fill=GREEN_LIGHT)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    img.save(output_path, format="PNG", optimize=False)
    log.info("certificate_png_generated", cert_id=cert_id, path=output_path, size=size)
    return output_path


def generate_certificate_pdf(
    cert_id: str,
    generator_id: str,
    source_type: str,
    energy_kwh: float,
    generation_date: str,
    issuer_id: str,
    output_path: str,
    issued_at: Optional[str] = None,
) -> str:
    """
    Render a plain (non-steganographic) PDF certificate with reportlab.
    Used for previews / exports; the issuer pipeline embeds the PNG artwork instead
    so that the hidden payload survives as exact pixels.
    """
    from reportlab.lib.pagesizes import landscape, A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas as rl_canvas

    page_w, page_h = landscape(A4)
    c = rl_canvas.Canvas(output_path, pagesize=(page_w, page_h))
    c.setTitle(cert_id)
    c.setAuthor("REC Guard")

    c.setFillColorRGB(*(v / 255 for v in NAVY))
    c.rect(0, page_h - 28 * mm, page_w, 28 * mm, fill=1, stroke=0)
    c.setFillColorRGB(1, 1, 1)
    c.setFont("Helvetica-Bold", 22)
    c.drawString(20 * mm, page_h - 17 * mm, "REC GUARD")
    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, page_h - 23 * mm, "Tamper-evident Renewable Energy Certificate Registry")

    c.setFillColorRGB(*(v / 255 for v in INK))
    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(page_w / 2, page_h - 50 * mm, "RENEWABLE ENERGY CERTIFICATE")
    c.setFont("Courier-Bold", 20)
    c.drawCentredString(page_w / 2, page_h - 64 * mm, cert_id)

    c.setFillColorRGB(*(v / 255 for v in GREEN))
    c.setFont("Helvetica-Bold", 48)
    c.drawCentredString(page_w / 2, page_h - 95 * mm, f"{_fmt_kwh(energy_kwh)} kWh")

    c.setFillColorRGB(*(v / 255 for v in INK))
    c.setFont("Helvetica", 12)
    y = page_h - 120 * mm
    for label, value in [
        ("Generator / Facility", generator_id),
        ("Energy Source", source_type),
        ("Generation Date", generation_date),
        ("Issuing Body", issuer_id),
        ("Issued (UTC)", issued_at or datetime.now(timezone.utc).isoformat(timespec="seconds")),
    ]:
        c.setFont("Helvetica-Bold", 12)
        c.drawString(40 * mm, y, f"{label}:")
        c.setFont("Helvetica", 12)
        c.drawString(95 * mm, y, str(value))
        y -= 9 * mm

    c.showPage()
    c.save()
    log.info("certificate_pdf_generated", cert_id=cert_id, path=output_path)
    return output_path
