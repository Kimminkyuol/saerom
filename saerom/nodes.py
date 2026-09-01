"""구문트리의 마디."""


class Node:
    def __init__(self, **fields):
        self.__dict__.update(fields)

    def __repr__(self):
        inner = ", ".join(f"{k}={v!r}" for k, v in self.__dict__.items())
        return f"{type(self).__name__}({inner})"


class Literal(Node): """리터럴"""
class Name(Node): """이름 참조"""
class ListExpr(Node): """목록식"""
class Template(Node): """보간"""
class Property(Node): """필드 접근"""
class Call(Node): """호출"""
class PassiveCall(Node): """피동 호출"""
class DictExpr(Node): """사전식"""

class Declare(Node): """선언문"""
class ExecStmt(Node): """실행문"""
class IfStmt(Node): """조건문"""
class LoopStmt(Node): """반복문"""
class ExprStmt(Node): """표현문"""
class BreakStmt(Node): """중단문"""
class ContinueStmt(Node): """계속문"""
class DefineStmt(Node): """정의문"""
class NounDef(Node): """파생 필드 정의"""
class ReturnStmt(Node): """반환문"""
class TryStmt(Node): """예외처리문"""
class WithStmt(Node): """자원문"""
class RaiseStmt(Node): """예외발생문"""
class ImportStmt(Node): """가져오기문"""

AND, OR = "그리고", "또는"
