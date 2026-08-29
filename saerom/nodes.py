"""Syntax tree nodes, named after the terms in docs/rules.md."""


class Node:
    def __init__(self, **fields):
        self.__dict__.update(fields)

    def __repr__(self):
        inner = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"{type(self).__name__}({inner})"


# --- 표현 ---
class Literal(Node): pass       # 리터럴
class Name(Node): pass          # 이름 참조
class ListExpr(Node): pass      # 목록식
class Template(Node): pass      # 보간 — "{이름}님"
class Property(Node): pass      # 필드 접근 — X의 Y
class Call(Node): pass          # 호출 — <구절들> <동사>ㄴ 값
class PassiveCall(Node): pass   # 피동 호출 — 정렬된 목록
class Filter(Node): pass        # 필터 — <관형절> A들
class MapExpr(Node): pass       # 맵 — A들을 각각 ~한 값들
class FoldExpr(Node): pass      # 리듀스 — A들을 모두 ~한 값
class SelectExpr(Node): pass    # 최대·최소 — A들 중 가장 ~ㄴ 값
class QuantExpr(Node): pass     # 모두/하나라도 ~ㄴ지
class RecordLit(Node): pass     # 구조체 만들기
class SortSpec(Node): pass      # 정렬 기준 — <관형절> 순으로

# --- 문장 ---
class Declare(Node): pass       # 선언문
class ExecStmt(Node): pass      # 실행문
class IfStmt(Node): pass        # 조건문
class LoopStmt(Node): pass      # 반복문
class ExprStmt(Node): pass      # 표현문
class BreakStmt(Node): pass     # 중단문
class ContinueStmt(Node): pass  # 계속문
class DefineStmt(Node): pass    # 정의문
class ReturnStmt(Node): pass    # 반환문
class RecordType(Node): pass    # 구조체 선언
class TryStmt(Node): pass       # 예외처리문
class WithStmt(Node): pass      # 자원문
class RaiseStmt(Node): pass     # 예외발생문
class ImportStmt(Node): pass    # 가져오기문

AND, OR = "그리고", "또는"
