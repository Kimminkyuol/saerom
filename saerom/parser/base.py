"""Parser state: tokens, blocks, and what to say when they do not fit."""
from collections import namedtuple

from ..errors import SyntaxError_, quote
from ..words import BUILTIN_SIGNATURES
from .modules import ordered

VerbInfo = namedtuple("VerbInfo", "name pos ending surface negated line col end")


class ParserBase:
    """토큰을 하나씩 먹고, 블록을 나누고, 어긋나면 알린다."""

    _kept = []

    KIND_NAMES = {
        "name": "이름", "number": "수", "string": "글", "template": "글",
        "particle": "조사", "verb": "동사", "copula": "'이다'", "symbol": "기호",
        "keyword": "예약어", "newline": "줄 끝", "indent": "들여쓰기",
        "dedent": "내어쓰기", "eof": "파일 끝", "adverb": "부사",
    }

    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.types = set()      # 선언된 틀 이름들
        self.signatures = {name: [ordered(sig) for sig in sigs]
                           for name, sigs in BUILTIN_SIGNATURES.items()}
        self.known = frozenset()
        self.base_dir = None
        self.module_names = set()   # 가져온 모듈 이름들

    @staticmethod
    def where(token):
        return {"line": token.line, "col": token.col, "end": token.end}

    @staticmethod
    def where_verb(info):
        return {"line": info.line, "col": info.col, "end": info.end}

    def peek(self, ahead=0):
        i = self.pos + ahead
        return self.tokens[i] if i < len(self.tokens) else self.tokens[-1]

    def next(self):
        token = self.peek()
        self.pos += 1
        return token

    def at(self, kind, value=None):
        token = self.peek()
        return token.kind == kind and (value is None or token.value == value)

    def describe(self, token):
        shown = str(token.value) if token.kind != "template" else "글"
        return f"{self.KIND_NAMES.get(token.kind, token.kind)} '{shown}'"

    def expect(self, kind, value=None):
        if not self.at(kind, value):
            token = self.peek()
            want = quote(value, "subject") if value else \
                quote(self.KIND_NAMES.get(kind, kind), "subject")
            if token.kind in ("newline", "eof"):
                raise SyntaxError_(f"{want} 없이 줄이 끝남", **self.where(token))
            raise SyntaxError_(f"{want} 아님: {self.describe(token)}",
                               **self.where(token))
        return self.next()

    def accept(self, kind, value=None):
        if self.at(kind, value):
            self.next()
            return True
        return False

    def line_end(self):
        i = self.pos
        while i < len(self.tokens) and self.tokens[i].kind != "newline":
            i += 1
        return i

    def program(self):
        statements = []
        while not self.at("eof"):
            if self.accept("newline"):
                continue
            statements.append(self.statement())
        return statements

    def block(self):
        self.expect("symbol", ":")
        self.expect("newline")
        self.expect("indent")
        statements = []
        while not self.at("dedent") and not self.at("eof"):
            if self.accept("newline"):
                continue
            statements.append(self.statement())
        self.accept("dedent")
        return statements
