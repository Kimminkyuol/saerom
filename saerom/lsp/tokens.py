"""시맨틱 토큰 — 편집기가 소스를 칠하는 데 쓰는 조각들."""
from ..errors import SaeromError
from ..lexer import tokenize
from ..formatter import code_part
from ..words import COMPARATIVES

TOKEN_TYPES = ["namespace", "type", "function", "variable", "property",
               "keyword", "string", "number", "comment", "operator",
               "particle", "ending", "adverb", "embedded"]

TOKEN_MODIFIERS = ["declaration", "definition"]

TYPE_INDEX = {name: index for index, name in enumerate(TOKEN_TYPES)}

KIND_TO_TYPE = {
    "name": "variable",
    "verb": "function",
    "copula": "ending",
    "particle": "particle",
    "keyword": "keyword",
    "adverb": "adverb",
    "string": "string",
    "template": "string",
    "number": "number",
}


class TokenMixin:
    """문서를 (줄, 칸, 길이, 갈래) 조각으로 나눈다."""

    def semantic_tokens(self):
        spans = []
        for index, token in enumerate(self.tokens):
            if token.kind == "template":
                spans += self._template_spans(token)
                continue
            if token.kind == "verb":
                spans += verb_spans(token)
                continue
            name = KIND_TO_TYPE.get(token.kind)
            if name is None:
                continue
            if name == "variable":
                name = self._name_role(index)
            spans.append((token.line - 1, token.col, token.end - token.col, name))
        spans += self._comment_spans()
        spans.sort(key=lambda span: (span[0], span[1]))
        return encode(spans)

    def _name_role(self, index):
        if heads_a_definition(self.tokens, index):
            return "function"
        return name_role(self.tokens[index],
                         self.tokens[index - 1] if index else None,
                         self.modules, self.types)

    def _template_spans(self, token):
        """A string keeps its colour, but the {...} inside is real code.

        Semantic tokens may not overlap, so the string is emitted as the pieces
        around each hole rather than as one span underneath them.
        """
        line = token.line - 1
        text = self.lines[line] if line < len(self.lines) else ""
        spans, cursor = [], token.col

        for kind, inner, start, stop in token.value:
            if kind != "expr":
                continue
            opening = text.rfind("{", cursor, start)
            closing = text.find("}", stop)
            if opening < 0 or closing < 0:
                continue
            spans.append((line, cursor, opening - cursor, "string"))
            spans.append((line, opening, 1, "embedded"))
            spans += self._inner_spans(line, start, inner)
            spans.append((line, closing, 1, "embedded"))
            cursor = closing + 1

        spans.append((line, cursor, token.end - cursor, "string"))
        return [span for span in spans if span[2] > 0]

    def _inner_spans(self, line, offset, inner):
        try:
            pieces = tokenize(inner, frozenset(self.names), self.stems)
        except SaeromError:
            return []
        spans = []
        for index, piece in enumerate(pieces):
            if piece.line != 1:
                continue
            if piece.kind == "verb":
                spans += [(line, offset + col, length, name)
                          for _, col, length, name in verb_spans(piece)]
                continue
            name = KIND_TO_TYPE.get(piece.kind)
            if name is None:
                continue
            if name == "variable":
                name = name_role(piece, pieces[index - 1] if index else None,
                                 self.modules, self.types)
            spans.append((line, offset + piece.col, piece.end - piece.col, name))
        return spans

    def _comment_spans(self):
        spans = []
        for number, line in enumerate(self.lines):
            code = code_part(line)
            if len(code) < len(line):
                spans.append((number, len(code), len(line) - len(code), "comment"))
        return spans


def heads_a_definition(tokens, index):
    """'<사전형>라는 것은:' 의 사전형. 이름 꼴이지만 용언이다."""
    rest = tokens[index + 1:index + 5]
    if len(rest) < 4 or not tokens[index].value.endswith("다"):
        return False
    quotative, tail, topic, colon = rest
    return (quotative.kind == "copula" and quotative.extra[1] == "quotative"
            and tail.kind == "name" and tail.value == "것"
            and topic.kind == "particle" and topic.extra == "topic"
            and colon.kind == "symbol" and colon.value == ":")


def name_role(token, previous, modules, types):
    """이름 하나가 무엇을 가리키는가."""
    if token.value in COMPARATIVES:
        return "operator"
    if token.value in modules:
        return "namespace"
    if token.value in types:
        return "type"
    if previous is not None and previous.kind == "particle" and previous.value == "의":
        return "property"
    return "variable"


def verb_spans(token):
    """Split a verb into its noun part and its ending.

    출력한다 -> 출력 + 한다,  나누어떨어지면 -> 나누어떨어지 + 면.
    The ending fuses into the last syllable of the stem, so we compare the
    dictionary form with what was written and colour the shared head as the
    verb and the rest as an ending.
    """
    line, surface = token.line - 1, token.extra[2]
    base = token.value[:-1] if token.value.endswith("다") else token.value
    shared = 0
    while shared < len(base) and shared < len(surface) and base[shared] == surface[shared]:
        shared += 1
    if shared == 0 or shared >= len(surface):
        return [(line, token.col, token.end - token.col, "function")]
    return [(line, token.col, shared, "function"),
            (line, token.col + shared, len(surface) - shared, "ending")]

def encode(spans):
    """LSP wants (deltaLine, deltaChar, length, type, modifiers) fives."""
    data = []
    last_line = last_char = 0
    for line, char, length, name in spans:
        if length <= 0:
            continue
        delta_line = line - last_line
        delta_char = char - (last_char if delta_line == 0 else 0)
        if delta_char < 0:
            continue
        data += [delta_line, delta_char, length, TYPE_INDEX[name], 0]
        last_line, last_char = line, char
    return data
