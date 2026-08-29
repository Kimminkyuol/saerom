"""암호 — 파이썬으로 적은 새롬 모듈. (docs/tools.md 4)"""
import base64
import hashlib

from saerom.extension import fail, predicate, verb

VALUES = {"해시이름": "sha256"}


@verb("해시구하다", "의")
def hash_of(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@verb("부호화하다", "를")
def encode(text):
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


@verb("복호화하다", "를")
def decode(text):
    try:
        return base64.b64decode(text.encode("ascii")).decode("utf-8")
    except Exception:
        fail("복호화할 수 없음")


@predicate("같은해시이다", "가", "와")
def same_hash(left, right):
    return hash_of(left) == hash_of(right)
