import logging
import tempfile
import zipfile
from io import BytesIO
from pathlib import Path
from typing import BinaryIO

from docx import Document
from pypdf import PdfReader

from src.apps.plagiarism.constants import (
    MAX_DOC_FILE_SIZE_BYTES,
    MAX_EXTRACTED_TEXT_CHARS,
    MAX_IMAGE_FILE_SIZE_BYTES,
    MAX_TEXT_FILE_SIZE_BYTES,
    SUPPORTED_ARCHIVE_EXTENSIONS,
    SUPPORTED_DOCX_EXTENSIONS,
    SUPPORTED_IMAGE_EXTENSIONS,
    SUPPORTED_PDF_EXTENSIONS,
    SUPPORTED_TEXT_EXTENSIONS,
)
from src.apps.plagiarism.services.archive_security import (
    UnsafeArchiveError,
    extract_zip_safely,
)
from src.apps.plagiarism.services.ocr import extract_image_text

logger = logging.getLogger(__name__)


class ExtractionError(ValueError):
    pass


def extract_text_from_answer(answer) -> str:
    parts = [answer.description or ""]

    for answer_file in answer.files.all():
        text = extract_text_from_answer_file(answer_file)
        if text:
            parts.append(text)

    return _truncate_text("\n".join(parts))


def extract_text_from_answer_file(answer_file) -> str:
    if not answer_file.file:
        return ""

    file_name = answer_file.original_name or answer_file.file.name
    extension = Path(file_name).suffix.lower()

    try:
        answer_file.file.open("rb")
        return _extract_by_extension(answer_file.file, file_name, extension)
    except Exception:
        logger.exception("Failed to extract text from answer file %s", answer_file.pk)
        return ""
    finally:
        try:
            answer_file.file.close()
        except Exception:
            logger.debug("Could not close answer file %s", answer_file.pk, exc_info=True)


def extract_text_from_path(path: Path) -> str:
    extension = path.suffix.lower()
    if extension in SUPPORTED_ARCHIVE_EXTENSIONS:
        logger.warning("Skipping nested archive at %s", path)
        return ""

    size = path.stat().st_size
    with path.open("rb") as file_obj:
        return _extract_by_extension(file_obj, path.name, extension, size=size)


def _extract_by_extension(
    file_obj: BinaryIO,
    file_name: str,
    extension: str,
    *,
    size: int | None = None,
) -> str:
    if extension in SUPPORTED_TEXT_EXTENSIONS:
        return _extract_plain_text(file_obj, size)
    if extension in SUPPORTED_DOCX_EXTENSIONS:
        return _extract_docx(file_obj, size)
    if extension in SUPPORTED_PDF_EXTENSIONS:
        return _extract_pdf(file_obj, size)
    if extension in SUPPORTED_IMAGE_EXTENSIONS:
        return _extract_image(file_obj, size)
    if extension in SUPPORTED_ARCHIVE_EXTENSIONS:
        return _extract_zip(file_obj, file_name, size)

    logger.info("Skipping unsupported file type for plagiarism extraction: %s", file_name)
    return ""


def _read_limited(file_obj: BinaryIO, limit: int, size: int | None = None) -> bytes:
    if size is not None and size > limit:
        raise ExtractionError("File exceeds extraction size limit")

    data = file_obj.read(limit + 1)
    if len(data) > limit:
        raise ExtractionError("File exceeds extraction size limit")
    return data


def _extract_plain_text(file_obj: BinaryIO, size: int | None = None) -> str:
    data = _read_limited(file_obj, MAX_TEXT_FILE_SIZE_BYTES, size)
    return data.decode("utf-8", errors="ignore")


def _extract_docx(file_obj: BinaryIO, size: int | None = None) -> str:
    data = _read_limited(file_obj, MAX_DOC_FILE_SIZE_BYTES, size)
    document = Document(BytesIO(data))
    return "\n".join(paragraph.text for paragraph in document.paragraphs)


def _extract_pdf(file_obj: BinaryIO, size: int | None = None) -> str:
    data = _read_limited(file_obj, MAX_DOC_FILE_SIZE_BYTES, size)
    reader = PdfReader(BytesIO(data))
    pages_text = []
    for page in reader.pages:
        pages_text.append(page.extract_text() or "")
    return "\n".join(pages_text)


def _extract_image(file_obj: BinaryIO, size: int | None = None) -> str:
    data = _read_limited(file_obj, MAX_IMAGE_FILE_SIZE_BYTES, size)
    return extract_image_text(data)


def _extract_zip(file_obj: BinaryIO, file_name: str, size: int | None = None) -> str:
    data = _read_limited(file_obj, MAX_DOC_FILE_SIZE_BYTES, size)

    try:
        with zipfile.ZipFile(BytesIO(data)) as archive:
            with tempfile.TemporaryDirectory(prefix="plagiarism_zip_") as temp_dir:
                paths = extract_zip_safely(archive, Path(temp_dir))
                parts = [extract_text_from_path(path) for path in paths]
                return _truncate_text("\n".join(part for part in parts if part))
    except (zipfile.BadZipFile, UnsafeArchiveError, ExtractionError):
        logger.warning("Skipping unsafe or invalid zip archive: %s", file_name, exc_info=True)
        return ""


def _truncate_text(text: str) -> str:
    return text[:MAX_EXTRACTED_TEXT_CHARS]
