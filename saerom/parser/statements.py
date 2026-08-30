"""문장 하나하나."""
import os

from ..errors import SaeromError, SyntaxError_, ending_name
from ..nodes import (BreakStmt, Call, ContinueStmt, Declare, DefineStmt, ExecStmt,
                     ExprStmt, Filter, FoldExpr, IfStmt, ImportStmt, Literal,
                     LoopStmt, MapExpr, Name, PassiveCall, Property, RaiseStmt,
                     RecordLit, RecordType, ReturnStmt, SelectExpr, TryStmt,
                     WithStmt)
from ..words import BUILTIN_SIGNATURES
from .modules import ordered, parse_file, resolve_module
from .native import load as load_native
from .phrases import PhraseParser


class StatementParser(PhraseParser):
    """선언문·조건문·반복문·정의문·모듈."""

    def statement(self):
        token = self.peek()

        if token.kind == "keyword" and token.value == "만약":
            return self.if_statement()

        if self.looks_like_definition():
            return self.definition()

        if (token.kind in ("number", "string")
                or (token.kind == "keyword" and token.value in ("참", "거짓"))):
            if self.peek(1).kind == "newline":
                value = self.primary()
                self.expect("newline")
                return ExprStmt(value=value, line=token.line)

        if self.looks_like_import():
            return self.import_statement()

        if self.looks_like_raise():
            return self.raise_statement()

        target = self.try_target()
        if target is not None:
            return self.declaration(target, token.line)

        return self.exec_or_loop()

    def try_target(self):
        """A 선언문 target: <이름> or <이름>의<속성>... followed by 은/는."""
        i = self.pos
        if self.tokens[i].kind != "name":
            return None
        node = Name(name=self.tokens[i].value)
        i += 1
        while (self.tokens[i].kind == "particle" and self.tokens[i].value == "의"
               and self.tokens[i + 1].kind == "name"):
            node = Property(owner=node, field=self.tokens[i + 1].value)
            i += 2
        if self.tokens[i].kind == "particle" and self.tokens[i].extra == "topic":
            self.pos = i + 1
            return node
        return None

    def declaration(self, target, line):
        # 틀 선언 / 블록 틀 만들기:  X는 이런 (것|<틀>)이다:
        if self.at("keyword", "이런"):
            self.next()
            type_name = self.expect("name").value
            self.expect("copula")
            body = self.block()
            if type_name == "것":
                self.types.add(target.name)
                return RecordType(name=target.name, fields=self.record_fields(body),
                                  line=line)
            return Declare(target=target, line=line,
                           value=RecordLit(type=type_name, fields=self.record_fields(body),
                                           line=line))

        value = self.value_until_copula()
        self.expect("symbol", ".")
        self.expect("newline")
        return Declare(target=target, value=value, line=line)

    @staticmethod
    def record_fields(body):
        fields = []
        for statement in body:
            if not isinstance(statement, Declare) or not isinstance(statement.target, Name):
                raise SyntaxError_("구조체 안이 선언문이 아님",
                                  getattr(statement, "line", None))
            fields.append((statement.target.name, statement.value))
        return fields

    def looks_like_definition(self):
        end = self.line_end()
        return (end - self.pos >= 3
                and self.tokens[end - 1].kind == "symbol" and self.tokens[end - 1].value == ":"
                and self.tokens[end - 2].kind == "particle" and self.tokens[end - 2].extra == "topic"
                and self.tokens[end - 3].kind == "name" and self.tokens[end - 3].value == "것")

    def looks_like_raise(self):
        end = self.line_end()
        return any(self.tokens[i].kind == "keyword" and self.tokens[i].value == "오류"
                   for i in range(self.pos, end))

    def looks_like_import(self):
        end = self.line_end()
        return (end - self.pos >= 3
                and self.tokens[end - 1].value == "."
                and self.tokens[end - 2].kind == "verb"
                and self.tokens[end - 2].value == "가져오다")

    def import_name(self):
        """가져올 것의 사전형. 술어는 '음수이다' 처럼 '이다'로 끝난다."""
        token = self.peek()
        if token.kind not in ("name", "verb"):
            raise SyntaxError_(f"가져올 이름이 아님: {self.describe(token)}",
                               **self.where(token))
        self.next()
        if (token.kind == "name" and self.at("copula")
                and self.peek().extra[1] == "final"):
            self.next()
            return token.value + "이다"
        return token.value

    def import_statement(self):
        """<모듈>을 가져온다.  /  <모듈>에서 <이름>과 <이름>을 가져온다."""
        start = self.peek()
        first = self.import_name()
        particle = self.expect("particle")
        names = None
        module = first
        if particle.value == "에서":
            names = [self.import_name()]
            while self.at("particle") and self.peek().extra == "conj":
                self.next()
                names.append(self.import_name())
            self.expect("particle")
        self.expect("verb", "가져오다")
        self.expect("symbol", ".")
        self.expect("newline")

        path = resolve_module(module, self.base_dir)
        if path is None:
            raise SyntaxError_(f"모듈 파일이 없음: {module}.sr, {module}.py",
                               **self.where(start))
        if path.endswith(".py"):
            try:
                other = load_native(path)
            except SaeromError as error:
                if error.line is None:
                    error.line = start.line
                raise
        else:
            _, other, _ = parse_file(path)
        self.absorb(other, module, names)
        return ImportStmt(module=module, names=names, path=os.path.abspath(path),
                          line=start.line)

    def absorb(self, other, module, names):
        """가져온 쪽의 조사 자리를 물려받는다. 그래야 구절을 몇 개까지
        가져갈지 알 수 있다 (docs/rules.md 3.3)."""
        if names is None:
            self.known |= {module}
            self.module_names.add(module)
            for verb, signatures in other.signatures.items():
                if verb in BUILTIN_SIGNATURES:
                    continue
                self.signatures.setdefault(verb, []).extend(
                    tuple(signature) for signature in signatures)
            return
        self.known |= set(names)
        for name in names:
            if name in other.signatures:
                self.signatures.setdefault(name, []).extend(other.signatures[name])
            if name in other.types:
                self.types.add(name)

    def raise_statement(self):
        line = self.peek().line
        message = self.primary()
        if self.at("copula"):
            self.next()
        self.expect("keyword", "오류")
        self.expect("particle")
        self.expect("verb", "내다")
        self.expect("symbol", ".")
        self.expect("newline")
        return RaiseStmt(message=message, line=line)

    def definition(self):
        start = self.peek()
        params = []
        while True:
            token = self.peek()

            if token.kind == "verb":
                pos, ending, surface = token.extra
                if ending not in ("adnominal_pres", "adnominal_past"):
                    raise SyntaxError_(
                        f"정의의 머리가 '-는' 이나 '-ㄴ'이 아님: {ending_name(ending)}",
                        token.line)
                self.next()
                name = token.value
                kind = "verb"
                break

            if (token.kind == "name" and self.peek(1).kind == "copula"
                    and self.peek(1).extra[1] == "adnominal_past"):
                name, kind = token.value + "이다", "predicate"
                self.pos += 2
                break

            if token.kind != "name":
                raise SyntaxError_(
                    f"정의의 머리가 이름과 조사가 아님: "
                    f"{self.describe(token)}", **self.where(token),)
            self.next()
            particle = self.expect("particle")
            params.append((particle.value, token.value))

        self.expect("name", "것")
        self.expect("particle")
        self.signatures.setdefault(name, []).append(ordered(p for p, _ in params))
        return DefineStmt(name=name, kind=kind, params=params,
                          body=self.block(), line=start.line)

    def if_statement(self):
        branches, otherwise = [], None
        self.expect("keyword", "만약")
        branches.append((self.condition(), self.block()))
        while True:
            if self.at("keyword", "아니고"):
                self.next()
                self.expect("keyword", "만약")
                branches.append((self.condition(), self.block()))
            elif self.at("keyword", "아니면"):
                self.next()
                otherwise = self.block()
                break
            else:
                break
        return IfStmt(branches=branches, otherwise=otherwise)

    def looks_like_record_end(self):
        """`... 인 <틀이름>이다.` -- a one-line 틀 만들기.

        The name must be a declared 틀, otherwise `반이 반번호인 학생들이다`
        would read as a record instead of a 걸러내기.
        """
        end = self.line_end()
        return (end - self.pos >= 3
                and self.tokens[end - 1].kind == "symbol" and self.tokens[end - 1].value == "."
                and self.tokens[end - 2].kind == "copula"
                and self.tokens[end - 2].extra[1] == "final"
                and self.tokens[end - 3].kind == "name"
                and self.tokens[end - 3].value in self.types
                and self.tokens[end - 4].kind == "copula"
                and self.tokens[end - 4].extra[1] == "adnominal_past")

    def record_literal(self, slots):
        """<속성>이 <값>이고 ... <속성>이 <값>인 <틀>이다."""
        line = self.peek().line
        fields = []
        pending = list(slots)
        adverbs = []
        while True:
            token = self.peek()
            if token.kind == "copula" and token.extra[1] in ("conjunctive", "adnominal_past"):
                ending = token.extra[1]
                self.next()
                if len(pending) != 2 or not isinstance(pending[0][1], Name):
                    raise SyntaxError_("구조체 필드가 '<이름>이 <값>' 짝이 아님", line)
                fields.append((pending[0][1].name, pending[1][1]))
                pending = []
                if ending == "adnominal_past":
                    type_name = self.expect("name").value
                    self.expect("copula")
                    return RecordLit(type=type_name, fields=fields, line=line)
                continue
            if token.kind in ("verb", "copula"):
                info = self.take_verb()
                value = self.reduce(pending[1:], adverbs, info)
                pending = pending[:1]
                pending = self.push(pending, value)
                adverbs = []
                continue
            if token.kind == "adverb":
                adverbs.append(token.value); self.next(); continue
            pending = self.push(pending, self.primary())

    def exec_or_loop(self):
        slots, adverbs, calls = [], [], []
        aux = None
        while True:
            token = self.peek()

            if token.kind in ("verb", "copula"):
                info = self.take_verb()

                if info.name == "반복하다" and info.ending == "final":
                    return self.loop(slots, adverbs)

                if info.name in ("빠져나가다", "넘어가다") and info.ending == "final":
                    self.expect("symbol", ".")
                    self.expect("newline")
                    node = BreakStmt if info.name == "빠져나가다" else ContinueStmt
                    return node(line=info.line)

                if info.name == "돌려주다" and info.ending == "final":
                    self.expect("symbol", ".")
                    self.expect("newline")
                    if len(slots) != 1:
                        raise SyntaxError_("돌려줄 값이 하나가 아님", info.line)
                    return ReturnStmt(value=slots[0][1], line=info.line)

                if info.ending == "auxiliary":
                    aux = info
                    continue

                if aux is not None and info.name in ("보다", "두다") and info.ending == "final":
                    if info.name == "보다":
                        # '해 본다:' 는 블록 전체를 시도한다.
                        call = None if (aux.name == "하다" and not slots) else Call(
                            verb=aux.name, slots=slots, adverbs=[], negated=False,
                            tail=None, line=aux.line)
                        return self.try_statement(call, aux.line)
                    # 자원문의 '로' 자리는 열어 둔 것을 묶을 이름이다.
                    name = "파일"
                    kept = []
                    for particle, expr in slots:
                        if particle == "로" and isinstance(expr, Name):
                            name = expr.name
                        else:
                            kept.append((particle, expr))
                    call = Call(verb=aux.name, slots=kept, adverbs=[],
                                negated=False, tail=None, line=aux.line)
                    return WithStmt(call=call, name=name, body=self.block(),
                                    line=aux.line)

                if info.ending == "nominal":
                    slots = self.push(slots, Literal(value=info.surface))
                    continue

                if info.ending in ("adnominal_past", "adnominal_pres", "interrogative"):
                    value = self.reduce(slots, adverbs, info)
                    slots = self.push(self._kept, value)
                    adverbs = []
                    continue

                if info.ending in ("final", "conjunctive"):
                    calls.append(Call(verb=info.name, slots=slots, adverbs=adverbs,
                                      negated=info.negated, tail=None,
                                      **self.where_verb(info)))
                    slots, adverbs = [], []
                    if info.ending == "final":
                        self.expect("symbol", ".")
                        self.expect("newline")
                        return ExecStmt(calls=calls, line=info.line)
                    continue

                raise SyntaxError_(
                    f"실행문에 쓸 수 없는 어미: {ending_name(info.ending)}", info.line)

            if token.kind == "adverb":
                adverbs.append(token.value)
                self.next()
                continue

            if token.kind == "keyword" and token.value == "간격":
                self.next()
                if self.at("particle") and self.peek().value == "의":
                    self.next()
                if not slots:
                    raise SyntaxError_("'간격' 앞에 수가 없음", **self.where(token))
                slots[-1] = ("간격", slots[-1][1])
                continue

            if token.kind == "keyword" and token.value == "동안":
                self.next()
                self.expect("verb", "반복하다")
                if len(slots) != 1:
                    raise SyntaxError_("'동안' 앞의 조건이 하나가 아님", token.line)
                return LoopStmt(kind="while", test=slots[0][1], body=self.block(),
                                line=token.line)

            slots = self.push(slots, self.primary())

    def try_statement(self, call, line):
        body = self.block()
        handlers, ensure = [], None
        while True:
            if self.at("keyword", "끝으로"):
                self.next()
                ensure = self.block()
                break
            saved = self.pos
            reason = None
            if self.peek().kind == "string":
                reason = Literal(value=self.next().value)
                if self.at("particle"):
                    self.next()
            if self.at("verb", "실패하다") and self.peek().extra[1] == "conditional":
                self.next()
                handlers.append((reason, self.block()))
                continue
            self.pos = saved
            break
        return TryStmt(call=call, body=body, handlers=handlers, ensure=ensure,
                       line=line)

    def loop(self, slots, adverbs):
        start = stop = step = source = variable = None
        for particle, expr in slots:
            if particle == "부터":
                start = expr
            elif particle == "까지":
                stop = expr
            elif particle == "간격":
                step = expr
            elif particle == "마다":
                source = expr
                name = self.collection_name(expr)
                if name is None:
                    raise SyntaxError_("'마다' 앞이 목록 이름이 아님")
                variable = name[:-1] if name.endswith("들") else name
        if variable is None:
            raise SyntaxError_("반복문에 '마다'가 없음")
        body = self.block()
        if start is not None:
            return LoopStmt(kind="range", variable=variable, start=start, stop=stop,
                            step=step, body=body)
        return LoopStmt(kind="each", variable=variable, source=source, body=body)

    @classmethod
    def collection_name(cls, expr):
        """The name a 반복문 takes its 원소 from."""
        if isinstance(expr, Name):
            return expr.name
        if isinstance(expr, Property):
            return expr.field
        if isinstance(expr, Filter):
            return cls.collection_name(expr.source) or expr.item + "들"
        if isinstance(expr, PassiveCall):
            return cls.collection_name(expr.head)
        if isinstance(expr, (MapExpr, FoldExpr, SelectExpr)):
            return cls.collection_name(expr.source)
        return None
