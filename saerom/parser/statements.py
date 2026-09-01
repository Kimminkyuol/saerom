"""문장 하나하나."""
import os

from ..errors import SaeromError, SyntaxError_, ending_name, quote
from ..nodes import (BreakStmt, Call, ContinueStmt, Declare, DefineStmt, ExecStmt,
                     ExprStmt, IfStmt, ImportStmt, LoopStmt, Name, NounDef,
                     Property, RaiseStmt, ReturnStmt, TryStmt, WithStmt)
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
        """A 선언문 target: <이름> or <이름>의<속성>... followed by 은/는 or 이/가.

        '이/가'는 그 줄이 '<식>이다.'로 끝날 때만 선언으로 읽는다. 그래야
        '말이 "안녕"을 담는다.' 가 선언으로 넘어가지 않는다.
        """
        i = self.pos
        if self.tokens[i].kind != "name":
            if (self.tokens[i].kind == "keyword"
                    and self.tokens[i + 1].kind == "particle"
                    and self.tokens[i + 1].extra == "topic"):
                raise SyntaxError_(
                    f"예약어에 값을 매길 수 없음: '{self.tokens[i].value}'",
                    **self.where(self.tokens[i]))
            return None
        node = Name(name=self.tokens[i].value, **self.where(self.tokens[i]))
        i += 1
        while (self.tokens[i].kind == "particle" and self.tokens[i].value == "의"
               and self.tokens[i + 1].kind == "name"):
            field = self.tokens[i + 1]
            node = Property(owner=node, field=field.value, **self.where(field))
            i += 2
        if self.tokens[i].kind == "particle" and (
                self.tokens[i].extra == "topic"
                or (self.tokens[i].extra == "subject" and self.ends_with_copula())):
            self.pos = i + 1
            return node
        return None

    def ends_with_copula(self):
        """이 줄이 '<식>이다.' 로 끝나는가."""
        end = self.line_end()
        return (end - self.pos >= 2
                and self.tokens[end - 1].kind == "symbol"
                and self.tokens[end - 1].value == "."
                and self.tokens[end - 2].kind == "copula"
                and self.tokens[end - 2].extra[1] == "final")

    def declaration(self, target, line):
        """선언문."""
        value = self.value_until_copula()
        self.expect("symbol", ".")
        self.expect("newline")
        return Declare(target=target, value=value, line=line)

    def looks_like_definition(self):
        """'<이름><은/는>:' 으로 끝나는 줄. '것은:' 이 아닌 것도 여기로 보내야
        머리가 어긋났다고 알릴 수 있다."""
        end = self.line_end()
        if end - self.pos < 3:
            return False
        head, topic, colon = self.tokens[end - 3:end]
        return (colon.kind == "symbol" and colon.value == ":"
                and topic.kind == "particle" and topic.extra == "topic"
                and head.kind == "name")

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
            try:
                _, other, _ = parse_file(path)
            except SyntaxError_ as error:
                if error.line is None:
                    error.line = start.line
                raise
        self.absorb(other, module, names)
        return ImportStmt(module=module, names=names, path=os.path.abspath(path),
                          line=start.line)

    def absorb(self, other, module, names):
        """가져온 쪽의 조사 자리를 물려받는다. 그래야 그 용언이 구절을 몇 개까지
        가져갈지 알 수 있다."""
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
        self.nouns |= {name for name in names if name in other.nouns}
        for name in names:
            if name in other.signatures:
                self.signatures.setdefault(name, []).extend(other.signatures[name])

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
        """'<구절>* <사전형>라는 것은:'. 머리가 '다'로 끝나면 용언, 아니면 파생
        필드다."""
        start = self.peek()
        head, params = self.definition_head()
        self.expect("name", "것")
        self.expect("particle")

        if not head.endswith("다"):
            if len(params) != 1 or params[0][0] != "의":
                raise SyntaxError_(
                    f"파생 필드 {quote(head, 'subject')} 받는 구절이 "
                    f"'<소유자>의' 하나가 아님", **self.where(start))
            self.nouns.add(head)
            return NounDef(name=head, owner=params[0][1], body=self.block(),
                           line=start.line)

        kind = "predicate" if head.endswith("이다") else "verb"
        self.signatures.setdefault(head, []).append(ordered(p for p, _ in params))
        return DefineStmt(name=head, kind=kind, params=params,
                          body=self.block(), line=start.line)

    def definition_head(self):
        """정의 머리를 (사전형, 구절)로. 구절은 <이름><조사> 짝이다."""
        params = []
        while True:
            token, after = self.peek(), self.peek(1)

            if token.kind == "name" and after.kind == "copula":
                if after.extra[1] != "quotative":
                    raise self.not_a_dictionary_form(
                        token, token.value + after.extra[2])
                self.pos += 2
                return token.value, params

            if token.kind in ("verb", "copula"):
                raise self.not_a_dictionary_form(token, token.extra[2])

            if token.kind != "name":
                raise SyntaxError_(
                    f"정의의 머리가 이름과 조사가 아님: {self.describe(token)}",
                    **self.where(token))

            if after.kind != "particle":
                raise self.not_a_dictionary_form(token, token.value)

            if self.at_symbol(2, ":"):
                raise SyntaxError_("정의의 머리에 '라는 것은'이 없음",
                                   **self.where(token))

            if self.tail_is_the_head(2):
                raise self.not_a_dictionary_form(token, token.value + after.value)

            self.next()
            particle = self.next()
            if any(particle.value == taken for taken, _ in params):
                raise SyntaxError_(
                    f"정의에 조사 {quote(particle.value)} 두 번 있음",
                    **self.where(particle))
            params.append((particle.value, token.value))

    def not_a_dictionary_form(self, token, written):
        return SyntaxError_(
            f"정의의 머리가 사전형이 아님: {quote(written, 'object')} 적었음",
            **self.where(token))

    def tail_is_the_head(self, offset):
        """이 자리부터 '것은:' 뿐인가. 그렇다면 방금 본 낱말이 머리 자리다."""
        return (self.peek(offset).kind == "name" and self.peek(offset).value == "것"
                and self.peek(offset + 1).kind == "particle"
                and self.peek(offset + 1).extra == "topic"
                and self.at_symbol(offset + 2, ":"))

    def at_symbol(self, offset, value):
        token = self.peek(offset)
        return token.kind == "symbol" and token.value == value

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

    def exec_or_loop(self):
        slots, calls = [], []
        aux = None
        while True:
            token = self.peek()

            if token.kind in ("verb", "copula"):
                info = self.take_verb()

                if info.name == "반복하다" and info.ending == "final":
                    return self.loop(slots, info.line)

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
                        if aux.name != "하다" or slots:
                            raise SyntaxError_(
                                "예외처리문이 '해 본다'가 아님", aux.line)
                        return self.try_statement(aux.line)
                    name, kept = None, []
                    for particle, expr in slots:
                        if particle == "로" and isinstance(expr, Name) and name is None:
                            name = expr.name
                        else:
                            kept.append((particle, expr))
                    if name is None:
                        raise SyntaxError_(
                            "자원문에 열어 둔 것을 받을 이름이 없음", aux.line)
                    call = Call(verb=aux.name, slots=kept,
                                negated=False, tail=None, line=aux.line)
                    return WithStmt(call=call, name=name, body=self.block(),
                                    line=aux.line)

                if info.ending in ("adnominal_past", "adnominal_pres", "interrogative"):
                    value = self.reduce(slots, info)
                    slots = self.push(self._kept, value)
                    continue

                if info.ending in ("final", "conjunctive"):
                    calls.append(Call(verb=info.name, slots=slots,
                                      negated=info.negated, tail=None,
                                      **self.where_verb(info)))
                    slots = []
                    if info.ending == "final":
                        self.expect("symbol", ".")
                        self.expect("newline")
                        return ExecStmt(calls=calls, line=info.line)
                    continue

                raise SyntaxError_(
                    f"실행문에 쓸 수 없는 어미: {ending_name(info.ending)}", info.line)

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

    def try_statement(self, line):
        body = self.block()
        catch, handler, ensure = None, None, None
        if self.starts_recovery():
            catch, handler = self.recovery_name(), self.block()
        if self.at("keyword", "끝으로"):
            self.next()
            ensure = self.block()
        if self.starts_recovery():
            raise SyntaxError_("'실패하면'이 두 번 있음", self.peek().line)
        return TryStmt(body=body, catch=catch, handler=handler,
                       ensure=ensure, line=line)

    def starts_recovery(self):
        token = self.peek()
        if self.at("verb", "실패하다") and token.extra[1] == "conditional":
            return True
        return (self.peek(1).kind == "particle" and self.peek(1).value == "로"
                and self.peek(2).kind == "verb" and self.peek(2).value == "실패하다")

    def recovery_name(self):
        """'<이름>으로 실패하면:' 의 이름. 이름을 적지 않으면 이유를 받지 않는다."""
        token = self.peek()
        if self.at("verb", "실패하다") and token.extra[1] == "conditional":
            self.next()
            return None
        if token.kind != "name":
            raise SyntaxError_(
                f"'실패하면'이 받을 이름이 아님: {self.describe(token)}",
                **self.where(token))
        self.pos += 3
        return token.value

    def loop(self, slots, line=None):
        """'<시작>부터 <끝>까지 (<간격> 간격)의 <이름>마다 반복한다:'"""
        start = stop = step = variable = None
        for particle, expr in slots:
            if particle == "부터":
                start = expr
            elif particle == "까지":
                stop = expr
            elif particle == "간격":
                step = expr
            elif particle == "마다":
                if not isinstance(expr, Name):
                    raise SyntaxError_("'마다' 앞이 이름이 아님", line)
                variable = expr.name
        if variable is None:
            raise SyntaxError_("반복문에 '마다'가 없음", line)
        if start is None or stop is None:
            raise SyntaxError_("반복문에 범위가 없음", line)
        return LoopStmt(kind="range", variable=variable, start=start, stop=stop,
                        step=step, body=self.block(), line=line)
