"""Turning a source file into the things an editor asks for."""
import os

from ..errors import SaeromError
from ..lexer import prescan, tokenize
from ..nodes import (Call, Declare, DefineStmt, Name, Node, NounDef,
                     PassiveCall)
from ..parser import make_parser
from ..words import BUILTIN_SIGNATURES
from .completion import CompletionMixin
from .tokens import TOKEN_MODIFIERS, TOKEN_TYPES, TokenMixin  # noqa: F401

# LSP SymbolKind
FUNCTION, METHOD, VARIABLE, FIELD = 12, 6, 13, 8

SEVERITY_ERROR = 1

SEVERITY_WARNING = 2

INTERNAL_VERBS = {"이다", "아니다", "그리고", "또는"}


def signature_text(statement):
    return " ".join(f"~{particle}" for particle, _ in statement.params)


class Analysis(TokenMixin, CompletionMixin):
    """실행하지 않고 문서 하나에서 알아낼 수 있는 것."""

    def __init__(self, uri, text, path=None):
        self.uri = uri
        self.text = text
        self.path = path
        self.lines = text.split("\n")
        self.error = None
        self.tokens = []
        self.statements = []
        self.names = set()
        self.stems = frozenset()
        self.verbs = dict(BUILTIN_SIGNATURES)
        self.nouns = set()
        self.modules = set()
        self._analyse()

    def _analyse(self):
        try:
            vocabulary = prescan(self.text, self.directory())
            self.tokens = tokenize(self.text, vocabulary.names, vocabulary.stems)
        except SaeromError as error:
            self.error = error
            return
        self.names = set(vocabulary.names)
        self.stems = vocabulary.stems
        try:
            parser = make_parser(self.text, self.directory())
            self.statements = parser.program()
            self.verbs = dict(parser.signatures)
            self.nouns = set(parser.nouns)
            self.modules = set(parser.module_names)
        except SaeromError as error:
            self.error = error
        self.names |= {statement.target.name for statement in self.statements
                       if isinstance(statement, Declare)
                       and isinstance(statement.target, Name)}

    def directory(self):
        return os.path.dirname(self.path) if self.path else None

    def diagnostics(self):
        """이 문서의 오류만 알린다. 가져온 다른 파일의 오류는 그 파일에서 알린다."""
        error = self.error
        if error is None:
            return self.unknown_verbs()
        if error.path and self.path and error.path != self.path:
            return []
        line = max((error.line or 1) - 1, 0)
        start = error.col or 0
        end = error.end or start + 1
        message = error.message + (f"\n{error.hint}" if error.hint else "")
        return [{
            "range": {"start": {"line": line, "character": start},
                      "end": {"line": line, "character": end}},
            "severity": SEVERITY_ERROR,
            "source": "saerom",
            "code": error.kind,
            "message": message,
        }]

    def unknown_verbs(self):
        """동사는 전역이므로 실행하지 않고도 확인할 수 있다.

        이름은 반복 변수·매개변수·원소 필드로 생기므로 이렇게 볼 수 없다.
        """
        out = []
        for call in walk(self.statements):
            if not isinstance(call, (Call, PassiveCall)):
                continue
            name = call.verb
            if name in INTERNAL_VERBS or name in self.verbs:
                continue
            line = max((getattr(call, "line", 1) or 1) - 1, 0)
            start = getattr(call, "col", None) or 0
            end = getattr(call, "end", None) or start + 1
            out.append({
                "range": {"start": {"line": line, "character": start},
                          "end": {"line": line, "character": end}},
                "severity": SEVERITY_WARNING,
                "source": "saerom",
                "code": "이름 오류",
                "message": f"동사 '{name}' 정의되지 않음",
            })
        return out

    def symbols(self):
        out = []
        for statement in self.statements:
            if isinstance(statement, DefineStmt):
                kind = FUNCTION if statement.kind == "verb" else METHOD
                out.append(self._symbol(statement.name, kind, statement.line,
                                        detail=signature_text(statement)))
            elif isinstance(statement, NounDef):
                out.append(self._symbol(statement.name, FIELD, statement.line,
                                        detail=f"~의 {statement.name}"))
            elif isinstance(statement, Declare) and isinstance(statement.target, Name):
                out.append(self._symbol(statement.target.name, VARIABLE, statement.line))
        return out

    def _symbol(self, name, kind, line, detail=""):
        number = max((line or 1) - 1, 0)
        text = self.lines[number] if number < len(self.lines) else ""
        span = {"start": {"line": number, "character": 0},
                "end": {"line": number, "character": len(text)}}
        return {"name": name, "kind": kind, "detail": detail,
                "range": span, "selectionRange": span}


def walk(value, seen=None):
    """Every node in a tree, once."""
    seen = set() if seen is None else seen
    if isinstance(value, Node):
        if id(value) in seen:
            return
        seen.add(id(value))
        yield value
        for inner in value.__dict__.values():
            yield from walk(inner, seen)
    elif isinstance(value, (list, tuple)):
        for inner in value:
            yield from walk(inner, seen)
