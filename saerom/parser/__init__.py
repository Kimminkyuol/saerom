"""Syntactic analysis: tokens -> syntax tree."""
from ..lexer import prescan, tokenize
from .base import VerbInfo
from .modules import MODULES, STDLIB, parse_file, resolve_module
from .statements import StatementParser

__all__ = ["Parser", "VerbInfo", "MODULES", "STDLIB", "make_parser", "parse",
           "parse_file", "resolve_module"]


class Parser(StatementParser):
    """새롬 소스를 구문트리로."""


def make_parser(source, base_dir=None):
    vocabulary = prescan(source, base_dir)
    parser = Parser(tokenize(source, vocabulary.names, vocabulary.stems))
    parser.known = vocabulary.names
    parser.stems = vocabulary.stems
    parser.base_dir = base_dir
    return parser


def parse(source, base_dir=None):
    return make_parser(source, base_dir).program()
