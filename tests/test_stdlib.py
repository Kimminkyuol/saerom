import unittest

from tests.support import failure, run


class Module(unittest.TestCase):
    """모듈 하나마다 한 줄짜리 식을 돌려 본다."""
    SETUP = ""

    def check(self, expression, wanted):
        self.assertEqual(run(self.SETUP + f'"{{{expression}}}"을 출력한다.'), wanted)


class Math(Module):
    SETUP = "수학을 가져온다.\n"

    def test_constant(self):
        self.check("수학의 원주율", "3.14159265359")

    def test_sign_and_absolute(self):
        self.check("-3의 수학의 부호구한 값", "-1")
        self.check("0의 수학의 부호구한 값", "0")
        self.check("-7을 수학의 절댓값구한 값", "7")

    def test_negative(self):
        self.check("-1이 수학의 음수인지", "참")
        self.check("1이 수학의 음수인지", "거짓")

    def test_rounding(self):
        self.check("2.7을 수학의 내림한 값", "2")
        self.check("-2.7을 수학의 내림한 값", "-3")
        self.check("2.1을 수학의 올림한 값", "3")
        self.check("-2.1을 수학의 올림한 값", "-2")
        self.check("2.5를 수학의 반올림한 값", "3")
        self.check("2.4를 수학의 반올림한 값", "2")

    def test_power(self):
        self.check("2를 10만큼 수학의 거듭제곱한 값", "1024")
        self.check("5를 0만큼 수학의 거듭제곱한 값", "1")

    def test_square_root(self):
        self.check("16의 수학의 제곱근구한 값", "4")
        self.check("0의 수학의 제곱근구한 값", "0")

    def test_square_root_of_a_negative(self):
        self.assertEqual(
            failure("수학을 가져온다.\n-1의 수학의 제곱근구한 값을 출력한다.").kind, "예외")

    def test_factorial(self):
        self.check("5의 수학의 계승구한 값", "120")
        self.check("0의 수학의 계승구한 값", "1")

    def test_prime(self):
        self.check("7이 수학의 소수인지", "참")
        self.check("8이 수학의 소수인지", "거짓")
        self.check("1이 수학의 소수인지", "거짓")

    def test_divisors(self):
        self.check("12의 수학의 약수구한 값", "[1, 2, 3, 4, 6, 12]")

    def test_gcd_and_lcm(self):
        self.check("12와 18의 수학의 최대공약수구한 값", "6")
        self.check("12와 18의 수학의 최소공배수구한 값", "36")


class Statistics(Module):
    SETUP = ("통계에서 합구하다와 평균구하다와 분산구하다와 표준편차구하다와 "
             "범위구하다와 중앙값구하다와 최빈값구하다를 가져온다.\n"
             "수들은 [4, 1, 3, 1, 2]이다.\n")

    def test_sum_and_mean(self):
        self.check("수들의 합구한 값", "11")
        self.check("수들의 평균구한 값", "2.2")

    def test_spread(self):
        self.check("수들의 분산구한 값", "1.36")
        self.check("수들의 범위구한 값", "3")

    def test_median(self):
        self.check("수들의 중앙값구한 값", "2")
        self.check("[4, 1, 3, 2]의 중앙값구한 값", "2.5")

    def test_mode(self):
        self.check("수들의 최빈값구한 값", "1")

    def test_empty(self):
        self.check("빈목록의 합구한 값", "0")
        self.check("빈목록의 평균구한 값", "0")


class Lists(Module):
    SETUP = ("목록에서 포함하다와 위치구하다와 역순구하다와 중복제거하다와 "
             "앞부분구하다와 뒷부분구하다와 연결하다와 개수구하다를 가져온다.\n")

    def test_contains_and_position(self):
        self.check("[1, 2, 3]이 2를 포함하는지", "참")
        self.check("[1, 2]가 5를 포함하는지", "거짓")
        self.check("[10, 20, 30]에서 20의 위치구한 값", "2")
        self.check("[1]에서 9의 위치구한 값", "0")

    def test_reverse(self):
        self.check("[1, 2, 3]의 역순구한 값", "[3, 2, 1]")
        self.check('["가", "나"]의 역순구한 값', "[나, 가]")
        self.check("빈목록의 역순구한 값", "[]")

    def test_unique(self):
        self.check("[1, 2, 1, 3, 2]의 중복제거한 값", "[1, 2, 3]")

    def test_slices(self):
        self.check("[1, 2, 3, 4]에서 2만큼 앞부분구한 값", "[1, 2]")
        self.check("[1, 2, 3, 4]에서 2만큼 뒷부분구한 값", "[3, 4]")

    def test_join_and_count(self):
        self.check("[1, 2]에 [3]을 연결한 값", "[1, 2, 3]")
        self.check("[1, 2, 1, 1]에서 1의 개수구한 값", "3")


class Text(Module):
    SETUP = ("글자에서 글자들구하다와 뒤집기하다와 치환하다와 되풀이하다와 "
             "부분구하다와 자리구하다와 분리하다와 왼쪽채움하다를 가져온다.\n")

    def test_characters(self):
        self.check('"가나다"의 글자들구한 값', "[가, 나, 다]")
        self.check('""의 글자들구한 값', "[]")

    def test_reverse(self):
        self.check('"가나다"의 뒤집기한 값', "다나가")

    def test_replace(self):
        self.check('"a-b-c"에서 "-"를 "+"로 치환한 값', "a+b+c")

    def test_repeat(self):
        self.check('"가"를 3만큼 되풀이한 값', "가가가")
        self.check('"가"를 0만큼 되풀이한 값', "")

    def test_substring(self):
        self.check('"가나다라"에서 2부터 2만큼 부분구한 값', "나다")
        self.check('"가나다"에서 1부터 9만큼 부분구한 값', "가나다")

    def test_find(self):
        self.check('"가나다"에서 "나다"의 자리구한 값', "2")
        self.check('"가나"에서 "라"의 자리구한 값', "0")

    def test_split(self):
        self.check('"a,,b"를 ","로 분리한 값', "[a, b]")

    def test_pad(self):
        self.check('"7"을 3만큼 왼쪽채움한 값', "  7")
        self.check('"1234"를 3만큼 왼쪽채움한 값', "1234")


class Imports(unittest.TestCase):
    def test_whole_module_uses_the_namespace(self):
        self.assertEqual(run('수학을 가져온다.\n"{수학의 원주율}"을 출력한다.'),
                         "3.14159265359")

    def test_selective_import_needs_no_namespace(self):
        self.assertEqual(
            run('수학에서 절댓값구하다를 가져온다.\n"{-3을 절댓값구한 값}"을 출력한다.'), "3")

    def test_predicate_by_dictionary_form(self):
        self.assertEqual(
            run("수학에서 음수이다를 가져온다.\n수들은 [1, -2]이다.\n"
                '"{음수인 수들}"을 출력한다.'), "[-2]")

    def test_module_can_import_a_module(self):
        """글자 는 목록 을 가져다 쓴다."""
        self.assertEqual(
            run('글자에서 뒤집기하다를 가져온다.\n"{"가나"의 뒤집기한 값}"을 출력한다.'), "나가")

    def test_unknown_module(self):
        self.assertEqual(failure("없는모듈을 가져온다.").kind, "구문 오류")

    def test_unknown_member(self):
        self.assertEqual(failure("수학에서 없는것을 가져온다.").kind, "이름 오류")


if __name__ == "__main__":
    unittest.main()
