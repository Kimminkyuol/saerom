"""Formatting: put a source file into its canonical shape.

The one thing a Korean language can do that others cannot is fix the
programmer's particles for them. docs/rules.md 3.2 says 을/를 and friends are all
valid, and that the formatter settles the spelling -- but only after a name.
A string's particle is chosen by how the string reads aloud, which no compiler
can judge, so those are left exactly as written.

Formatting rewrites spans of the original text rather than re-printing a
syntax tree. That keeps comments, blank lines and string contents untouched.
"""
import unicodedata
from collections import defaultdict

from .hangul import allomorph
from .lexer import tokenize, prescan

# Particle roles that have two spellings, and what those spellings are.
ALLOMORPHS = {
    "topic": {"은", "는"},
    "subject": {"이", "가"},
    "object": {"을", "를"},
    "instrument": {"으로", "로"},
    "conj": {"과", "와"},
}

# Tokens whose spelling the formatter may use to choose a particle.
CORRECTABLE = ("name", "keyword")

NO_SPACE_BEFORE = {",", ".", ":", "]"}
NO_SPACE_AFTER = {"["}

INDENT = "    "


def format_source(source):
    """Return `source` in canonical shape. Raises SaeromError if it will not parse."""
    text = unicodedata.normalize("NFC", source).replace("\t", INDENT)
    if not text.strip():
        return ""
    text = fix_particles(text)
    text = fix_spacing(text)
    text = fix_indentation(text)
    return text.rstrip("\n") + "\n"


def is_formatted(source):
    return format_source(source) == source


# --- particles -----------------------------------------------------------

def fix_particles(text):
    known = prescan(text)
    lines = text.split("\n")
    tokens = tokenize(text, known)
    edits = defaultdict(list)

    for index, token in enumerate(tokens):
        # 보간 안도 똑같이 고친다. { } 안은 이름이 놓이는 자리이기 때문이다.
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
        if index == 0:
            continue
        previous = tokens[index - 1]
        # Only right after a name, with nothing in between (docs/rules.md 3.2).
        if previous.kind not in CORRECTABLE:
            continue
        if previous.line != token.line or previous.end != token.col:
            continue

        line = lines[token.line - 1]
        written = line[token.col:token.end]
        if written not in ALLOMORPHS[token.extra]:
            continue                     # 까지의 같은 겹조사는 건드리지 않는다
        correct = allomorph(line[previous.col:previous.end], token.extra)
        if written != correct:
            edits[token.line].append((token.col, token.end, correct))

    for lineno, spans in edits.items():
        line = lines[lineno - 1]
        for start, stop, replacement in sorted(spans, reverse=True):
            line = line[:start] + replacement + line[stop:]
        lines[lineno - 1] = line
    return "\n".join(lines)


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


# --- spacing -------------------------------------------------------------

def comment_start(line, string_spans):
    """Where the trailing comment begins, ignoring # inside strings."""
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
            continue                     # 토큰이 주석에 걸치면 손대지 않는다

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
    if before == ",":
        return " "                       # 쉼표 뒤는 언제나 한 칸
    if glued:
        return ""                        # 한 어절에서 갈라진 토큰끼리는 붙인다
    if after in NO_SPACE_BEFORE or before in NO_SPACE_AFTER:
        return ""
    return " "


def join_tokens(line, pieces):
    """Rebuild one line's code from its tokens, spacing them canonically."""
    out = []
    for index, token in enumerate(pieces):
        text = line[token.col:token.end]
        if index:
            previous = pieces[index - 1]
            out.append(gap_between(line[previous.col:previous.end], text,
                                   previous.end == token.col))
        out.append(text)
    return "".join(out)


# --- indentation ---------------------------------------------------------

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
            # 이어지는 줄과 주석 줄은 제 문장을 따라 함께 옮긴다
            result.append(" " * max(0, original + shift) + stripped)
    return "\n".join(result)


def statement_depths(lines):
    """Block depth of every line that starts a statement.

    Mirrors the lexer: a line that does not end in '.' or ':' continues onto
    the next one, and only statement-starting lines carry indentation.
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
                depths[comment] = depth     # 주석은 뒤따르는 문장에 맞춘다
        pending_comments = []
        # 주석을 뺀 부분으로 따져야 한다. '출력한다.  # 하나' 도 끝난 문장이다.
        at_statement_start = code_part(stripped).rstrip().endswith((".", ":"))

    for comment in pending_comments:
        depths[comment] = 0
    return depths
