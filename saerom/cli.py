"""명령줄."""
import os
import sys
import traceback

from .errors import SaeromError, format_error
from .formatter import format_source
from .runner import run_source

USAGE = """새롬

  saerom <파일.sr>              실행
  saerom --format <파일.sr>...  형식 교정
  saerom --check  <파일.sr>...  형식 검사
  saerom --lsp                  언어 서버 (stdio)

SAEROM_DEBUG=1 — 파이썬 추적 함께 보기
"""

INTERNAL = (
    "\n새롬 내부 오류: 실행기가 처리하지 못한 상태\n"
    "  SAEROM_DEBUG=1 로 파이썬 추적을 볼 수 있음\n"
)


def debugging():
    return bool(os.environ.get("SAEROM_DEBUG"))


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def complain(path, error):
    if isinstance(error, FileNotFoundError):
        print(f"파일 없음: {path}", file=sys.stderr)
    else:
        print(f"UTF-8 파일이 아님: {path}", file=sys.stderr)


def show(error, source, path):
    sys.stdout.flush()
    sys.stderr.write(format_error(error, source, path))
    if debugging():
        traceback.print_exc()


def execute(path):
    try:
        source = read(path)
    except (FileNotFoundError, UnicodeDecodeError) as error:
        complain(path, error)
        return 1

    try:
        run_source(source, path=path)
    except SaeromError as error:
        show(error, source, path)
        return 1
    except KeyboardInterrupt:
        return 130
    except Exception:
        sys.stdout.flush()
        if debugging():
            traceback.print_exc()
        else:
            sys.stderr.write(INTERNAL)
        return 70
    return 0


def reformat(paths, write):
    changed, failed = [], 0
    for path in paths:
        try:
            source = read(path)
        except (FileNotFoundError, UnicodeDecodeError) as error:
            complain(path, error)
            failed += 1
            continue
        try:
            formatted = format_source(source)
        except SaeromError as error:
            show(error, source, path)
            failed += 1
            continue
        if formatted == source:
            continue
        changed.append(path)
        if write:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(formatted)

    if write:
        for path in changed:
            print(f"수정됨: {path}")
        if not changed and not failed:
            print("고칠 것이 없음")
        return 1 if failed else 0

    for path in changed:
        print(f"형식 어긋남: {path}", file=sys.stderr)
    if changed:
        print(f"\n{len(changed)}개 파일", file=sys.stderr)
    return 1 if (changed or failed) else 0


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)

    if not args or args[0] in ("-h", "--help"):
        print(USAGE, file=sys.stderr)
        return 2

    if args[0] == "--lsp":
        from .lsp import main as serve
        return serve()

    if args[0] in ("--format", "--check"):
        if len(args) < 2:
            print(USAGE, file=sys.stderr)
            return 2
        return reformat(args[1:], args[0] == "--format")

    if len(args) != 1:
        print(USAGE, file=sys.stderr)
        return 2
    return execute(args[0])
