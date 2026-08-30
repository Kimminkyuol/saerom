"""Finding and reading module files."""
import os
import unicodedata

from ..errors import SyntaxError_

# 기본으로 딸려 오는 모듈들이 있는 곳
STDLIB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "stdlib")

# path -> (statements, parser, source).  None 이면 지금 읽고 있는 중이다.
MODULES = {}


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


def forget_modules():
    """읽어 둔 .sr 모듈을 잊는다.

    한 번 읽은 모듈을 다시 읽지 않는 것은 한 프로그램을 실행하는 동안의
    약속이다. 편집기처럼 같은 프로세스가 계속 살아 있는 곳에서는 파일이
    바뀌었을 수 있으므로, 다시 훑기 전에 이것을 부른다.
    """
    MODULES.clear()


def resolve_module(name, base_dir):
    """<이름>.sr 이나 <이름>.py 를 찾는다. 옆자리 먼저, 그 다음 기본모듈."""
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
                # macOS는 한글 파일명을 NFD로 담아 둔다
                if unicodedata.normalize("NFC", entry) == one:
                    return os.path.join(folder, entry)
    return None


def parse_file(path):
    """모듈 하나를 읽어 (문장들, 파서, 소스)를 돌려준다. 한 번만 읽는다."""
    from . import make_parser

    path = os.path.abspath(path)
    if path in MODULES:
        if MODULES[path] is None:
            raise SyntaxError_(f"'{os.path.basename(path)}'가 자기 자신을 가져옴")
        return MODULES[path]

    with open(path, encoding="utf-8") as handle:
        source = handle.read()
    MODULES[path] = None
    try:
        parser = make_parser(source, os.path.dirname(path))
        statements = parser.program()
    except SyntaxError_ as error:
        MODULES.pop(path, None)
        if error.path is None:
            error.path, error.source = path, source
        raise
    MODULES[path] = (statements, parser, source)
    return MODULES[path]
