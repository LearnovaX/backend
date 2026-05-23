import re
import string


_PUNCTUATION_TRANSLATION = str.maketrans("", "", string.punctuation)
_WHITESPACE_PATTERN = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    text = text.lower()
    text = text.translate(_PUNCTUATION_TRANSLATION)
    text = _WHITESPACE_PATTERN.sub(" ", text)
    return text.strip()
