import logging
import os
import zipfile
from pathlib import Path, PurePosixPath

from src.apps.plagiarism.constants import (
    MAX_ARCHIVE_FILE_COUNT,
    MAX_ARCHIVE_MEMBER_BYTES,
    MAX_ARCHIVE_UNCOMPRESSED_BYTES,
    UNSUPPORTED_NESTED_ARCHIVE_EXTENSIONS,
)

logger = logging.getLogger(__name__)


class UnsafeArchiveError(ValueError):
    pass


def _safe_member_path(member_name: str) -> PurePosixPath:
    normalized_name = member_name.replace("\\", "/")
    path = PurePosixPath(normalized_name)
    if path.is_absolute() or ".." in path.parts or ":" in path.parts[0]:
        raise UnsafeArchiveError(f"Unsafe archive path: {member_name}")
    return path


def validate_zip_archive(archive: zipfile.ZipFile) -> None:
    members = [info for info in archive.infolist() if not info.is_dir()]
    if len(members) > MAX_ARCHIVE_FILE_COUNT:
        raise UnsafeArchiveError("Archive contains too many files")

    total_size = 0
    for member in members:
        member_path = _safe_member_path(member.filename)
        extension = Path(member_path.name).suffix.lower()

        if extension in UNSUPPORTED_NESTED_ARCHIVE_EXTENSIONS:
            raise UnsafeArchiveError("Nested archives are not supported")

        if member.file_size > MAX_ARCHIVE_MEMBER_BYTES:
            raise UnsafeArchiveError("Archive member is too large")

        total_size += member.file_size
        if total_size > MAX_ARCHIVE_UNCOMPRESSED_BYTES:
            raise UnsafeArchiveError("Archive uncompressed size is too large")


def extract_zip_safely(archive: zipfile.ZipFile, destination: Path) -> list[Path]:
    validate_zip_archive(archive)
    extracted_files: list[Path] = []
    destination = destination.resolve()

    for member in archive.infolist():
        if member.is_dir():
            continue

        relative_path = _safe_member_path(member.filename)
        target_path = (destination / os.fspath(relative_path)).resolve()
        if not target_path.is_relative_to(destination):
            raise UnsafeArchiveError(f"Archive member escapes destination: {member.filename}")

        target_path.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(member) as source, target_path.open("wb") as target:
            remaining = MAX_ARCHIVE_MEMBER_BYTES + 1
            while remaining > 0:
                chunk = source.read(min(64 * 1024, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                target.write(chunk)

            if remaining <= 0:
                raise UnsafeArchiveError("Archive member exceeded size limit while extracting")

        extracted_files.append(target_path)

    logger.info("Safely extracted %s archive files", len(extracted_files))
    return extracted_files
