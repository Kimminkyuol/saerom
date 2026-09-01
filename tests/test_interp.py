import os
import tempfile
import unittest

from tests.support import failure, run


class Basics(unittest.TestCase):
    def test_declare_and_print(self):
        self.assertEqual(run('이름은 "새롬"이다.\n이름을 출력한다.'), "새롬")

    def test_reassign(self):
        self.assertEqual(run("수는 1이다.\n수는 2이다.\n수를 출력한다."), "2")

    def test_arithmetic(self):
        cases = [
            ("3에 4를 더한 값", "7"),
            ("10에서 4를 뺀 값", "6"),
            ("3에 4를 곱한 값", "12"),
            ("10을 4로 나눈 값", "2.5"),
            ("10을 4로 나눈 나머지", "2"),
        ]
        for expression, wanted in cases:
            with self.subTest(expression=expression):
                self.assertEqual(run(f"{expression}을 출력한다."), wanted)

    def test_interpolation(self):
        self.assertEqual(
            run('이름은 "새롬"이다.\n"안녕, {이름}({3에 4를 더한 값})"을 출력한다.'),
            "안녕, 새롬(7)")

    def test_chained_verbs(self):
        self.assertEqual(run('"가"를 출력하고 "나"를 출력한다.'), "가나")

    def test_list_from_conjunction(self):
        self.assertEqual(run('"가"와 "나"와 "다"를 이은 값을 출력한다.'), "가나다")


class Control(unittest.TestCase):
    def test_if_chain(self):
        source = ("수는 {}이다.\n"
                  "만약 수가 10보다 크면:\n    \"큼\"을 출력한다.\n"
                  "아니고 만약 수가 10이면:\n    \"같음\"을 출력한다.\n"
                  "아니면:\n    \"작음\"을 출력한다.\n")
        self.assertEqual(run(source.format(20)), "큼")
        self.assertEqual(run(source.format(10)), "같음")
        self.assertEqual(run(source.format(1)), "작음")

    def test_and_or_not(self):
        self.assertEqual(
            run("만약 1이 0보다 크고 2가 3보다 작으면:\n    \"참\"을 출력한다."), "참")
        self.assertEqual(
            run("만약 1이 5보다 크거나 2가 3보다 작으면:\n    \"참\"을 출력한다."), "참")
        self.assertEqual(
            run("만약 1이 5보다 크지 않으면:\n    \"참\"을 출력한다."), "참")

    def test_not_equal(self):
        """'X가 Y가 아니면' — 이중주격. 뒤의 '가'가 보어다."""
        source = '수는 {}이다.\n만약 수가 2가 아니면:\n    "다름"을 출력한다.'
        self.assertEqual(run(source.format(1)), "다름")
        self.assertEqual(run(source.format(2)), "")

    def test_predicate_negated(self):
        self.assertEqual(
            run("수가 음수이다라는 것은:\n    수가 0보다 작은지를 돌려준다.\n"
                "만약 1이 음수가 아니면:\n    \"양수\"를 출력한다."), "양수")

    def test_shared_subject(self):
        """이어진 술어는 주어만 물려받는다."""
        self.assertEqual(
            run("만약 1이 2보다 작거나 1과 같으면:\n    \"참\"을 출력한다."), "참")

    def test_range_loop(self):
        self.assertEqual(run("1부터 5까지의 수마다 반복한다:\n    수를 출력한다."), "12345")

    def test_range_counts_down(self):
        self.assertEqual(run("3부터 1까지의 수마다 반복한다:\n    수를 출력한다."), "321")

    def test_range_step(self):
        self.assertEqual(
            run("10부터 0까지 5 간격의 수마다 반복한다:\n    수를 출력한다."), "1050")
        self.assertEqual(
            run("0부터 10까지 5 간격의 수마다 반복한다:\n    수를 출력한다."), "0510")

    def test_while(self):
        self.assertEqual(
            run("수는 3이다.\n수가 0보다 큰 동안 반복한다:\n"
                "    수를 출력한다.\n    수는 수에서 1을 뺀 값이다."), "321")

    def test_break_and_continue(self):
        self.assertEqual(
            run("1부터 9까지의 수마다 반복한다:\n"
                "    만약 수가 3보다 크면:\n        빠져나간다.\n"
                "    수를 출력한다."), "123")
        self.assertEqual(
            run("1부터 5까지의 수마다 반복한다:\n"
                "    만약 수를 2로 나눈 나머지가 0이면:\n        넘어간다.\n"
                "    수를 출력한다."), "135")

    def test_bare_value_is_a_no_op(self):
        self.assertEqual(run("만약 참이면:\n    참\n"), "")


class Definitions(unittest.TestCase):
    def test_verb(self):
        self.assertEqual(
            run("반지름으로 원넓이계산하다라는 것은:\n"
                "    반지름에 반지름을 곱한 값을 돌려준다.\n"
                "3으로 원넓이계산한 값을 출력한다."), "9")

    def test_free_argument_order(self):
        source = ("사람에게 말을 전하다라는 것은:\n    \"{말}/{사람}\"을 출력한다.\n")
        self.assertEqual(run(source + '"가"에게 "나"를 전한다.'), "나/가")
        self.assertEqual(run(source + '"나"를 "가"에게 전한다.'), "나/가")

    def test_recursion(self):
        self.assertEqual(
            run("수를 계승계산하다라는 것은:\n"
                "    만약 수가 1보다 크지 않으면:\n        1을 돌려준다.\n"
                "    앞값은 수에서 1을 뺀 값을 계승계산한 값이다.\n"
                "    수에 앞값을 곱한 값을 돌려준다.\n"
                "5를 계승계산한 값을 출력한다."), "120")

    def test_predicate_in_two_places(self):
        head = "수가 홀수이다라는 것은:\n    수를 2로 나눈 나머지가 1인지를 돌려준다.\n"
        self.assertEqual(run(head + "만약 7이 홀수이면:\n    \"참\"을 출력한다."), "참")
        self.assertEqual(run(head + "7이 홀수인지를 출력한다."), "참")

    def test_signature_is_the_particle_set(self):
        source = ("값들을 정리하다라는 것은:\n    \"하나\"를 출력한다.\n"
                  "값들을 사이로 정리하다라는 것은:\n    \"둘\"을 출력한다.\n")
        self.assertEqual(run(source + "[1]을 정리한다."), "하나")
        self.assertEqual(run(source + '[1]을 ","로 정리한다.'), "둘")

    def test_distinct_particles_stay_free(self):
        source = "사람에게 말을 전하다라는 것은:\n    \"{말}/{사람}\"을 돌려준다.\n"
        self.assertEqual(run(source + '"나"를 "가"에게 전한 값을 출력한다.'), "나/가")
        self.assertEqual(run(source + '"가"에게 "나"를 전한 값을 출력한다.'), "나/가")

    def test_repeated_particle_is_rejected(self):
        """한 정의에서 같은 조사는 한 번만 쓴다."""
        error = failure('앞을 뒤를 이어붙이하다라는 것은:\n    참을 돌려준다.\n')
        self.assertEqual(error.kind, "구문 오류")
        self.assertIn("두 번 있음", error.message)

    def test_every_head_is_a_dictionary_form(self):
        """다섯 갈래를 모두 '<사전형>라는 것은:' 하나로 적는다."""
        source = ("글을 뒤집다라는 것은:\n    글을 돌려준다.\n"
                  "수로 도시락을 만들다라는 것은:\n    수를 돌려준다.\n"
                  "수를 두배하다라는 것은:\n    수에 수를 더한 값을 돌려준다.\n"
                  "수가 저축되다라는 것은:\n    수에 1을 더한 값을 돌려준다.\n"
                  "수가 짝수이다라는 것은:\n    수를 2로 나눈 나머지가 0인지를 돌려준다.\n"
                  "수들의 크기라는 것은:\n    수들의 개수를 돌려준다.\n")
        self.assertEqual(
            run(source + '"{"가"를 뒤집은 값} {3으로 1을 만든 값} {2를 두배한 값} '
                '{1이 저축된 값} {4가 짝수인지} {[1, 2]의 크기}"을 출력한다.'),
            "가 3 4 2 참 2")

    OLD_HEADS = [
        "글을 뒤집는 것은:\n    글을 돌려준다.\n",
        "수를 두배하는 것은:\n    수를 돌려준다.\n",
        "수가 저축되는 것은:\n    수를 돌려준다.\n",
        "수가 짝수인 것은:\n    참을 돌려준다.\n",
        "수들의 평균은:\n    1을 돌려준다.\n",
    ]

    def test_the_old_head_is_a_syntax_error(self):
        """관형형 머리와 '<소유자>의 <이름>는:' 은 이제 없는 꼴이다."""
        for source in self.OLD_HEADS:
            with self.subTest(source=source):
                error = failure(source)
                self.assertEqual(error.kind, "구문 오류")
                self.assertIn("머리", error.message)

    def test_adnominal_takes_only_its_own_slots(self):
        """'학생들에 줄들을 해석한 값을 더한다' 에서 해석하다는 줄들만 가져간다."""
        self.assertEqual(
            run("줄들을 해석하다라는 것은:\n    줄들에 100을 더한 값을 돌려준다.\n"
                "목록은 []이다.\n"
                "목록에 1을 해석한 값을 더한다.\n"
                "목록을 출력한다."), "[101]")


class Stems(unittest.TestCase):
    """'명사 + 하다' 가 아닌 고유어 어간으로 만든 동사."""

    REVERSE = ("글을 뒤집다라는 것은:\n"
               "    모은것은 \"\"이다.\n"
               "    1부터 글의 글자수까지의 자리마다 반복한다:\n"
               "        뒷자리는 글의 글자수에서 자리를 뺀 값에 1을 더한 값이다.\n"
               "        모은것은 모은것과 글의 뒷자리번째를 이은 값이다.\n"
               "    모은것을 돌려준다.\n")
    COUNT = "수들을 세다라는 것은:\n    수들의 개수를 돌려준다.\n"

    def test_endings(self):
        head = "수를 늘리다라는 것은:\n    수에 1을 더한 값을 돌려준다.\n"
        self.assertEqual(run(head + "3을 늘린 값을 출력한다."), "4")
        self.assertEqual(run(head + '만약 3을 늘린 값이 4와 같으면:\n    "예"를 출력한다.'),
                         "예")
        self.assertEqual(run(head + '"{3을 늘리는 값}"을 출력한다.'), "4")
        self.assertEqual(run("수를 늘리다라는 것은:\n    수를 출력한다.\n"
                             "1을 늘리고 2를 늘린다."), "12")

    def test_interrogative(self):
        self.assertEqual(
            run("수가 넘치다라는 것은:\n    수가 9보다 큰지를 돌려준다.\n"
                '"{10이 넘치는지}"를 출력한다.'), "참")

    def test_vowel_stem(self):
        self.assertEqual(run(self.COUNT + "[1, 2, 3]을 센 값을 출력한다."), "3")

    def test_stem_with_a_coda(self):
        self.assertEqual(
            run(self.REVERSE + '"가나다"를 뒤집은 값을 출력한다.'), "다나가")

    def test_declared_name_wins(self):
        """'세기' 는 '세다'의 명사형이기도 하지만 선언된 이름이 앞선다."""
        self.assertEqual(
            run(self.COUNT + "세기는 3이다.\n"
                '"{세기} {[1, 2]를 센 값}"을 출력한다.'), "3 2")

    def test_declared_name_wins_over_a_builtin_form(self):
        """'크기' 는 '크다'의 명사형이기도 하지만 선언된 이름이 앞선다."""
        self.assertEqual(run("크기는 3이다.\n\"{크기}\"를 출력한다."), "3")
        self.assertEqual(
            run("갑은 {크기: 3}이다.\n\"{갑의 크기}\"를 출력한다."), "3")
        self.assertEqual(
            run("갑은 {나누기: 3}이다.\n"
                "상자의 두배라는 것은:\n    상자의 나누기에 2를 곱한 값을 돌려준다.\n"
                "\"{갑의 두배}\"를 출력한다."), "6")

    RIUL = ("재료로 도시락을 만들다라는 것은:\n"
            "    \"{재료} {도시락}\"을 돌려준다.\n")

    def test_riul_stem(self):
        """ㄹ 어간은 ㄴ·는 앞에서 ㄹ이 빠진다."""
        self.assertEqual(run(self.RIUL + '"김"으로 "밥"을 만든 값을 출력한다.'),
                         "김 밥")
        self.assertEqual(
            run(self.RIUL + '만약 "김"으로 "밥"을 만든 값이 "김 밥"과 같으면:\n'
                '    "예"를 출력한다.'), "예")
        self.assertEqual(run(self.RIUL + '"{"김"으로 "밥"을 만드는 값}"을 출력한다.'),
                         "김 밥")
        self.assertEqual(
            run("수로 만들다라는 것은:\n    수를 출력한다.\n"
                "1로 만들고 2로 만든다."), "12")
        self.assertEqual(
            run("수로 만들다라는 것은:\n    수가 0보다 큰지를 돌려준다.\n"
                '"{1로 만드는지}"를 출력한다.'), "참")
        self.assertEqual(
            run("수로 만들다라는 것은:\n    수를 돌려준다.\n"
                '만약 1로 만들면:\n    "예"를 출력한다.'), "예")

    def test_wrong_particle_names_the_verb(self):
        error = failure(self.COUNT + "[1]에 센다.")
        self.assertEqual(error.kind, "조사 오류")
        self.assertIn("세다", error.message)
        self.assertIn("~를 센다", error.hint)


class StemModules(unittest.TestCase):
    """어간 동사를 가져오려면 그 파일을 가르기 전에 저쪽을 훑어야 한다."""

    TOOL = ("글을 뒤집다라는 것은:\n"
            "    모은것은 \"\"이다.\n"
            "    1부터 글의 글자수까지의 자리마다 반복한다:\n"
            "        뒷자리는 글의 글자수에서 자리를 뺀 값에 1을 더한 값이다.\n"
            "        모은것은 모은것과 글의 뒷자리번째를 이은 값이다.\n"
            "    모은것을 돌려준다.\n")

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.folder.cleanup()

    def write(self, name, text):
        path = os.path.join(self.folder.name, name)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    def run_source(self, source):
        return run(source, path=self.write("주.sr", source))

    def test_imported_stem_verb(self):
        self.write("도구.sr", self.TOOL)
        self.assertEqual(
            self.run_source('도구에서 뒤집다를 가져온다.\n'
                            '"가나다"를 뒤집은 값을 출력한다.'), "다나가")

    def test_imported_stem_verb_through_the_namespace(self):
        self.write("도구.sr", self.TOOL)
        self.assertEqual(
            self.run_source('도구를 가져온다.\n'
                            '"가나다"를 도구의 뒤집은 값을 출력한다.'), "다나가")

    def test_imported_riul_stem_verb(self):
        """ㄹ 어간은 가져온 쪽에서도 ㄹ이 빠진 꼴로 불린다."""
        self.write("도구.sr", "재료로 만들다라는 것은:\n    재료를 돌려준다.\n")
        self.assertEqual(
            self.run_source('도구에서 만들다를 가져온다.\n'
                            '"김"으로 만든 값을 출력한다.'), "김")

    def test_self_import_still_fails(self):
        source = "자기를 가져온다.\n\n" + self.TOOL
        error = failure(source, path=self.write("자기.sr", source))
        self.assertEqual(error.kind, "구문 오류")


class Lists(unittest.TestCase):
    SETUP = "수들은 [3, 8, 15, 4]이다.\n"

    def check(self, expression, wanted):
        self.assertEqual(run(self.SETUP + f"{expression}을 출력한다."), wanted)

    def test_fields(self):
        self.check("수들의 개수", "4")
        self.check("수들의 첫째", "3")
        self.check("수들의 마지막", "4")
        self.check("수들의 2번째", "8")

    def test_ordinals_up_to_ten(self):
        source = "수들은 [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]이다.\n"
        for field, wanted in [("첫째", "1"), ("다섯째", "5"), ("여섯째", "6"),
                              ("아홉째", "9"), ("열째", "10")]:
            with self.subTest(field=field):
                self.assertEqual(run(source + f"수들의 {field}를 출력한다."), wanted)

    def test_field_out_of_range(self):
        for expression in ("[]의 첫째", "[]의 마지막", "수들의 5번째",
                           '""의 첫째', '""의 마지막'):
            with self.subTest(expression=expression):
                error = failure(self.SETUP + f"{expression}을 출력한다.")
                self.assertEqual(error.kind, "값 오류")

    def test_length_is_not_a_field(self):
        self.assertEqual(failure("[1]의 길이를 출력한다.").kind, "이름 오류")
        self.assertEqual(failure('"가"의 개수를 출력한다.').kind, "이름 오류")


class LoopControl(unittest.TestCase):
    """중단문과 계속문은 반복문 안에서만 뜻이 있다."""

    def test_break_and_continue(self):
        self.assertEqual(
            run("1부터 5까지의 수마다 반복한다:\n"
                "    만약 수가 2이면:\n        넘어간다.\n"
                "    만약 수가 4이면:\n        빠져나간다.\n"
                '    "{수}"를 출력한다.'), "13")

    def test_break_outside_a_loop(self):
        self.assertIn("반복문", failure("빠져나간다.").message)

    def test_continue_outside_a_loop(self):
        self.assertIn("반복문", failure("넘어간다.").message)

    def test_break_does_not_cross_a_verb(self):
        error = failure("수를 재주하다라는 것은:\n    빠져나간다.\n"
                        "1부터 1까지의 수마다 반복한다:\n    수를 재주한다.")
        self.assertIn("반복문", error.message)

    def test_break_inside_a_verb_with_its_own_loop(self):
        self.assertEqual(
            run("수를 재주하다라는 것은:\n"
                "    1부터 3까지의 수마다 반복한다:\n"
                "        빠져나간다.\n"
                '    "안"을 출력한다.\n'
                "1부터 2까지의 수마다 반복한다:\n    수를 재주한다."), "안안")


class Counter(unittest.TestCase):
    """차례는 특수 이름이 아니라 세어서 쓴다."""

    def test_counting_over_a_list(self):
        self.assertEqual(
            run('이름들은 ["가", "나"]이다.\n'
                "1부터 이름들의 개수까지의 자리마다 반복한다:\n"
                '    "{자리}:{이름들의 자리번째} "을 출력한다.'), "1:가 2:나 ")

    def test_counting_in_a_while_loop(self):
        self.assertEqual(
            run("자리는 0이다.\n남은것은 2이다.\n남은것이 0보다 큰 동안 반복한다:\n"
                "    자리는 자리에 1을 더한 값이다.\n"
                '    "{자리}"를 출력한다.\n'
                "    남은것은 남은것에서 1을 뺀 값이다."), "12")

    def test_the_old_counter_is_gone(self):
        error = failure("1부터 1까지의 수마다 반복한다:\n    번째를 출력한다.")
        self.assertEqual(error.kind, "이름 오류")


class Predicates(unittest.TestCase):
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
        self.assertIn("돌려주지 않음", error.message)

    def test_verbs_may_return_anything(self):
        self.assertEqual(
            run("수를 두배하다라는 것은:\n    수에 수를 더한 값을 돌려준다.\n"
                "3을 두배한 값을 출력한다."), "6")

    def test_two_slots(self):
        """'A가 B와 <술어>ㄴ지' 의 '와'는 목록을 잇는 조사가 아니다."""
        head = ("왼쪽이 오른쪽과 짝이다라는 것은:\n"
                "    왼쪽이 오른쪽과 같은지를 돌려준다.\n")
        self.assertEqual(run(head + "3이 3과 짝인지를 출력한다."), "참")
        self.assertEqual(run(head + "3이 4와 짝인지를 출력한다."), "거짓")

    def test_conjunction_still_makes_a_list(self):
        self.assertEqual(run("수들은 1과 2와 3이다.\n수들을 출력한다."), "[1, 2, 3]")


class Questions(unittest.TestCase):
    """물음꼴로 부른 것은 참이나 거짓만 낸다."""

    def test_verb_asked_must_answer_yes_or_no(self):
        error = failure("수를 두배하다라는 것은:\n    수에 수를 더한 값을 돌려준다.\n"
                        "2를 두배하는지를 출력한다.")
        self.assertEqual(error.kind, "값 오류")
        self.assertIn("논리값", error.message)

    def test_verb_that_answers_passes(self):
        self.assertEqual(run('"가나"가 "나"를 담는지를 출력한다.'), "참")

    def test_negated_question_passes(self):
        self.assertEqual(run('"가나"가 "다"를 담지 않은지를 출력한다.'), "참")

    def test_negation_does_not_hide_a_non_boolean(self):
        """뒤집기 전에 이미 참이나 거짓이어야 한다."""
        error = failure("수를 두배하다라는 것은:\n    수에 수를 더한 값을 돌려준다.\n"
                        "2를 두배하지 않은지를 출력한다.")
        self.assertEqual(error.kind, "값 오류")
        self.assertIn("논리값", error.message)

    def test_verb_called_for_its_value_may_return_anything(self):
        self.assertEqual(
            run("수를 두배하다라는 것은:\n    수에 수를 더한 값을 돌려준다.\n"
                "2를 두배한 값을 출력한다."), "4")


class NoValue(unittest.TestCase):
    """값을 내지 않는 동사를 값 자리에서 부르면 값 오류다. 파이썬의 None 이 새면 안 된다."""

    QUIET = "수를 조용히하다라는 것은:\n    참\n"

    def check(self, source):
        error = failure(source)
        self.assertEqual(error.kind, "값 오류")
        self.assertIn("돌려주지 않음", error.message)

    def test_plain_call(self):
        self.check(self.QUIET + "값은 1을 조용히한 값이다.\n참")

    def test_printing_gives_no_value(self):
        self.check('값은 "가"를 출력한 값이다.\n참')

    def test_block_name_stays_closed(self):
        """값을 내지 않은 동사는 자원문의 이름을 열지 않는다."""
        self.assertEqual(
            failure(self.QUIET + "1을 조용히해 통으로 둔다:\n    통을 출력한다.").kind,
            "이름 오류")


class Comparatives(unittest.TestCase):
    """이상·이하·초과·미만."""

    def branch(self, test):
        return run(f"수는 10이다.\n만약 {test}:\n    \"참\"을 출력한다.")

    def test_each_word_in_a_condition(self):
        self.assertEqual(self.branch("수가 10 이상이면"), "참")
        self.assertEqual(self.branch("수가 10 이하이면"), "참")
        self.assertEqual(self.branch("수가 10 초과이면"), "")
        self.assertEqual(self.branch("수가 10 미만이면"), "")
        self.assertEqual(self.branch("수가 9 초과이면"), "참")
        self.assertEqual(self.branch("수가 11 미만이면"), "참")

    def test_question(self):
        self.assertEqual(run('"{3이 3 이상인지}"를 출력한다.'), "참")
        self.assertEqual(run('"{3이 3 초과인지}"를 출력한다.'), "거짓")

    def test_negation(self):
        self.assertEqual(self.branch("수가 20 이상이 아니면"), "참")

    def test_joined_conditions_share_the_subject(self):
        self.assertEqual(self.branch("수가 5 이상이고 20 이하이면"), "참")
        self.assertEqual(self.branch("수가 5 이상이고 8 이하이면"), "")
        self.assertEqual(self.branch("수가 100 이상이거나 5 초과이면"), "참")

    def test_a_name_of_that_spelling_still_works(self):
        self.assertEqual(
            run("이상은 10이다.\n수는 10이다.\n"
                '만약 수가 이상이면:\n    "같음"을 출력한다.'), "같음")


class BlockNames(unittest.TestCase):
    """블록이 여는 이름은 그 블록 안에서만 산다."""

    WRITE = '"/tmp/새롬블록.txt"를 기록으로 열어 둔다:\n    "가"를 기록에 쓴다.\n'
    FAIL = '해 본다:\n    "없는파일.txt"를 읽는다.\n까닭으로 실패하면:\n'

    def test_reason_lives_in_the_handler(self):
        self.assertEqual(run(self.FAIL + "    까닭을 출력한다."), "파일없음")

    def test_reason_does_not_leak(self):
        error = failure(self.FAIL + "    참\n까닭을 출력한다.")
        self.assertEqual(error.kind, "이름 오류")

    def test_reason_can_be_kept_by_name(self):
        self.assertEqual(
            run(self.FAIL + "    남긴것은 까닭이다.\n남긴것을 출력한다."), "파일없음")

    def test_the_resource_name_is_required(self):
        error = failure('"/tmp/새롬블록.txt"를 열어 둔다:\n    참')
        self.assertEqual(error.kind, "구문 오류")

    def test_handle_lives_in_the_resource_block(self):
        self.assertEqual(
            run(self.WRITE + '"/tmp/새롬블록.txt"를 읽은 값을 출력한다.'), "가")

    def test_handle_does_not_leak(self):
        error = failure(self.WRITE + "파일을 출력한다.")
        self.assertEqual(error.kind, "이름 오류")

    def test_chosen_handle_name_does_not_leak(self):
        error = failure('"/tmp/새롬블록.txt"를 기록으로 열어 둔다:\n    참\n'
                        "기록을 출력한다.")
        self.assertEqual(error.kind, "이름 오류")


class ChangesAndValues(unittest.TestCase):
    """능동은 그 자리에서 고치고, 값을 내는 자리에서는 원본을 두고 복사한다."""

    def test_append_as_a_statement_changes_the_list(self):
        self.assertEqual(
            run("수들은 [1]이다.\n수들에 2를 더한다.\n수들을 출력한다."), "[1, 2]")

    def test_append_as_a_value_spares_the_list(self):
        self.assertEqual(
            run("원본은 [1, 2]이다.\n새것은 원본에 3을 더한 값이다.\n"
                '"{새것} {원본}"을 출력한다.'), "[1, 2, 3] [1, 2]")


class Dicts(unittest.TestCase):
    """사전. 열쇠는 이름 하나이고, 읽기와 쓰기는 'X의 Y' 로 한다."""

    SETUP = '철수는 {이름: "김철수", 나이: 17}이다.\n'

    def test_literal_and_read(self):
        self.assertEqual(run(self.SETUP + "철수의 이름을 출력한다."), "김철수")

    def test_empty_literal(self):
        self.assertEqual(run("빈것은 {}이다.\n빈것을 출력한다."), "{}")

    def test_shown_like_the_literal(self):
        self.assertEqual(run(self.SETUP + "철수를 출력한다."),
                         "{이름: 김철수, 나이: 17}")

    def test_write_an_existing_key(self):
        self.assertEqual(run(self.SETUP + "철수의 나이는 18이다.\n철수의 나이를 출력한다."),
                         "18")

    def test_write_makes_a_new_key(self):
        self.assertEqual(
            run("빈것은 {}이다.\n빈것의 나이는 3이다.\n빈것을 출력한다."), "{나이: 3}")

    def test_a_value_may_be_any_expression(self):
        self.assertEqual(
            run("수는 2이다.\n갑은 {값: 수에 3을 더한 값, 목록: [1, 2]}이다.\n"
                '"{갑의 값} {갑의 목록의 개수}"를 출력한다.'), "5 2")

    def test_missing_key_is_a_name_error(self):
        error = failure(self.SETUP + "철수의 점수를 출력한다.")
        self.assertEqual(error.kind, "이름 오류")
        self.assertIn("점수", error.message)
        self.assertIn("이름", error.hint)

    def test_a_key_may_be_called_값(self):
        head = "갑은 {값: 3}이다.\n"
        self.assertEqual(run(head + '"{갑의 값}"을 출력한다.'), "3")
        self.assertEqual(run(head + '"{갑의 값에 2를 더한 값}"을 출력한다.'), "5")
        self.assertEqual(
            run(head + "갑의 값은 갑의 값에 1을 더한 값이다.\n"
                '"{갑의 값}"을 출력한다.'), "4")

    def test_nested(self):
        self.assertEqual(
            run('집은 {주소: {도시: "서울"}}이다.\n집의 주소의 도시를 출력한다.'), "서울")

    def test_equal_by_value(self):
        self.assertEqual(
            run("갑은 {수: 1}이다.\n병은 {수: 1}이다.\n갑이 병과 같은지를 출력한다."), "참")
        self.assertEqual(
            run("갑은 {수: 1}이다.\n병은 {수: 2}이다.\n갑이 병과 같은지를 출력한다."), "거짓")

    def test_copy(self):
        self.assertEqual(
            run("내것은 {금액: 100}이다.\n새것은 내것의 복사본이다.\n"
                "새것의 금액은 200이다.\n"
                '"{새것의 금액} {내것의 금액}"을 출력한다.'), "200 100")

    def test_type_field(self):
        self.assertEqual(run("갑은 {수: 1}이다.\n갑의 자료형을 출력한다."), "사전")

    def test_a_nested_target(self):
        self.assertEqual(
            run("갑들은 [{무게: 1}]이다.\n갑들의 첫째의 무게는 9이다.\n"
                "갑들의 첫째의 무게를 출력한다."), "9")

    def test_assigning_to_something_that_is_not_a_dict(self):
        error = failure("목록은 [1]이다.\n목록의 자리는 3이다.\n참")
        self.assertEqual(error.kind, "실행 오류")
        self.assertIn("목록", error.message)

    def test_a_key_is_a_bare_name(self):
        for source in ('갑은 {"이름": 1}이다.\n참', "갑은 {1: 2}이다.\n참"):
            with self.subTest(source=source):
                self.assertEqual(failure(source).kind, "구문 오류")


class Subjects(unittest.TestCase):
    """'이/가' 로도 선언한다."""

    def test_declare_with_a_subject(self):
        self.assertEqual(run("철수가 3이다.\n철수를 출력한다."), "3")

    def test_declare_a_key_with_a_subject(self):
        self.assertEqual(
            run("철수는 {나이: 17}이다.\n철수의 나이가 18이다.\n철수의 나이를 출력한다."),
            "18")

    def test_a_call_is_still_a_call(self):
        self.assertEqual(run('말은 "안녕"이다.\n말이 "안"을 담는지를 출력한다.'), "참")


class PythonValues(unittest.TestCase):
    """파이썬 모듈은 새롬 값만 내놓을 수 있다."""

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.folder.cleanup()

    def write(self, name, text):
        path = os.path.join(self.folder.name, name)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    def fails(self, module, source):
        self.write("짐.py", module)
        return failure(source, path=self.write("주.sr", source))

    def test_a_verb_that_returns_a_set(self):
        error = self.fails('from saerom.extension import verb\n\n'
                           '@verb("모으하다", "를")\n'
                           "def gather(one):\n    return set()\n",
                           "짐에서 모으하다를 가져온다.\n[1]을 모으한 값을 출력한다.")
        self.assertEqual(error.kind, "값 오류")
        self.assertIn("새롬 값이 아닌", error.message)

    def test_a_verb_that_returns_a_dict(self):
        self.write("짐.py", 'from saerom.extension import verb\n\n'
                            '@verb("모으하다", "를")\n'
                            "def gather(one):\n    return {\"수\": one}\n")
        source = "짐에서 모으하다를 가져온다.\n1을 모으한 값을 출력한다."
        self.assertEqual(run(source, path=self.write("주.sr", source)), "{수: 1}")

    def test_values_that_are_not_saerom_values(self):
        error = self.fails('from saerom.extension import verb\n\n'
                           "VALUES = {\"자루\": set()}\n\n"
                           '@verb("모으하다", "를")\n'
                           "def gather(one):\n    return 1\n",
                           "짐을 가져온다.\n짐의 자루를 출력한다.")
        self.assertIn("새롬 값이 아닌", error.message)

    def test_nested_lists_are_fine(self):
        self.write("짐.py", 'from saerom.extension import verb\n\n'
                            '@verb("모으하다", "를")\n'
                            "def gather(one):\n    return [one, [1, True]]\n")
        source = "짐에서 모으하다를 가져온다.\n[9]를 모으한 값을 출력한다."
        self.assertEqual(run(source, path=self.write("주.sr", source)),
                         "[[9], [1, 참]]")


class DerivedFields(unittest.TestCase):
    """계산되는 `X의 Y`."""

    AVERAGE = ("수들의 평균이라는 것은:\n"
               "    모은것은 0이다.\n"
               "    1부터 수들의 개수까지의 자리마다 반복한다:\n"
               "        모은것은 모은것에 수들의 자리번째를 더한 값이다.\n"
               "    모은것을 수들의 개수로 나눈 값을 돌려준다.\n")

    def test_define_and_use(self):
        self.assertEqual(
            run(self.AVERAGE + "점수들은 [80, 90, 100]이다.\n점수들의 평균을 출력한다."),
            "90")

    def test_branching_body(self):
        source = ("수의 절댓값이라는 것은:\n"
                  "    만약 수가 0보다 작으면:\n"
                  "        0에서 수를 뺀 값을 돌려준다.\n"
                  "    수를 돌려준다.\n"
                  '"{-7의 절댓값} {7의 절댓값}"을 출력한다.')
        self.assertEqual(run(source), "7 7")

    def test_body_that_ends_without_a_value(self):
        error = failure("수의 절반이라는 것은:\n    만약 수가 0보다 크면:\n"
                        "        수를 2로 나눈 값을 돌려준다.\n"
                        "0의 절반을 출력한다.")
        self.assertEqual(error.kind, "값 오류")
        self.assertIn("절반", error.message)

    def test_dict_key_comes_first(self):
        source = ("사람의 나이라는 것은:\n    99를 돌려준다.\n"
                  "철수는 {나이: 3}이다.\n"
                  '"{철수의 나이}"를 출력한다.')
        self.assertEqual(run(source), "3")

    def test_builtin_field_comes_first(self):
        source = ("항목들의 개수라는 것은:\n    0을 돌려준다.\n"
                  '"{[1, 2, 3]의 개수}"를 출력한다.')
        self.assertEqual(run(source), "3")

    def test_dict_without_the_key_falls_through(self):
        source = (self.AVERAGE +
                  "사람의 평균점수라는 것은:\n    사람의 점수들의 평균을 돌려준다.\n"
                  "철수는 {점수들: [80, 90, 100]}이다.\n"
                  '"{철수의 평균점수}"를 출력한다.')
        self.assertEqual(run(source), "90")

    def test_owner_is_bound_by_name(self):
        self.assertEqual(
            run("사람의 인사라는 것은:\n"
                '    "안녕, {사람}"을 돌려준다.\n'
                '"{"새롬"의 인사}"를 출력한다.'), "안녕, 새롬")

    def test_from_a_module(self):
        self.assertEqual(
            run("통계에서 평균을 가져온다.\n"
                '"{[1, 2, 3]의 평균}"을 출력한다.'), "2")

    def test_module_namespace_does_not_reach_it(self):
        error = failure("통계를 가져온다.\n[1, 2]의 통계의 평균을 출력한다.")
        self.assertEqual(error.kind, "이름 오류")


class ActiveAndPassive(unittest.TestCase):
    SAVINGS = ("저금통에 돈을 저축하다라는 것은:\n"
               "    저금통의 금액은 저금통의 금액에 돈을 더한 값이다.\n"
               "저금통에 돈이 저축되다라는 것은:\n"
               "    새것은 저금통의 복사본이다.\n"
               "    새것에 돈을 저축한다.\n"
               "    새것을 돌려준다.\n"
               "내것은 {금액: 100}이다.\n")

    def test_active_mutates(self):
        self.assertEqual(
            run("수들은 [1]이다.\n수들에 2를 더한다.\n수들을 출력한다."), "[1, 2]")

    def test_user_passive_returns_what_its_body_gives(self):
        self.assertEqual(
            run(self.SAVINGS + "50이 저축된 내것의 금액을 출력한다.\n"
                "내것의 금액을 출력한다."), "150100")

    def test_user_passive_is_a_verb_of_its_own(self):
        self.assertEqual(
            run(self.SAVINGS + "저금은 50이 저축된 내것이다.\n"
                "저금의 금액을 출력한다."), "150")

    def test_undefined_passive_is_a_name_error(self):
        error = failure(
            "저금통에 돈을 저축하다라는 것은:\n"
            "    저금통의 금액은 저금통의 금액에 돈을 더한 값이다.\n"
            "내것은 {금액: 100}이다.\n"
            "50이 저축된 내것의 금액을 출력한다.")
        self.assertEqual(error.kind, "이름 오류")
        self.assertIn("저축되다", error.message)
        self.assertIn("저축하다", error.hint)

    def test_copy_of_a_list(self):
        self.assertEqual(
            run("수들은 [1, 2]이다.\n새것들은 수들의 복사본이다.\n"
                "새것들에 3을 더한다.\n새것들을 출력한다.\n수들을 출력한다."),
            "[1, 2, 3][1, 2]")

    def test_copy_reaches_into_nested_values(self):
        self.assertEqual(
            run("내것은 {수들: [1, 2]}이다.\n"
                "새것은 내것의 복사본이다.\n새것의 수들에 3을 더한다.\n"
                "새것의 수들을 출력한다.\n내것의 수들을 출력한다."),
            "[1, 2, 3][1, 2]")


class Exceptions(unittest.TestCase):
    def test_try_catches(self):
        self.assertEqual(
            run('해 본다:\n    "없는파일.txt"를 읽는다.\n'
                '실패하면:\n    "잡음"을 출력한다.'), "잡음")

    def test_only_the_bare_form(self):
        error = failure('"없는파일.txt"를 읽어 본다:\n    참\n실패하면:\n    참')
        self.assertEqual(error.kind, "구문 오류")

    def test_a_handler_without_a_name_keeps_no_reason(self):
        error = failure('해 본다:\n    "가"라는 오류를 낸다.\n'
                        '실패하면:\n    이유를 출력한다.')
        self.assertEqual(error.kind, "이름 오류")

    def test_reason_is_bound_to_the_given_name(self):
        self.assertEqual(
            run('해 본다:\n    "없는파일.txt"를 읽는다.\n'
                '내용으로 실패하면:\n    내용을 출력한다.'), "파일없음")

    def test_the_bound_name_does_not_leak(self):
        error = failure('해 본다:\n    "가"라는 오류를 낸다.\n'
                        '내용으로 실패하면:\n    참\n내용을 출력한다.')
        self.assertEqual(error.kind, "이름 오류")

    def test_only_one_handler(self):
        error = failure('해 본다:\n    참\n실패하면:\n    참\n실패하면:\n    참')
        self.assertEqual(error.kind, "구문 오류")

    def test_a_reserved_word_may_not_be_a_target(self):
        for source in ('오류는 "가"이다.', "끝으로는 3이다."):
            with self.subTest(source=source):
                error = failure(source)
                self.assertEqual(error.kind, "구문 오류")
                self.assertIn("예약어", error.message)

    def test_a_string_is_not_a_name(self):
        error = failure('해 본다:\n    참\n"입력끝"으로 실패하면:\n    참')
        self.assertEqual(error.kind, "구문 오류")

    def test_finally_always_runs(self):
        self.assertEqual(
            run('해 본다:\n    "없는파일.txt"를 읽는다.\n'
                '실패하면:\n    "가"를 출력한다.\n끝으로:\n    "나"를 출력한다.'), "가나")

    def test_raise(self):
        error = failure('"망했다"라는 오류를 낸다.')
        self.assertEqual((error.kind, error.message), ("예외", "망했다"))


class Conversion(unittest.TestCase):
    def test_to_number(self):
        self.assertEqual(run('"12"를 정수로 바꾼 값에 1을 더한 값을 출력한다.'), "13")
        self.assertEqual(run('"3.5"를 실수로 바꾼 값을 출력한다.'), "3.5")

    def test_to_text(self):
        self.assertEqual(run("12를 문자열로 바꾼 값의 글자수를 출력한다."), "2")

    def test_to_boolean(self):
        self.assertEqual(run('"참"을 논리값으로 바꾼 값을 출력한다.'), "참")
        self.assertEqual(run("0을 논리값으로 바꾼 값을 출력한다."), "거짓")

    def test_type_field(self):
        cases = [("12", "정수"), ("3.5", "실수"), ('"가"', "문자열"),
                 ("[1]", "목록"), ("참", "논리값")]
        for value, wanted in cases:
            with self.subTest(value=value):
                self.assertEqual(run(f"{value}의 자료형을 출력한다."), wanted)

    def test_type_of_a_dict(self):
        self.assertEqual(run('철수는 {이름: "가"}이다.\n철수의 자료형을 출력한다.'), "사전")

    def test_type_compares_with_the_type_name(self):
        self.assertEqual(
            run('만약 12의 자료형이 정수이면:\n    "수"를 출력한다.'), "수")

    def test_bad_conversion(self):
        self.assertEqual(failure('"가"를 정수로 바꾼 값을 출력한다.').kind, "값 오류")


class Resources(unittest.TestCase):
    def test_default_name(self):
        self.assertEqual(
            run('"/tmp/새롬시험1.txt"를 기록으로 열어 둔다:\n    "가"를 기록에 쓴다.\n'
                '"/tmp/새롬시험1.txt"를 읽은 값을 출력한다.'), "가")

    def test_chosen_name(self):
        self.assertEqual(
            run('"/tmp/새롬시험2.txt"를 기록으로 열어 둔다:\n    "나"를 기록에 쓴다.\n'
                '"/tmp/새롬시험2.txt"를 읽은 값을 출력한다.'), "나")

    def test_reads_and_writes_the_same_handle(self):
        run('"/tmp/새롬시험3.txt"를 기록으로 열어 둔다:\n    "옛"을 기록에 쓴다.')
        self.assertEqual(
            run('"/tmp/새롬시험3.txt"를 기록으로 열어 둔다:\n'
                '    기록을 읽은 값을 출력한다.\n'
                '    "새"를 기록에 쓴다.\n'
                '"/tmp/새롬시험3.txt"를 읽은 값을 출력한다.'), "옛새")

    def test_closed_after_the_block(self):
        self.assertEqual(
            run('"/tmp/새롬시험4.txt"를 기록으로 열어 둔다:\n    "가"를 기록에 쓴다.\n'
                '"/tmp/새롬시험4.txt"를 읽은 값의 글자수를 출력한다.'), "1")


class Input(unittest.TestCase):
    def feed(self, text, source):
        import io
        import sys
        saved = sys.stdin
        sys.stdin = io.StringIO(text)
        try:
            return run(source)
        finally:
            sys.stdin = saved

    def test_one_line(self):
        self.assertEqual(self.feed("새롬\n", "이름은 입력받은 값이다.\n이름을 출력한다."),
                         "새롬")

    def test_line_is_text(self):
        self.assertEqual(
            self.feed("3\n", "수는 입력받은 값을 정수로 바꾼 값이다.\n"
                              "수에 1을 더한 값을 출력한다."), "4")

    def test_reads_until_the_end(self):
        self.assertEqual(
            self.feed("가\n나\n",
                      "해 본다:\n"
                      "    언제나는 참이다.\n"
                      "    언제나인 동안 반복한다:\n"
                      '        "{입력받은 값} "를 출력한다.\n'
                      '실패하면:\n    "끝"을 출력한다.'), "가 나 끝")

    def test_end_of_input_is_catchable(self):
        self.assertEqual(
            self.feed("", '해 본다:\n    입력받은 값을 출력한다.\n'
                          '실패하면:\n    "끝"을 출력한다.'), "끝")


class Errors(unittest.TestCase):
    def test_unknown_name_suggests(self):
        error = failure("반복횟수는 0이다.\n반복회수를 출력한다.")
        self.assertEqual(error.kind, "이름 오류")
        self.assertIn("반복횟수", error.hint)

    def test_wrong_particle_shows_the_signature(self):
        error = failure("3에서 5를 더한 값을 출력한다.")
        self.assertEqual(error.kind, "조사 오류")
        self.assertIn("~에 ~를 더한다", error.hint)

    def test_missing_key_lists_the_keys(self):
        error = failure('철수는 {이름: "가"}이다.\n철수의 점수를 출력한다.')
        self.assertEqual(error.kind, "이름 오류")
        self.assertIn("이름", error.hint)

    def test_divide_by_zero(self):
        self.assertEqual(failure("1을 0으로 나눈 값을 출력한다.").kind, "산술 오류")

    def test_type_error(self):
        self.assertEqual(failure('"가"에 1을 더한 값을 출력한다.').kind, "값 오류")

    def test_runaway_recursion(self):
        error = failure("수를 도는것하다라는 것은:\n    수를 도는것한 값을 돌려준다.\n"
                        "1을 도는것한 값을 출력한다.")
        self.assertEqual(error.kind, "재귀 오류")

    def test_call_stack_is_recorded(self):
        error = failure("수를 안쪽하다라는 것은:\n    없는이름을 출력한다.\n"
                        "수를 바깥쪽하다라는 것은:\n    수를 안쪽한 값을 돌려준다.\n"
                        "1을 바깥쪽한 값을 출력한다.")
        self.assertEqual([frame.verb for frame in error.frames],
                         ["바깥쪽하다", "안쪽하다"])

    def test_predicate_is_not_conjugated_like_a_verb(self):
        error = failure("수학에서 짝수이다를 가져온다.\n"
                        "3이 4로 짝수인지를 출력한다.")
        shown = f"{error.message} {error.hint or ''}"
        self.assertIn("짝수이다", shown)
        self.assertNotIn("짝수인다", shown)

    def test_builtin_given_the_wrong_kind(self):
        """내장이 파이썬 오류를 내도 새롬 오류로 나와야 한다."""
        error = failure("목록은 [1]이다.\n목록에서 목록을 뺀 값을 출력한다.")
        self.assertEqual(error.kind, "값 오류")
        self.assertIn("빼다", error.message)

    def test_a_loop_needs_a_range(self):
        error = failure("수들은 [1]이다.\n수들마다 반복한다:\n    참")
        self.assertEqual(error.kind, "구문 오류")
        self.assertIn("범위", error.message)

    def test_range_with_a_step_that_is_not_a_number(self):
        error = failure('1부터 3까지 "가" 간격의 수마다 반복한다:\n    참')
        self.assertEqual(error.kind, "값 오류")
        self.assertEqual(error.line, 1)

    def test_return_outside_a_definition(self):
        error = failure("1을 돌려준다.")
        self.assertEqual(error.kind, "실행 오류")
        self.assertIn("돌려주다", error.message)
        self.assertEqual(failure("1부터 2까지의 수마다 반복한다:\n"
                                 "    수를 돌려준다.").kind, "실행 오류")

    def test_position_is_recorded(self):
        error = failure("1을 출력한다.\n없는이름을 출력한다.")
        self.assertEqual((error.line, error.col, error.end), (2, 0, 4))


class Gone(unittest.TestCase):
    """지운 꼴은 분명한 오류가 되어야 한다."""

    def test_list_loop(self):
        error = failure("수들은 [1]이다.\n수들마다 반복한다:\n    참")
        self.assertEqual(error.kind, "구문 오류")

    def test_record_declaration(self):
        self.assertEqual(
            failure("학생은 이런 것이다:\n    이름은 문자열이다.\n참").kind, "구문 오류")

    def test_empty_list_keyword(self):
        self.assertEqual(failure("빈것은 빈목록이다.\n참").kind, "이름 오류")

    def test_filter(self):
        self.assertEqual(
            failure("수학에서 짝수이다를 가져온다.\n수들은 [1]이다.\n"
                    "짝수인 수들을 출력한다.").kind, "구문 오류")

    def test_collection_adverbs(self):
        """모두·각각·가장·하나라도는 이제 그저 이름이다."""
        for source in ("수들을 모두 더한 값을 출력한다.",
                       "수들 중 가장 큰 값을 출력한다.",
                       "수들을 각각 늘린 값을 출력한다."):
            with self.subTest(source=source):
                self.assertEqual(failure("수들은 [1, 2]이다.\n" + source).kind,
                                 "이름 오류")

    def test_sorting(self):
        self.assertEqual(failure("수들은 [3, 1]이다.\n수들을 정렬한다.").kind, "이름 오류")



if __name__ == "__main__":
    unittest.main()
