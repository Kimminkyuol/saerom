import unittest

from tests.support import STDLIB, run
from saerom.errors import SaeromError
from saerom.formatter import format_source


class Particles(unittest.TestCase):
    CASES = [
        ("목록를 정렬한다.\n", "목록을 정렬한다.\n"),
        ("숫자을 출력한다.\n", "숫자를 출력한다.\n"),
        ("반복횟수은 0이다.\n", "반복횟수는 0이다.\n"),
        ("학생는 이름이다.\n", "학생은 이름이다.\n"),
        ("숫자이 크다.\n", "숫자가 크다.\n"),
        ("파일으로 자른다.\n", "파일로 자른다.\n"),
        ("목록로 자른다.\n", "목록으로 자른다.\n"),
        ("목록와 값을 잇는다.\n", "목록과 값을 잇는다.\n"),
        ("숫자과 값을 잇는다.\n", "숫자와 값을 잇는다.\n"),
    ]

    AFTER_A_LITERAL = ['"beer"을 출력한다.\n', '"wall"를 출력한다.\n',
                       "3를 출력한다.\n"]
    STACKED_PARTICLES = ["1부터 100까지의 숫자들마다 반복한다:\n    참\n"]

    def test_corrected(self):
        for source, wanted in self.CASES:
            with self.subTest(source=source):
                self.assertEqual(format_source(source), wanted)

    def test_after_a_literal_is_left_alone(self):
        for source in self.AFTER_A_LITERAL:
            with self.subTest(source=source):
                self.assertEqual(format_source(source), source)

    def test_stacked_particles_are_left_alone(self):
        for source in self.STACKED_PARTICLES:
            with self.subTest(source=source):
                self.assertEqual(format_source(source), source)

    def test_inside_interpolation(self):
        self.assertEqual(
            format_source('목록은 [1]이다.\n"{목록를 정렬한 값}"을 출력한다.\n'),
            '목록은 [1]이다.\n"{목록을 정렬한 값}"을 출력한다.\n')


class Layout(unittest.TestCase):
    CASES = [
        ("만약 참이면:\n  참\n", "만약 참이면:\n    참\n"),
        ("만약 참이면:\n\t참\n", "만약 참이면:\n    참\n"),
        ("만약 참이면:\n      만약 참이면:\n            참\n",
         "만약 참이면:\n    만약 참이면:\n        참\n"),
        ("값들은 [1,2 , 3]이다.\n", "값들은 [1, 2, 3]이다.\n"),
        ("값들은 [ 1, 2 ]이다.\n", "값들은 [1, 2]이다.\n"),
        ("숫자를   출력한다 .\n", "숫자를 출력한다.\n"),
        ("숫자를 출력한다. # 하나\n", "숫자를 출력한다.  # 하나\n"),
        ("숫자를 출력한다.   \n\n\n", "숫자를 출력한다.\n"),
        ("", ""),
    ]

    COMMENTS = [
        ("만약 참이면:\n  참  # 하나\n  거짓\n",
         "만약 참이면:\n    참  # 하나\n    거짓\n"),
        ('"# 우물정"을 출력한다.\n', '"# 우물정"을 출력한다.\n'),
        ("숫자를 출력한다.          # 줄 맞춤\n",
         "숫자를 출력한다.          # 줄 맞춤\n"),
        ("만약 참이면:\n  # 설명\n  참\n", "만약 참이면:\n    # 설명\n    참\n"),
    ]

    def test_comments(self):
        for source, wanted in self.COMMENTS:
            with self.subTest(source=source):
                self.assertEqual(format_source(source), wanted)

    def test_all(self):
        for source, wanted in self.CASES:
            with self.subTest(source=source):
                self.assertEqual(format_source(source), wanted)


class Properties(unittest.TestCase):
    """포매터가 지켜야 하는 두 가지."""

    SOURCES = [path.read_text(encoding="utf-8") for path in sorted(STDLIB.glob("*.sr"))]

    def test_stdlib_is_already_formatted(self):
        for source in self.SOURCES:
            self.assertEqual(format_source(source), source)

    def test_idempotent(self):
        messy = ("반복횟수은 0이다.\n"
                 "목록를 [ 3,1 , 2 ]로 바꾼다.\n"
                 "만약 반복횟수이 0이면:\n"
                 "  파일으로 자른다. # 주석\n"
                 "\t\"{목록를 정렬한 값}\"을 출력한다.\n")
        once = format_source(messy)
        self.assertEqual(format_source(once), once)

    def test_behaviour_is_preserved(self):
        messy = ('수들은 [ 3,1 , 2 ]이다.\n'
                 '정렬된 수들를 출력한다.\n'
                 '만약 수들의 개수이 3이면:\n'
                 '  "셋"를 출력한다.\n')
        self.assertEqual(run(messy), run(format_source(messy)))


class Failure(unittest.TestCase):
    def test_broken_source_raises(self):
        with self.assertRaises(SaeromError):
            format_source('"닫히지 않은 문자열\n')


if __name__ == "__main__":
    unittest.main()
