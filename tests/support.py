"""Shared helpers for the test suite."""
import io
import pathlib

from saerom import run_source
from saerom.errors import SaeromError

STDLIB = pathlib.Path(__file__).resolve().parents[1] / "saerom" / "stdlib"


def run(source, path=None):
    """Run source and return everything it printed."""
    out = io.StringIO()
    run_source(source, out=out, path=path)
    return out.getvalue()


def failure(source, path=None):
    """Run source and return the error it raised."""
    try:
        run(source, path=path)
    except SaeromError as error:
        return error
    raise AssertionError("오류가 나야 하는데 그냥 끝났습니다")
