"""형식 교정: 소스를 정해진 꼴로.

조사의 꼴은 이름 뒤에서만 고친다. 문자열 뒤의 조사는 그 문자열을 소리 내어
읽는 방법에 달렸고 그것은 판단할 수 없다.

구문트리를 다시 찍지 않고 원본의 자리만 고쳐 쓴다. 그래야 주석과 빈 줄과
문자열 속이 그대로 남는다.
"""
import unicodedata
from collections import defaultdict

from .hangul import allomorph
from .lexer import tokenize, prescan

ALLOMORPHS = {
    "topic": {"은", "는"},
    "subject": {"이", "가"},
    "object": {"을", "를"},
    "instrument": {"으로", "로"},
    "conj": {"과", "와"},
}

CORRECTABLE = ("name", "keyword")

NO_SPACE_BEFORE = {",", ".", ":", "]"}
NO_SPACE_AFTER = {"["}

INDENT = "    "


def format_source(source):
    """소스를 정해진 꼴로. 갈라지지 않으면 SaeromError."""
    text = unicodedata.normalize("NFC", source).replace("\t", INDENT)
    if not text.strip():
        return ""
    text = fix_particles(text)
    text = fix_spacing(text)
    text = fix_indentation(text)
    return text.rstrip("\n") + "\n"


def is_formatted(source):
    return format_source(source) == source


def fix_particles(text):
    known = prescan(text)
    lines = text.split("\n")
    tokens = tokenize(text, known)
    edits = defaultdict(list)

    for index, token in enumerate(tokens):
        if token.kind == "template":
            line = lines[token.line - 1]
            for kind, inner, start, stop in token.value:
                if kind != "expr":
                    continue
                fixed = fix_fragment(inner, known)
                if fixed != inner:
                    edits[token.line].append((start, stop, fixed))
            continue

        if token.kind != "particle" or token.extra not in ALLOMORPHS:
            continue
        if index == 0 or not touches_name(tokens[index - 1], token):
            continue

        previous = tokens[index - 1]
        line = lines[token.line - 1]
        written = line[token.col:token.end]
        if written not in ALLOMORPHS[token.extra]:
            continue
        correct = allomorph(line[previous.col:previous.end], token.extra)
        if written != correct:
            edits[token.line].append((token.col, token.end, correct))

    for lineno, spans in edits.items():
        line = lines[lineno - 1]
        for start, stop, replacement in sorted(spans, reverse=True):
            line = line[:start] + replacement + line[stop:]
        lines[lineno - 1] = line
    return "\n".join(lines)


def touches_name(previous, particle):
    """조사가 이름 바로 뒤에, 사이에 아무것도 없이 붙어 있는가."""
    return (previous.kind in CORRECTABLE
            and previous.line == particle.line and previous.end == particle.col)


def fix_fragment(fragment, known):
    """Correct particles inside one {...} of a 보간 string."""
    try:
        pieces = tokenize(fragment, known)
    except Exception:
        return fragment
    edits = []
    for index, piece in enumerate(pieces):
        if index == 0 or piece.kind != "particle" or piece.extra not in ALLOMORPHS:
            continue
        previous = pieces[index - 1]
        if previous.kind not in CORRECTABLE or previous.end != piece.col:
            continue
        written = fragment[piece.col:piece.end]
        if written not in ALLOMORPHS[piece.extra]:
            continue
        correct = allomorph(fragment[previous.col:previous.end], piece.extra)
        if written != correct:
            edits.append((piece.col, piece.end, correct))
    for start, stop, replacement in sorted(edits, reverse=True):
        fragment = fragment[:start] + replacement + fragment[stop:]
    return fragment


def comment_start(line, string_spans):
    """줄 끝 주석이 시작하는 자리. 문자열 안의 #은 세지 않는다."""
    for index, char in enumerate(line):
        if char != "#":
            continue
        if not any(start <= index < stop for start, stop in string_spans):
            return index
    return len(line)


def code_part(line):
    """The line without its trailing comment, found without tokenising."""
    inside, index = False, 0
    while index < len(line):
        char = line[index]
        if char == "\\" and inside:
            index += 2
            continue
        if char == '"':
            inside = not inside
        elif char == "#" and not inside:
            return line[:index]
        index += 1
    return line


def fix_spacing(text):
    lines = text.split("\n")
    tokens = tokenize(text)

    by_line = defaultdict(list)
    for token in tokens:
        if token.kind in ("indent", "dedent", "newline", "eof"):
            continue
        by_line[token.line].append(token)

    for lineno, line in enumerate(lines, 1):
        pieces = by_line.get(lineno)
        if not pieces:
            continue
        strings = [(t.col, t.end) for t in pieces if t.kind in ("string", "template")]
        cut = comment_start(line, strings)
        if pieces[-1].end > cut:
            continue

        indent = len(line) - len(line.lstrip(" "))
        rebuilt = join_tokens(line, pieces)
        comment = line[cut:].rstrip()
        if comment:
            gap = line[:cut].rstrip()
            spacing = " " * max(2, cut - len(gap))
            rebuilt = rebuilt + spacing + comment
        lines[lineno - 1] = " " * indent + rebuilt

    return "\n".join(lines)


def gap_between(before, after, glued):
    """두 토큰 사이의 빈 칸. glued 는 한 어절에서 갈라진 토큰끼리라는 뜻이다."""
    if before == ",":
        return " "
    if glued:
        return ""
    if after in NO_SPACE_BEFORE or before in NO_SPACE_AFTER:
        return ""
    return " "


def join_tokens(line, pieces):
    """한 줄의 코드를 토큰에서 다시 짓는다."""
    out = []
    for index, token in enumerate(pieces):
        text = line[token.col:token.end]
        if index:
            previous = pieces[index - 1]
            out.append(gap_between(line[previous.col:previous.end], text,
                                   previous.end == token.col))
        out.append(text)
    return "".join(out)


def fix_indentation(text):
    lines = text.split("\n")
    depths = statement_depths(lines)

    result = []
    shift = 0
    for lineno, line in enumerate(lines, 1):
        stripped = line.lstrip(" ")
        if not stripped:
            result.append("")
            continue
        original = len(line) - len(stripped)
        if lineno in depths:
            wanted = len(INDENT) * depths[lineno]
            shift = wanted - original
            result.append(" " * wanted + stripped)
        else:
            result.append(" " * max(0, original + shift) + stripped)
    return "\n".join(result)


def statement_depths(lines):
    """문장을 시작하는 줄마다의 블록 깊이. 주석 줄은 뒤따르는 문장을 따른다.

    어휘 분석과 같은 셈이다. '.' 이나 ':' 로 끝나지 않는 줄은 다음 줄로 이어지고,
    문장을 시작하는 줄만 들여쓰기를 갖는다.
    """
    depths = {}
    stack = [0]
    at_statement_start = True
    pending_comments = []

    for lineno, line in enumerate(lines, 1):
        stripped = line.lstrip(" ")
        if not stripped:
            continue
        if stripped.startswith("#"):
            pending_comments.append(lineno)
            continue

        column = len(line) - len(stripped)
        if at_statement_start:
            if column > stack[-1]:
                stack.append(column)
            while column < stack[-1]:
                stack.pop()
            depth = len(stack) - 1
            depths[lineno] = depth
            for comment in pending_comments:
                depths[comment] = depth
        pending_comments = []
        at_statement_start = code_part(stripped).rstrip().endswith((".", ":"))

    for comment in pending_comments:
        depths[comment] = 0
    return depths
