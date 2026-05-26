import secrets
import uuid

from django.contrib.auth.hashers import check_password, make_password
from django.core.cache import cache

OTP_LEN = 6
TTL_SECONDS = 300
MAX_ATTEMPTS = 5


def _key(token: str) -> str:
    return f"otp:{token}"


def create_otp_code(user_id: int) -> tuple[str, str]:
    code = f"{secrets.randbelow(10 ** OTP_LEN):0{OTP_LEN}d}"
    token = str(uuid.uuid4())
    cache.set(
        _key(token), {"uid": user_id, "code": make_password(code), "attempts": 0}, TTL_SECONDS
    )
    return token, code


def verify(token: str, code: str):
    data = cache.get(_key(token))
    if not data:
        return None  # expired/not found
    if data["attempts"] >= MAX_ATTEMPTS:
        cache.delete(_key(token))
        return None
    ok = check_password(code, data["code"])
    if ok:
        uid = data["uid"]
        cache.delete(_key(token))
        return uid
    data["attempts"] += 1
    cache.set(_key(token), data, TTL_SECONDS)
    return False
