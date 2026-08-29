"""Errors: what went wrong, where, and how the program got there."""
import os
import sys
import unicodedata

from .hangul import decompose, conjugate, allomorph

# The order particles are listed in when we show how a verb may be called.
PARTICLE_ORDER = ["가", "의", "에서", "에게", "에", "를", "로", "보다", "와",
                  "부터", "까지", "만큼", "씩", "중", "마다"]

# 어미를 사람이 읽는 이름으로.
ENDING_NAMES = {
    "final": "-ㄴ다", "adnominal_past": "-ㄴ", "adnominal_pres": "-는",
    "conditional": "-면", "conjunctive": "-고", "alternative": "-거나",
    "interrogative": "-ㄴ지", "nominal": "-기", "auxiliary": "-어",
    "negative": "-지", "quotative": "-라는",
}


def ending_name(ending):
    return ENDING_NAMES.get(ending, ending)


def display_width(text):
    """Columns a string occupies in a terminal. Hangul takes two."""
    return sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in text)


class Frame:
    """One entry of the 호출 스택."""
    __slots__ = ("verb", "line")

    def __init__(self, verb, line):
        self.verb, self.line = verb, line


class SaeromError(Exception):
    def __init__(self, message, line=None, col=None, end=None,
                 kind="실행 오류", hint=None):
        self.message = message
        self.line, self.col, self.end = line, col, end
        self.kind = kind
        self.hint = hint
        self.frames = []
        self.path = None
        self.source = None      # 모듈 안에서 난 오류는 제 소스를 들고 다닌다
        super().__init__(message)

    def locate(self, node):
        """Fill in whatever position we are still missing from a syntax node."""
        if node is None:
            return self
        line = getattr(node, "line", None)
        if self.line is None:
            self.line = line
            self.col, self.end = getattr(node, "col", None), getattr(node, "end", None)
        elif self.col is None and line == self.line:
            self.col, self.end = getattr(node, "col", None), getattr(node, "end", None)
        return self


class LexError(SaeromError):
    def __init__(self, message, line=None, col=None, end=None, hint=None):
        super().__init__(message, line, col, end, "어휘 오류", hint)


class SyntaxError_(SaeromError):
    def __init__(self, message, line=None, col=None, end=None, hint=None):
        super().__init__(message, line, col, end, "구문 오류", hint)


class NameError_(SaeromError):
    def __init__(self, message, line=None, col=None, end=None, hint=None):
        super().__init__(message, line, col, end, "이름 오류", hint)


class ParticleError(SaeromError):
    def __init__(self, message, line=None, col=None, end=None, hint=None):
        super().__init__(message, line, col, end, "조사 오류", hint)


class ValueError_(SaeromError):
    def __init__(self, message, line=None, col=None, end=None, hint=None):
        super().__init__(message, line, col, end, "값 오류", hint)


class ArithmeticError_(SaeromError):
    def __init__(self, message, line=None, col=None, end=None, hint=None):
        super().__init__(message, line, col, end, "산술 오류", hint)


class RecursionError_(SaeromError):
    def __init__(self, message, line=None, col=None, end=None, hint=None):
        super().__init__(message, line, col, end, "재귀 오류", hint)


class Raised(SaeromError):
    """An 오류 raised by 새롬 code with '~라는 오류를 낸다'."""
    def __init__(self, message, line=None, col=None, end=None):
        super().__init__(message, line, col, end, "예외")


# --- 비슷한 이름 찾기 -----------------------------------------------------

def quote(word, role="subject"):
    """'반복횟수' + 주격  ->  "'반복횟수'가".

    The language corrects particle allomorphs for the programmer, so its own
    messages had better get them right too.
    """
    return f"'{word}'{allomorph(word, role)}"


def jamo(word):
    """Spell a word out in jamo so 회 and 횟 differ by one, not by a whole
    syllable. That is what makes '반복회수' → '반복횟수' a close match."""
    out = []
    for ch in word:
        parts = decompose(ch)
        out.extend(p for p in parts if p) if parts else out.append(ch)
    return out


def distance(left, right):
    previous = list(range(len(right) + 1))
    for i, a in enumerate(left, 1):
        current = [i]
        for j, b in enumerate(right, 1):
            current.append(min(previous[j] + 1, current[j - 1] + 1,
                               previous[j - 1] + (a != b)))
        previous = current
    return previous[-1]


def suggest(word, candidates):
    """The closest candidate, if one is close enough to be worth naming."""
    spelled = jamo(word)
    limit = max(2, len(spelled) // 3)
    best, best_score = None, limit + 1
    for candidate in candidates:
        if candidate == word:
            continue
        score = distance(spelled, jamo(candidate))
        if score < best_score:
            best, best_score = candidate, score
    return best


def describe_signature(verb, particles):
    """'더하다' + {(에,1), (를,1)}  ->  '~에 ~를 더한다'

    시그니처는 (조사, 갯수) 짝의 모음이다. 같은 조사가 여럿이면 그만큼 늘어놓는다.
    """
    from .words import BUILTINS
    spread = []
    for item in particles:
        if isinstance(item, tuple):
            spread += [item[0]] * item[1]
        else:
            spread.append(item)
    ordered = sorted((p for p in spread if p),
                     key=lambda p: PARTICLE_ORDER.index(p)
                     if p in PARTICLE_ORDER else len(PARTICLE_ORDER))
    if verb in BUILTINS:
        stem, pos, overrides = BUILTINS[verb]
        surface = overrides.get("final") or conjugate(stem, pos, "final")
    else:
        surface = conjugate(verb[:-1], "verb", "final")
    slots = " ".join(f"~{p}" for p in ordered)
    return f"{slots} {surface}".strip()


# --- 보여주기 -------------------------------------------------------------
#
# 파이썬의 트레이스백을 그대로 옮겼다. 이미 그 모양에 익숙한 사람이 많고,
# 편집기와 터미널이 'File "x", line N' 꼴을 눌러서 열어 주기도 한다.

SYNTAX_KINDS = ("어휘 오류", "구문 오류")


def colored(text, code, enabled):
    return f"\033[{code}m{text}\033[0m" if enabled else text


def call_frames(error):
    """호출 스택을 파이썬의 프레임 꼴로 옮긴다.

    쌓아 둔 것은 (부른 동사, 부른 자리) 지만, 파이썬은 프레임마다
    '그 프레임이 지금 실행 중인 줄'을 보여 준다. 그래서 한 칸씩 밀어 준다.
    """
    frames = error.frames
    if not frames:
        return [("<맨바깥>", error.line)]
    out = [("<맨바깥>", frames[0].line)]
    for index, frame in enumerate(frames):
        following = frames[index + 1].line if index + 1 < len(frames) else error.line
        out.append((frame.verb, following))
    return out


def source_line(lines, number):
    if not lines or not number or not (1 <= number <= len(lines)):
        return None, 0
    text = lines[number - 1].replace("\t", "    ")
    stripped = text.lstrip()
    return stripped, len(text) - len(stripped)


def caret_line(stripped, removed, col, end):
    if stripped is None or col is None or col < removed:
        return None
    start = display_width(stripped[:col - removed])
    width = max(1, display_width(stripped[col - removed:(end or col + 1) - removed]))
    return " " * (4 + start) + "^" * width


def format_error(error, source=None, path=None):
    if error.source is not None:
        source, path = error.source, error.path or path
    color = sys.stderr.isatty() and not os.environ.get("NO_COLOR")
    red = lambda t: colored(t, "31;1", color)
    dim = lambda t: colored(t, "2", color)

    lines = source.split("\n") if source else []
    where = f'파일 "{path}"' if path else "파일"
    out = []

    if error.kind in SYNTAX_KINDS:
        if error.line:
            out.append(f"  {where}, {error.line}번째 줄")
            stripped, removed = source_line(lines, error.line)
            if stripped is not None:
                out.append("    " + stripped)
                caret = caret_line(stripped, removed, error.col, error.end)
                if caret:
                    out.append(red(caret))
    else:
        out.append("역추적 (가장 최근 호출이 마지막):")
        frames = call_frames(error)
        index = 0
        while index < len(frames):
            name, line = frames[index]
            repeats = 0
            while (index + repeats + 1 < len(frames)
                   and frames[index + repeats + 1] == (name, line)):
                repeats += 1
            innermost = index + repeats == len(frames) - 1
            out.append(f"  {where}, {line}번째 줄, {name}" +
                       ("" if name == "<맨바깥>" else " 안"))
            stripped, removed = source_line(lines, line)
            if stripped is not None:
                out.append("    " + stripped)
                if innermost:
                    caret = caret_line(stripped, removed, error.col, error.end)
                    if caret:
                        out.append(red(caret))
            if repeats:
                out.append(dim(f"  [앞 줄이 {repeats}번 더 되풀이됨]"))
            index += repeats + 1

    out.append(f"{red(error.kind)}: {error.message}")
    if error.hint:
        out.append(dim(" " * (display_width(error.kind) + 2) + error.hint))
    return "\n".join(out) + "\n"
