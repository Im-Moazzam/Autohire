import io
import zipfile

import pytest

from app.services.resume_validation import (
    EmptyFile,
    FileTooLarge,
    read_capped,
    sniff_extension,
)


def test_sniffs_pdf() -> None:
    assert sniff_extension(b"%PDF-1.4 rest of file") == "pdf"


def test_doc_ole_header_is_unsupported() -> None:
    # .doc is recognised (OLE2 magic) but deliberately rejected — extract_text
    # has no handler for it (TS-06/R-03).
    assert sniff_extension(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1junk") is None


def test_renamed_exe_matches_nothing() -> None:
    assert sniff_extension(b"MZ\x90\x00\x03\x00\x00\x00") is None


def _zip_bytes(entries: dict[str, str]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        for name, content in entries.items():
            archive.writestr(name, content)
    return buf.getvalue()


def test_valid_docx_package_sniffs_as_docx() -> None:
    content = _zip_bytes({"[Content_Types].xml": "<Types/>", "word/document.xml": "<doc/>"})
    assert sniff_extension(content) == "docx"


def test_plain_zip_without_ooxml_markers_is_unsupported() -> None:
    content = _zip_bytes({"hello.txt": "hi"})
    assert sniff_extension(content) is None


def test_malformed_zip_is_unsupported() -> None:
    assert sniff_extension(b"PK\x03\x04not actually a zip") is None


def test_read_capped_returns_full_content_under_cap() -> None:
    data = b"a" * 100
    assert read_capped(io.BytesIO(data), 200) == data


def test_read_capped_raises_before_reading_past_cap() -> None:
    reads: list[int] = []
    real_file = io.BytesIO(b"a" * (10 * 1024 * 1024))

    class _CountingFile:
        def read(self, size: int) -> bytes:
            reads.append(size)
            return real_file.read(size)

    with pytest.raises(FileTooLarge):
        read_capped(_CountingFile(), max_bytes=100)

    # stopped after the first chunk exceeded the cap, not after consuming the
    # whole 10MB source — proves the check fires mid-stream (TC-06)
    assert len(reads) <= 2


def test_read_capped_raises_on_empty_file() -> None:
    with pytest.raises(EmptyFile):
        read_capped(io.BytesIO(b""), 200)
