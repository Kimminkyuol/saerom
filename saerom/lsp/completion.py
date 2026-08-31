"""자동 완성과 호버."""
from ..errors import describe_signature
from ..hangul import allomorph
from ..words import ADVERBS, KEYWORDS

PARTICLE_HELP = {
    "는": "선언", "가": "비교의 주어", "를": "목적어",
    "에": "도착지, 덧셈·곱셈의 기준", "에서": "출처, 뺄셈의 기준",
    "에게": "수신자", "로": "수단, 나눗셈의 기준, 변환 결과",
    "의": "필드 접근, 모듈 이름공간", "부터": "범위 시작", "까지": "범위 끝",
    "마다": "반복", "보다": "비교 기준", "만큼": "수량",
    "중": "부분 선택", "와": "접속",
}

COMPARATIVE_HELP = {"이상": "≥", "이하": "≤", "초과": ">", "미만": "<"}

OFFERED = ["는", "가", "를", "의", "에", "에서", "에게", "로", "보다",
           "와", "부터", "까지", "마다", "만큼", "중"]

ROLE_OF = {"는": "topic", "가": "subject", "를": "object",
           "로": "instrument", "와": "conj"}

# LSP CompletionItemKind
VARIABLE, FUNCTION, MODULE, KEYWORD, STRUCT, SNIPPET, OPERATOR = 6, 3, 9, 14, 22, 15, 24
FIELD = 5


class CompletionMixin:
    """무엇을 이어 칠 수 있는지, 무엇을 가리키고 있는지."""

    def completions(self, line, character):
        text = self.lines[line] if line < len(self.lines) else ""
        start = word_start(text, character)
        word = text[start:character]
        span = {"start": {"line": line, "character": start},
                "end": {"line": line, "character": character}}

        groups = []
        if has_hangul(word):
            groups.append((0, particle_items(word)))
        groups.append((1, [item(name, VARIABLE, "이름")
                           for name in sorted(self.names - self.nouns)]))
        groups.append((2, [item(name, FUNCTION, signature_hint(name, self.verbs))
                           for name in sorted(self.verbs)]))
        groups.append((2, [item(name, FIELD, "파생 필드")
                           for name in sorted(self.nouns)]))
        groups.append((3, [item(name, STRUCT, "구조체") for name in sorted(self.types)]))
        groups.append((3, [item(name, MODULE, "모듈") for name in sorted(self.modules)]))
        groups.append((3, [item(name, OPERATOR, f"견줌 — {mark}")
                           for name, mark in sorted(COMPARATIVE_HELP.items())]))
        groups.append((4, [item(name, KEYWORD, "예약어") for name in sorted(KEYWORDS)]))
        groups.append((4, [item(name, KEYWORD, "부사") for name in sorted(ADVERBS)]))
        groups.append((5, [dict(snippet) for snippet in SNIPPETS]))

        out = []
        for rank, items in groups:
            for order, entry in enumerate(items):
                entry.setdefault("insertText", entry["label"])
                entry["sortText"] = f"{rank}{order:03d}"
                entry["textEdit"] = {"range": span, "newText": entry["insertText"]}
                if entry.get("insertTextFormat") == 2:
                    entry["textEdit"]["newText"] = entry["insertText"]
                out.append(entry)
        return out

    def hover(self, line, character):
        token = self.token_at(line, character)
        if token is None:
            return None
        if token.kind == "verb":
            return verb_help(token.value, self.verbs)
        if token.kind == "particle":
            role = PARTICLE_HELP.get(token.value)
            return f"조사 `{token.value}` — {role}" if role else None
        if token.kind == "name":
            if token.value in COMPARATIVE_HELP:
                return f"견줌 `{token.value}` — {COMPARATIVE_HELP[token.value]}"
            if token.value in self.modules:
                return f"모듈 `{token.value}`"
            if token.value in self.nouns:
                return f"파생 필드 `{token.value}`"
            if token.value in self.types:
                return f"구조체 `{token.value}`"
            return f"이름 `{token.value}`"
        return None

    def token_at(self, line, character):
        for token in self.tokens:
            if token.line - 1 == line and token.col <= character < token.end:
                return token
        return None


def word_start(text, character):
    """Where the word under the cursor begins."""
    index = min(character, len(text))
    while index and (text[index - 1].isalnum() or text[index - 1] == "_"):
        index -= 1
    return index

def has_hangul(word):
    return any("가" <= ch <= "힣" for ch in word)

def particle_items(word):
    """앞 낱말의 받침에 맞춘 꼴로 조사를 내놓는다."""
    out = []
    for particle in OFFERED:
        role = ROLE_OF.get(particle)
        spelled = allomorph(word, role) if role else particle
        detail = PARTICLE_HELP.get(particle, "")
        out.append({
            "label": word + spelled,
            "kind": OPERATOR,
            "detail": f"조사 — {detail}" if detail else "조사",
            "insertText": word + spelled,
            "filterText": word + spelled,
        })
    return out

def kind_name(name):
    return "술어" if name.endswith("이다") else "동사"


def signature_hint(name, verbs):
    ways = verbs.get(name) or []
    return " / ".join(describe_signature(name, way) for way in ways) or kind_name(name)

def signature_text(statement):
    return " ".join(f"~{particle}" for particle, _ in statement.params)

def verb_help(name, verbs):
    ways = verbs.get(name)
    if not ways:
        return f"{kind_name(name)} `{name}`"
    lines = [f"{kind_name(name)} `{name}`", ""]
    lines += [f"- `{describe_signature(name, way)}`" for way in ways]
    return "\n".join(lines)

def item(label, kind, detail):
    return {"label": label, "kind": kind, "detail": detail}


SNIPPETS = [
    {"label": "만약", "kind": SNIPPET, "detail": "조건문",
     "insertText": "만약 ${1:조건}이면:\n    ${0}", "insertTextFormat": 2},
    {"label": "반복한다", "kind": SNIPPET, "detail": "반복문",
     "insertText": "${1:1}부터 ${2:10}까지의 ${3:수}들마다 반복한다:\n    ${0}",
     "insertTextFormat": 2},
    {"label": "라는 것은", "kind": SNIPPET, "detail": "용언 정의",
     "insertText": "${1:값}을 ${2:이름}하다라는 것은:\n    ${0}", "insertTextFormat": 2},
    {"label": "이라는 것은", "kind": SNIPPET, "detail": "파생 필드 정의",
     "insertText": "${1:소유자}의 ${2:이름}이라는 것은:\n    ${0}", "insertTextFormat": 2},
    {"label": "이런 것이다", "kind": SNIPPET, "detail": "구조체 선언",
     "insertText": "${1:이름}은 이런 것이다:\n    ${2:필드}는 ${3:정수}이다.\n${0}",
     "insertTextFormat": 2},
]
