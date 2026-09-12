"""
REC Guard — Steganography Module (LSB — Least Significant Bit)
Hides the cryptographic payload inside a PNG/PDF certificate file's pixels.

Embedding: The JSON payload is converted to bytes, then each bit of those bytes
is hidden in the least significant bit of the R/G/B channels of image pixels
(row-major, R then G then B, most-significant bit first). This is visually
imperceptible but recoverable on extraction.

Wire format hidden in the pixels:
    MAGIC_HEADER (8 bytes) + payload length (4 bytes, big-endian uint32) + payload

Why LSB steganography?
- The hidden payload travels with the file wherever it is copied or shared.
- Tampering with the visible certificate data breaks the hidden proof.
- No external service is needed to verify authenticity.

PDF handling:
- Embedding renders/loads the certificate image, hides the payload in its pixels,
  and writes a PDF whose page image is stored *losslessly* (FlateDecode).
- Extraction pulls the raw image XObject back out of the PDF with PyPDF2, so the
  exact pixel values (and therefore the LSBs) are recovered. Rasterising the page
  with poppler is only used as a last-resort fallback, because resampling
  destroys LSB data.
"""

import io
import json
import os
import struct
from typing import Optional

import numpy as np
import structlog
from PIL import Image

log = structlog.get_logger()

# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────

MAGIC_HEADER = b"RECGUARD"  # 8-byte magic string to detect our payload
HEADER_SIZE = 8 + 4  # magic (8 bytes) + payload length (4 bytes uint32)
MAX_PAYLOAD_BYTES = 1024 * 1024  # sanity cap on declared payload length (1 MB)
SUPPORTED_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp")

# ─────────────────────────────────────────────
# Utility — Image Preparation
# ─────────────────────────────────────────────


def _ensure_rgb(img: Image.Image) -> Image.Image:
    """Ensure image is in RGB mode for consistent channel access."""
    if img.mode == "RGBA":
        # Convert RGBA → RGB (flatten alpha onto white for LSB embed)
        background = Image.new("RGB", img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[3])
        return background
    if img.mode != "RGB":
        return img.convert("RGB")
    return img


def _image_capacity_bytes(img: Image.Image) -> int:
    """
    Calculate how many bytes can be hidden in this image.
    Each pixel's R, G, B channels each hold 1 bit → 3 bits/pixel.
    Capacity in bytes = (width * height * 3) // 8
    """
    w, h = img.size
    return (w * h * 3) // 8


def image_capacity_bytes(img: Image.Image) -> int:
    """Public alias — usable payload capacity (after the header) in bytes."""
    return max(0, _image_capacity_bytes(img) - HEADER_SIZE)


# ─────────────────────────────────────────────
# Core LSB Embed
# ─────────────────────────────────────────────


def _lsb_embed(img: Image.Image, data: bytes) -> Image.Image:
    """
    Embed arbitrary bytes into image pixels using LSB steganography.
    Format: MAGIC_HEADER (8 bytes) + length (4 bytes, big-endian uint32) + data

    The length prefix allows extraction without knowing payload size in advance.
    """
    img = _ensure_rgb(img)
    payload = MAGIC_HEADER + struct.pack(">I", len(data)) + data
    capacity = _image_capacity_bytes(img)

    if len(payload) > capacity:
        raise ValueError(
            f"Payload too large: {len(payload)} bytes > image capacity {capacity} bytes. "
            f"Use a larger certificate image (minimum ~{len(payload) * 8 // 3} pixels)."
        )

    arr = np.array(img, dtype=np.uint8)  # shape (h, w, 3), row-major
    flat = arr.reshape(-1)  # R,G,B,R,G,B,... in pixel order
    bits = np.unpackbits(np.frombuffer(payload, dtype=np.uint8))  # MSB first
    n = bits.size
    flat[:n] = (flat[:n] & 0xFE) | bits
    return Image.fromarray(flat.reshape(arr.shape), "RGB")


# ─────────────────────────────────────────────
# Core LSB Extract
# ─────────────────────────────────────────────


def _lsb_extract(img: Image.Image) -> Optional[bytes]:
    """
    Extract hidden bytes from image pixels.
    Returns raw bytes if MAGIC_HEADER found, None otherwise.
    """
    img = _ensure_rgb(img)
    flat = np.array(img, dtype=np.uint8).reshape(-1)
    total_bits = flat.size

    # Need at least HEADER_SIZE bytes
    header_bits = HEADER_SIZE * 8
    if total_bits < header_bits:
        return None

    header = np.packbits(flat[:header_bits] & 1).tobytes()
    if header[:8] != MAGIC_HEADER:
        log.debug("no_magic_header_found")
        return None  # No payload — not an REC Guard certificate

    payload_length = struct.unpack(">I", header[8:12])[0]
    if payload_length == 0 or payload_length > MAX_PAYLOAD_BYTES:
        log.warning("payload_length_implausible", declared=payload_length)
        return None

    start = header_bits
    end = start + payload_length * 8
    if total_bits < end:
        log.warning("payload_truncated", expected=payload_length)
        return None

    return np.packbits(flat[start:end] & 1).tobytes()


# ─────────────────────────────────────────────
# Serialisation helpers
# ─────────────────────────────────────────────


def _payload_to_bytes(payload: dict) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=False).encode("utf-8")


def _bytes_to_payload(raw: bytes) -> Optional[dict]:
    try:
        obj = json.loads(raw.decode("utf-8"))
        return obj if isinstance(obj, dict) else None
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        log.error("payload_decode_failed", error=str(e))
        return None


def _open_cover_image(path: str) -> Image.Image:
    """Open a PNG/JPEG cover image, or rasterise the first page of a PDF."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        pages = _render_pdf_pages(path)
        if not pages:
            raise ValueError(f"Could not render PDF: {path}")
        return _ensure_rgb(pages[0])
    with Image.open(path) as img:
        img.load()
        return _ensure_rgb(img.copy())


def _render_pdf_pages(pdf_path: str):
    """Rasterise page 1 of a PDF via poppler (pdf2image). Returns [] if unavailable."""
    try:
        from pdf2image import convert_from_path

        return convert_from_path(pdf_path, dpi=200, first_page=1, last_page=1)
    except Exception as e:  # poppler missing, corrupt file, etc.
        log.warning("pdf_render_unavailable", path=pdf_path, error=str(e))
        return []


# ─────────────────────────────────────────────
# High-Level API
# ─────────────────────────────────────────────


def embed_payload_in_png(image_path: str, payload: dict, output_path: str) -> str:
    """
    Embed a JSON payload dict into a PNG file using LSB steganography.
    Saves the result to output_path and returns output_path.
    """
    payload_bytes = _payload_to_bytes(payload)
    cover = _open_cover_image(image_path)
    steg_img = _lsb_embed(cover, payload_bytes)
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    steg_img.save(output_path, format="PNG", optimize=False)
    log.info("payload_embedded_png", input=image_path, output=output_path, payload_bytes=len(payload_bytes))
    return output_path


def embed_payload_in_pdf(source_path: str, payload: dict, output_path: str) -> str:
    """
    Embed payload into a PDF by:
    1. Loading the cover image (a PNG certificate, or page 1 of an existing PDF)
    2. Embedding the LSB payload in the pixels
    3. Writing a new single-page PDF whose page image is stored losslessly
    Returns output_path.
    """
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen import canvas as rl_canvas

    payload_bytes = _payload_to_bytes(payload)
    cover_img = _open_cover_image(source_path)
    steg_img = _lsb_embed(cover_img, payload_bytes)

    # Page size follows the image aspect ratio (72 pt per inch at 150 dpi)
    w_px, h_px = steg_img.size
    scale = 72.0 / 150.0
    page_w, page_h = w_px * scale, h_px * scale

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    c = rl_canvas.Canvas(output_path, pagesize=(page_w, page_h))
    c.setTitle(str(payload.get("cert_id", "REC Certificate")))
    c.setAuthor("REC Guard")
    c.setSubject("Renewable Energy Certificate — tamper-evident")
    # reportlab stores non-JPEG images with FlateDecode (lossless), preserving LSBs.
    c.drawImage(ImageReader(steg_img), 0, 0, width=page_w, height=page_h)
    c.showPage()
    c.save()

    log.info("payload_embedded_pdf", input=source_path, output=output_path, payload_bytes=len(payload_bytes))
    return output_path


def extract_payload_from_png(image_path: str) -> Optional[dict]:
    """
    Extract and decode the hidden JSON payload from a PNG/JPEG file.
    Returns payload dict on success, None if no payload found.
    """
    try:
        with Image.open(image_path) as img:
            raw_bytes = _lsb_extract(img)
        if raw_bytes is None:
            log.warning("no_payload_in_png", path=image_path)
            return None
        payload = _bytes_to_payload(raw_bytes)
        if payload is not None:
            log.info("payload_extracted_png", path=image_path, cert_id=payload.get("cert_id"))
        return payload
    except Exception as e:
        log.error("steg_extract_error", path=image_path, error=str(e))
        return None


def _pdf_embedded_images(pdf_path: str):
    """
    Yield PIL images stored as XObjects on page 1 of a PDF (lossless recovery).

    PyPDF2's convenience `page.images` gives up on filter *chains* such as
    [/ASCII85Decode, /FlateDecode] (which is exactly what reportlab writes), so
    the stream is decoded here by hand: get_data() applies every filter and
    returns the raw sample bytes, which are then wrapped as a PIL image.
    """
    try:
        from PyPDF2 import PdfReader

        reader = PdfReader(pdf_path)
        if not reader.pages:
            return
        page = reader.pages[0]
        resources = page.get("/Resources")
        if not resources or "/XObject" not in resources:
            return
        xobjects = resources["/XObject"].get_object()
        for name in xobjects:
            obj = xobjects[name].get_object()
            if obj.get("/Subtype") != "/Image":
                continue
            try:
                filters = obj.get("/Filter", [])
                if not isinstance(filters, list):
                    filters = [filters]
                filters = [str(f) for f in filters]
                if "/DCTDecode" in filters or "/JPXDecode" in filters:
                    # Lossy image: LSBs will not have survived, but let the caller try.
                    yield Image.open(io.BytesIO(obj.get_data()))
                    continue
                width, height = int(obj["/Width"]), int(obj["/Height"])
                bpc = int(obj.get("/BitsPerComponent", 8))
                cs = obj.get("/ColorSpace", "/DeviceRGB")
                cs = str(cs.get_object() if hasattr(cs, "get_object") else cs)
                mode = {"/DeviceRGB": "RGB", "/DeviceGray": "L", "/DeviceCMYK": "CMYK"}.get(cs)
                if mode is None or bpc != 8:
                    log.debug("pdf_image_unsupported_colorspace", name=str(name), cs=cs, bpc=bpc)
                    continue
                data = obj.get_data()  # all filters applied → raw samples
                yield Image.frombytes(mode, (width, height), data)
            except Exception as e:
                log.debug("pdf_image_decode_failed", name=str(name), error=str(e))
    except Exception as e:
        log.warning("pdf_image_extraction_failed", path=pdf_path, error=str(e))


def extract_payload_from_pdf(pdf_path: str) -> Optional[dict]:
    """
    Extract hidden payload from a PDF certificate file.
    First tries the embedded image XObjects (exact pixels); falls back to rasterising.
    """
    try:
        for img in _pdf_embedded_images(pdf_path):
            raw = _lsb_extract(img)
            if raw is not None:
                payload = _bytes_to_payload(raw)
                if payload is not None:
                    log.info("payload_extracted_pdf", path=pdf_path, cert_id=payload.get("cert_id"))
                    return payload

        # Fallback: rasterise page 1 (LSBs usually don't survive, but try anyway)
        for page in _render_pdf_pages(pdf_path):
            raw = _lsb_extract(page)
            if raw is not None:
                return _bytes_to_payload(raw)

        log.warning("no_payload_in_pdf", path=pdf_path)
        return None
    except Exception as e:
        log.error("pdf_steg_extract_error", path=pdf_path, error=str(e))
        return None


def extract_payload_from_file(file_path: str) -> Optional[dict]:
    """
    Universal extractor — detects file type and routes to correct extractor.
    Supports .png, .jpg, .pdf
    """
    ext = os.path.splitext(file_path)[1].lower()
    if ext in SUPPORTED_IMAGE_EXTENSIONS:
        return extract_payload_from_png(file_path)
    if ext == ".pdf":
        return extract_payload_from_pdf(file_path)
    raise ValueError(f"Unsupported file type: {ext}. Use PNG or PDF.")


def has_payload(file_path: str) -> bool:
    """Cheap check: does this file carry an REC Guard payload at all?"""
    try:
        return extract_payload_from_file(file_path) is not None
    except ValueError:
        return False
