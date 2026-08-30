"""Lexical analysis: source text -> tokens."""
import unicodedata

from .words import (PARTICLES, PARTICLES_BY_LENGTH, COPULA, COPULA_BY_LENGTH,
                    VERB_FORMS, KEYWORDS, ADVERBS, HADA_FORMS, HADA_BY_LENGTH,
                    DOEDA_FORMS, DOEDA_BY_LENGTH)


from .errors import LexError


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
               allow_copula=True, known=frozenset()):
    """Split one whitespace-delimited chunk into tokens (see docs/rules.md 2.2).

    allow_particle=False forbids stripping another case particle, keeping rule 6
    (at most one) while still re-analysing the body for a copula.
    allow_copula=False stops '성인인' from splitting twice into 성 + 인 + 인.
    """
    if end is None:
        end = col + len(chunk)

    if chunk in KEYWORDS:
        return [Token("keyword", chunk, line, col, end=end)]

    if chunk in ADVERBS:
        return [Token("adverb", chunk, line, col, end=end)]

    # docs/rules.md 2.2 (2): a chunk that is already a declared name is not cut.
    # Without this, {나이} splits into 나 + 이.
    if chunk in known:
        return [Token("name", chunk, line, col, end=end)]

    if chunk in VERB_FORMS:
        name, pos, ending = VERB_FORMS[chunk]
        return [Token("verb", name, line, col, (pos, ending, chunk), end)]

    # A user verb the lexer has never seen. Since every user verb is
    # "noun + 하다", its shape alone identifies it -- no symbol table needed.
    for form in HADA_BY_LENGTH:
        if chunk.endswith(form) and len(chunk) > len(form):
            name = chunk[: -len(form)] + "하다"
            return [Token("verb", name, line, col,
                          ("verb", HADA_FORMS[form], chunk), end)]

    for form in DOEDA_BY_LENGTH:
        if chunk.endswith(form) and len(chunk) > len(form):
            name = chunk[: -len(form)] + "하다"
            return [Token("verb", name, line, col,
                          ("passive", DOEDA_FORMS[form], chunk), end)]

    if chunk in COPULA:
        return [Token("copula", "이다", line, col,
                          ("descriptive", COPULA[chunk], chunk), end)]

    for form in (COPULA_BY_LENGTH if allow_copula else []):
        if chunk.endswith(form) and len(chunk) > len(form):
            cut = end - len(form)
            head = split_word(chunk[: -len(form)], line, col, cut,
                              allow_particle, False, known)
            return head + [Token("copula", "이다", line, cut,
                                 ("descriptive", COPULA[form], form), end)]

    if chunk in PARTICLES:
        role, canonical = PARTICLES[chunk]
        return [Token("particle", canonical, line, col, role, end)]

    if is_number(chunk):
        value = float(chunk) if "." in chunk else int(chunk)
        return [Token("number", value, line, col, end=end)]

    # Strip exactly one particle from the end.
    if allow_particle:
        for form in PARTICLES_BY_LENGTH:
            if chunk.endswith(form) and len(chunk) > len(form):
                body = chunk[: -len(form)]
                role, canonical = PARTICLES[form]
                # The particle gets its own span so the formatter can rewrite
                # just those characters, and carets underline just the name.
                cut = end - len(form)
                head = split_word(body, line, col, cut, allow_particle=False,
                                  allow_copula=allow_copula, known=known)
                return head + [Token("particle", canonical, line, cut, role, end)]

    return [Token("name", chunk, line, col, end=end)]


ESCAPES = {"n": "\n", "t": "\t", "\\": "\\", '"': '"'}


def tokenize(source, known=None):
    source = unicodedata.normalize("NFC", source).replace("\t", "    ")
    if known is None:
        known = prescan(source)
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
                # Every string interpolates: "{이름}님" embeds an expression.
                # A literal brace is written \{ .
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
                        # 조각의 자리를 함께 담아 둔다. 포매터가 그 안의 조사도
                        # 고쳐야 하기 때문이다.
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
                produced += split_word(text[i:j], lineno, i, j, known=known)
                i = j
                continue
            raise LexError(f"쓸 수 없는 글자: {ch!r}", lineno, i, i + 1)

        tokens += produced
        # A statement ends at '.' or ':', or is a lone value (표현문).
        closed = bool(produced) and produced[-1].kind == "symbol" and produced[-1].value in ".:"
        lone = len(produced) == 1 and produced[0].kind in ("number", "string",
                                                            "template", "keyword", "name")
        if closed or lone:
            tokens.append(Token("newline", None, lineno, len(text)))
            at_statement_start = True
        else:
            at_statement_start = False   # the next physical line continues this one

    while len(indents) > 1:
        indents.pop()
        tokens.append(Token("dedent", 0, len(lines), 0))
    tokens.append(Token("eof", None, len(lines), 0))
    return tokens


def prescan(source):
    """Collect the names a source declares, so the second pass can honour
    docs/rules.md 2.2 (2) and leave them whole.

    A name is anything that carries a particle somewhere, plus the 원소 of any
    collection walked by '~들마다'.
    """
    names = set()
    tokens = tokenize(source, known=frozenset())
    for index, token in enumerate(tokens):
        if token.kind != "name":
            continue
        following = tokens[index + 1] if index + 1 < len(tokens) else None
        if following is not None and following.kind == "particle":
            names.add(token.value)
            if token.value.endswith("들"):
                names.add(token.value[:-1])
    return frozenset(names)
