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
        self.assertTrue(has_coda("1"))     # 일
        self.assertFalse(has_coda("2"))    # 이


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


if __name__ == "__main__":
    unittest.main()
