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
        self.assertEqual(run("1부터 5까지의 수들마다 반복한다:\n    수를 출력한다."), "12345")

    def test_range_counts_down(self):
        self.assertEqual(run("3부터 1까지의 수들마다 반복한다:\n    수를 출력한다."), "321")

    def test_range_step(self):
        self.assertEqual(
            run("10부터 0까지 5 간격의 수들마다 반복한다:\n    수를 출력한다."), "1050")
        self.assertEqual(
            run("0부터 10까지 5 간격의 수들마다 반복한다:\n    수를 출력한다."), "0510")

    def test_while(self):
        self.assertEqual(
            run("수는 3이다.\n수가 0보다 큰 동안 반복한다:\n"
                "    수를 출력한다.\n    수는 수에서 1을 뺀 값이다."), "321")

    def test_break_and_continue(self):
        self.assertEqual(
            run("1부터 9까지의 수들마다 반복한다:\n"
                "    만약 수가 3보다 크면:\n        빠져나간다.\n"
                "    수를 출력한다."), "123")
        self.assertEqual(
            run("1부터 5까지의 수들마다 반복한다:\n"
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

    def test_predicate_in_three_places(self):
        head = "수가 홀수이다라는 것은:\n    수를 2로 나눈 나머지가 1인지를 돌려준다.\n"
        self.assertEqual(run(head + "만약 7이 홀수이면:\n    \"참\"을 출력한다."), "참")
        self.assertEqual(run(head + "7이 홀수인지를 출력한다."), "참")
        self.assertEqual(run(head + "수들은 [1, 2, 3]이다.\n홀수인 수들을 출력한다."),
                         "[1, 3]")

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
                  "수들의 평균이라는 것은:\n    수들을 모두 더한 값을 돌려준다.\n")
        self.assertEqual(
            run(source + '"{"가"를 뒤집은 값} {3으로 1을 만든 값} {2를 두배한 값} '
                '{1이 저축된 값} {4가 짝수인지} {[1, 2]의 평균}"을 출력한다.'),
            "가 3 4 2 참 3")

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
                "목록은 빈목록이다.\n"
                "목록에 1을 해석한 값을 더한다.\n"
                "목록을 출력한다."), "[101]")


class Stems(unittest.TestCase):
    """'명사 + 하다' 가 아닌 고유어 어간으로 만든 동사."""

    REVERSE = ("글을 뒤집다라는 것은:\n"
               "    글자들은 글을 \"\"로 자른 값들이다.\n"
               "    글자들의 역순을 \"\"로 이은 값을 돌려준다.\n")
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
            run("목록에서 역순을 가져온다.\n" + self.REVERSE +
                '"가나다"를 뒤집은 값을 출력한다.'), "다나가")

    def test_declared_name_wins(self):
        """'세기' 는 '세다'의 명사형이기도 하지만 선언된 이름이 앞선다."""
        self.assertEqual(
            run(self.COUNT + "세기는 3이다.\n"
                '"{세기} {[1, 2]를 센 값}"을 출력한다.'), "3 2")

    def test_declared_name_wins_over_a_builtin_form(self):
        """'크기' 는 '크다'의 명사형이기도 하지만 선언된 이름이 앞선다."""
        self.assertEqual(run("크기는 3이다.\n\"{크기}\"를 출력한다."), "3")
        self.assertEqual(
            run("상자는 이런 것이다:\n    크기는 정수이다.\n"
                "갑은 크기가 3인 상자이다.\n\"{갑의 크기}\"를 출력한다."), "3")
        self.assertEqual(
            run("상자는 이런 것이다:\n    나누기는 정수이다.\n"
                "갑은 나누기가 3인 상자이다.\n"
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
            "    글을 \"\"로 자른 값들의 역순을 \"\"로 이은 값을 돌려준다.\n")

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
        self.write("도구.sr", "목록에서 역순을 가져온다.\n\n" + self.TOOL)
        self.assertEqual(
            self.run_source('도구에서 뒤집다를 가져온다.\n'
                            '"가나다"를 뒤집은 값을 출력한다.'), "다나가")

    def test_imported_stem_verb_through_the_namespace(self):
        self.write("도구.sr", "목록에서 역순을 가져온다.\n\n" + self.TOOL)
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
    SETUP = "수학에서 짝수이다를 가져온다.\n수들은 [3, 8, 15, 4]이다.\n"

    def check(self, expression, wanted):
        self.assertEqual(run(self.SETUP + f"{expression}을 출력한다."), wanted)

    def test_filter(self):
        self.check("짝수인 수들", "[8, 4]")
        self.check("10보다 큰 수들", "[15]")

    def test_map(self):
        self.check("수들을 각각 2로 나눈 값들", "[1.5, 4, 7.5, 2]")

    def test_reduce(self):
        self.check("수들을 모두 더한 값", "30")

    def test_select(self):
        self.check("수들 중 가장 큰 값", "15")
        self.check("수들 중 가장 작은 값", "3")

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

    def test_empty_reduce_is_an_error(self):
        error = failure("빈목록을 모두 더한 값을 출력한다.")
        self.assertIn("모을 원소가 없음", error.message)

    def test_reduce_leaves_the_source_alone(self):
        self.assertEqual(
            run("겹친것은 [[1], [2]]이다.\n겹친것을 모두 더한 값을 출력한다.\n"
                "겹친것을 출력한다."), "[1, 2][[1], [2]]")

    def test_field_out_of_range(self):
        for expression in ("빈목록의 첫째", "빈목록의 마지막", "수들의 5번째",
                           '""의 첫째', '""의 마지막'):
            with self.subTest(expression=expression):
                error = failure(self.SETUP + f"{expression}을 출력한다.")
                self.assertEqual(error.kind, "값 오류")

    def test_quantifiers(self):
        self.check("수들이 모두 짝수인지", "거짓")
        self.check("수들 중 하나라도 10보다 큰지", "참")

    def test_filter_over_an_expression(self):
        self.check("수들을 각각 2로 나눈 값들 중 5보다 큰 것들", "[7.5]")

    def test_length_is_not_a_field(self):
        self.assertEqual(failure("[1]의 길이를 출력한다.").kind, "이름 오류")
        self.assertEqual(failure('"가"의 개수를 출력한다.').kind, "이름 오류")

    def test_string_fields(self):
        self.assertEqual(run('이름들은 ["가나", "다"]이다.\n이름들의 글자수들을 출력한다.'),
                         "[2, 1]")


class LoopControl(unittest.TestCase):
    """중단문과 계속문은 반복문 안에서만 뜻이 있다."""

    def test_break_and_continue(self):
        self.assertEqual(
            run("1부터 5까지의 수들마다 반복한다:\n"
                "    만약 수가 2이면:\n        넘어간다.\n"
                "    만약 수가 4이면:\n        빠져나간다.\n"
                '    "{수}"를 출력한다.'), "13")

    def test_break_outside_a_loop(self):
        self.assertIn("반복문", failure("빠져나간다.").message)

    def test_continue_outside_a_loop(self):
        self.assertIn("반복문", failure("넘어간다.").message)

    def test_break_does_not_cross_a_verb(self):
        error = failure("수를 재주하다라는 것은:\n    빠져나간다.\n"
                        "수들은 [1]이다.\n수들마다 반복한다:\n    수를 재주한다.")
        self.assertIn("반복문", error.message)

    def test_break_inside_a_verb_with_its_own_loop(self):
        self.assertEqual(
            run("수를 재주하다라는 것은:\n"
                "    1부터 3까지의 수들마다 반복한다:\n"
                "        빠져나간다.\n"
                '    "안"을 출력한다.\n'
                "1부터 2까지의 수들마다 반복한다:\n    수를 재주한다."), "안안")


class Counter(unittest.TestCase):
    """차례는 특수 이름이 아니라 세어서 쓴다."""

    def test_counting_over_a_list(self):
        self.assertEqual(
            run('이름들은 ["가", "나"]이다.\n'
                "1부터 이름들의 개수까지의 자리들마다 반복한다:\n"
                '    "{자리}:{이름들의 자리번째} "을 출력한다.'), "1:가 2:나 ")

    def test_counting_in_a_while_loop(self):
        self.assertEqual(
            run("자리는 0이다.\n남은것은 2이다.\n남은것이 0보다 큰 동안 반복한다:\n"
                "    자리는 자리에 1을 더한 값이다.\n"
                '    "{자리}"를 출력한다.\n'
                "    남은것은 남은것에서 1을 뺀 값이다."), "12")

    def test_the_old_counter_is_gone(self):
        error = failure("수들은 [1]이다.\n수들마다 반복한다:\n    번째를 출력한다.")
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
        self.assertEqual(run(head + "수들은 [1, 2, 3]이다.\n"
                                    "2와 짝인 수들을 출력한다."), "[2]")

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

    def test_map(self):
        self.check(self.QUIET + "수들은 [1, 2]이다.\n"
                   "수들을 각각 조용히한 값들을 출력한다.")

    def test_fold(self):
        self.check("목록에 수를 조용히하다라는 것은:\n    참\n수들은 [1, 2]이다.\n"
                   "수들을 모두 조용히한 값을 출력한다.")

    def test_printing_gives_no_value(self):
        self.check('값은 "가"를 출력한 값이다.\n참')

    def test_block_name_stays_closed(self):
        """값을 내지 않은 동사는 자원문의 이름을 열지 않는다."""
        self.assertEqual(
            failure(self.QUIET + "1을 조용히해 통으로 둔다:\n    통을 출력한다.").kind,
            "이름 오류")

    def test_sort_spec_shows_a_korean_name(self):
        self.assertEqual(run('"{큰 순}"을 출력한다.'), "정렬 기준")


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

    def test_filters(self):
        source = "수들은 [1, 10, 30]이다.\n"
        self.assertEqual(run(source + '"{10 이상인 수들}"을 출력한다.'), "[10, 30]")
        self.assertEqual(run(source + '"{10 이하인 수들}"을 출력한다.'), "[1, 10]")
        self.assertEqual(run(source + '"{10 초과인 수들}"을 출력한다.'), "[30]")
        self.assertEqual(run(source + '"{10 미만인 수들}"을 출력한다.'), "[1]")

    def test_question(self):
        self.assertEqual(run('"{3이 3 이상인지}"를 출력한다.'), "참")
        self.assertEqual(run('"{3이 3 초과인지}"를 출력한다.'), "거짓")

    def test_negation(self):
        self.assertEqual(self.branch("수가 20 이상이 아니면"), "참")
        self.assertEqual(
            run("수들은 [1, 10, 30]이다.\n"
                '"{10 이상이 아닌 수들}"을 출력한다.'), "[1]")

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

    def test_sort_as_a_statement_changes_the_list(self):
        self.assertEqual(
            run("수들은 [3, 1]이다.\n수들을 정렬한다.\n수들을 출력한다."), "[1, 3]")

    def test_sort_as_a_value_spares_the_list(self):
        self.assertEqual(
            run("원본은 [3, 1]이다.\n"
                '"{원본을 정렬한 값} {원본}"을 출력한다.'), "[1, 3] [3, 1]")

    def test_map_spares_the_items(self):
        self.assertEqual(
            run("겹친것은 [[3, 1]]이다.\n"
                '"{겹친것을 각각 정렬한 값들} {겹친것}"을 출력한다.'),
            "[[1, 3]] [[3, 1]]")


class RecordFields(unittest.TestCase):
    HEAD = "학생은 이런 것이다:\n    이름은 문자열이다.\n    나이는 정수이다.\n"

    def test_unknown_field(self):
        error = failure(self.HEAD + '철수는 이름이 "가"이고 나이가 1이고 점수가 9인 학생이다.\n참')
        self.assertEqual(error.kind, "이름 오류")
        self.assertIn("점수", error.message)

    def test_missing_field(self):
        error = failure(self.HEAD + '철수는 이름이 "가"인 학생이다.\n참')
        self.assertIn("나이", error.message)

    def test_unknown_field_in_block_form(self):
        error = failure(self.HEAD + '철수는 이런 학생이다:\n    이름은 "가"이다.\n'
                        "    점수는 1이다.\n참")
        self.assertIn("점수", error.message)

    def test_struct_name_may_not_be_a_field(self):
        error = failure(self.HEAD + '철수는 이름이 "가"이고 나이가 1인 학생이다.\n'
                        "철수의 이름은 이런 것이다:\n    쪽은 문자열이다.\n참")
        self.assertEqual(error.kind, "구문 오류")

    def test_unknown_struct(self):
        self.assertEqual(failure('철수는 이름이 "가"인 사람이다.\n참').kind, "이름 오류")

    def test_matching_types_pass(self):
        self.assertEqual(
            run(self.HEAD + '철수는 이름이 "가"이고 나이가 1인 학생이다.\n'
                "철수의 나이를 출력한다."), "1")

    def test_wrong_type_when_made(self):
        error = failure(self.HEAD + '철수는 이름이 "가"이고 나이가 "열"인 학생이다.\n참')
        self.assertEqual(error.kind, "값 오류")
        self.assertIn("정수", error.message)

    def test_wrong_type_when_changed(self):
        error = failure(self.HEAD + '철수는 이름이 "가"이고 나이가 1인 학생이다.\n'
                        '철수의 나이는 "둘"이다.\n참')
        self.assertEqual(error.kind, "값 오류")
        self.assertIn("정수", error.message)

    def test_a_boolean_is_not_a_whole_number(self):
        self.assertEqual(
            failure(self.HEAD + '철수는 이름이 "가"이고 나이가 참인 학생이다.\n참').kind,
            "값 오류")

    def test_a_whole_number_fits_a_real_field(self):
        self.assertEqual(
            run("점은 이런 것이다:\n    높이는 실수이다.\n"
                "하나는 높이가 3인 점이다.\n하나의 높이를 출력한다."), "3")

    def test_list_field_checks_each_item(self):
        head = "반은 이런 것이다:\n    점수들은 정수들이다.\n"
        self.assertEqual(run(head + "하나는 점수들이 [1, 2]인 반이다.\n"
                                    "하나의 점수들의 개수를 출력한다."), "2")
        self.assertEqual(failure(head + '하나는 점수들이 [1, "가"]인 반이다.\n참').kind,
                         "값 오류")

    def test_a_field_may_be_a_struct(self):
        head = ("주소는 이런 것이다:\n    도시는 문자열이다.\n"
                "학생은 이런 것이다:\n    사는곳은 주소이다.\n"
                '집은 도시가 "서울"인 주소이다.\n')
        self.assertEqual(run(head + "철수는 사는곳이 집인 학생이다.\n"
                                    "철수의 사는곳의 도시를 출력한다."), "서울")
        self.assertEqual(failure(head + '철수는 사는곳이 "서울"인 학생이다.\n참').kind,
                         "값 오류")

    def test_unknown_field_type(self):
        error = failure("학생은 이런 것이다:\n    나이는 정슈이다.\n참")
        self.assertEqual(error.kind, "이름 오류")
        self.assertIn("정슈", error.message)

    def test_a_field_may_be_called_값(self):
        head = ("상자는 이런 것이다:\n    값은 정수이다.\n"
                "갑은 값이 3인 상자이다.\n")
        self.assertEqual(run(head + '"{갑의 값}"을 출력한다.'), "3")
        self.assertEqual(run(head + '"{갑의 값에 2를 더한 값}"을 출력한다.'), "5")
        self.assertEqual(
            run(head + "갑의 값은 갑의 값에 1을 더한 값이다.\n"
                '"{갑의 값}"을 출력한다.'), "4")
        self.assertEqual(
            run(head + "상자들은 [갑]이다.\n" + '"{상자들의 값들}"을 출력한다.'),
            "[3]")

    def test_a_nested_field_target(self):
        """'X들의 첫째의 <필드>는 ...이다.' 도 자리를 알아야 오류가 제자리를 가리킨다."""
        head = ("상자는 이런 것이다:\n    무게는 정수이다.\n"
                "갑은 무게가 1인 상자이다.\n상자들은 [갑]이다.\n")
        self.assertEqual(
            run(head + "상자들의 첫째의 무게는 9이다.\n"
                '"{갑의 무게}"를 출력한다.'), "9")
        error = failure(head + "없는것의 첫째의 무게는 9이다.\n참")
        self.assertEqual(error.kind, "이름 오류")
        self.assertEqual(error.line, 5)


class Chosen(unittest.TestCase):
    """'가장' 은 기준을 받을 수 있고, 없으면 원소 자체가 기준이다."""

    HEAD = ("학생은 이런 것이다:\n    이름은 문자열이다.\n    점수들은 정수들이다.\n"
            "학생의 평균이라는 것은:\n    학생의 점수들을 모두 더한 값을 "
            "학생의 점수들의 개수로 나눈 값을 돌려준다.\n"
            '갑은 이름이 "갑"이고 점수들이 [80, 90]인 학생이다.\n'
            '둘은 이름이 "둘"이고 점수들이 [95, 99]인 학생이다.\n'
            "학생들은 [갑, 둘]이다.\n")

    def test_with_a_key(self):
        self.assertEqual(
            run(self.HEAD + "학생들 중 평균이 가장 큰 값의 이름을 출력한다."), "둘")
        self.assertEqual(
            run(self.HEAD + "학생들 중 평균이 가장 작은 값의 이름을 출력한다."), "갑")

    def test_without_a_key(self):
        self.assertEqual(run("[3, 9, 1] 중 가장 큰 값을 출력한다."), "9")

    def test_a_key_it_cannot_use_is_rejected(self):
        error = failure("수들은 [1]이다.\n수들 중 가장 100보다 큰 값을 출력한다.")
        self.assertEqual(error.kind, "구문 오류")


class Mapped(unittest.TestCase):
    """맵의 관형절도 걸러내기처럼 원소의 필드를 읽는다."""

    def test_element_field(self):
        self.assertEqual(
            run("학생은 이런 것이다:\n    이름은 문자열이다.\n"
                '갑은 이름이 "갑"인 학생이다.\n둘은 이름이 "둘"인 학생이다.\n'
                "학생들은 [갑, 둘]이다.\n"
                '학생들을 각각 이름을 잇는 값들을 출력한다.'), "[갑, 둘]")


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

    def test_a_verb_that_returns_a_dict(self):
        error = self.fails('from saerom.extension import verb\n\n'
                           '@verb("모으하다", "를")\n'
                           "def gather(one):\n    return {}\n",
                           "짐에서 모으하다를 가져온다.\n[1]을 모으한 값을 출력한다.")
        self.assertEqual(error.kind, "값 오류")
        self.assertIn("새롬 값이 아닌", error.message)

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


class Records(unittest.TestCase):
    def test_assigning_an_undeclared_field_is_rejected(self):
        error = failure('학생은 이런 것이다:\n    이름은 문자열이다.\n'
                        '철수는 이름이 "가"인 학생이다.\n철수의 점수는 1이다.')
        self.assertEqual(error.kind, "이름 오류")
        self.assertIn("점수", error.message)

    SETUP = ("학생은 이런 것이다:\n    이름은 문자열이다.\n    나이는 정수이다.\n"
             "철수는 이름이 \"김철수\"이고 나이가 17인 학생이다.\n")

    def test_field_access(self):
        self.assertEqual(run(self.SETUP + "철수의 이름을 출력한다."), "김철수")

    def test_field_assignment(self):
        self.assertEqual(run(self.SETUP + "철수의 나이는 18이다.\n철수의 나이를 출력한다."),
                         "18")

    def test_block_form(self):
        self.assertEqual(
            run(self.SETUP + "민수는 이런 학생이다:\n"
                "    이름은 \"박민수\"이다.\n    나이는 20이다.\n"
                "민수의 이름을 출력한다."), "박민수")

    def test_attached_verb(self):
        self.assertEqual(
            run(self.SETUP + "학생의 소개하다라는 것은:\n"
                "    \"{학생의 이름}({학생의 나이})\"를 돌려준다.\n"
                "철수의 소개한 값을 출력한다."), "김철수(17)")

    def test_records_are_equal_by_value(self):
        source = self.SETUP + '민수는 이름이 "김철수"이고 나이가 17인 학생이다.\n'
        self.assertEqual(run(source + "철수가 민수와 같은지를 출력한다."), "참")
        self.assertEqual(
            run(source + "민수의 나이는 18이다.\n철수가 민수와 같은지를 출력한다."), "거짓")

    def test_filter_reads_fields_of_the_element(self):
        self.assertEqual(
            run(self.SETUP + "학생들은 [철수]이다.\n"
                "나이가 17인 학생들의 개수를 출력한다."), "1")


class DerivedFields(unittest.TestCase):
    """계산되는 `X의 Y`."""

    AVERAGE = ("수들의 평균이라는 것은:\n"
               "    수들을 모두 더한 값을 수들의 개수로 나눈 값을 돌려준다.\n")

    SCORES = ("사람은 이런 것이다:\n    점수들은 정수들이다.\n"
              "수들의 평균이라는 것은:\n"
              "    수들을 모두 더한 값을 수들의 개수로 나눈 값을 돌려준다.\n"
              "사람의 평균점수라는 것은:\n    사람의 점수들의 평균을 돌려준다.\n"
              "철수는 점수들이 [60, 60]인 사람이다.\n"
              "영희는 점수들이 [90, 90]인 사람이다.\n"
              "사람들은 [철수, 영희]이다.\n")

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

    def test_record_field_comes_first(self):
        source = ("사람은 이런 것이다:\n    나이는 정수이다.\n"
                  "사람의 나이라는 것은:\n    99를 돌려준다.\n"
                  "철수는 나이가 3인 사람이다.\n"
                  '"{철수의 나이}"를 출력한다.')
        self.assertEqual(run(source), "3")

    def test_builtin_field_comes_first(self):
        source = ("항목들의 개수라는 것은:\n    0을 돌려준다.\n"
                  '"{[1, 2, 3]의 개수}"를 출력한다.')
        self.assertEqual(run(source), "3")

    def test_record_without_the_field_falls_through(self):
        source = ("사람은 이런 것이다:\n    점수들은 정수들이다.\n"
                  + self.AVERAGE +
                  "사람의 평균점수라는 것은:\n    사람의 점수들의 평균을 돌려준다.\n"
                  "철수는 점수들이 [80, 90, 100]인 사람이다.\n"
                  '"{철수의 평균점수}"를 출력한다.')
        self.assertEqual(run(source), "90")

    def test_inside_an_adnominal_clause(self):
        source = ("사람은 이런 것이다:\n    이름은 문자열이다.\n    점수들은 정수들이다.\n"
                  + self.AVERAGE +
                  "사람의 평균점수라는 것은:\n    사람의 점수들의 평균을 돌려준다.\n"
                  '철수는 이름이 "철수"이고 점수들이 [60, 60]인 사람이다.\n'
                  '영희는 이름이 "영희"이고 점수들이 [90, 90]인 사람이다.\n'
                  "사람들은 [철수, 영희]이다.\n"
                  '"{평균점수가 큰 순으로 정렬된 사람들의 이름들}"을 출력한다.')
        self.assertEqual(run(source), "[영희, 철수]")

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

    def test_quantifier_keeps_its_own_subject(self):
        """'~들이 모두' 의 '이'가 관형절 안의 '가' 자리를 먹지 않는다."""
        self.assertEqual(
            run(self.SCORES + '"{사람들이 모두 평균점수가 50보다 큰지}"를 출력한다.'),
            "참")
        self.assertEqual(
            run(self.SCORES + '"{사람들이 모두 평균점수가 70보다 큰지}"를 출력한다.'),
            "거짓")
        self.assertEqual(
            run(self.SCORES + '"{사람들 중 하나라도 평균점수가 70보다 큰지}"를 출력한다.'),
            "참")

    def test_element_does_not_leak_into_a_called_verb(self):
        """관형절의 원소는 그 절 안에서만 산다. 부른 동사 안까지 따라가지 않는다."""
        error = failure(self.SCORES +
                        "사람이 잘한것이다라는 것은:\n    평균점수가 70보다 큰지를 돌려준다.\n"
                        "잘한것인 사람들의 개수를 출력한다.")
        self.assertEqual(error.kind, "이름 오류")
        self.assertIn("평균점수", error.message)


class ActiveAndPassive(unittest.TestCase):
    SAVINGS = ("저금통은 이런 것이다:\n    금액은 정수이다.\n"
               "저금통에 돈을 저축하다라는 것은:\n"
               "    저금통의 금액은 저금통의 금액에 돈을 더한 값이다.\n"
               "저금통에 돈이 저축되다라는 것은:\n"
               "    새것은 저금통의 복사본이다.\n"
               "    새것에 돈을 저축한다.\n"
               "    새것을 돌려준다.\n"
               "내것은 금액이 100인 저금통이다.\n")

    def test_active_mutates(self):
        self.assertEqual(
            run("수들은 [3, 1, 2]이다.\n수들을 정렬한다.\n수들을 출력한다."), "[1, 2, 3]")

    def test_builtin_passive_leaves_the_original(self):
        self.assertEqual(
            run("수들은 [3, 1, 2]이다.\n정렬된 수들을 출력한다.\n수들을 출력한다."),
            "[1, 2, 3][3, 1, 2]")

    def test_sort_by_the_element_itself(self):
        self.assertEqual(run("수들은 [1, 3, 2]이다.\n큰 순으로 정렬된 수들을 출력한다."),
                         "[3, 2, 1]")
        self.assertEqual(run("수들은 [1, 3, 2]이다.\n작은 순으로 정렬된 수들을 출력한다.\n"
                             "수들을 출력한다."), "[1, 2, 3][1, 3, 2]")

    def test_sort_by_key(self):
        self.assertEqual(
            run("학생은 이런 것이다:\n    점수는 정수이다.\n"
                "낮은학생은 점수가 2인 학생이다.\n높은학생은 점수가 9인 학생이다.\n"
                "학생들은 [낮은학생, 높은학생]이다.\n"
                "점수가 큰 순으로 정렬된 학생들의 첫째의 점수를 출력한다."), "9")

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
            "저금통은 이런 것이다:\n    금액은 정수이다.\n"
            "저금통에 돈을 저축하다라는 것은:\n"
            "    저금통의 금액은 저금통의 금액에 돈을 더한 값이다.\n"
            "내것은 금액이 100인 저금통이다.\n"
            "50이 저축된 내것의 금액을 출력한다.")
        self.assertEqual(error.kind, "이름 오류")
        self.assertIn("저축되다", error.message)
        self.assertIn("저축하다", error.hint)

    def test_copy_of_a_list(self):
        self.assertEqual(
            run("수들은 [1, 2]이다.\n새것들은 수들의 복사본이다.\n"
                "새것들에 3을 더한다.\n새것들을 출력한다.\n수들을 출력한다."),
            "[1, 2, 3][1, 2]")

    def test_copy_of_a_record(self):
        self.assertEqual(
            run("저금통은 이런 것이다:\n    금액은 정수이다.\n"
                "내것은 금액이 100인 저금통이다.\n"
                "새것은 내것의 복사본이다.\n새것의 금액은 200이다.\n"
                "새것의 금액을 출력한다.\n내것의 금액을 출력한다."), "200100")

    def test_copy_reaches_into_nested_values(self):
        self.assertEqual(
            run("가방은 이런 것이다:\n    수들은 정수들이다.\n"
                "내것은 수들이 [1, 2]인 가방이다.\n"
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

    def test_type_of_a_record(self):
        self.assertEqual(
            run("학생은 이런 것이다:\n    이름은 문자열이다.\n"
                '철수는 이름이 "가"인 학생이다.\n철수의 자료형을 출력한다.'), "학생")

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

    def test_missing_field_lists_the_fields(self):
        error = failure("학생은 이런 것이다:\n    이름은 문자열이다.\n"
                        '철수는 이름이 "가"인 학생이다.\n철수의 점수를 출력한다.')
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

    def test_select_rejects_slots_it_cannot_use(self):
        """'가장'은 견줌 하나만 쓴다. 남는 구절을 말없이 버리지 않는다."""
        error = failure("수들은 [1, 5, 3]이다.\n"
                        "수들 중 가장 100보다 큰 값을 출력한다.")
        self.assertEqual(error.kind, "구문 오류")
        self.assertIn("보다", error.message)

    def test_quantifier_needs_a_source(self):
        self.assertEqual(failure("수들은 [1]이다.\n"
                                 "수들 중 모두 큰지를 출력한다.").kind, "구문 오류")

    def test_builtin_given_the_wrong_kind(self):
        """내장이 파이썬 오류를 내도 새롬 오류로 나와야 한다."""
        error = failure("목록은 [1]이다.\n목록에서 목록을 뺀 값을 출력한다.")
        self.assertEqual(error.kind, "값 오류")
        self.assertIn("빼다", error.message)

    def test_collection_adverbs_need_a_list(self):
        for expression in ("수를 모두 더한 값", "수 중 가장 큰 값",
                           "수를 각각 배한 값들", "수가 모두 좋은것인지"):
            with self.subTest(expression=expression):
                error = failure("수는 5이다.\n"
                                "수를 배하다라는 것은:\n    수에 2를 곱한 값을 돌려준다.\n"
                                "수가 좋은것이다라는 것은:\n    참을 돌려준다.\n"
                                f"{expression}을 출력한다.")
                self.assertEqual(error.kind, "실행 오류")
                self.assertIn("목록이 아님", error.message)

    def test_loop_over_something_that_is_not_a_list(self):
        error = failure("수는 3이다.\n수마다 반복한다:\n    참")
        self.assertEqual(error.kind, "실행 오류")
        self.assertEqual(error.line, 2)

    def test_range_with_a_step_that_is_not_a_number(self):
        error = failure('1부터 3까지 "가" 간격의 수들마다 반복한다:\n    참')
        self.assertEqual(error.kind, "값 오류")
        self.assertEqual(error.line, 1)

    def test_field_on_something_that_is_not_a_record(self):
        error = failure("목록은 [1]이다.\n목록의 자리는 3이다.\n참")
        self.assertEqual(error.kind, "실행 오류")
        self.assertIn("목록", error.message)

    def test_return_outside_a_definition(self):
        error = failure("1을 돌려준다.")
        self.assertEqual(error.kind, "실행 오류")
        self.assertIn("돌려주다", error.message)
        self.assertEqual(failure("1부터 2까지의 수들마다 반복한다:\n"
                                 "    수를 돌려준다.").kind, "실행 오류")

    def test_position_is_recorded(self):
        error = failure("1을 출력한다.\n없는이름을 출력한다.")
        self.assertEqual((error.line, error.col, error.end), (2, 0, 4))


if __name__ == "__main__":
    unittest.main()
