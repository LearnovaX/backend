import logging
from io import BytesIO

from PIL import Image
from django.conf import settings

from src.apps.plagiarism.constants import MAX_OCR_PIXELS

logger = logging.getLogger(__name__)


def extract_image_text(image_bytes: bytes) -> str:
    try:
        import pytesseract
        pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
    except ImportError:
        logger.warning("pytesseract is not installed; skipping OCR")
        return ""

    try:
        with Image.open(BytesIO(image_bytes)) as image:
            width, height = image.size
            if width * height > MAX_OCR_PIXELS:
                logger.warning(
                    "Skipping OCR for oversized image: %sx%s pixels",
                    width,
                    height,
                )
                return ""
            return pytesseract.image_to_string(image) or ""
    except Exception:
        logger.exception("OCR extraction failed")
        return ""
