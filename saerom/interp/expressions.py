"""값을 내는 일."""
from ..errors import NameError_, SaeromError, ValueError_, suggest
from ..nodes import (AND, OR, Call, Filter, FoldExpr, ListExpr, Literal, MapExpr,
                     Name, PassiveCall, Property, QuantExpr, RecordLit, SelectExpr,
                     SortSpec, Template)
from .calls import CallMixin
import copy

from .values import (ORDINALS, Module, Record, SortKey, kind_of,
                     signature_of, to_text, truthy)


class ExpressionMixin(CallMixin):
    """식 하나를 값으로."""

    TYPE_NAMES = {bool: "논리값", int: "정수", float: "실수", str: "문자열",
                  list: "목록"}

    def evaluate(self, node):
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
        # 관형절 안에서 임자를 생략하면 원소의 필드로 읽는다:
        # '나이가 17인 학생들', '글자수가 0이 아닌 글줄들'
        if self.items:
            try:
                return self.get_property(self.items[-1], node.name)
            except SaeromError:
                pass
        names = set(self.scope) | set(self.globals)
        close = suggest(node.name, names)
        raise NameError_(
            f"'{node.name}' 정의되지 않음",
            hint=f"비슷한 이름: '{close}'" if close else None).locate(node)

    def evaluate_list(self, node):
        return [self.evaluate(item) for item in node.items]

    def evaluate_template(self, node):
        return "".join(to_text(self.evaluate(part)) for part in node.parts)

    def evaluate_property(self, node):
        try:
            return self.get_property(self.evaluate(node.owner), node.field)
        except SaeromError as error:
            raise error.locate(node)

    def evaluate_sort_spec(self, node):
        return SortKey(self, node.key, node.descending, "것")

    def evaluate_map(self, node):
        source = self.evaluate(node.source)
        verb = node.clause.verb
        extra = {p: self.evaluate(e) for p, e in node.clause.slots}
        return [self.apply(verb, self.fill_item(verb, dict(extra), item), node.line)
                for item in source]

    def evaluate_quantifier(self, node):
        source = self.evaluate(node.source)
        item_name = self.item_name(node.source)
        results = [self.test_clause(node.clause, item, item_name) for item in source]
        return all(results) if node.kind == "all" else any(results)

    def get_property(self, value, field):
        if field == "자료형":
            if isinstance(value, Record):
                return value.type_name
            return self.TYPE_NAMES.get(type(value), "값")

        if isinstance(value, Module):
            if field in value.values:
                return value.values[field]
            close = suggest(field, set(value.values)
                            | {verb for verb, _ in value.functions})
            raise NameError_(
                f"모듈 '{value.name}'에 '{field}' 없음",
                hint=f"비슷한 이름: '{close}'" if close else None)

        if isinstance(value, Record):
            if field in value.fields:
                return value.fields[field]
            close = suggest(field, value.fields)
            raise NameError_(
                f"구조체 '{value.type_name}'에 필드 '{field}' 없음",
                hint=f"비슷한 이름: '{close}'" if close else
                     "필드: " + ", ".join(value.fields))

        if isinstance(value, list) and field.endswith("들"):
            return [self.get_property(item, field[:-1]) for item in value]

        if isinstance(value, list):
            if field in ("개수", "길이"):
                return len(value)
            if field in ORDINALS:
                return self.at(value, ORDINALS[field], field)
            if field.endswith("번째"):
                return value[self.position(field[:-2], len(value)) - 1]
            if field == "마지막":
                return self.at(value, -1, field)
        if isinstance(value, str):
            if field in ("글자수", "길이", "개수"):
                return len(value)
            if field in ORDINALS:
                return self.at(value, ORDINALS[field], field)
            if field.endswith("번째"):
                return value[self.position(field[:-2], len(value)) - 1]
            if field == "마지막":
                return self.at(value, -1, field)
        raise NameError_(
            f"{kind_of(value)}에 필드 '{field}' 없음",
            hint="목록: 개수, 길이, 첫째, 마지막, <수>번째 / 문자열: 글자수")

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

    @staticmethod
    def item_name(source):
        if isinstance(source, Name) and source.name.endswith("들"):
            return source.name[:-1]
        return "것"

    def with_item(self, item_name, item, thunk):
        outer = self.scope.get(item_name)
        self.scope[item_name] = item
        self.items.append(item)
        try:
            return thunk()
        finally:
            self.items.pop()
            if outer is None:
                self.scope.pop(item_name, None)
            else:
                self.scope[item_name] = outer

    def fill_item(self, verb, args, item):
        """관형절에서 빠진 자리가 하나면 원소가 채운다.

        '짝수인 숫자들' fills 가; '평균점수계산한 값이 큰 학생들' fills 의.
        """
        given = frozenset(args)
        key = (verb, given, id(self.functions), len(self.functions))
        if key not in self.empty_slots:
            self.empty_slots[key] = self.empty_slot(verb, given)
        found = self.empty_slots[key]
        if found is None:              # 자리를 고를 수 없으면 그대로 둔다
            return args
        alone, particle = found
        if alone:
            args[particle] = item
        else:
            args.setdefault(particle, item)
        return args

    def empty_slot(self, verb, given):
        """이 동사에서 아직 비어 있는 조사 자리. 목록을 도는 동안 바뀌지 않는다."""
        candidates = {(dict(signature).keys() - given).pop()
                      for name, signature in list(self.functions) + list(self.builtins)
                      if name == verb and given < dict(signature).keys()
                      and len(signature) == len(given) + 1}
        if len(candidates) == 1:
            return True, candidates.pop()
        if "가" in candidates or not candidates:
            return False, "가"
        return None

    def evaluate_clause(self, clause, item):
        """Evaluate a 관형절 for one item and return its value."""
        if not isinstance(clause, Call):
            return self.evaluate(clause)

        # '우등생인 학생들' / '음수가 아닌 수들' — 이다 앞의 이름이 값이 아니라
        # 술어를 가리킬 수 있다. 한국어의 이중주격이라 조사가 없기도, '가'이기도 하다.
        if clause.verb == "이다":
            found = self.predicate_slot(clause.slots)
            if found is not None:
                name, rest = found
                # 뒤집기는 test_clause가 한 번만 한다.
                args = {p: self.evaluate(e) for p, e in rest}
                return self.apply(name, self.fill_item(name, args, item), clause.line)

        args = {p: self.evaluate(e) for p, e in clause.slots}
        return self.apply(clause.verb, self.fill_item(clause.verb, args, item), clause.line)

    def predicate_slot(self, slots):
        """이다의 슬롯 가운데 술어 이름을 가리키는 것을 찾는다."""
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

    def test_clause(self, clause, item, item_name):
        def run():
            result = self.evaluate_clause(clause, item)
            return not truthy(result) if getattr(clause, "negated", False) else truthy(result)
        return self.with_item(item_name, item, run)

    def run_filter(self, node):
        source = self.evaluate(node.source)
        if not isinstance(source, list):
            raise SaeromError("걸러낼 대상이 목록이 아님", node.line)
        return [item for item in source
                if self.test_clause(node.clause, item, node.item)]

    def fold(self, node):
        source = self.evaluate(node.source)
        verb = node.clause.verb
        extra = {p: self.evaluate(e) for p, e in node.clause.slots}
        whole = self.lookup(verb, list(extra) + ["를"])
        if whole is not None:
            return self.apply(verb, {**extra, "를": source}, node.line)
        if not source:
            return 0
        signature = self.two_slot_signature(verb)
        if signature is None:
            raise SaeromError(f"'{verb}'로 모을 수 없음", node.line)
        accumulator_slot = (signature - {"를"}).pop()
        total = source[0]
        for item in source[1:]:
            total = self.apply(verb, {accumulator_slot: total, "를": item}, node.line)
        return total

    def two_slot_signature(self, verb):
        for name, signature in list(self.functions) + list(self.builtins):
            names = dict(signature).keys()
            if name == verb and len(names) == 2 and "를" in names:
                return set(names)
        return None

    def select(self, node):
        source = self.evaluate(node.source)
        if not source:
            raise SaeromError("고를 원소가 없음", node.line)
        best = source[0]
        for item in source[1:]:
            if truthy(self.apply(node.clause.verb, {"가": item, "보다": best}, node.line)):
                best = item
        return best

    def passive(self, node):
        target = copy.deepcopy(self.evaluate(node.head))
        extra = {p: self.evaluate(e) for p, e in node.slots}
        if "가" in extra:                      # 능동의 '~을'이 피동에서 '~이'가 된다
            extra["를"] = extra.pop("가")
        for particle in self.head_particles(node.verb, set(extra)):
            handler = self.lookup(node.verb, list(extra) + [particle])
            if handler is not None:
                self.apply(node.verb, {**extra, particle: target}, node.line)
                return target
        raise SaeromError(f"'{node.verb}'의 피동형 정의되지 않음", node.line)

    def call(self, node):
        try:
            return self.dispatch(node)
        except SaeromError as error:
            raise error.locate(node)

    def dispatch(self, node):
        if node.verb in (AND, OR):
            left = truthy(self.evaluate(node.slots[0][1]))
            if node.verb == AND and not left:
                return False
            if node.verb == OR and left:
                return True
            return truthy(self.evaluate(node.slots[1][1]))

        # '수학의 소수인지' — 모듈 안의 술어.
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
                    value = self.invoke(function, args, node.line)
                    return not truthy(value) if node.negated else value

        # 'X가 <이름>이면' is either a comparison or a 술어 call.
        if node.verb == "이다":
            found = self.predicate_slot(node.slots)
            if found is not None:
                name, rest = found
                args = {p: self.evaluate(e) for p, e in rest}
                if self.lookup(name, args) is not None:
                    value = self.apply(name, args, node.line)
                    return not truthy(value) if node.negated else value

        # 같은 조사가 여럿일 수 있으므로 적은 차례를 지킨 짝으로 넘긴다.
        pairs = [(particle, self.evaluate(expr)) for particle, expr in node.slots]
        name = node.verb + ("·나머지" if getattr(node, "tail", None) == "나머지" else "")
        result = self.apply(name, pairs, node.line)
        return not truthy(result) if node.negated else result

    def evaluate_record(self, node):
        # 구조체 만들기는 자료형을 아는 실행기가 맡는다.
        return self.build_record(node)

    # 마디의 갈래마다 하나씩. 이 표를 거치므로 갈래를 더할 때 함께 적는다.
    EVALUATE = {
        Literal: evaluate_literal,
        Name: evaluate_name,
        ListExpr: evaluate_list,
        Template: evaluate_template,
        Property: evaluate_property,
        SortSpec: evaluate_sort_spec,
        RecordLit: evaluate_record,
        Call: call,
        PassiveCall: passive,
        Filter: run_filter,
        MapExpr: evaluate_map,
        FoldExpr: fold,
        SelectExpr: select,
        QuantExpr: evaluate_quantifier,
    }
