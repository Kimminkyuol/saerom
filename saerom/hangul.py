"""Hangul jamo decomposition and verb conjugation."""

BASE, LAST = 0xAC00, 0xD7A3

ONSETS = list("ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ")
VOWELS = list("ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ")
CODAS = [""] + list("ㄱㄲㄳㄴㄵㄶㄷㄹㄺㄻㄼㄽㄾㄿㅀㅁㅂㅄㅅㅆㅇㅈㅊㅋㅌㅍㅎ")

# Whether the Korean reading of each digit ends in a consonant.
# Used to pick the right particle allomorph after a number.
DIGIT_HAS_CODA = {"0": True, "1": True, "2": False, "3": True, "4": False,
                  "5": False, "6": True, "7": True, "8": True, "9": False}


def is_syllable(ch):
    return len(ch) == 1 and BASE <= ord(ch) <= LAST


def decompose(ch):
    """Split one syllable into (onset, vowel, coda). None if not Hangul."""
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
    """Does the word end in a consonant? Decides particle allomorphs."""
    if not word:
        return False
    parts = decompose(word[-1])
    if parts:
        return parts[2] != ""
    return DIGIT_HAS_CODA.get(word[-1], False)


def add_coda(ch, coda):
    """Attach a coda to a codaless syllable: 하 + ㄴ -> 한."""
    onset, vowel, existing = decompose(ch)
    assert existing == "", f"{ch} already has a coda"
    return compose(onset, vowel, coda)


def allomorph(word, role):
    """Pick the particle spelling that matches the word's ending."""
    table = {"topic": ("은", "는"), "subject": ("이", "가"), "object": ("을", "를"),
             "instrument": ("으로", "로"), "conj": ("과", "와")}
    with_coda, without = table[role]
    # 로/으로 is the odd one out: a ㄹ coda takes 로, like a bare vowel does.
    if role == "instrument" and word and coda_of(word[-1]) == "ㄹ":
        return without
    return with_coda if has_coda(word) else without


# --- Conjugation ---------------------------------------------------------
#
# User-defined verbs must be "noun + 하다", so their stem always ends in 하
# and conjugation is fully regular. Only built-in verbs need irregular forms,
# and those live in an explicit override table in words.py.

ENDINGS = ("final", "adnominal_past", "adnominal_pres", "conditional",
           "conjunctive", "alternative", "interrogative", "nominal", "auxiliary",
           "negative")


def conjugate(stem, pos, ending):
    """Attach an ending to a stem.

    pos: "verb" (action) or "descriptive" (adjective / copula-like)
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

    if ending == "negative":       # 크지 않다,  계산하지 않다
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
