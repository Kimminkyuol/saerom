import unittest

from saerom.errors import SaeromError
from saerom.lexer import tokenize
from saerom.words import BUILTINS


def kinds(source, stems=frozenset()):
    known = None if not stems else frozenset()
    return [(t.kind, t.value) for t in tokenize(source, known, stems)
            if t.kind not in ("newline", "indent", "dedent", "eof")]


class Splitting(unittest.TestCase):
    def test_particle_is_split_off(self):
        self.assertEqual(kinds("반복횟수는 0이다."),
                         [("name", "반복횟수"), ("particle", "는"),
                          ("number", 0), ("copula", "이다"), ("symbol", ".")])

    def test_declared_name_is_not_split(self):
        """'나이' 는 '나' + '이' 로 갈라지지 않는다."""
        self.assertEqual(kinds("나이는 3이다.\n나이를 출력한다."),
                         [("name", "나이"), ("particle", "는"),
                          ("number", 3), ("copula", "이다"), ("symbol", "."),
                          ("name", "나이"), ("particle", "를"),
                          ("verb", "출력하다"), ("symbol", ".")])

    def test_only_one_case_particle(self):
        self.assertEqual(kinds("20보다"), [("number", 20), ("particle", "보다")])

    def test_range_particle_takes_one_more(self):
        self.assertEqual(kinds("100까지의"), [("number", 100), ("particle", "까지")])

    def test_declared_name_wins_over_the_longer_copula(self):
        """'나이라는' 은 '나' + '이라는' 이 아니다. '나이' 가 이미 이름이라서다."""
        self.assertEqual(kinds("나이는 3이다.\n나이라는 오류를 낸다."),
                         [("name", "나이"), ("particle", "는"),
                          ("number", 3), ("copula", "이다"), ("symbol", "."),
                          ("name", "나이"), ("copula", "이다"),
                          ("keyword", "오류"), ("particle", "를"),
                          ("verb", "내다"), ("symbol", ".")])

    def test_the_longer_copula_wins_without_a_name(self):
        """아는 이름이 없으면 긴 것부터 뗀다."""
        self.assertEqual(kinds("나이라는 오류를 낸다.")[:2],
                         [("name", "나"), ("copula", "이다")])

    def test_copula_is_not_split_twice(self):
        """'성인인' 은 성 + 인 + 인 이 아니다."""
        self.assertEqual(kinds("성인인"), [("name", "성인"), ("copula", "이다")])


class Verbs(unittest.TestCase):
    def test_unseen_hada_verb(self):
        """처음 보는 동사도 꼴만으로 알아본다."""
        self.assertEqual(kinds("원넓이계산한다"), [("verb", "원넓이계산하다")])
        self.assertEqual(kinds("원넓이계산하는"), [("verb", "원넓이계산하다")])

    def test_passive(self):
        token = tokenize("정렬된")[0]
        self.assertEqual((token.value, token.extra[0]), ("정렬되다", "passive"))

    def test_negation(self):
        self.assertEqual(kinds("크지 않으면"), [("verb", "크다"), ("verb", "않다")])

    def test_riul_builtin_comes_from_the_rule(self):
        """'열다'의 ㄹ탈락은 규칙이라 words.py 에 표가 없다."""
        self.assertEqual(BUILTINS["열다"], ("열", "verb", {}))
        for text in ("연다", "연", "여는", "여는지", "열면", "열고"):
            with self.subTest(text=text):
                self.assertEqual(kinds(text), [("verb", "열다")])

    def test_stem_forms(self):
        """어간을 알면 그 활용형이 동사가 된다."""
        for text in ("뒤집는다", "뒤집은", "뒤집는", "뒤집으면", "뒤집는지"):
            with self.subTest(text=text):
                self.assertEqual(kinds(text, {"뒤집"}), [("verb", "뒤집다")])

    def test_definition_head_is_one_name(self):
        """정의 머리의 사전형은 이름 하나로 나온다."""
        for source, head in (("글을 뒤집다라는 것은:", "뒤집다"),
                             ("글을 만들다라는 것은:", "만들다"),
                             ("수를 두배하다라는 것은:", "두배하다"),
                             ("돈이 저축되다라는 것은:", "저축되다"),
                             ("수가 짝수이다라는 것은:", "짝수이다"),
                             ("수들의 평균이라는 것은:", "평균")):
            with self.subTest(source=source):
                self.assertEqual(kinds(source)[2:4],
                                 [("name", head), ("copula", "이다")])

    def test_declared_stem_comes_from_the_head(self):
        """머리가 사전형이라 '다'를 떼면 어간이다. 그래서 부를 때 동사가 된다."""
        source = ('글을 만들다라는 것은:\n    글을 돌려준다.\n'
                  '"가"를 만든다.\n')
        self.assertIn(("verb", "만들다"), kinds(source))

    def test_stem_is_a_name_without_the_prescan(self):
        """어간을 모르면 '뒤집는'은 이름과 조사로 갈라진다."""
        self.assertEqual(kinds("뒤집는"), [("name", "뒤집"), ("particle", "는")])


class Spans(unittest.TestCase):
    def test_name_and_particle_have_their_own_span(self):
        name, particle = tokenize("반복횟수는")[:2]
        self.assertEqual((name.col, name.end), (0, 4))
        self.assertEqual((particle.col, particle.end), (4, 5))


class Strings(unittest.TestCase):
    def test_plain(self):
        self.assertEqual(kinds('"안녕"'), [("string", "안녕")])

    def test_escapes(self):
        self.assertEqual(kinds(r'"줄\n탭\t따옴\"중괄호\{"'),
                         [("string", '줄\n탭\t따옴"중괄호{')])

    def test_interpolation(self):
        token = tokenize('"안녕 {이름}님"')[0]
        self.assertEqual(token.kind, "template")
        self.assertEqual([(k, t) for k, t, _, _ in token.value],
                         [("text", "안녕 "), ("expr", "이름"), ("text", "님")])

    def test_hash_inside_string_is_not_a_comment(self):
        self.assertEqual(kinds('"# 우물정"'), [("string", "# 우물정"), ])


class Errors(unittest.TestCase):
    def test_unclosed_quote(self):
        with self.assertRaises(SaeromError) as caught:
            tokenize('"안녕')
        self.assertEqual(caught.exception.kind, "어휘 오류")

    def test_bad_indent(self):
        with self.assertRaises(SaeromError):
            tokenize("만약 참이면:\n    참\n  참\n")


if __name__ == "__main__":
    unittest.main()
