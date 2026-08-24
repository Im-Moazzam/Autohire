"""File acceptance for the public apply endpoint — the security-critical half
of US-12. No FastAPI import here: these are plain functions over bytes and
file-like objects, unit-testable without a request, and the route/service
layer is what turns their exceptions into HTTP responses.

Extension and Content-Type are attacker-controlled and are never read here —
acceptance is decided purely from the bytes themselves.
"""

import io
import zipfile
from typing import BinaryIO

_CHUNK_SIZE = 64 * 1024  # 64 KiB

_PDF_MAGIC = b"%PDF-"
_OLE_MAGIC = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"  # .doc (OLE2 compound file)
_ZIP_MAGIC = b"PK\x03\x04"  # .docx candidate — a ZIP container, verified below


class FileTooLarge(Exception):
    """Raised by read_capped once the running total exceeds the cap — the
    check fires mid-stream, before the rest of the file is read."""


class EmptyFile(Exception):
    """Raised by read_capped when zero bytes were read."""


class UnsupportedFileType(Exception):
    """Raised by the caller when sniff_extension finds no match."""


def read_capped(file: BinaryIO, max_bytes: int) -> bytes:
    """Reads `file` in fixed-size chunks, counting bytes as they arrive, and
    aborts the moment the running total exceeds `max_bytes` — the cap is
    never enforced by trusting Content-Length (TC-06). Even a lying
    Content-Length header only ever under-declares the true size, since the
    ASGI server itself won't hand us more bytes than were sent; over-declaring
    just means the stream ends early. Either way this loop is what actually
    decides, not the header.

    # ponytail: by the time a sync route function runs, Starlette has already
    # finished parsing the multipart body — parts over ~1MiB are spooled to a
    # SpooledTemporaryFile on disk, not held fully in memory, so a 15MB upload
    # is never fully buffered in RAM (the AC's stated requirement). It does
    # reach disk before this function gets to reject it. Rejecting before any
    # bytes hit disk would mean parsing the multipart stream by hand via
    # Request.form(max_part_size=...), which gives up the declarative
    # UploadFile signature and the generated OpenAPI multipart schema with it.
    # Upgrade path: hand-parse the stream if disk-spooling of oversized
    # uploads becomes a measured problem.
    """
    total = 0
    chunks: list[bytes] = []
    while True:
        chunk = file.read(_CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise FileTooLarge()
        chunks.append(chunk)
    if total == 0:
        raise EmptyFile()
    return b"".join(chunks)


def _is_docx(content: bytes) -> bool:
    """A ZIP header alone isn't proof of .docx — a .zip/.jar/.apk shares it.
    Require the OOXML package markers: the content-types manifest and at
    least one word/ part."""
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            names = archive.namelist()
    except zipfile.BadZipFile:
        return False
    return "[Content_Types].xml" in names and any(name.startswith("word/") for name in names)


def sniff_extension(content: bytes) -> str | None:
    """Returns the validated extension for `content`'s magic bytes, or None
    if nothing matches. The declared filename and Content-Type are never
    consulted — a `.exe` renamed to `.pdf` presents `MZ` and matches nothing
    here (TC-05).

    `.doc` (OLE2) is recognised by `_OLE_MAGIC` but deliberately rejected
    (returns None, not "doc") — extract_text has no handler for it, so
    accepting it here only produced a silent PARSE_ERROR later (TS-06/R-03)."""
    if content.startswith(_PDF_MAGIC):
        return "pdf"
    if content.startswith(_ZIP_MAGIC):
        return "docx" if _is_docx(content) else None
    return None
