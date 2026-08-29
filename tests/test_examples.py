"""Every example must run, stay in canonical form, and print what it says."""
import io
import pathlib
import re
import sys
import unittest

from saerom import run_source
from saerom.formatter import format_source

EXAMPLES = sorted((pathlib.Path(__file__).resolve().parents[1] / "examples").glob("*.sr"))

# 넣는 값에 따라 출력이 달라지는 예시
NEEDS_INPUT = {"14-입력.sr"}


def run_example(path):
    stdin, out = sys.stdin, io.StringIO()
    sys.stdin = io.StringIO("")            # 입력 예시가 멈추지 않도록
    try:
        run_source(path.read_text(encoding="utf-8"), out=out, path=str(path))
    finally:
        sys.stdin = stdin
    return out.getvalue()


def flatten(text):
    """빈 칸의 갯수와 탭은 견주지 않는다."""
    return " ".join(text.split())


def annotations(text):
    """'# → ' 뒤에 적어 둔 출력."""
    return [flatten(found.group(1)) for found in
            re.finditer(r"#\s*→\s?(.*)$", text, re.MULTILINE)]


class Examples(unittest.TestCase):
    def test_there_are_examples(self):
        self.assertGreater(len(EXAMPLES), 0)

    def test_each_one_runs(self):
        for path in EXAMPLES:
            with self.subTest(example=path.name):
                self.assertTrue(run_example(path))

    def test_each_one_prints_what_it_says(self):
        """예시에 달아 둔 '# →' 주석이 실제 출력에 차례대로 나와야 한다."""
        for path in EXAMPLES:
            if path.name in NEEDS_INPUT:
                continue
            with self.subTest(example=path.name):
                wanted = annotations(path.read_text(encoding="utf-8"))
                self.assertTrue(wanted, "출력 주석이 없음")
                printed = [flatten(line) for line in run_example(path).split("\n")]
                left = list(wanted)
                for line in printed:
                    if left and left[0] == line:
                        left.pop(0)
                self.assertEqual(left, [], f"출력에 없는 주석: {left[:1]}")

    def test_each_one_is_formatted(self):
        for path in EXAMPLES:
            with self.subTest(example=path.name):
                source = path.read_text(encoding="utf-8")
                self.assertEqual(format_source(source), source)


if __name__ == "__main__":
    unittest.main()
