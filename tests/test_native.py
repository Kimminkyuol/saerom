"""파이썬으로 적은 모듈과 술어의 반환값."""
import os
import tempfile
import unittest

from saerom.lsp.analysis import Analysis
from saerom.parser import native
from tests.support import failure, run

MODULE = '''
from saerom.extension import fail, noun, predicate, verb

VALUES = {"하루초": 86400}


@verb("두배하다", "를")
def twice(number):
    return number * 2


@verb("더하기하다", "에", "를")
def add(left, right):
    return left + right


@verb("나누기하다", "를", "로")
def divide(left, right):
    return left / right


@verb("확인하다", "를")
def check(number):
    if number < 0:
        fail("음수임")
    return number


@verb("두배되다", "가")
def doubled(number):
    return number * 2


@predicate("윤년이다", "가")
def is_leap(year):
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


@predicate("이상한것이다", "가")
def strange(value):
    return value + 1


@noun("절반")
def half(number):
    return number / 2
'''


class PythonModule(unittest.TestCase):
    """`<이름>.py` 는 `<이름>.sr` 와 같은 자리에서 같은 꼴로 쓰인다."""

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.write("도구.py", MODULE)
        native.LOADED.clear()

    def tearDown(self):
        self.folder.cleanup()
        native.LOADED.clear()

    def write(self, name, text):
        path = os.path.join(self.folder.name, name)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    def run_source(self, source):
        return run(source, path=self.write("주.sr", source))

    def fails(self, source):
        return failure(source, path=self.write("주.sr", source))

    def test_import_whole_module(self):
        self.assertEqual(
            self.run_source("도구를 가져온다.\n"
                            '"{3을 도구의 두배한 값} {도구의 하루초}"를 출력한다.'),
            "6 86400")

    def test_import_names(self):
        self.assertEqual(
            self.run_source("도구에서 두배하다를 가져온다.\n"
                            '"{3을 두배한 값}"을 출력한다.'), "6")

    def test_particle_order_is_free(self):
        self.assertEqual(
            self.run_source("도구에서 더하기하다를 가져온다.\n"
                            '"{4를 3에 더하기한 값}"을 출력한다.'), "7")

    def test_noun_is_a_field(self):
        self.assertEqual(
            self.run_source("도구에서 절반을 가져온다.\n"
                            '"{9의 절반}"을 출력한다.'), "4.5")

    def test_noun_takes_the_owner_alone(self):
        self.write("틀림.py", "from saerom.extension import noun\n\n"
                              '@noun("몫")\n'
                              "def share(left, right):\n    return left / right\n")
        self.assertIn("매개변수", self.fails("틀림을 가져온다.").message)

    def test_predicate_filters(self):
        self.assertEqual(
            self.run_source("도구에서 윤년이다를 가져온다.\n"
                            "해들은 [2023, 2024, 2000, 2100]이다.\n"
                            '"{윤년인 해들}"을 출력한다.'), "[2024, 2000]")

    def test_fail_is_caught(self):
        self.assertEqual(
            self.run_source("도구에서 확인하다를 가져온다.\n"
                            "해 본다:\n    -1을 확인한다.\n까닭으로 실패하면:\n"
                            '    "{까닭}"을 출력한다.'), "음수임")

    def test_python_error_becomes_value_error(self):
        error = self.fails("도구에서 나누기하다를 가져온다.\n"
                           '"{"가"를 2로 나누기한 값}"을 출력한다.')
        self.assertEqual(error.kind, "값 오류")
        self.assertIn("나누기하다", error.message)

    def test_zero_division(self):
        self.assertEqual(
            self.fails("도구에서 나누기하다를 가져온다.\n"
                       '"{3을 0으로 나누기한 값}"을 출력한다.').kind, "산술 오류")

    def test_native_predicate_must_answer_yes_or_no(self):
        error = self.fails("도구에서 이상한것이다를 가져온다.\n"
                           '"{3이 이상한것인지}"를 출력한다.')
        self.assertEqual(error.kind, "값 오류")
        self.assertIn("논리값", error.message)

    def test_call_stack_records_the_verb(self):
        error = self.fails("도구에서 확인하다를 가져온다.\n"
                           "-1을 확인한 값을 출력한다.")
        self.assertEqual([frame.verb for frame in error.frames], ["확인하다"])

    def test_repeated_particle_is_rejected(self):
        self.write("이음.py", "from saerom.extension import verb\n\n"
                              '@verb("이음하다", "를", "를")\n'
                              "def join(first, second):\n"
                              '    return f"{first}-{second}"\n')
        self.assertIn("두 번 있음", self.fails("이음을 가져온다.").message)

    def test_no_particles(self):
        self.write("빈것.py", "from saerom.extension import predicate, verb\n\n"
                              '@verb("지금하다")\n'
                              "def now():\n    return 42\n\n"
                              '@predicate("맑음이다")\n'
                              "def clear():\n    return True\n")
        self.assertEqual(
            self.run_source("빈것에서 지금하다와 맑음이다를 가져온다.\n"
                            '"{지금한 값}"을 출력한다.\n'
                            '만약 맑음이면:\n    "맑음"을 출력한다.'), "42맑음")

    def test_sr_wins_over_py(self):
        self.write("겹침.py", "from saerom.extension import verb\n\n"
                              '@verb("두배하다", "를")\n'
                              "def twice(number):\n    return number * 2\n")
        self.write("겹침.sr", '수를 두배하다라는 것은:\n    "sr"을 돌려준다.\n')
        self.assertEqual(
            self.run_source("겹침에서 두배하다를 가져온다.\n"
                            '"{3을 두배한 값}"을 출력한다.'), "sr")

    def test_editor_sees_the_verbs(self):
        """편집기는 실행하지 않고도 파이썬 모듈의 동사를 안다."""
        source = ("도구에서 두배하다와 윤년이다를 가져온다.\n"
                  '"{3을 두배한 값}"을 출력한다.\n')
        path = self.write("주.sr", source)
        analysis = Analysis("file://" + path, source, path)
        self.assertIsNone(analysis.error)
        self.assertIn("두배하다", analysis.verbs)
        self.assertIn("윤년이다", analysis.verbs)

    def test_passive_verb(self):
        self.assertEqual(
            self.run_source("도구에서 두배되다를 가져온다.\n"
                            "수는 3이다.\n"
                            '"{두배된 수}"를 출력한다.'), "6")

    def test_verb_name_must_end_in_hada(self):
        self.write("틀림.py", "from saerom.extension import verb\n\n"
                              '@verb("더하기", "에", "를")\n'
                              "def add(left, right):\n    return left + right\n")
        self.assertIn("'하다'나 '되다'", self.fails("틀림을 가져온다.").message)

    def test_predicate_name_must_end_in_ida(self):
        self.write("틀림.py", "from saerom.extension import predicate\n\n"
                              '@predicate("음수", "가")\n'
                              "def negative(number):\n    return number < 0\n")
        self.assertIn("'이다'", self.fails("틀림을 가져온다.").message)

    def test_particle_must_be_a_particle(self):
        self.write("틀림.py", "from saerom.extension import verb\n\n"
                              '@verb("두배하다", "에게서")\n'
                              "def twice(number):\n    return number * 2\n")
        self.assertIn("조사가 아닌", self.fails("틀림을 가져온다.").message)


class ChangedOnDisk(unittest.TestCase):
    """모듈 파일이 바뀌면 다시 읽는다."""

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.folder.cleanup()

    def write(self, name, text):
        path = os.path.join(self.folder.name, name)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    def go(self, source):
        return run(source, path=self.write("주.sr", source))

    def test_saerom_module_is_reread(self):
        source = "도구에서 두배하다를 가져온다.\n1을 두배한 값을 출력한다."
        self.write("도구.sr", '수를 두배하다라는 것은:\n    2를 돌려준다.\n')
        self.assertEqual(self.go(source), "2")
        self.write("도구.sr", '수를 두배하다라는 것은:\n    22를 돌려준다.\n')
        self.assertEqual(self.go(source), "22")

    def test_python_module_is_reread(self):
        source = "파이에서 세배하다를 가져온다.\n1을 세배한 값을 출력한다."
        self.write("파이.py", "from saerom.extension import verb\n\n"
                              '@verb("세배하다", "를")\n'
                              "def triple(number):\n    return 3\n")
        self.assertEqual(self.go(source), "3")
        self.write("파이.py", "from saerom.extension import verb\n\n"
                              '@verb("세배하다", "를")\n'
                              "def triple(number):\n    return 33\n")
        self.assertEqual(self.go(source), "33")


class PredicateResult(unittest.TestCase):
    """술어는 참이나 거짓만 낸다."""

    def test_non_boolean_is_rejected(self):
        error = failure("수가 이상한것이다라는 것은:\n    수에 1을 더한 값을 돌려준다.\n"
                        "3이 이상한것인지를 출력한다.")
        self.assertEqual(error.kind, "값 오류")
        self.assertIn("논리값", error.message)

    def test_missing_return_is_rejected(self):
        error = failure("수가 큰수이다라는 것은:\n    만약 수가 100보다 크면:\n"
                        "        참을 돌려준다.\n"
                        "3이 큰수인지를 출력한다.")
        self.assertEqual(error.kind, "값 오류")
        self.assertIn("돌려주지 않음", error.message)

    def test_boolean_passes(self):
        self.assertEqual(
            run("수가 음수이다라는 것은:\n    수가 0보다 작은지를 돌려준다.\n"
                "-1이 음수인지를 출력한다."), "참")

    def test_verbs_may_return_anything(self):
        self.assertEqual(
            run("수를 두배하다라는 것은:\n    수에 수를 더한 값을 돌려준다.\n"
                "3을 두배한 값을 출력한다."), "6")


if __name__ == "__main__":
    unittest.main()
