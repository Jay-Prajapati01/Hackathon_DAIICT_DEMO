"""Unit tests for LSB steganography (PNG + PDF)."""

import json
import struct

import numpy as np
import pytest
from PIL import Image

from modules.steg import (
    HEADER_SIZE,
    MAGIC_HEADER,
    _lsb_embed,
    _lsb_extract,
    embed_payload_in_pdf,
    embed_payload_in_png,
    extract_payload_from_file,
    extract_payload_from_pdf,
    extract_payload_from_png,
    has_payload,
    image_capacity_bytes,
)

PAYLOAD = {
    "cert_id": "REC-WND-2026-0091",
    "generator_id": "WF-A-01",
    "source_type": "Wind",
    "energy_kwh": 100.0,
    "generation_date": "2026-03-01",
    "issuer_id": "ISSUER-GreenCert-04",
    "issued_at": "2026-03-02T10:15:00+00:00",
    "data_hash": "c9" * 32,
    "signature": "QUJD" * 86,
}


def _noise_image(path, size=(400, 300), mode="RGB", seed=1):
    rng = np.random.default_rng(seed)
    arr = rng.integers(0, 256, size=(size[1], size[0], 3 if mode == "RGB" else 4), dtype=np.uint8)
    Image.fromarray(arr, mode).save(path)
    return str(path)


def test_png_roundtrip(tmp_path):
    cover = _noise_image(tmp_path / "cover.png")
    out = embed_payload_in_png(cover, PAYLOAD, str(tmp_path / "steg.png"))
    assert extract_payload_from_png(out) == PAYLOAD
    assert extract_payload_from_file(out) == PAYLOAD
    assert has_payload(out)


def test_embedding_is_visually_imperceptible(tmp_path):
    cover = _noise_image(tmp_path / "cover.png")
    out = embed_payload_in_png(cover, PAYLOAD, str(tmp_path / "steg.png"))
    a = np.array(Image.open(cover)).astype(int)
    b = np.array(Image.open(out)).astype(int)
    assert np.abs(a - b).max() <= 1  # only the least significant bit changes


def test_plain_image_has_no_payload(tmp_path):
    plain = tmp_path / "plain.png"
    Image.new("RGB", (200, 200), (255, 255, 255)).save(plain)
    assert extract_payload_from_png(str(plain)) is None
    assert has_payload(str(plain)) is False


def test_noise_image_without_payload_returns_none(tmp_path):
    cover = _noise_image(tmp_path / "noise.png", seed=7)
    assert extract_payload_from_png(cover) is None


def test_wire_format_header():
    img = Image.new("RGB", (64, 64), (10, 20, 30))
    data = b"hello"
    steg = _lsb_embed(img, data)
    flat = np.array(steg).reshape(-1)
    header = np.packbits(flat[: HEADER_SIZE * 8] & 1).tobytes()
    assert header[:8] == MAGIC_HEADER
    assert struct.unpack(">I", header[8:12])[0] == len(data)
    assert _lsb_extract(steg) == data


def test_payload_too_large_raises():
    tiny = Image.new("RGB", (4, 4), (0, 0, 0))  # 6 bytes capacity
    with pytest.raises(ValueError, match="Payload too large"):
        _lsb_embed(tiny, b"x" * 100)


def test_capacity_calculation():
    img = Image.new("RGB", (100, 100))
    assert image_capacity_bytes(img) == (100 * 100 * 3) // 8 - HEADER_SIZE


def test_truncated_payload_returns_none():
    img = Image.new("RGB", (64, 64), (0, 0, 0))
    steg = _lsb_embed(img, b"x" * 500)
    cropped = steg.crop((0, 0, 64, 20))  # header intact, body missing
    assert _lsb_extract(cropped) is None


def test_corrupted_length_field_returns_none():
    img = Image.new("RGB", (64, 64), (0, 0, 0))
    steg = _lsb_embed(img, b"x" * 50)
    flat = np.array(steg).reshape(-1).copy()
    # set declared length to 0xFFFFFFFF by forcing the 32 length bits to 1
    flat[64:96] |= 1
    broken = Image.fromarray(flat.reshape(64, 64, 3), "RGB")
    assert _lsb_extract(broken) is None


def test_corrupted_json_returns_none(tmp_path):
    cover = _noise_image(tmp_path / "cover.png")
    out = embed_payload_in_png(cover, PAYLOAD, str(tmp_path / "steg.png"))
    img = Image.open(out)
    flat = np.array(img).reshape(-1).copy()
    flat[HEADER_SIZE * 8 : HEADER_SIZE * 8 + 8] ^= 1  # flip the first payload byte ('{')
    Image.fromarray(flat.reshape(np.array(img).shape), "RGB").save(out)
    assert extract_payload_from_png(out) is None


def test_rgba_cover_is_flattened(tmp_path):
    cover = _noise_image(tmp_path / "cover.png", mode="RGBA")
    out = embed_payload_in_png(cover, PAYLOAD, str(tmp_path / "steg.png"))
    assert Image.open(out).mode == "RGB"
    assert extract_payload_from_png(out) == PAYLOAD


def test_jpeg_cover_embeds_to_png(tmp_path):
    cover = tmp_path / "cover.jpg"
    Image.fromarray(np.random.default_rng(3).integers(0, 256, (300, 400, 3), dtype=np.uint8)).save(cover, quality=90)
    out = embed_payload_in_png(str(cover), PAYLOAD, str(tmp_path / "steg.png"))
    assert extract_payload_from_png(out) == PAYLOAD


def test_pdf_roundtrip_from_png_cover(tmp_path):
    cover = _noise_image(tmp_path / "cover.png", size=(600, 400))
    out = embed_payload_in_pdf(cover, PAYLOAD, str(tmp_path / "steg.pdf"))
    assert extract_payload_from_pdf(out) == PAYLOAD
    assert extract_payload_from_file(out) == PAYLOAD


def test_pdf_without_payload_returns_none(tmp_path):
    from reportlab.pdfgen import canvas

    pdf = tmp_path / "plain.pdf"
    c = canvas.Canvas(str(pdf))
    c.drawString(100, 700, "Just a PDF, no hidden data.")
    c.save()
    assert extract_payload_from_pdf(str(pdf)) is None


def test_unsupported_extension_raises(tmp_path):
    f = tmp_path / "file.txt"
    f.write_text("nope")
    with pytest.raises(ValueError, match="Unsupported file type"):
        extract_payload_from_file(str(f))
    assert has_payload(str(f)) is False


def test_payload_serialisation_is_compact(tmp_path):
    cover = _noise_image(tmp_path / "cover.png")
    out = embed_payload_in_png(cover, PAYLOAD, str(tmp_path / "steg.png"))
    raw = _lsb_extract(Image.open(out))
    assert raw == json.dumps(PAYLOAD, separators=(",", ":")).encode()
