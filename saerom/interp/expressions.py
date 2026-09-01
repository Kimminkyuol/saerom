"""식 하나를 값으로."""
from ..errors import NameError_, SaeromError, ValueError_, quote, suggest
from ..nodes import (AND, OR, Call, DictExpr, ListExpr, Literal, Name,
                     PassiveCall, Property, Template)
from .builtins import CHANGES
from .calls import CallMixin
import copy

from .values import (ORDINALS, Module, kind_of, show, signature_of, to_text,
                     truthy)


class ExpressionMixin(CallMixin):
    """식 하나를 값으로."""

    TYPE_NAMES = {bool: "논리값", int: "정수", float: "실수", str: "문자열",
                  list: "목록", dict: "사전"}

    def evaluate(self, node):
        """EVALUATE 에 적힌 갈래대로 식 하나를 값으로 바꾼다."""
        found = self.EVALUATE.get(type(node))
        if found is None:
            raise SaeromError(f"값이 될 수 없음: {type(node).__name__}",
                              getattr(node, "line", None))
        return found(self, node)

    def evaluate_literal(self, node):
        return node.value

    def evaluate_name(self, node):
        if node.name in self.scope:
            return self.scope[node.name]
        if node.name in self.globals:
            return self.globals[node.name]
        names = set(self.scope) | set(self.globals)
        close = suggest(node.name, names)
        raise NameError_(
            f"'{node.name}' 정의되지 않음",
            hint=f"비슷한 이름: '{close}'" if close else None).locate(node)

    def evaluate_list(self, node):
        return [self.evaluate(item) for item in node.items]

    def evaluate_dict(self, node):
        return {key: self.evaluate(value) for key, value in node.items}

    def evaluate_template(self, node):
        return "".join(to_text(self.evaluate(part)) for part in node.parts)

    def evaluate_property(self, node):
        try:
            return self.get_property(self.evaluate(node.owner), node.field,
                                     getattr(node, "line", None))
        except SaeromError as error:
            raise error.locate(node)

    def valued(self, verb, result, line=None):
        """값 자리에서 부른 동사는 값을 내야 한다."""
        if result is None:
            raise ValueError_(
                f"동사 {quote(verb)} 아무 값도 돌려주지 않음", line)
        return result

    def get_property(self, value, field, line=None):
        if field == "복사본":
            return copy.deepcopy(value)

        if field == "자료형":
            return self.TYPE_NAMES.get(type(value), "값")

        if isinstance(value, Module):
            if field in value.values:
                return value.values[field]
            close = suggest(field, set(value.values)
                            | {verb for verb, _ in value.functions})
            raise NameError_(
                f"모듈 '{value.name}'에 '{field}' 없음",
                hint=f"비슷한 이름: '{close}'" if close else None)

        if isinstance(value, dict):
            if field in value:
                return value[field]
            if field in self.nouns:
                return self.derived(value, field, line)
            close = suggest(field, value)
            raise NameError_(
                f"사전에 '{field}' 없음",
                hint=f"비슷한 이름: '{close}'" if close else
                     ("열쇠: " + ", ".join(value) if value else None))

        if isinstance(value, list):
            if field == "개수":
                return len(value)
            if field in ORDINALS:
                return self.at(value, ORDINALS[field], field)
            if field.endswith("번째"):
                return value[self.position(field[:-2], len(value)) - 1]
            if field == "마지막":
                return self.at(value, -1, field)
        if isinstance(value, str):
            if field == "글자수":
                return len(value)
            if field in ORDINALS:
                return self.at(value, ORDINALS[field], field)
            if field.endswith("번째"):
                return value[self.position(field[:-2], len(value)) - 1]
            if field == "마지막":
                return self.at(value, -1, field)
        if field in self.nouns:
            return self.derived(value, field, line)
        raise NameError_(
            f"{kind_of(value)}에 필드 '{field}' 없음",
            hint="목록·문자열: 첫째 ~ 열째, 마지막, <수>번째 / "
                 "목록: 개수 / 문자열: 글자수")

    def derived(self, value, field, line=None):
        """파생 필드. 소유자를 매개변수에 묶어 몸을 실행한다."""
        return self.invoke(self.nouns[field], [("의", value)], line)

    @staticmethod
    def at(value, index, field):
        """'첫째' 처럼 자리가 정해진 필드. 자리를 벗어나면 값 오류."""
        if not -len(value) <= index < len(value):
            raise ValueError_(f"'{field}' 없음. 개수는 {len(value)}")
        return value[index]

    def position(self, head, size):
        """'3번째' 의 3, 또는 '가운데번째' 의 가운데가 담고 있는 수."""
        if head.isdigit():
            index = int(head)
        elif head in self.scope:
            index = self.scope[head]
        elif head in self.globals:
            index = self.globals[head]
        else:
            raise NameError_(f"'{head}' 정의되지 않음")
        if isinstance(index, bool) or not isinstance(index, int):
            raise ValueError_(f"자리가 정수가 아님: {to_text(index)}")
        if not 1 <= index <= size:
            raise ValueError_(f"{index}번째 없음. 개수는 {size}")
        return index

    def predicate_slot(self, slots):
        """이다의 슬롯 가운데 술어 이름을 가리키는 것. 이중주격이라 조사가
        없기도, '가'이기도 하다: '우등생인 학생들', '음수가 아닌 수들'."""
        for index, (particle, expr) in enumerate(slots):
            if particle in (None, "가") and isinstance(expr, Name):
                name = expr.name + "이다"
                if self.is_known(name):
                    rest = [pair for position, pair in enumerate(slots)
                            if position != index and pair[0] is not None]
                    return name, rest
        return None

    def is_known(self, name):
        """정의된 용언인가. 이름 표는 자주 바뀌지 않으므로 모아 두고 본다."""
        key = (id(self.functions), len(self.functions))
        if key != self.verb_names_key:
            self.verb_names_key = key
            self.verb_names = {verb for verb, _ in self.functions} | \
                              {verb for verb, _ in self.builtins}
        return name in self.verb_names

    def passive(self, node):
        """머리 명사가 비어 있는 조사 자리를 채운다. 값은 그 호출이 낸 것이다."""
        head = self.evaluate(node.head)
        args = {p: self.evaluate(e) for p, e in node.slots}
        for particle in self.head_particles(node.verb, set(args)):
            if self.lookup(node.verb, list(args) + [particle]) is not None:
                return self.valued(node.verb, self.apply(
                    node.verb, {**args, particle: head}, node.line), node.line)
        raise self.unknown_call(node.verb, {**args, "가": head}, node.line).locate(node)

    def call(self, node):
        """값 자리에서 부른 동사는 값을 내야 한다."""
        try:
            result = self.dispatch(node)
        except SaeromError as error:
            raise error.locate(node)
        if result is None and getattr(node, "tail", None):
            raise ValueError_(
                f"동사 {quote(node.verb)} 아무 값도 돌려주지 않음").locate(node)
        return result

    def answered(self, node, value):
        """물음꼴로 부른 것은 뒤집기 전에 이미 참이나 거짓이어야 한다."""
        if getattr(node, "asks", False) and not isinstance(value, bool):
            raise ValueError_(
                f"{quote(node.verb, 'object')} 물은 결과가 논리값이 아님: "
                f"{kind_of(value)} {show(value)}")
        return not truthy(value) if node.negated else value

    def dispatch(self, node):
        """'이다'는 견줌일 수도, 술어를 부르는 것일 수도 있다. 그것은 실행 때 갈린다."""
        if node.verb in (AND, OR):
            left = truthy(self.evaluate(node.slots[0][1]))
            if node.verb == AND and not left:
                return False
            if node.verb == OR and left:
                return True
            return truthy(self.evaluate(node.slots[1][1]))

        if node.verb == "이다":
            holder = [expr for particle, expr in node.slots if particle == "모듈"]
            if holder:
                module = self.evaluate(holder[0])
                bare = [expr for particle, expr in node.slots
                        if particle is None and isinstance(expr, Name)]
                rest = [(p, e) for p, e in node.slots if p not in ("모듈", None)]
                args = {p: self.evaluate(e) for p, e in rest}
                if isinstance(module, Module) and len(bare) == 1:
                    name = bare[0].name + "이다"
                    function = module.functions.get((name, signature_of(args)))
                    if function is None:
                        raise self.unknown_module_call(module, name, args, node.line)
                    return self.answered(
                        node, self.invoke(function, args, node.line))

        if node.verb == "이다":
            found = self.predicate_slot(node.slots)
            if found is not None:
                name, rest = found
                args = {p: self.evaluate(e) for p, e in rest}
                if self.lookup(name, args) is not None:
                    return self.answered(node, self.apply(name, args, node.line))
                bare = name[:-2]
                if bare not in self.scope and bare not in self.globals:
                    raise self.unknown_call(name, args, node.line)

        pairs = [(particle, self.evaluate(expr)) for particle, expr in node.slots]
        if node.tail:
            pairs = spare_pairs(node.verb, pairs)
        name = node.verb + ("·나머지" if node.tail == "나머지" else "")
        return self.answered(node, self.apply(name, pairs, node.line))

    EVALUATE = {
        Literal: evaluate_literal,
        Name: evaluate_name,
        ListExpr: evaluate_list,
        Template: evaluate_template,
        Property: evaluate_property,
        DictExpr: evaluate_dict,
        Call: call,
        PassiveCall: passive,
    }


def spare_pairs(verb, pairs):
    slot = CHANGES.get(verb)
    if slot is None:
        return pairs
    return [(particle, list(value)
             if particle == slot and isinstance(value, list) else value)
            for particle, value in pairs]
