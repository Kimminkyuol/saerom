"""어휘 분석: 소스 -> 토큰."""
import os
import unicodedata
from collections import namedtuple

from .hangul import conjugate, is_syllable
from .words import (PARTICLES, PARTICLES_BY_LENGTH, COMPARATIVES, COPULA,
                    COPULA_BY_LENGTH, VERB_FORMS, KEYWORDS, ADVERBS, HADA_FORMS,
                    HADA_BY_LENGTH, DOEDA_FORMS, DOEDA_BY_LENGTH, stem_forms)


from .errors import LexError, SaeromError

Vocabulary = namedtuple("Vocabulary", "names stems")

EMPTY = Vocabulary(frozenset(), frozenset())


class Token:
    __slots__ = ("kind", "value", "extra", "line", "col", "end")

    def __init__(self, kind, value, line, col, extra=None, end=None):
        self.kind, self.value, self.extra = kind, value, extra
        self.line, self.col = line, col
        self.end = col + 1 if end is None else end

    def __repr__(self):
        extra = f"/{self.extra}" if self.extra else ""
        return f"{self.kind}({self.value}{extra})"


def is_word_char(ch):
    return ch.isalnum() or ch == "_"


def is_number(text):
    return text.replace(".", "", 1).isdigit()


def split_word(chunk, line, col, end=None, allow_particle=True,
               allow_copula=True, known=frozenset(), forms=None):
    """어절 하나를 토큰으로 가른다.

    allow_particle=False 는 격조사를 하나만 떼게 막으면서도 몸통에서 '이다'는
    다시 찾게 한다. allow_copula=False 는 '성인인'이 성 + 인 + 인으로 두 번
    갈라지는 것을 막는다.
    """
    if end is None:
        end = col + len(chunk)

    if chunk in KEYWORDS:
        return [Token("keyword", chunk, line, col, end=end)]

    if chunk in ADVERBS:
        return [Token("adverb", chunk, line, col, end=end)]

    if chunk in known or chunk in COMPARATIVES:
        return [Token("name", chunk, line, col, end=end)]

    if chunk in VERB_FORMS:
        name, pos, ending = VERB_FORMS[chunk]
        return [Token("verb", name, line, col, (pos, ending, chunk), end)]

    if forms and chunk in forms:
        name, pos, ending = forms[chunk]
        return [Token("verb", name, line, col, (pos, ending, chunk), end)]

    for form in HADA_BY_LENGTH:
        if chunk.endswith(form) and len(chunk) > len(form):
            name = chunk[: -len(form)] + "하다"
            return [Token("verb", name, line, col,
                          ("verb", HADA_FORMS[form], chunk), end)]

    for form in DOEDA_BY_LENGTH:
        if chunk.endswith(form) and len(chunk) > len(form):
            name = chunk[: -len(form)] + "되다"
            return [Token("verb", name, line, col,
                          ("passive", DOEDA_FORMS[form], chunk), end)]

    if chunk in COPULA:
        return [Token("copula", "이다", line, col,
                          ("descriptive", COPULA[chunk], chunk), end)]

    for form in (COPULA_BY_LENGTH if allow_copula else []):
        if chunk.endswith(form) and len(chunk) > len(form):
            cut = end - len(form)
            head = split_word(chunk[: -len(form)], line, col, cut,
                              allow_particle, False, known, forms)
            return head + [Token("copula", "이다", line, cut,
                                 ("descriptive", COPULA[form], form), end)]

    if chunk in PARTICLES:
        role, canonical = PARTICLES[chunk]
        return [Token("particle", canonical, line, col, role, end)]

    if is_number(chunk):
        value = float(chunk) if "." in chunk else int(chunk)
        return [Token("number", value, line, col, end=end)]

    if allow_particle:
        for form in PARTICLES_BY_LENGTH:
            if chunk.endswith(form) and len(chunk) > len(form):
                body = chunk[: -len(form)]
                role, canonical = PARTICLES[form]
                cut = end - len(form)
                head = split_word(body, line, col, cut, allow_particle=False,
                                  allow_copula=allow_copula, known=known,
                                  forms=forms)
                return head + [Token("particle", canonical, line, cut, role, end)]

    return [Token("name", chunk, line, col, end=end)]


ESCAPES = {"n": "\n", "t": "\t", "\\": "\\", '"': '"'}


def tokenize(source, known=None, stems=frozenset(), base_dir=None):
    """토큰 목록. known 은 이미 선언된 이름, stems 는 고유어 동사의 어간이다."""
    source = unicodedata.normalize("NFC", source).replace("\t", "    ")
    if known is None:
        known, stems = prescan(source, base_dir)
    forms = stem_forms(frozenset(stems))
    lines = source.split("\n")
    tokens = []
    indents = [0]
    at_statement_start = True

    for lineno, text in enumerate(lines, 1):
        stripped = text.lstrip(" ")
        if not stripped or stripped.startswith("#"):
            continue

        depth = len(text) - len(stripped)
        if at_statement_start:
            if depth > indents[-1]:
                indents.append(depth)
                tokens.append(Token("indent", depth, lineno, 0))
            while depth < indents[-1]:
                indents.pop()
                tokens.append(Token("dedent", depth, lineno, 0))
            if depth != indents[-1]:
                raise LexError("들여쓰기가 맞지 않음", lineno, 0, depth)

        produced = []
        i, n = 0, len(text)
        while i < n:
            ch = text[i]
            if ch == " ":
                i += 1
                continue
            if ch == "#":
                break
            if ch == '"':
                j, chars, parts = i + 1, [], []
                while j < n and text[j] != '"':
                    if text[j] == "\\" and j + 1 < n:
                        chars.append(ESCAPES.get(text[j + 1], text[j + 1]))
                        j += 2
                    elif text[j] == "{":
                        depth, k = 1, j + 1
                        while k < n and depth:
                            if text[k] == "{":
                                depth += 1
                            elif text[k] == "}":
                                depth -= 1
                            if depth:
                                k += 1
                        if k >= n:
                            raise LexError("'{'가 닫히지 않음", lineno, j, j + 1)
                        raw = text[j + 1:k]
                        inner = raw.strip()
                        if not inner:
                            raise LexError("'{}' 안이 비었음", lineno, j, k + 1)
                        offset = j + 1 + (len(raw) - len(raw.lstrip()))
                        parts.append(("text", "".join(chars), None, None))
                        parts.append(("expr", inner, offset, offset + len(inner)))
                        chars = []
                        j = k + 1
                    else:
                        chars.append(text[j])
                        j += 1
                if j >= n:
                    raise LexError("따옴표가 닫히지 않음", lineno, i, i + 1)
                if parts:
                    parts.append(("text", "".join(chars), None, None))
                    parts = [part for part in parts if part[0] == "expr" or part[1]]
                    produced.append(Token("template", parts, lineno, i, end=j + 1))
                else:
                    produced.append(Token("string", "".join(chars), lineno, i, end=j + 1))
                i = j + 1
                continue
            if ch == "-" and i + 1 < n and text[i + 1].isdigit():
                j = i + 1
                while j < n and (text[j].isdigit() or
                                 (text[j] == "." and j + 1 < n and text[j + 1].isdigit())):
                    j += 1
                raw = text[i:j]
                produced.append(Token("number", float(raw) if "." in raw else int(raw),
                                      lineno, i, end=j))
                i = j
                continue
            if ch in "[],:.":
                produced.append(Token("symbol", ch, lineno, i, end=i + 1))
                i += 1
                continue
            if is_word_char(ch):
                j = i
                while j < n and (is_word_char(text[j]) or
                                 (text[j] == "." and text[i].isdigit()
                                  and j + 1 < n and text[j + 1].isdigit())):
                    j += 1
                produced += split_word(text[i:j], lineno, i, j, known=known,
                                       forms=forms)
                i = j
                continue
            raise LexError(f"쓸 수 없는 글자: {ch!r}", lineno, i, i + 1)

        tokens += produced
        closed = bool(produced) and produced[-1].kind == "symbol" and produced[-1].value in ".:"
        lone = len(produced) == 1 and produced[0].kind in ("number", "string",
                                                            "template", "keyword", "name")
        if closed or lone:
            tokens.append(Token("newline", None, lineno, len(text)))
            at_statement_start = True
        else:
            at_statement_start = False

    while len(indents) > 1:
        indents.pop()
        tokens.append(Token("dedent", 0, len(lines), 0))
    tokens.append(Token("eof", None, len(lines), 0))
    return tokens


def prescan(source, base_dir=None, chain=None):
    """소스가 선언한 이름과 고유어 동사의 어간을 모은다. 두 번째 훑기가 그
    이름은 가르지 않고 그 어간은 활용형으로 알아본다.

    어간을 모르는 채로 훑으므로 정의 머리 '<어간>는 것은:' 은 아직 이름과
    조사로 갈라져 있고, 여기서 그 모양을 찾는다.
    """
    source = unicodedata.normalize("NFC", source)
    tokens = tokenize(source, known=frozenset())
    lines = source.replace("\t", "    ").split("\n")
    stems = declared_stems(tokens, lines)
    stems |= imported_stems(tokens, base_dir,
                            set() if chain is None else chain)
    return Vocabulary(declared_names(tokens), frozenset(stems))


def declared_names(tokens):
    """어딘가에서 조사를 달고 나온 것, 그리고 '~들마다'가 도는 목록의 원소가 이름이다."""
    names = set()
    for index, token in enumerate(tokens):
        if token.kind != "name":
            continue
        following = tokens[index + 1] if index + 1 < len(tokens) else None
        if following is not None and following.kind == "particle":
            names.add(token.value)
            if token.value.endswith("들"):
                names.add(token.value[:-1])
    return frozenset(names)


def declared_stems(tokens, lines):
    """정의 머리 '<어간>는 것은:' 의 어간. '하'로 끝나면 하다 동사라 뺀다.

    적힌 꼴이 그 어간의 관형현재형과 같을 때만 받는다. 그래서 ㄹ이 빠지는
    '만들는' 같은 것은 어간이 되지 않는다.
    """
    stems = set()
    for index in range(len(tokens) - 4):
        head, particle, tail, topic, colon = tokens[index:index + 5]
        if head.kind != "name" or head.value.endswith("하"):
            continue
        if not is_syllable(head.value[-1]):
            continue
        if particle.kind != "particle" or particle.extra != "topic":
            continue
        if head.line != particle.line or head.end != particle.col:
            continue
        if tail.kind != "name" or tail.value != "것":
            continue
        if topic.kind != "particle" or topic.extra != "topic":
            continue
        if colon.kind != "symbol" or colon.value != ":":
            continue
        written = lines[head.line - 1][head.col:particle.end]
        if conjugate(head.value, "verb", "adnominal_pres") == written:
            stems.add(head.value)
    return stems


def imported_modules(tokens):
    """'<모듈>...을 가져온다.' 의 모듈 이름."""
    names = []
    line = []
    for token in tokens:
        if token.kind in ("indent", "dedent"):
            continue
        if token.kind != "newline":
            line.append(token)
            continue
        if (len(line) >= 3 and line[0].kind == "name"
                and line[-1].kind == "symbol" and line[-1].value == "."
                and line[-2].kind == "verb" and line[-2].value == "가져오다"):
            names.append(line[0].value)
        line = []
    return names


def imported_stems(tokens, base_dir, chain):
    """가져오는 모듈의 어간도 물려받는다. 토큰화가 파싱보다 먼저라서 이 파일을
    가르기 전에 그 파일을 훑어야 한다. 파이썬 모듈은 어간을 내지 못한다."""
    from .parser.modules import resolve_module

    stems = set()
    for name in imported_modules(tokens):
        path = resolve_module(name, base_dir)
        if path is not None and path.endswith(".sr"):
            stems |= file_stems(path, chain)
    return stems


def file_stems(path, chain):
    """파일 하나가 내놓는 어간. 도는 가져오기는 여기서 끊는다."""
    from .parser.modules import stamp_of

    path = os.path.abspath(path)
    if path in chain:
        return frozenset()
    try:
        stamp = stamp_of(path)
    except OSError:
        return frozenset()
    cached = STEM_CACHE.get(path)
    if cached is not None and cached[0] == stamp:
        return cached[1]
    try:
        with open(path, encoding="utf-8") as handle:
            source = handle.read()
    except OSError:
        return frozenset()

    chain.add(path)
    try:
        stems = prescan(source, os.path.dirname(path), chain).stems
    except SaeromError:
        return frozenset()
    finally:
        chain.discard(path)
    STEM_CACHE[path] = (stamp, stems)
    return stems


STEM_CACHE = {}
