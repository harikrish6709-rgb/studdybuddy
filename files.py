"""Turns uploaded files into 'attachments' the AI can use."""
import io

IMAGE_EXT = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp"}
VIDEO_EXT = {"mp4": "video/mp4", "mov": "video/quicktime", "webm": "video/webm"}
AUDIO_EXT = {"wav": "audio/wav", "mp3": "audio/mpeg"}

ALLOWED_TYPES = [
    "png", "jpg", "jpeg", "webp",          # images
    "pdf", "docx", "pptx", "txt", "md", "csv",  # documents
    "mp4", "mov", "webm",                  # video
    "mp3", "wav",                          # audio
]

MAX_TEXT = 60000  # characters of text kept from a document
MAX_IMAGE_SIDE = 2048  # bigger photos are scaled down (no visible loss, much faster upload)


def _shrink_image(data: bytes, ext: str):
    """Scale very large photos down. Returns (data, mime) or (data, None) if unchanged."""
    try:
        from PIL import Image, ImageOps
        img = Image.open(io.BytesIO(data))
        if max(img.size) <= MAX_IMAGE_SIDE and len(data) < 4 * 1024 * 1024:
            return data, None
        img = ImageOps.exif_transpose(img)
        img.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))
        buf = io.BytesIO()
        if ext == "png":
            img.save(buf, "PNG", optimize=True)
            return buf.getvalue(), "image/png"
        img.convert("RGB").save(buf, "JPEG", quality=90, optimize=True)
        return buf.getvalue(), "image/jpeg"
    except Exception:
        return data, None


def _pdf_text(data: bytes) -> str:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(data))
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def _docx_text(data: bytes) -> str:
    from docx import Document
    doc = Document(io.BytesIO(data))
    lines = [p.text for p in doc.paragraphs]
    for table in doc.tables:
        for row in table.rows:
            lines.append(" | ".join(cell.text for cell in row.cells))
    return "\n".join(lines)


def _pptx_text(data: bytes) -> str:
    from pptx import Presentation
    prs = Presentation(io.BytesIO(data))
    out = []
    for i, slide in enumerate(prs.slides, 1):
        out.append(f"--- Slide {i} ---")
        for shape in slide.shapes:
            if shape.has_text_frame:
                out.append(shape.text_frame.text)
    return "\n".join(out)


def make_attachment(name: str, data: bytes, read_pdf_text: bool = True) -> dict:
    """Build an attachment dict: name, kind, mime, bytes and (for documents) text."""
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    att = {"name": name, "data": data, "ext": ext, "mime": None,
           "kind": "text", "text": "", "ref": None}
    try:
        if ext in IMAGE_EXT:
            data, new_mime = _shrink_image(data, ext)
            att.update(kind="image", data=data, mime=new_mime or IMAGE_EXT[ext])
        elif ext in VIDEO_EXT:
            att.update(kind="video", mime=VIDEO_EXT[ext])
        elif ext in AUDIO_EXT:
            att.update(kind="audio", mime=AUDIO_EXT[ext])
        elif ext == "pdf":
            att.update(kind="pdf", mime="application/pdf",
                       text=_pdf_text(data) if read_pdf_text else "")
        elif ext == "docx":
            att["text"] = _docx_text(data)
        elif ext == "pptx":
            att["text"] = _pptx_text(data)
        else:
            att["text"] = data.decode("utf-8", errors="ignore")
    except Exception:
        att["text"] = ""
    att["text"] = att["text"][:MAX_TEXT]
    return att
