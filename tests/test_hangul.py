import unittest

from saerom.hangul import allomorph, conjugate, decompose, has_coda


class Jamo(unittest.TestCase):
    def test_decompose(self):
        self.assertEqual(decompose("한"), ("ㅎ", "ㅏ", "ㄴ"))
        self.assertEqual(decompose("하"), ("ㅎ", "ㅏ", ""))
        self.assertIsNone(decompose("a"))

    def test_has_coda(self):
        self.assertTrue(has_coda("목록"))
        self.assertFalse(has_coda("숫자"))
        self.assertTrue(has_coda("1"))
        self.assertFalse(has_coda("2"))


class Allomorph(unittest.TestCase):
    def test_pairs(self):
        self.assertEqual(allomorph("목록", "object"), "을")
        self.assertEqual(allomorph("숫자", "object"), "를")
        self.assertEqual(allomorph("목록", "topic"), "은")
        self.assertEqual(allomorph("숫자", "subject"), "가")
        self.assertEqual(allomorph("목록", "conj"), "과")

    def test_instrument_riul(self):
        """ㄹ 받침은 '으로'가 아니라 '로'를 쓴다."""
        self.assertEqual(allomorph("파일", "instrument"), "로")
        self.assertEqual(allomorph("서울", "instrument"), "로")
        self.assertEqual(allomorph("목록", "instrument"), "으로")
        self.assertEqual(allomorph("수학", "instrument"), "으로")


class Conjugate(unittest.TestCase):
    CASES = [
        ("하", "verb", "final", "한다"),
        ("주", "verb", "final", "준다"),
        ("읽", "verb", "final", "읽는다"),
        ("크", "descriptive", "final", "크다"),
        ("하", "verb", "adnominal_past", "한"),
        ("빼", "verb", "adnominal_past", "뺀"),
        ("읽", "verb", "adnominal_past", "읽은"),
        ("작", "descriptive", "adnominal_past", "작은"),
        ("계산하", "verb", "adnominal_pres", "계산하는"),
        ("작", "descriptive", "conditional", "작으면"),
        ("하", "verb", "conditional", "하면"),
        ("크", "descriptive", "interrogative", "큰지"),
        ("나누어떨어지", "verb", "interrogative", "나누어떨어지는지"),
        ("하", "verb", "auxiliary", "해"),
        ("열", "verb", "auxiliary", "열어"),
        ("크", "descriptive", "negative", "크지"),
    ]

    def test_all(self):
        for stem, pos, ending, wanted in self.CASES:
            with self.subTest(stem=stem, ending=ending):
                self.assertEqual(conjugate(stem, pos, ending), wanted)

    def test_no_nominal_ending(self):
        """'~기' 는 어미가 아니라 이름이다."""
        from saerom.hangul import ENDINGS
        self.assertNotIn("nominal", ENDINGS)

    RIUL = [
        ("만들", "verb", "final", "만든다"),
        ("만들", "verb", "adnominal_past", "만든"),
        ("만들", "verb", "adnominal_pres", "만드는"),
        ("만들", "verb", "interrogative", "만드는지"),
        ("만들", "verb", "conditional", "만들면"),
        ("만들", "verb", "conjunctive", "만들고"),
        ("만들", "verb", "alternative", "만들거나"),
        ("만들", "verb", "negative", "만들지"),
        ("만들", "verb", "auxiliary", "만들어"),
        ("열", "verb", "final", "연다"),
        ("열", "verb", "adnominal_pres", "여는"),
        ("살", "verb", "final", "산다"),
        ("살", "verb", "auxiliary", "살아"),
        ("길", "descriptive", "final", "길다"),
        ("길", "descriptive", "adnominal_past", "긴"),
        ("길", "descriptive", "conditional", "길면"),
    ]

    def test_riul_drops_before_nieun(self):
        """ㄹ 받침은 ㄴ·는 앞에서 빠진다. 조건은 '으' 없이 붙는다."""
        for stem, pos, ending, wanted in self.RIUL:
            with self.subTest(stem=stem, ending=ending):
                self.assertEqual(conjugate(stem, pos, ending), wanted)


if __name__ == "__main__":
    unittest.main()
