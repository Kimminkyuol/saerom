"""파이썬으로 적은 모듈 읽기."""
import importlib.util
import os
import sys

from .. import extension
from ..errors import SaeromError, quote
from ..words import PARTICLES
from .modules import ordered, stamp_of

PARTICLE_NAMES = {canonical for _, canonical in PARTICLES.values()}

LOADED = {}


class NativeModule:
    """파이썬으로 적은 모듈. 파서에게는 .sr 모듈과 같은 얼굴을 보인다.
    구조체는 내놓을 수 없다."""

    def __init__(self, name, exports, values):
        self.name, self.exports, self.values = name, exports, values
        self.signatures = {}
        for export in exports:
            if export.kind == "noun":
                continue
            self.signatures.setdefault(export.name, []).append(
                ordered(export.particles))
        self.nouns = {export.name for export in exports if export.kind == "noun"}
        self.types = set()


def load(path):
    path = os.path.abspath(path)
    stamp = stamp_of(path)
    cached = LOADED.get(path)
    if cached is not None and cached[0] == stamp:
        return cached[1]

    name = os.path.splitext(os.path.basename(path))[0]
    inner = f"새롬모듈.{name}"
    spec = importlib.util.spec_from_file_location(inner, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[inner] = module
    try:
        spec.loader.exec_module(module)
    except SaeromError:
        raise
    except Exception as error:
        sys.modules.pop(inner, None)
        extension.taken(inner)
        raise SaeromError(
            f"모듈 '{name}'을 읽는 중 파이썬 오류가 남: "
            f"{type(error).__name__}: {error}")

    exports = extension.taken(inner)
    values = getattr(module, "VALUES", {})
    if not isinstance(values, dict):
        raise SaeromError(f"모듈 '{name}'의 VALUES가 사전이 아님")
    for export in exports:
        check(name, export)

    LOADED[path] = (stamp, NativeModule(name, exports, dict(values)))
    return LOADED[path][1]


def check(module, export):
    """내놓는 이름과 조사가 새롬이 부를 수 있는 꼴인가."""
    if export.kind == "noun":
        wanted = count_parameters(export.call)
        if wanted is not None and wanted != 1:
            raise SaeromError(
                f"모듈 '{module}'의 파생 필드 '{export.name}'의 매개변수가 "
                f"하나가 아님: {wanted}개")
        return
    tails = ("하다", "되다") if export.kind == "verb" else ("이다",)
    what = "동사" if export.kind == "verb" else "술어"
    if not any(export.name.endswith(tail) and len(export.name) > len(tail)
               for tail in tails):
        shown = "나 ".join(f"'{tail}'" for tail in tails)
        raise SaeromError(
            f"모듈 '{module}'의 {what} 이름이 {shown}로 끝나지 않음: "
            f"'{export.name}'")
    seen = set()
    for particle in export.particles:
        if particle not in PARTICLE_NAMES:
            raise SaeromError(
                f"모듈 '{module}'의 '{export.name}'에 조사가 아닌 자리가 있음: "
                f"'{particle}'")
        if particle in seen:
            raise SaeromError(
                f"모듈 '{module}'의 '{export.name}'에 조사 {quote(particle)} "
                f"두 번 있음")
        seen.add(particle)
    wanted = count_parameters(export.call)
    if wanted is not None and wanted != len(export.particles):
        raise SaeromError(
            f"모듈 '{module}'의 '{export.name}'은 조사를 {len(export.particles)}개 "
            f"적었으나 매개변수는 {wanted}개임")


def count_parameters(call):
    code = getattr(call, "__code__", None)
    return None if code is None else code.co_argcount
