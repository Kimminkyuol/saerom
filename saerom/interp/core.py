"""실행기."""
import sys

from ..errors import NameError_, Raised, SaeromError, quote, suggest
from ..nodes import (BreakStmt, ContinueStmt, Declare, DefineStmt, ExecStmt,
                     ExprStmt, IfStmt, ImportStmt, LoopStmt, Name, Property,
                     RaiseStmt, RecordType, ReturnStmt, TryStmt, WithStmt)
from ..parser import parse_file
from ..parser.native import load as load_native
from . import builtins as builtin_table
from .calls import MAX_DEPTH
from .expressions import ExpressionMixin
from .values import (Break, Continue, Function, Handle, Module, NativeFunction,
                     Record, Return, check_numbers, to_text, truthy)


class Interpreter(ExpressionMixin):
    """구문트리를 실행한다."""

    TYPE_VALUES = ("정수", "실수", "문자열", "논리값",
                   "정수들", "실수들", "문자열들", "논리값들")

    def __init__(self, out=sys.stdout):
        sys.setrecursionlimit(max(sys.getrecursionlimit(), MAX_DEPTH * 40))
        self.out = out
        self.globals = {name: name for name in self.TYPE_VALUES}
        self.scope = self.globals
        self.functions = {}
        self.types = {}
        self.items = []
        self.stack = []
        self.modules = {}
        self.builtins = builtin_table.build(self)
        self.empty_slots = {}
        self.verb_names = set()
        self.verb_names_key = None
        self.loops = 0

    def run(self, statements):
        for statement in statements:
            self.execute(statement)

    def execute(self, node):
        """EXECUTE 에 적힌 갈래대로 문장 하나를 실행한다."""
        found = self.EXECUTE.get(type(node))
        if found is None:
            raise SaeromError(f"실행할 수 없는 문장: {type(node).__name__}",
                              getattr(node, "line", None))
        found(self, node)

    def run_define(self, node):
        function = Function(node.name, node.kind, node.params, node.body)
        self.functions[(node.name, function.signature)] = function

    def run_record_type(self, node):
        self.types[node.name] = [name for name, _ in node.fields]

    def run_declare(self, node):
        self.assign(node.target, self.evaluate(node.value))

    def run_exec(self, node):
        for call in node.calls:
            self.evaluate(call)

    def run_return(self, node):
        raise Return(self.evaluate(node.value))

    def run_raise(self, node):
        raise Raised(to_text(self.evaluate(node.message)), node.line)

    def run_break(self, node):
        self.in_loop("빠져나가다", node)
        raise Break()

    def run_continue(self, node):
        self.in_loop("넘어가다", node)
        raise Continue()

    def in_loop(self, verb, node):
        """중단문과 계속문은 반복문 안에서만 뜻이 있다."""
        if not self.loops:
            raise SaeromError(f"{quote(verb)} 반복문 안이 아님", node.line)

    def run_if(self, node):
        for test, body in node.branches:
            if truthy(self.evaluate(test)):
                self.run(body)
                return
        if node.otherwise is not None:
            self.run(node.otherwise)

    EXECUTE = {
        Declare: run_declare,
        ExecStmt: run_exec,
        ExprStmt: lambda self, node: self.evaluate(node.value),
        IfStmt: run_if,
        LoopStmt: lambda self, node: self.run_loop(node),
        TryStmt: lambda self, node: self.run_try(node),
        WithStmt: lambda self, node: self.run_with(node),
        DefineStmt: run_define,
        RecordType: run_record_type,
        ImportStmt: lambda self, node: self.run_import(node),
        ReturnStmt: run_return,
        RaiseStmt: run_raise,
        BreakStmt: run_break,
        ContinueStmt: run_continue,
    }

    def load_module(self, name, path):
        if path in self.modules:
            return self.modules[path]
        if path.endswith(".py"):
            return self.load_native_module(name, path)
        statements, _, _ = parse_file(path)
        inner = Interpreter(self.out)
        inner.modules = self.modules
        module = Module(name, inner.globals, inner.functions, inner.types)
        self.modules[path] = module
        inner.run(statements)
        for function in inner.functions.values():
            function.module = module
        return module

    def load_native_module(self, name, path):
        """파이썬으로 적은 모듈. 내놓은 것들이 그대로 모듈의 알맹이가 된다."""
        native = load_native(path)
        module = Module(name, dict(native.values), {}, {})
        for export in native.exports:
            function = NativeFunction(export.name, export.kind,
                                      export.particles, export.call, module)
            module.functions[(function.name, function.signature)] = function
        self.modules[path] = module
        return module

    def run_import(self, node):
        module = self.load_module(node.module, node.path)
        if node.names is None:
            self.globals[node.module] = module
            return
        for name in node.names:
            taken = False
            for (verb, signature), function in module.functions.items():
                if verb == name:
                    self.functions[(verb, signature)] = function
                    taken = True
            if name in module.values:
                self.globals[name] = module.values[name]
                taken = True
            if name in module.types:
                self.types[name] = module.types[name]
                taken = True
            if not taken:
                close = suggest(name, {verb for verb, _ in module.functions}
                                | set(module.values) | set(module.types))
                raise NameError_(
                    f"모듈 '{node.module}'에 '{name}' 없음", node.line,
                    hint=f"비슷한 이름: '{close}'" if close else None)

    def assign(self, target, value):
        if isinstance(target, Name):
            self.scope[target.name] = value
            return
        if isinstance(target, Property):
            owner = self.evaluate(target.owner)
            if not isinstance(owner, Record):
                raise SaeromError(f"필드를 매길 수 없음: '{target.field}'")
            owner.fields[target.field] = value
            return
        raise SaeromError("값을 매길 수 없는 자리")

    def run_try(self, node):
        try:
            if node.call is not None:
                self.scope["결과"] = self.evaluate(node.call)
            self.run(node.body)
        except (Raised, SaeromError) as error:
            reason = getattr(error, "message", str(error))
            for expected, body in node.handlers:
                if expected is None or self.evaluate(expected) == reason:
                    self.scope["이유"] = reason
                    self.run(body)
                    break
            else:
                raise
        finally:
            if node.ensure:
                self.run(node.ensure)

    def run_with(self, node):
        handle = self.evaluate(node.call)
        self.scope[node.name] = handle
        try:
            self.run(node.body)
        finally:
            if isinstance(handle, Handle):
                handle.stream.close()

    def run_loop(self, node):
        self.loops += 1
        outer = self.scope.get("번째")
        try:
            if node.kind == "while":
                self.repeat_while(node)
            else:
                self.repeat_over(node, self.loop_values(node))
        finally:
            self.loops -= 1
            if outer is None:
                self.scope.pop("번째", None)
            else:
                self.scope["번째"] = outer

    def repeat_while(self, node):
        index = 1
        while True:
            self.scope["번째"] = index
            if not truthy(self.evaluate(node.test)):
                return
            if not self.run_body(node.body, index):
                return
            index += 1

    def repeat_over(self, node, values):
        for index, value in enumerate(values, 1):
            self.scope[node.variable] = value
            if not self.run_body(node.body, index):
                return

    def loop_values(self, node):
        if node.kind != "range":
            values = self.evaluate(node.source)
            if not isinstance(values, list):
                raise SaeromError("'마다' 앞이 목록이 아님", node.line)
            return values

        start, stop = self.evaluate(node.start), self.evaluate(node.stop)
        step = self.evaluate(node.step) if node.step is not None else 1
        check_numbers("반복하다", start, stop, step)
        step = abs(step) or 1
        down = start > stop
        values, current = [], start
        while (current >= stop) if down else (current <= stop):
            values.append(current)
            current += -step if down else step
        return values

    def run_body(self, body, index):
        self.scope["번째"] = index
        try:
            self.run(body)
        except Break:
            return False
        except Continue:
            pass
        return True

    def build_record(self, node):
        declared = self.types.get(node.type)
        if declared is None:
            raise NameError_(f"구조체 '{node.type}' 정의되지 않음", node.line)
        given = [name for name, _ in node.fields]
        listed = "필드: " + ", ".join(declared)
        for name in given:
            if name not in declared:
                raise NameError_(f"구조체 '{node.type}'에 없는 필드: '{name}'",
                                 node.line, hint=listed)
        for name in declared:
            if name not in given:
                raise NameError_(
                    f"구조체 '{node.type}'의 필드 {quote(name, 'subject')} 빠짐",
                    node.line, hint=listed)
        values = {name: self.evaluate(value) for name, value in node.fields}
        return Record(node.type, [(name, values[name]) for name in declared])
