"""자동 완성과 호버."""
from ..errors import describe_signature
from ..hangul import allomorph
from ..words import ADVERBS, KEYWORDS

PARTICLE_HELP = {
    "는": "선언", "가": "비교의 주어", "를": "목적어",
    "에": "도착지, 덧셈·곱셈의 기준", "에서": "출처, 뺄셈의 기준",
    "에게": "수신자", "로": "수단, 나눗셈의 기준, 변환 결과",
    "의": "필드 접근, 모듈 이름공간", "부터": "범위 시작", "까지": "범위 끝",
    "마다": "반복", "보다": "비교 기준", "만큼": "수량", "씩": "증감 폭",
    "중": "부분 선택", "와": "접속",
}

OFFERED = ["는", "가", "를", "의", "에", "에서", "에게", "로", "보다",
           "와", "부터", "까지", "마다", "만큼", "씩", "중"]

ROLE_OF = {"는": "topic", "가": "subject", "를": "object",
           "로": "instrument", "와": "conj"}


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
            # 앞 낱말의 받침에 맞춘 조사부터 보여 준다.
            groups.append((0, particle_items(word)))
        groups.append((1, [item(name, 6, "이름") for name in sorted(self.names)]))
        groups.append((2, [item(name, 3, signature_hint(name, self.verbs))
                           for name in sorted(self.verbs)]))
        groups.append((3, [item(name, 22, "구조체") for name in sorted(self.types)]))
        groups.append((3, [item(name, 9, "모듈") for name in sorted(self.modules)]))
        groups.append((4, [item(name, 14, "예약어") for name in sorted(KEYWORDS)]))
        groups.append((4, [item(name, 14, "부사") for name in sorted(ADVERBS)]))
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
            if token.value in self.modules:
                return f"모듈 `{token.value}`"
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
    """Offer particles already spelled to match the word in front of them."""
    out = []
    for particle in OFFERED:
        role = ROLE_OF.get(particle)
        spelled = allomorph(word, role) if role else particle
        detail = PARTICLE_HELP.get(particle, "")
        out.append({
            "label": word + spelled,
            "kind": 24,                                   # Operator
            "detail": f"조사 — {detail}" if detail else "조사",
            "insertText": word + spelled,
            "filterText": word + spelled,
        })
    return out

def signature_hint(name, verbs):
    ways = verbs.get(name) or []
    return " / ".join(describe_signature(name, way) for way in ways) or "동사"

def signature_text(statement):
    return " ".join(f"~{particle}" for particle, _ in statement.params)

def verb_help(name, verbs):
    ways = verbs.get(name)
    if not ways:
        return f"동사 `{name}`"
    lines = [f"동사 `{name}`", ""]
    lines += [f"- `{describe_signature(name, way)}`" for way in ways]
    return "\n".join(lines)

def item(label, kind, detail):
    return {"label": label, "kind": kind, "detail": detail}


SNIPPETS = [
    {"label": "만약", "kind": 15, "detail": "조건문",
     "insertText": "만약 ${1:조건}이면:\n    ${0}", "insertTextFormat": 2},
    {"label": "반복한다", "kind": 15, "detail": "반복문",
     "insertText": "${1:1}부터 ${2:10}까지의 ${3:수}들마다 반복한다:\n    ${0}",
     "insertTextFormat": 2},
    {"label": "것은", "kind": 15, "detail": "정의문",
     "insertText": "${1:값}을 ${2:이름}하는 것은:\n    ${0}", "insertTextFormat": 2},
    {"label": "이런 것이다", "kind": 15, "detail": "구조체 선언",
     "insertText": "${1:이름}은 이런 것이다:\n    ${2:필드}는 ${3:정수}이다.\n${0}",
     "insertTextFormat": 2},
]
