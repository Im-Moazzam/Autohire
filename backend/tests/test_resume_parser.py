from pathlib import Path

import pytest

from app.services.resume_parser import ExtractionFailed, extract_text

_FIXTURES = Path(__file__).parent / "fixtures" / "resumes"


def _read(name: str) -> bytes:
    return (_FIXTURES / name).read_bytes()


def test_extracts_text_from_real_pdf() -> None:
    text = extract_text(_read("Moazzam_Resume.pdf"), "pdf")
    assert len(text.strip()) >= 50


def test_real_pdf_strips_icon_font_glyph_artifacts() -> None:
    # This fixture's icon font (phone/location/email pictograms) maps into
    # the Private Use Area; pypdf returns the raw codepoint with no
    # whitespace around it, gluing onto the adjacent word (a real
    # extraction-quality bug found via manual smoke testing on this file,
    # not a synthetic case).
    text = extract_text(_read("Moazzam_Resume.pdf"), "pdf")
    assert not any(0xE000 <= ord(ch) <= 0xF8FF for ch in text)
    assert "+923228032990" in text
    assert "moazzamaleem786@gmail.com" in text


def test_extracts_text_from_real_docx() -> None:
    text = extract_text(_read("word_doc_resume.docx"), "docx")
    assert len(text.strip()) >= 50


def test_corrupt_pdf_raises_extraction_failed() -> None:
    with pytest.raises(ExtractionFailed):
        extract_text(_read("corrupt.pdf"), "pdf")


def test_scanned_pdf_has_distinct_message_from_corrupt_pdf() -> None:
    with pytest.raises(ExtractionFailed) as scanned_exc:
        extract_text(_read("scanned_image_resume.pdf"), "pdf")
    with pytest.raises(ExtractionFailed) as corrupt_exc:
        extract_text(_read("corrupt.pdf"), "pdf")
    assert str(scanned_exc.value) != str(corrupt_exc.value)
    assert "scanned" in str(scanned_exc.value).lower() or "image" in str(scanned_exc.value).lower()


def test_password_protected_pdf_raises_distinct_message() -> None:
    with pytest.raises(ExtractionFailed) as exc:
        extract_text(_read("protected.pdf"), "pdf")
    assert "password" in str(exc.value).lower()
