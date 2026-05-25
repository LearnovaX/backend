import logging

from celery import shared_task
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from src.apps.plagiarism.constants import PLAGIARISM_SIMILARITY_THRESHOLD
from src.apps.plagiarism.models import PlagiarismReport
from src.apps.plagiarism.services.extraction import extract_text_from_answer
from src.apps.plagiarism.services.normalization import normalize_text
from src.apps.plagiarism.services.similarity import calculate_similarity
from src.apps.submissions.models import Answer

logger = logging.getLogger(__name__)

PLAGIARISM_BATCH_LOCK_KEY = "plagiarism:nightly_batch_lock"
PLAGIARISM_BATCH_LOCK_TIMEOUT_SECONDS = 55 * 60
DEFAULT_BATCH_SIZE = 100


@shared_task(
    bind=True,
    name="plagiarism.run_nightly_batch",
    soft_time_limit=1500,
    time_limit=1800,
    ignore_result=True,
)
def run_nightly_plagiarism_batch(self, batch_size: int = DEFAULT_BATCH_SIZE) -> dict[str, int]:
    if not cache.add(
        PLAGIARISM_BATCH_LOCK_KEY,
        self.request.id,
        timeout=PLAGIARISM_BATCH_LOCK_TIMEOUT_SECONDS,
    ):
        logger.info("Skipping plagiarism batch because another run is active")
        return {"processed": 0, "failed": 0, "reports": 0}

    processed = 0
    failed = 0
    reports = 0

    try:
        answer_ids = list(
            Answer.objects.filter(
                plagiarism_status=Answer.PlagiarismStatus.pending_analysis,
                is_deleted=False,
            )
            .order_by("created_at")
            .values_list("id", flat=True)[:batch_size]
        )

        logger.info("Starting plagiarism batch for %s pending answers", len(answer_ids))

        for answer_id in answer_ids:
            try:
                reports += _process_answer(answer_id)
                processed += 1
            except Exception:
                failed += 1
                logger.exception("Plagiarism processing failed for answer %s", answer_id)
                Answer.objects.filter(pk=answer_id).update(
                    plagiarism_status=Answer.PlagiarismStatus.failed,
                    analyzed_at=timezone.now(),
                )

        _notify_admins_placeholder(processed=processed, failed=failed, reports=reports)
        logger.info(
            "Finished plagiarism batch: processed=%s failed=%s reports=%s",
            processed,
            failed,
            reports,
        )
        return {"processed": processed, "failed": failed, "reports": reports}
    finally:
        cache.delete(PLAGIARISM_BATCH_LOCK_KEY)


def _process_answer(answer_id: int) -> int:
    answer = (
        Answer.objects.select_related("task", "user")
        .prefetch_related("files")
        .get(pk=answer_id)
    )

    extracted_text = extract_text_from_answer(answer)
    normalized_text = normalize_text(extracted_text)

    with transaction.atomic():
        Answer.objects.filter(pk=answer.pk).update(
            extracted_text=normalized_text,
            plagiarism_status=Answer.PlagiarismStatus.analyzed,
            analyzed_at=timezone.now(),
        )

    if not normalized_text:
        logger.info("Answer %s produced no extractable text", answer.pk)
        return 0

    comparison_candidates = (
        Answer.objects.filter(
            task_id=answer.task_id,
            plagiarism_status=Answer.PlagiarismStatus.analyzed,
            is_deleted=False,
        )
        .exclude(pk=answer.pk)
        .exclude(extracted_text="")
        .only("id", "extracted_text")
        .iterator(chunk_size=50)
    )

    created_or_updated = 0
    for candidate in comparison_candidates:
        score = calculate_similarity(normalized_text, candidate.extracted_text)
        if score <= 0:
            continue

        submission_a_id, submission_b_id = sorted((answer.pk, candidate.pk))
        flagged = score >= PLAGIARISM_SIMILARITY_THRESHOLD
        PlagiarismReport.objects.update_or_create(
            submission_a_id=submission_a_id,
            submission_b_id=submission_b_id,
            defaults={
                "similarity_score": score,
                "flagged": flagged,
            },
        )
        created_or_updated += 1

    return created_or_updated


def _notify_admins_placeholder(*, processed: int, failed: int, reports: int) -> None:
    logger.info(
        "Plagiarism notification placeholder: processed=%s failed=%s reports=%s",
        processed,
        failed,
        reports,
    )
