"""모듈 파일 찾아 읽기."""
import os
import unicodedata

from ..errors import SyntaxError_

STDLIB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "stdlib")

MODULES = {}
READING = set()


def ordered(particles):
    """시그니처를 견주기 좋은 꼴로. '이다'의 빈 자리(None)도 담는다."""
    return tuple(sorted(particles, key=lambda p: (p is None, p or "")))


def fits(used, signature):
    """쓰인 조사가 시그니처 안에 갯수까지 들어맞는가."""
    left = list(signature)
    for particle in used:
        if particle not in left:
            return False
        left.remove(particle)
    return True


def resolve_module(name, base_dir):
    """<이름>.sr 이나 <이름>.py 를 찾는다. 옆자리 먼저, 그다음 기본모듈.
    macOS 는 한글 파일명을 NFD 로 담아 두므로 이름을 견줄 때 맞춰 준다."""
    wanted = [unicodedata.normalize("NFC", name + suffix)
              for suffix in (".sr", ".py")]
    for folder in filter(None, (base_dir, STDLIB)):
        for one in wanted:
            direct = os.path.join(folder, one)
            if os.path.exists(direct):
                return direct
        try:
            entries = os.listdir(folder)
        except OSError:
            continue
        for one in wanted:
            for entry in entries:
                if unicodedata.normalize("NFC", entry) == one:
                    return os.path.join(folder, entry)
    return None


def stamp_of(path):
    """파일이 그대로인지 보는 표. 바뀌면 다시 읽는다."""
    info = os.stat(path)
    return info.st_mtime_ns, info.st_size


def parse_file(path):
    from . import make_parser

    path = os.path.abspath(path)
    if path in READING:
        raise SyntaxError_(f"'{os.path.basename(path)}'가 자기 자신을 가져옴")

    stamp = stamp_of(path)
    cached = MODULES.get(path)
    if cached is not None and cached[0] == stamp:
        return cached[1:]

    with open(path, encoding="utf-8") as handle:
        source = handle.read()
    READING.add(path)
    try:
        parser = make_parser(source, os.path.dirname(path))
        statements = parser.program()
    except SyntaxError_ as error:
        if error.path is None:
            error.path, error.source = path, source
        raise
    finally:
        READING.discard(path)

    MODULES[path] = (stamp, statements, parser, source)
    return statements, parser, source
