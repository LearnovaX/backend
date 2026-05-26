from difflib import SequenceMatcher

from src.apps.plagiarism.constants import MIN_TEXT_LENGTH_FOR_COMPARISON


def calculate_similarity(text_a: str, text_b: str) -> float:
    if (
        len(text_a) < MIN_TEXT_LENGTH_FOR_COMPARISON
        or len(text_b) < MIN_TEXT_LENGTH_FOR_COMPARISON
    ):
        return 0.0
    return SequenceMatcher(None, text_a, text_b).ratio()
