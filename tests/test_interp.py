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
            run("수가 음수인 것은:\n    수가 0보다 작은지를 돌려준다.\n"
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

    def test_index(self):
        self.assertEqual(
            run('이름들은 ["가", "나"]이다.\n이름들마다 반복한다:\n    번째를 출력한다.'),
            "12")

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
            run("반지름으로 원넓이계산하는 것은:\n"
                "    반지름에 반지름을 곱한 값을 돌려준다.\n"
                "3으로 원넓이계산한 값을 출력한다."), "9")

    def test_free_argument_order(self):
        source = ("사람에게 말을 전하는 것은:\n    \"{말}/{사람}\"을 출력한다.\n")
        self.assertEqual(run(source + '"가"에게 "나"를 전한다.'), "나/가")
        self.assertEqual(run(source + '"나"를 "가"에게 전한다.'), "나/가")

    def test_recursion(self):
        self.assertEqual(
            run("수를 계승계산하는 것은:\n"
                "    만약 수가 1보다 크지 않으면:\n        1을 돌려준다.\n"
                "    앞값은 수에서 1을 뺀 값을 계승계산한 값이다.\n"
                "    수에 앞값을 곱한 값을 돌려준다.\n"
                "5를 계승계산한 값을 출력한다."), "120")

    def test_predicate_in_three_places(self):
        head = "수가 홀수인 것은:\n    수를 2로 나눈 나머지가 1인지를 돌려준다.\n"
        self.assertEqual(run(head + "만약 7이 홀수이면:\n    \"참\"을 출력한다."), "참")
        self.assertEqual(run(head + "7이 홀수인지를 출력한다."), "참")
        self.assertEqual(run(head + "수들은 [1, 2, 3]이다.\n홀수인 수들을 출력한다."),
                         "[1, 3]")

    def test_signature_is_the_particle_set(self):
        source = ("값들을 정리하는 것은:\n    \"하나\"를 출력한다.\n"
                  "값들을 사이로 정리하는 것은:\n    \"둘\"을 출력한다.\n")
        self.assertEqual(run(source + "[1]을 정리한다."), "하나")
        self.assertEqual(run(source + '[1]을 ","로 정리한다.'), "둘")

    def test_repeated_particle_binds_in_order(self):
        """같은 조사를 여럿 쓰면 적은 차례대로 묶인다."""
        source = '앞을 뒤를 이어붙이하는 것은:\n    "{앞}/{뒤}"를 돌려준다.\n'
        self.assertEqual(run(source + '"가"를 "나"를 이어붙이한 값을 출력한다.'), "가/나")
        self.assertEqual(run(source + '"나"를 "가"를 이어붙이한 값을 출력한다.'), "나/가")

    def test_distinct_particles_stay_free(self):
        source = "사람에게 말을 전하는 것은:\n    \"{말}/{사람}\"을 돌려준다.\n"
        self.assertEqual(run(source + '"나"를 "가"에게 전한 값을 출력한다.'), "나/가")
        self.assertEqual(run(source + '"가"에게 "나"를 전한 값을 출력한다.'), "나/가")

    def test_repeated_particle_needs_the_same_count(self):
        source = '앞을 뒤를 이어붙이하는 것은:\n    참을 돌려준다.\n'
        self.assertEqual(failure(source + '"가"를 이어붙이한 값을 출력한다.').kind, "조사 오류")

    def test_adnominal_takes_only_its_own_slots(self):
        """'학생들에 줄들을 해석한 값을 더한다' 에서 해석하다는 줄들만 가져간다."""
        self.assertEqual(
            run("줄들을 해석하는 것은:\n    줄들에 100을 더한 값을 돌려준다.\n"
                "목록은 빈목록이다.\n"
                "목록에 1을 해석한 값을 더한다.\n"
                "목록을 출력한다."), "[101]")


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

    def test_reduce_of_an_empty_list_uses_the_identity(self):
        """원소가 없으면 셈을 한 번도 하지 않으므로 그 동사의 항등원을 낸다."""
        self.assertEqual(run("빈목록을 모두 더한 값을 출력한다."), "0")
        self.assertEqual(run("빈목록을 모두 곱한 값을 출력한다."), "1")
        self.assertEqual(run("빈목록을 모두 이은 값을 출력한다."), "")

    def test_reduce_of_an_empty_list_without_an_identity(self):
        error = failure("앞에 뒤를 겹치하는 것은:\n    앞을 돌려준다.\n"
                        "빈목록을 모두 겹치한 값을 출력한다.")
        self.assertIn("겹치하다", error.message)

    def test_native_ordinals(self):
        self.assertEqual(
            run("수들은 [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]이다.\n"
                '"{수들의 여섯째}{수들의 아홉째}{수들의 열째}"를 출력한다.'), "6910")

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
        error = failure("수를 재주하는 것은:\n    빠져나간다.\n"
                        "수들은 [1]이다.\n수들마다 반복한다:\n    수를 재주한다.")
        self.assertIn("반복문", error.message)

    def test_break_inside_a_verb_with_its_own_loop(self):
        self.assertEqual(
            run("수를 재주하는 것은:\n"
                "    1부터 3까지의 수들마다 반복한다:\n"
                "        빠져나간다.\n"
                '    "안"을 출력한다.\n'
                "1부터 2까지의 수들마다 반복한다:\n    수를 재주한다."), "안안")


class LoopIndex(unittest.TestCase):
    """'번째'는 반복문에 딸린 이름이다."""

    def test_counts_each_round(self):
        self.assertEqual(
            run('이름들은 ["가", "나"]이다.\n이름들마다 반복한다:\n'
                '    "{번째}{이름}"을 출력한다.'), "1가2나")

    def test_a_while_loop_counts_too(self):
        self.assertEqual(
            run("남은것은 3이다.\n남은것이 0보다 큰 동안 반복한다:\n"
                '    "{번째}"를 출력한다.\n'
                "    남은것은 남은것에서 1을 뺀 값이다."), "123")

    def test_an_inner_loop_does_not_clobber_the_outer_one(self):
        self.assertEqual(
            run('이름들은 ["가", "나"]이다.\n이름들마다 반복한다:\n'
                "    남은것은 2이다.\n"
                "    남은것이 0보다 큰 동안 반복한다:\n"
                "        남은것은 남은것에서 1을 뺀 값이다.\n"
                '    "{번째}"를 출력한다.'), "12")

    def test_gone_after_the_loop(self):
        for loop in ("1부터 2까지의 수들마다 반복한다:\n    1을 출력한다.\n",
                     "남은것은 1이다.\n남은것이 0보다 큰 동안 반복한다:\n"
                     "    남은것은 0이다.\n"):
            with self.subTest(loop=loop):
                self.assertEqual(failure(loop + "번째를 출력한다.").kind, "이름 오류")


class Predicates(unittest.TestCase):
    """술어는 참이나 거짓만 낸다."""

    def test_non_boolean_is_rejected(self):
        error = failure("수가 이상한것인 것은:\n    수에 1을 더한 값을 돌려준다.\n"
                        "3이 이상한것인지를 출력한다.")
        self.assertEqual(error.kind, "값 오류")
        self.assertIn("논리값", error.message)

    def test_missing_return_is_rejected(self):
        error = failure("수가 큰수인 것은:\n    만약 수가 100보다 크면:\n"
                        "        참을 돌려준다.\n"
                        "3이 큰수인지를 출력한다.")
        self.assertIn("돌려주지 않음", error.message)

    def test_verbs_may_return_anything(self):
        self.assertEqual(
            run("수를 두배하는 것은:\n    수에 수를 더한 값을 돌려준다.\n"
                "3을 두배한 값을 출력한다."), "6")

    def test_two_slots(self):
        """'A가 B와 <술어>ㄴ지' 의 '와'는 목록을 잇는 조사가 아니다."""
        head = ("왼쪽이 오른쪽과 짝인 것은:\n"
                "    왼쪽이 오른쪽과 같은지를 돌려준다.\n")
        self.assertEqual(run(head + "3이 3과 짝인지를 출력한다."), "참")
        self.assertEqual(run(head + "3이 4와 짝인지를 출력한다."), "거짓")
        self.assertEqual(run(head + "수들은 [1, 2, 3]이다.\n"
                                    "2와 짝인 수들을 출력한다."), "[2]")

    def test_conjunction_still_makes_a_list(self):
        self.assertEqual(run("수들은 1과 2와 3이다.\n수들을 출력한다."), "[1, 2, 3]")


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

    def test_unknown_struct(self):
        self.assertEqual(failure('철수는 이름이 "가"인 사람이다.\n참').kind, "이름 오류")


class Records(unittest.TestCase):
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
            run(self.SETUP + "학생의 소개하는 것은:\n"
                "    \"{학생의 이름}({학생의 나이})\"를 돌려준다.\n"
                "철수의 소개한 값을 출력한다."), "김철수(17)")

    def test_filter_reads_fields_of_the_element(self):
        self.assertEqual(
            run(self.SETUP + "학생들은 [철수]이다.\n"
                "나이가 17인 학생들의 개수를 출력한다."), "1")


class ActiveAndPassive(unittest.TestCase):
    def test_active_mutates(self):
        self.assertEqual(
            run("수들은 [3, 1, 2]이다.\n수들을 정렬한다.\n수들을 출력한다."), "[1, 2, 3]")

    def test_passive_copies(self):
        self.assertEqual(
            run("수들은 [3, 1, 2]이다.\n정렬된 수들을 출력한다.\n수들을 출력한다."),
            "[1, 2, 3][3, 1, 2]")

    def test_passive_of_a_user_verb(self):
        self.assertEqual(
            run("저금통은 이런 것이다:\n    금액은 정수이다.\n"
                "저금통에 돈을 저축하는 것은:\n"
                "    저금통의 금액은 저금통의 금액에 돈을 더한 값이다.\n"
                "내것은 금액이 100인 저금통이다.\n"
                "50이 저축된 내것의 금액을 출력한다.\n"
                "내것의 금액을 출력한다."), "150100")

    def test_sort_by_the_element_itself(self):
        self.assertEqual(run("수들은 [1, 3, 2]이다.\n큰 순으로 정렬된 수들을 출력한다."),
                         "[3, 2, 1]")
        self.assertEqual(run("수들은 [1, 3, 2]이다.\n작은 순으로 정렬된 수들을 출력한다."),
                         "[1, 2, 3]")

    def test_sort_by_key(self):
        self.assertEqual(
            run("학생은 이런 것이다:\n    점수는 정수이다.\n"
                "낮은학생은 점수가 2인 학생이다.\n높은학생은 점수가 9인 학생이다.\n"
                "학생들은 [낮은학생, 높은학생]이다.\n"
                "점수가 큰 순으로 정렬된 학생들의 첫째의 점수를 출력한다."), "9")


class Exceptions(unittest.TestCase):
    def test_try_catches(self):
        self.assertEqual(
            run('"없는파일.txt"를 읽어 본다:\n    결과를 출력한다.\n'
                '실패하면:\n    이유를 출력한다.'), "파일없음")

    def test_try_by_reason(self):
        self.assertEqual(
            run('"없는파일.txt"를 읽어 본다:\n    결과를 출력한다.\n'
                '"파일없음"으로 실패하면:\n    "잡음"을 출력한다.'), "잡음")

    def test_finally_always_runs(self):
        self.assertEqual(
            run('"없는파일.txt"를 읽어 본다:\n    참\n'
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
            run('"/tmp/새롬시험1.txt"를 열어 둔다:\n    "가"를 파일에 쓴다.\n'
                '"/tmp/새롬시험1.txt"를 읽은 값을 출력한다.'), "가")

    def test_chosen_name(self):
        self.assertEqual(
            run('"/tmp/새롬시험2.txt"를 기록으로 열어 둔다:\n    "나"를 기록에 쓴다.\n'
                '"/tmp/새롬시험2.txt"를 읽은 값을 출력한다.'), "나")

    def test_reads_and_writes_the_same_handle(self):
        run('"/tmp/새롬시험3.txt"를 열어 둔다:\n    "옛"을 파일에 쓴다.')
        self.assertEqual(
            run('"/tmp/새롬시험3.txt"를 기록으로 열어 둔다:\n'
                '    기록을 읽은 값을 출력한다.\n'
                '    "새"를 기록에 쓴다.\n'
                '"/tmp/새롬시험3.txt"를 읽은 값을 출력한다.'), "옛새")

    def test_closed_after_the_block(self):
        self.assertEqual(
            run('"/tmp/새롬시험4.txt"를 열어 둔다:\n    "가"를 파일에 쓴다.\n'
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
                      '"입력끝"으로 실패하면:\n    "끝"을 출력한다.'), "가 나 끝")

    def test_end_of_input_is_catchable(self):
        self.assertEqual(
            self.feed("", '입력받아 본다:\n    결과를 출력한다.\n'
                          '"입력끝"으로 실패하면:\n    "끝"을 출력한다.'), "끝")


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

    def test_predicate_signature_is_not_conjugated_as_a_verb(self):
        """술어의 사전형은 이미 '-이다'로 끝난다. '배수인다'가 되면 안 된다."""
        error = failure("수가 나눌수의 배수인 것은:\n    참을 돌려준다.\n"
                        "만약 3이 4로 배수이면:\n    1을 출력한다.")
        self.assertEqual(error.kind, "조사 오류")
        self.assertIn("~가 ~의 배수이다", error.hint)

    def test_sorting_a_non_list(self):
        self.assertEqual(failure('"가나"를 정렬한다.').kind, "값 오류")

    def test_adding_a_list_to_a_number(self):
        self.assertEqual(failure("수들은 [1]이다.\n1에 수들을 더한 값을 출력한다.").kind,
                         "값 오류")

    def test_divide_by_zero(self):
        self.assertEqual(failure("1을 0으로 나눈 값을 출력한다.").kind, "산술 오류")

    def test_type_error(self):
        self.assertEqual(failure('"가"에 1을 더한 값을 출력한다.').kind, "값 오류")

    def test_runaway_recursion(self):
        error = failure("수를 도는것하는 것은:\n    수를 도는것한 값을 돌려준다.\n"
                        "1을 도는것한 값을 출력한다.")
        self.assertEqual(error.kind, "재귀 오류")

    def test_call_stack_is_recorded(self):
        error = failure("수를 안쪽하는 것은:\n    없는이름을 출력한다.\n"
                        "수를 바깥쪽하는 것은:\n    수를 안쪽한 값을 돌려준다.\n"
                        "1을 바깥쪽한 값을 출력한다.")
        self.assertEqual([frame.verb for frame in error.frames],
                         ["바깥쪽하다", "안쪽하다"])

    def test_position_is_recorded(self):
        error = failure("1을 출력한다.\n없는이름을 출력한다.")
        self.assertEqual((error.line, error.col, error.end), (2, 0, 4))


if __name__ == "__main__":
    unittest.main()
