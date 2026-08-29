"""Running a source file end to end."""
import os
import sys

from .errors import RecursionError_, SaeromError
from .interp import Interpreter
from .parser import parse


def run_source(source, out=None, path=None):
    """Run 새롬 source and return the interpreter.

    Errors are raised with their position, source and call stack attached.
    """
    base = os.path.dirname(os.path.abspath(path)) if path else os.getcwd()
    interpreter = Interpreter(out or sys.stdout)
    try:
        interpreter.run(parse(source, base))
    except SaeromError as error:
        if error.path is None:
            error.path, error.source = path, source
        error.frames.reverse()
        raise
    except RecursionError:
        error = RecursionError_("재귀가 너무 깊음")
        error.path, error.source = path, source
        raise error from None
    return interpreter


def run_file(path):
    with open(path, encoding="utf-8") as handle:
        return run_source(handle.read(), path=path)
