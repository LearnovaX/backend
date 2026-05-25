import hashlib
import json
from collections.abc import Mapping

from django.core.cache import cache

COURSES_LIGHT_LIST_GENERATION_KEY = "courses:light-list:gen"
COURSE_GROUPS_LIST_GENERATION_KEY = "courses:groups:list:gen"
COURSE_GROUPS_PAGE_GENERATION_PREFIX = "courses:course:{course_id}:groups:gen"
COURSE_GROUPS_LIST_TTL = 300
COURSES_LIGHT_LIST_TTL = 300
COURSE_GROUPS_PAGE_TTL = 300


def _get_generation(key: str) -> int:
    value = cache.get(key)
    if value is None:
        cache.add(key, 1)
        value = cache.get(key)
    return int(value or 1)


def bump_generation(key: str) -> int:
    if cache.add(key, 2):
        return 2
    try:
        return cache.incr(key)
    except Exception:
        value = _get_generation(key) + 1
        cache.set(key, value)
        return value


def _query_signature(query_params: Mapping[str, object]) -> str:
    if hasattr(query_params, "lists"):
        normalized = sorted((key, tuple(values)) for key, values in query_params.lists())
    else:
        normalized = sorted(query_params.items())
    payload = json.dumps(normalized, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def course_light_list_cache_key(query_params: Mapping[str, object]) -> str:
    generation = _get_generation(COURSES_LIGHT_LIST_GENERATION_KEY)
    return f"courses:light-list:v{generation}:{_query_signature(query_params)}"


def course_groups_list_cache_key(query_params: Mapping[str, object]) -> str:
    generation = _get_generation(COURSE_GROUPS_LIST_GENERATION_KEY)
    return f"courses:groups:list:v{generation}:{_query_signature(query_params)}"


def course_groups_page_cache_key(course_id: int) -> str:
    generation_key = COURSE_GROUPS_PAGE_GENERATION_PREFIX.format(course_id=course_id)
    generation = _get_generation(generation_key)
    return f"courses:course:{course_id}:groups:v{generation}"


def invalidate_courses_light_list_cache() -> None:
    bump_generation(COURSES_LIGHT_LIST_GENERATION_KEY)


def invalidate_course_groups_list_cache() -> None:
    bump_generation(COURSE_GROUPS_LIST_GENERATION_KEY)


def invalidate_course_groups_page_cache(course_ids) -> None:
    for course_id in set(course_ids or []):
        bump_generation(COURSE_GROUPS_PAGE_GENERATION_PREFIX.format(course_id=course_id))

