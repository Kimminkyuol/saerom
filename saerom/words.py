"""Closed tables of particles, endings and built-in verbs.

These tables are part of the language. We never call out to a statistical
morphological analyser: the same source must always parse the same way.
"""
from .hangul import conjugate, ENDINGS

# --- Particles -----------------------------------------------------------
# value: (role, canonical spelling)

CASE_PARTICLES = {
    "은": ("topic", "는"), "는": ("topic", "는"),
    "이": ("subject", "가"), "가": ("subject", "가"),
    "을": ("object", "를"), "를": ("object", "를"),
    "에서": ("ablative", "에서"),
    "에게": ("dative_person", "에게"),
    "에": ("dative", "에"),
    "으로": ("instrument", "로"), "로": ("instrument", "로"),
    "의": ("genitive", "의"),
    "보다": ("comparative", "보다"),
    "마다": ("distributive", "마다"),
    "만큼": ("quantity", "만큼"),
    "중": ("partitive", "중"),
}
RANGE_PARTICLES = {"부터": ("from", "부터"), "까지": ("to", "까지")}
CONJ_PARTICLES = {"와": ("conj", "와"), "과": ("conj", "와")}

PARTICLES = {**CASE_PARTICLES, **RANGE_PARTICLES, **CONJ_PARTICLES}
# A range particle may carry one more case particle: 까지의, 부터를 ...
for _r, _v in RANGE_PARTICLES.items():
    for _c in ("의", "에", "를", "을"):
        PARTICLES[_r + _c] = _v

PARTICLES_BY_LENGTH = sorted(PARTICLES, key=len, reverse=True)

# --- Copula 이다 ---------------------------------------------------------
# The contracted forms 다 / 면 are deliberately absent: including them would
# split 20보다 into 20보 + 이다, and resolving that needs context-sensitive
# lexing, which docs/rules.md 2.2 forbids.

COPULA = {
    "이다": "final",
    "이면": "conditional",
    "인": "adnominal_past",
    "인지": "interrogative",
    "이고": "conjunctive",
    "이거나": "alternative",
    "이라는": "quotative", "라는": "quotative",
}
COPULA_BY_LENGTH = sorted(COPULA, key=len, reverse=True)

# --- Built-in verbs and descriptives -------------------------------------
# name: (stem, pos, irregular overrides)

BUILTINS = {
    "출력하다": ("출력하", "verb", {}),
    "바꾸다": ("바꾸", "verb", {}),
    "더하다": ("더하", "verb", {}),
    "빼다": ("빼", "verb", {}),
    "곱하다": ("곱하", "verb", {}),
    "나누다": ("나누", "verb", {}),
    "반복하다": ("반복하", "verb", {}),
    "빠져나가다": ("빠져나가", "verb", {}),
    "하다": ("하", "verb", {}),
    "보다": ("보", "verb", {}),
    "두다": ("두", "verb", {}),
    "내다": ("내", "verb", {}),
    "읽다": ("읽", "verb", {}),
    "입력받다": ("입력받", "verb", {}),
    "쓰다": ("쓰", "verb", {}),
    "열다": ("열", "verb", {"adnominal_pres": "여는", "adnominal_past": "연",
                           "final": "연다", "conditional": "열면"}),
    "실패하다": ("실패하", "verb", {}),
    "가져오다": ("가져오", "verb", {}),
    "시작하다": ("시작하", "verb", {}),
    "담다": ("담", "verb", {}),
    "끝나다": ("끝나", "verb", {}),
    "다듬다": ("다듬", "verb", {}),
    "자르다": ("자르", "verb", {"adnominal_past": "자른", "auxiliary": "잘라"}),
    "넘어가다": ("넘어가", "verb", {}),
    "돌려주다": ("돌려주", "verb", {}),
    "정렬하다": ("정렬하", "verb", {}),
    "잇다": ("잇", "verb", {"auxiliary": "이어", "adnominal_past": "이은",
                           "conditional": "이으면"}),
    "않다": ("않", "descriptive", {"final": "않다", "adnominal_past": "않은",
                                  "adnominal_pres": "않는", "conditional": "않으면",
                                  "conjunctive": "않고", "interrogative": "않은지",
                                  "alternative": "않거나"}),
    # '아니면'과 '아니고'는 조건문의 예약어라 여기서 만든 활용형에 닿지 않는다.
    # 조건 자리의 '~가 아니면'은 파서가 따로 알아본다.
    "아니다": ("아니", "descriptive", {"final": "아니다", "adnominal_past": "아닌",
                                      "adnominal_pres": "아닌", "interrogative": "아닌지",
                                      "conjunctive": "아니고", "conditional": "아니면"}),
    "크다": ("크", "descriptive", {}),
    "작다": ("작", "descriptive", {}),
    "같다": ("같", "descriptive", {}),
}


def build_form_table(verbs):
    """surface form -> (verb name, pos, ending)"""
    table = {}
    for name, (stem, pos, overrides) in verbs.items():
        for ending in ENDINGS:
            surface = overrides.get(ending) or conjugate(stem, pos, ending)
            table.setdefault(surface, (name, pos, ending))
    return table


VERB_FORMS = build_form_table(BUILTINS)

# --- Reserved words ------------------------------------------------------

KEYWORDS = {
    "만약", "아니고", "아니면", "동안", "이런",
    "참", "거짓", "빈목록", "번째",
    "간격", "끝으로", "오류", "이유", "결과",
}

# Adverbs. They are NOT part of a verb's name -- 각각 can sit apart from its
# verb (숫자들을 각각 2로 나눈 값들) -- so they stay separate tokens and select
# how a verb applies to a collection (docs/rules.md 10).
ADVERBS = {"모두", "각각", "가장", "하나라도"}

# Any user verb is "noun + 하다", so its conjugation is fully predictable.
# The lexer recognises these shapes without knowing the verb in advance.
HADA_FORMS = {
    "한다": "final", "하는": "adnominal_pres", "한": "adnominal_past",
    "하면": "conditional", "하고": "conjunctive", "하거나": "alternative",
    "하는지": "interrogative", "하기": "nominal", "하지": "negative",
    "해": "auxiliary",
}
HADA_BY_LENGTH = sorted(HADA_FORMS, key=len, reverse=True)

# Passive: 정렬하다 -> 정렬되다. Marks a call that copies its target instead
# of mutating it (docs/rules.md 11).
DOEDA_FORMS = {
    "된다": "final", "되는": "adnominal_pres", "된": "adnominal_past",
    "되면": "conditional", "되고": "conjunctive", "되는지": "interrogative",
}
DOEDA_BY_LENGTH = sorted(DOEDA_FORMS, key=len, reverse=True)

# Tails that turn an adnominal-past verb into an expression. They are NOT
# keywords: 값들 is a perfectly good parameter name. Only their position --
# straight after an adnominal verb form -- makes them tails.
CALL_TAILS = {"값", "것", "값들", "것들", "나머지"}


# Particle roles that never carry a verb argument. They belong to the
# construct (걸러내기, 반복문, 범위), not to the verb being reduced.
STRUCTURAL = {"중", "마다", "부터", "까지", "간격", "모듈"}

# What each built-in accepts. The parser needs this to know how many pending
# slots an adnominal verb may take: in '학생들에 줄들을 해석한 값을 더한다'
# 해석하다 must take only '줄들을', leaving '학생들에' for 더하다.
BUILTIN_SIGNATURES = {
    "출력하다": [{"를"}],
    "바꾸다": [{"를", "로"}],
    "잇다": [{"를"}, {"를", "로"}],
    "더하다": [{"에", "를"}],
    "빼다": [{"에서", "를"}],
    "곱하다": [{"에", "를"}],
    "나누다": [{"를", "로"}],
    "크다": [{"가", "보다"}],
    "작다": [{"가", "보다"}],
    "같다": [{"가", "와"}, {"가", "보다"}],
    "시작하다": [{"가", "로"}],
    "담다": [{"가", "를"}],
    "끝나다": [{"가", "로"}],
    "다듬다": [{"를"}],
    "자르다": [{"를", "로"}],
    "정렬하다": [{"를"}, {"를", "로"}],
    "읽다": [{"를"}],
    "입력받다": [set()],
    "열다": [{"를"}],
    "쓰다": [{"에", "를"}],
    "가져오다": [{"를"}],
    "돌려주다": [{"를"}],
    "이다": [{"가", None}, {"가"}, {None}],
    "아니다": [{"가", None}, {"가"}],
}
