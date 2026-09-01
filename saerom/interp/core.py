"""실행기."""
import sys
from contextlib import contextmanager

from ..errors import NameError_, Raised, SaeromError, quote, suggest
from ..nodes import (BreakStmt, ContinueStmt, Declare, DefineStmt, ExecStmt,
                     ExprStmt, IfStmt, ImportStmt, LoopStmt, Name, NounDef,
                     Property, RaiseStmt, ReturnStmt, TryStmt, WithStmt)
from ..parser import parse_file
from ..parser.native import load as load_native
from . import builtins as builtin_table
from .calls import MAX_DEPTH, checked_value
from .expressions import ExpressionMixin
from .values import (Break, Continue, Function, Handle, Module, NativeFunction,
                     Return, check_numbers, kind_of, to_text, truthy)


class Interpreter(ExpressionMixin):
    """구문트리를 실행한다."""

    TYPE_VALUES = ("정수", "실수", "문자열", "논리값")

    def __init__(self, out=sys.stdout):
        sys.setrecursionlimit(max(sys.getrecursionlimit(), MAX_DEPTH * 40))
        self.out = out
        self.globals = {name: name for name in self.TYPE_VALUES}
        self.scope = self.globals
        self.functions = {}
        self.nouns = {}
        self.stack = []
        self.modules = {}
        self.builtins = builtin_table.build(self)
        self.verb_names = set()
        self.verb_names_key = None
        self.loops = 0

    def run(self, statements):
        for statement in statements:
            self.execute(statement)

    def execute(self, node):
        """EXECUTE 에 적힌 갈래대로 문장 하나를 실행한다.

        자리를 모르는 채로 올라온 오류는 이 문장의 자리를 얻는다.
        """
        found = self.EXECUTE.get(type(node))
        if found is None:
            raise SaeromError(f"실행할 수 없는 문장: {type(node).__name__}",
                              getattr(node, "line", None))
        try:
            found(self, node)
        except SaeromError as error:
            raise error.locate(node)

    def run_define(self, node):
        function = Function(node.name, node.kind, node.params, node.body)
        self.functions[(node.name, function.signature)] = function

    def run_noun_def(self, node):
        self.nouns[node.name] = Function(node.name, "noun",
                                         [("의", node.owner)], node.body)

    def run_declare(self, node):
        self.assign(node.target, self.evaluate(node.value))

    def run_exec(self, node):
        for call in node.calls:
            self.evaluate(call)

    def run_return(self, node):
        if not self.stack:
            raise SaeromError(f"{quote('돌려주다')} 정의문 안이 아님", node.line)
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
        NounDef: run_noun_def,
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
        module = Module(name, inner.globals, inner.functions, inner.nouns)
        self.modules[path] = module
        inner.run(statements)
        for function in list(inner.functions.values()) + list(inner.nouns.values()):
            if function.module is None:
                function.module = module
        return module

    def load_native_module(self, name, path):
        """파이썬으로 적은 모듈. 내놓은 것들이 그대로 모듈의 알맹이가 된다."""
        native = load_native(path)
        module = Module(name, {key: checked_value(f"{name}의 {key}", value)
                               for key, value in native.values.items()}, {}, {})
        for export in native.exports:
            function = NativeFunction(export.name, export.kind,
                                      export.particles, export.call, module)
            if export.kind == "noun":
                module.nouns[function.name] = function
            else:
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
            if name in module.nouns:
                self.nouns[name] = module.nouns[name]
                taken = True
            if name in module.values:
                self.globals[name] = module.values[name]
                taken = True
            if not taken:
                close = suggest(name, {verb for verb, _ in module.functions}
                                | set(module.nouns) | set(module.values))
                raise NameError_(
                    f"모듈 '{node.module}'에 '{name}' 없음", node.line,
                    hint=f"비슷한 이름: '{close}'" if close else None)

    def assign(self, target, value):
        if isinstance(target, Name):
            self.scope[target.name] = value
            return
        if isinstance(target, Property):
            owner = self.evaluate(target.owner)
            if not isinstance(owner, dict):
                raise SaeromError(
                    f"{kind_of(owner)}에 열쇠 {quote(target.field, 'object')} "
                    f"매길 수 없음")
            owner[target.field] = value
            return
        raise SaeromError("값을 매길 수 없는 자리")

    def bind(self, name, value):
        """블록이 여는 이름. 값이 없으면 그 이름은 열리지 않는다."""
        if value is None:
            self.scope.pop(name, None)
        else:
            self.scope[name] = value

    @contextmanager
    def opened(self, name):
        """구문이 여는 이름은 그 블록 안에서만 산다."""
        outer = self.scope.get(name)
        try:
            yield
        finally:
            if outer is None:
                self.scope.pop(name, None)
            else:
                self.scope[name] = outer

    def run_try(self, node):
        try:
            self.run(node.body)
        except (Raised, SaeromError) as error:
            if node.handler is None:
                raise
            if node.catch is None:
                self.run(node.handler)
                return
            with self.opened(node.catch):
                self.scope[node.catch] = getattr(error, "message", str(error))
                self.run(node.handler)
        finally:
            if node.ensure:
                self.run(node.ensure)

    def run_with(self, node):
        handle = self.evaluate(node.call)
        try:
            with self.opened(node.name):
                self.bind(node.name, handle)
                self.run(node.body)
        finally:
            if isinstance(handle, Handle):
                handle.stream.close()

    def run_loop(self, node):
        self.loops += 1
        try:
            if node.kind == "while":
                self.repeat_while(node)
            else:
                self.repeat_over(node, self.loop_values(node))
        finally:
            self.loops -= 1

    def repeat_while(self, node):
        while truthy(self.evaluate(node.test)):
            if not self.run_body(node.body):
                return

    def repeat_over(self, node, values):
        for value in values:
            self.scope[node.variable] = value
            if not self.run_body(node.body):
                return

    def loop_values(self, node):
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

    def run_body(self, body):
        try:
            self.run(body)
        except Break:
            return False
        except Continue:
            pass
        return True
