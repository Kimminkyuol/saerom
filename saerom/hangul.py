"""자모 나누기와 용언 활용."""

BASE, LAST = 0xAC00, 0xD7A3

ONSETS = list("ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ")
VOWELS = list("ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ")
CODAS = [""] + list("ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ")

DIGIT_HAS_CODA = {"0": True, "1": True, "2": False, "3": True, "4": False,
                  "5": False, "6": True, "7": True, "8": True, "9": False}


def is_syllable(ch):
    return len(ch) == 1 and BASE <= ord(ch) <= LAST


def decompose(ch):
    """한 음절을 (초성, 중성, 종성)으로. 한글이 아니면 None."""
    if not is_syllable(ch):
        return None
    code = ord(ch) - BASE
    return ONSETS[code // 588], VOWELS[(code % 588) // 28], CODAS[code % 28]


def compose(onset, vowel, coda=""):
    return chr(BASE + ONSETS.index(onset) * 588 + VOWELS.index(vowel) * 28 + CODAS.index(coda))


def coda_of(ch):
    parts = decompose(ch)
    return parts[2] if parts else None


def has_coda(word):
    """낱말이 받침으로 끝나는가. 조사의 꼴을 고른다. 숫자는 읽는 소리를 따른다."""
    if not word:
        return False
    parts = decompose(word[-1])
    if parts:
        return parts[2] != ""
    return DIGIT_HAS_CODA.get(word[-1], False)


def add_coda(ch, coda):
    """받침 없는 음절에 받침을 붙인다: 하 + ㄴ -> 한."""
    onset, vowel, existing = decompose(ch)
    assert existing == "", f"{ch} already has a coda"
    return compose(onset, vowel, coda)


def allomorph(word, role):
    """낱말의 끝에 맞는 조사의 꼴. '로/으로' 만은 ㄹ 받침도 '로'를 쓴다."""
    table = {"topic": ("은", "는"), "subject": ("이", "가"), "object": ("을", "를"),
             "instrument": ("으로", "로"), "conj": ("과", "와")}
    with_coda, without = table[role]
    if role == "instrument" and word and coda_of(word[-1]) == "ㄹ":
        return without
    return with_coda if has_coda(word) else without


ENDINGS = ("final", "adnominal_past", "adnominal_pres", "conditional",
           "conjunctive", "alternative", "interrogative", "nominal", "auxiliary",
           "negative")


def conjugate(stem, pos, ending):
    """어간에 어미를 붙인다. 사용자 동사는 모두 '명사 + 하다' 라서 규칙적이고,
    불규칙한 것은 내장뿐이라 words.py 의 표가 따로 덮어쓴다.

    pos: "verb" (동사) 또는 "descriptive" (형용사·이다)
    """
    last = stem[-1]
    open_syllable = coda_of(last) == ""

    if ending == "final":
        if pos == "descriptive":
            return stem + "다"
        return stem[:-1] + add_coda(last, "ㄴ") + "다" if open_syllable else stem + "는다"

    if ending == "adnominal_past":
        return stem[:-1] + add_coda(last, "ㄴ") if open_syllable else stem + "은"

    if ending == "adnominal_pres":
        if pos == "descriptive":
            return conjugate(stem, pos, "adnominal_past")
        return stem + "는"

    if ending == "conditional":
        return stem + ("면" if open_syllable else "으면")

    if ending == "conjunctive":
        return stem + "고"

    if ending == "alternative":
        return stem + "거나"

    if ending == "interrogative":
        if pos == "descriptive":
            return conjugate(stem, pos, "adnominal_past") + "지"
        return stem + "는지"

    if ending == "nominal":
        return stem + "기"

    if ending == "negative":
        return stem + "지"

    if ending == "auxiliary":
        if last == "하":
            return stem[:-1] + "해"
        onset, vowel, coda = decompose(last)
        if coda == "":
            contracted = {"ㅗ": "ㅘ", "ㅜ": "ㅝ", "ㅡ": "ㅓ", "ㅣ": "ㅕ"}
            if vowel in ("ㅏ", "ㅓ", "ㅐ", "ㅔ"):
                return stem
            if vowel in contracted:
                return stem[:-1] + compose(onset, contracted[vowel])
            return stem + "어"
        return stem + ("아" if vowel in ("ㅏ", "ㅗ") else "어")

    raise ValueError(f"unknown ending: {ending}")
