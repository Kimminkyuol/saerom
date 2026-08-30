"""내장. 새롬으로 적을 수 없는 것만 둔다."""
import os
import sys

from ..errors import ArithmeticError_, Raised, ValueError_
from .values import (Handle, SortKey, check_numbers, show, signature_of,
                     to_text, truthy)


# 능동으로 부르면 고쳐지는 조사 자리. 값 자리에서 부르면 복사해서 넘긴다.
CHANGES = {"더하다": "에", "정렬하다": "를"}


def build(interp):
    """실행기에 매달린 내장 표를 만든다."""
    write = interp.out.write

    def as_list(value):
        return value if isinstance(value, list) else [value]

    def joined(a):
        sep = to_text(a["로"]) if "로" in a else ""
        return sep.join(to_text(v) for v in as_list(a["를"]))

    def change(a):
        return convert(a["를"], to_text(a["로"]))

    def convert(value, kind):
        try:
            if kind in ("정수", "수"):
                return int(float(value))
            if kind == "실수":
                return float(value)
            if kind == "문자열":
                return to_text(value)
            if kind == "논리값":
                if isinstance(value, str):
                    if value in ("참", "거짓"):
                        return value == "참"
                    raise ValueError(value)
                return truthy(value)
        except (TypeError, ValueError):
            raise ValueError_(f"{kind}로 바꿀 수 없음: {show(value)}")
        raise ValueError_(f"바꿀 수 없는 자료형: '{kind}'")

    def divide(a):
        check_numbers("나누다", a["를"], a["로"])
        if a["로"] == 0:
            raise ArithmeticError_("0으로 나눌 수 없음")
        result = a["를"] / a["로"]
        return int(result) if float(result).is_integer() else result

    def remainder(a):
        check_numbers("나누다", a["를"], a["로"])
        if a["로"] == 0:
            raise ArithmeticError_("0으로 나눌 수 없음")
        return a["를"] % a["로"]

    def split_text(a):
        text, mark = to_text(a["를"]), to_text(a["로"])
        return list(text) if mark == "" else text.split(mark)

    def contains(a):
        whole = a["가"]
        if isinstance(whole, list):
            return a["를"] in whole
        return to_text(a["를"]) in to_text(whole)


    def sort_in_place(a):
        target = a["를"]
        if not isinstance(target, list):
            raise SaeromError("'정렬하다'의 인자가 목록이 아님")
        spec = a.get("로")
        if isinstance(spec, SortKey):
            target.sort(key=lambda item: sort_key(spec.of(item)),
                        reverse=spec.descending)
        else:
            target.sort(key=sort_key)
        return target

    def sort_key(value):
        return (0, value, "") if isinstance(value, (int, float)) else (1, 0, to_text(value))

    def append(a):
        target = a["에"]
        if not isinstance(target, list):
            raise SaeromError("'더하다'의 '~에' 자리가 목록이 아님")
        if isinstance(a["를"], list):
            target.extend(a["를"])
        else:
            target.append(a["를"])
        return target

    def add(a):
        if isinstance(a["에"], list):
            return append(a)
        check_numbers("더하다", a["에"], a["를"])
        return a["에"] + a["를"]

    def read_line(a):
        interp.out.flush()
        line = sys.stdin.readline()
        if not line:
            raise Raised("입력끝")
        return line.rstrip("\n")

    def read_file(a):
        target = a["를"]
        if isinstance(target, Handle):
            target.stream.flush()
            target.stream.seek(0)
            return target.stream.read()
        try:
            with open(to_text(target), encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            raise Raised("파일없음")
        except PermissionError:
            raise Raised("권한없음")

    def open_file(a):
        """읽기와 쓰기를 함께 연다. 없으면 만들고, 첫 쓰기에서 비운다."""
        path = to_text(a["를"])
        mode = "r+" if os.path.exists(path) else "w+"
        try:
            return Handle(open(path, mode, encoding="utf-8"))
        except PermissionError:
            raise Raised("권한없음")

    def write_file(a):
        target = a["에"]
        if not isinstance(target, Handle):
            raise ValueError_("'쓰다'의 '~에' 자리가 파일이 아님")
        if not target.written:
            target.stream.seek(0)
            target.stream.truncate()
            target.written = True
        target.stream.write(to_text(a["를"]))
        return None

    return {
        ("출력하다", signature_of(["를"])): lambda a: write(to_text(a["를"])),
        ("바꾸다", signature_of(["를", "로"])): change,
        ("잇다", signature_of(["를"])): joined,
        ("잇다", signature_of(["를", "로"])): joined,
        ("더하다", signature_of(["에", "를"])): add,
        ("빼다", signature_of(["에서", "를"])): lambda a: a["에서"] - a["를"],
        ("곱하다", signature_of(["에", "를"])): lambda a: a["에"] * a["를"],
        ("나누다", signature_of(["를", "로"])): divide,
        ("나누다·나머지", signature_of(["를", "로"])): remainder,
        ("크다", signature_of(["가", "보다"])): lambda a: a["가"] > a["보다"],
        ("작다", signature_of(["가", "보다"])): lambda a: a["가"] < a["보다"],
        ("같다", signature_of(["가", "와"])): lambda a: a["가"] == a["와"],
        ("이다", signature_of(["가", None])): lambda a: a["가"] == a[None],
        ("이다", signature_of(["가"])): lambda a: truthy(a["가"]),
        ("이다", signature_of([None])): lambda a: truthy(a[None]),
        ("시작하다", signature_of(["가", "로"])): lambda a: to_text(a["가"]).startswith(to_text(a["로"])),
        ("담다", signature_of(["가", "를"])): contains,
        ("끝나다", signature_of(["가", "로"])): lambda a: to_text(a["가"]).endswith(to_text(a["로"])),
        ("다듬다", signature_of(["를"])): lambda a: to_text(a["를"]).strip(),
        ("자르다", signature_of(["를", "로"])): split_text,
        ("정렬하다", signature_of(["를"])): sort_in_place,
        ("정렬하다", signature_of(["를", "로"])): sort_in_place,
        ("읽다", signature_of(["를"])): read_file,
        ("입력받다", signature_of([])): read_line,
        ("열다", signature_of(["를"])): open_file,
        ("쓰다", signature_of(["에", "를"])): write_file,
        ("가져오다", signature_of(["를"])): lambda a: None,
    }
