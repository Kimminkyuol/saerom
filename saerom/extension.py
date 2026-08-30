"""Writing a 새롬 module in Python.

A ``<이름>.py`` file is a module just like a ``<이름>.sr`` file: 가져오기문
finds it the same way and calls what it exports.

    from saerom.extension import verb, predicate, noun, fail

    VALUES = {"원주율": 3.141592653589793}

    @noun("제곱근")
    def square_root(number):
        if number < 0:
            fail("음수의 제곱근은 없음")
        return number ** 0.5

    @predicate("소수이다", "가")
    def is_prime(number):
        return number > 1 and all(number % d for d in range(2, number))

The 새롬 name is spelled out; the particles are the ones the verb is called
with, in the order the Python parameters take them. A verb's name ends in
하다 or 되다, a predicate's in 이다 -- that is what lets the lexer conjugate it.
A noun is reached as `<소유자>의 <이름>`, so it takes the owner alone.
"""
from .errors import Raised

_PENDING = {}


class Export:
    def __init__(self, name, kind, particles, call):
        self.name, self.kind = name, kind
        self.particles, self.call = particles, call


def verb(name, *particles):
    """동사 하나를 내놓는다. 이름은 '하다'나 '되다'로 끝난다."""
    return _register("verb", name, particles)


def predicate(name, *particles):
    """술어 하나를 내놓는다. 이름은 '이다'로 끝나고, 참이나 거짓만 낸다."""
    return _register("predicate", name, particles)


def noun(name):
    """파생 필드 하나를 내놓는다. 소유자 하나를 받는다."""
    return _register("noun", name, ("의",))


def fail(message):
    """새롬의 오류를 낸다. '<message>으로 실패하면:' 이 받는다."""
    raise Raised(str(message))


def _register(kind, name, particles):
    def keep(function):
        _PENDING.setdefault(function.__module__, []).append(
            Export(name, kind, tuple(particles), function))
        return function
    return keep


def taken(module_name):
    """그 파이썬 모듈이 내놓은 것을 적재기에 넘긴다."""
    return _PENDING.pop(module_name, [])
