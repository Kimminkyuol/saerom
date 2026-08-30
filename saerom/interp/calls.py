"""동사를 찾아 부르는 일."""
from ..errors import (ArithmeticError_, Frame, NameError_, ParticleError,
                      RecursionError_, SaeromError, ValueError_,
                      describe_signature, quote, suggest)
from .values import (Break, Continue, Module, NativeFunction, Return,
                     kind_of, show, signature_of)

MAX_DEPTH = 200

NAMESPACE = frozenset(("모듈", "의"))


class CallMixin:
    """이름과 조사로 동사를 찾고, 매개변수에 묶어 실행한다."""

    def lookup(self, name, particles):
        signature = signature_of(particles)
        return self.functions.get((name, signature)) or self.builtins.get((name, signature))

    def signatures_of(self, name):
        return [signature for verb, signature in
                list(self.functions) + list(self.builtins) if verb == name]

    def apply(self, name, args, line=None):
        """이름과 조사로 동사를 골라 부른다. NAMESPACE 자리는 인자가 아니라
        이름공간이다: '수학의 제곱근구한 값'."""
        pairs = list(args.items()) if isinstance(args, dict) else list(args)
        particles, module = [], None
        for particle, value in pairs:
            particles.append(particle)
            if module is None and particle in NAMESPACE and isinstance(value, Module):
                module = value
        if module is not None:
            rest = [(p, v) for p, v in pairs if v is not module]
            key = (name, signature_of(tuple(p for p, _ in rest)))
            function = module.functions.get(key)
            if function is None:
                raise self.unknown_module_call(module, name, dict(rest), line)
            return self.invoke(function, rest, line)

        signature = signature_of(tuple(particles))
        function = self.functions.get((name, signature))
        if function is not None:
            return self.invoke(function, pairs, line)

        handler = self.builtins.get((name, signature))
        if handler is None:
            raise self.unknown_call(name, dict(pairs), line)

        try:
            return handler(dict(pairs))
        except (SaeromError, Break, Continue, Return):
            raise
        except ZeroDivisionError:
            raise ArithmeticError_("0으로 나눌 수 없음", line)
        except (IndexError, KeyError):
            raise ValueError_(f"'{name}'에 없는 자리", line)
        except (TypeError, ValueError, AttributeError) as error:
            shown = ", ".join(f"{kind_of(v)} {show(v)}" for v in args.values())
            raise ValueError_(f"'{name}'의 인자가 맞지 않음: {shown}", line)

    def unknown_module_call(self, module, name, args, line):
        used = ", ".join(f"'{p}'" for p in args if p) or "없음"
        ways = [signature for verb, signature in module.functions if verb == name]
        if ways:
            shown = " / ".join(describe_signature(name, s) for s in ways)
            return ParticleError(
                f"모듈 '{module.name}'의 '{name}'를 조사 {used}로 부를 수 없음", line,
                hint=f"조사: {shown}")
        close = suggest(name, {verb for verb, _ in module.functions})
        return NameError_(
            f"모듈 '{module.name}'에 동사 '{name}' 없음", line,
            hint=f"비슷한 이름: '{close}'" if close else None)

    def unknown_call(self, name, args, line):
        used = ", ".join(f"'{p}'" for p in args if p) or "없음"
        known = self.signatures_of(name)
        if not known:
            every = {verb for verb, _ in self.functions} | \
                    {verb for verb, _ in self.builtins}
            close = suggest(name, every)
            return NameError_(
                f"동사 '{name}' 정의되지 않음", line,
                hint=f"비슷한 이름: '{close}'" if close else None)

        ways = " / ".join(describe_signature(name, sig) for sig in known)
        missing = [dict(sig).keys() - set(args) for sig in known
                   if set(args) < dict(sig).keys()]
        if missing:
            slots = ", ".join(f"'{p}'" for p in sorted(missing[0]) if p)
            return ParticleError(
                f"'{name}' 호출에 조사 {slots} 없음", line, hint=f"조사: {ways}")
        return ParticleError(
            f"'{name}'를 조사 {used}로 부를 수 없음", line, hint=f"조사: {ways}")

    def invoke(self, function, args, line=None):
        """동사 하나를 실행한다. 반복문의 깊이는 동사를 넘지 않는다."""
        pairs = list(args.items()) if isinstance(args, dict) else list(args)
        if len(self.stack) >= MAX_DEPTH:
            raise RecursionError_(
                f"'{function.name}' 재귀가 {MAX_DEPTH}단계를 넘음", line)
        if isinstance(function, NativeFunction):
            return self.finish(function, self.invoke_native(function, pairs, line),
                               line)
        outer = self.scope
        outer_space = (self.globals, self.functions, self.types)
        if function.module is not None:
            self.globals = function.module.values
            self.functions = function.module.functions
            self.types = function.module.types
        self.scope = function.bind(pairs)
        outer_loops, self.loops = self.loops, 0
        self.stack.append(Frame(function.name, line))
        try:
            self.run(function.body)
            result = None
        except Return as returned:
            result = returned.value
        except SaeromError as error:
            error.frames.append(Frame(function.name, line))
            raise
        finally:
            self.stack.pop()
            self.scope = outer
            self.loops = outer_loops
            self.globals, self.functions, self.types = outer_space

        return self.finish(function, result, line)

    def finish(self, function, result, line):
        """술어는 '~ㄴ지'에 답하는 것이므로 참이나 거짓만 낸다."""
        if function.kind == "predicate" and not isinstance(result, bool):
            if result is None:
                raise ValueError_(
                    f"술어 {quote(function.name)} 아무 값도 돌려주지 않음", line)
            raise ValueError_(
                f"술어 {quote(function.name)} 낸 값이 논리값이 아님: "
                f"{kind_of(result)} {show(result)}", line)
        return result

    def invoke_native(self, function, pairs, line):
        """파이썬으로 적은 동사를 부른다."""
        bound = function.bind(pairs)
        args = [bound[index] for index in range(len(function.params))]
        self.stack.append(Frame(function.name, line))
        try:
            return function.call(*args)
        except SaeromError as error:
            error.frames.append(Frame(function.name, line))
            if error.line is None:
                error.line = line
            raise
        except ZeroDivisionError:
            raise ArithmeticError_("0으로 나눌 수 없음", line)
        except Exception as error:
            raise ValueError_(
                f"'{function.name}'가 파이썬 오류를 냄: "
                f"{type(error).__name__}: {error}", line)
        finally:
            self.stack.pop()

    def head_particles(self, verb, given):
        found = []
        for name, signature in list(self.functions) + list(self.builtins):
            names = dict(signature).keys()
            if name == verb and given <= names and len(names) == len(given) + 1:
                found += list(names - given)
        return found or ["를"]
