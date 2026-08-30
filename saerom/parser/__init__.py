"""Syntactic analysis: tokens -> syntax tree."""
from ..lexer import prescan, tokenize
from .base import VerbInfo
from .modules import MODULES, STDLIB, forget_modules, parse_file, resolve_module
from .statements import StatementParser

__all__ = ["Parser", "VerbInfo", "MODULES", "STDLIB", "forget_modules", "make_parser",
           "parse", "parse_file", "resolve_module"]


class Parser(StatementParser):
    """새롬 소스를 구문트리로."""


def make_parser(source, base_dir=None):
    known = prescan(source)
    parser = Parser(tokenize(source, known))
    parser.known = known
    parser.base_dir = base_dir
    return parser


def parse(source, base_dir=None):
    return make_parser(source, base_dir).program()
