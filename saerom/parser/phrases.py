"""구절을 쌓고 동사에서 줄이는 곳.

Korean is head-final, so a call's arguments arrive before its verb. The parser
keeps a stack of (particle, expression) slots and reduces it whenever a verb
appears.
"""
from ..errors import SaeromError, SyntaxError_, ending_name
from ..lexer import Token, tokenize
from ..nodes import (AND, OR, Call, Filter, FoldExpr, ListExpr, Literal, MapExpr,
                     Name, Node, PassiveCall, Property, QuantExpr, SelectExpr,
                     SortSpec, Template)
from ..words import CALL_TAILS, STRUCTURAL
from .base import ParserBase, VerbInfo
from .modules import fits


class PhraseParser(ParserBase):
    """구절·호출·표현."""

    VALUE_KEYWORDS = {"참", "거짓", "빈목록", "번째", "이유", "결과"}
    COLLECTION_ADVERBS = {"각각", "모두", "가장", "하나라도"}

    def take_verb(self):
        """Consume a verb (and its 않다 partner, if negated)."""
        token = self.expect_verb()
        pos, ending, surface = token.extra
        negated = False
        name = token.value
        if name == "아니다":
            return VerbInfo("이다", "descriptive", ending, surface, True,
                            token.line, token.col, token.end)
        if ending == "negative":
            partner = self.peek()
            if not (partner.kind == "verb" and partner.value == "않다"):
                raise SyntaxError_("'-지' 다음이 '않다'가 아님", token.line)
            self.next()
            _, ending, _ = partner.extra
            negated = True
        return VerbInfo(name, pos, ending, surface, negated,
                        token.line, token.col, token.end)

    def expect_verb(self):
        token = self.peek()
        if token.kind not in ("verb", "copula"):
            raise SyntaxError_(f"동사가 아님: {self.describe(token)}",
                               **self.where(token))
        return self.next()

    def push(self, slots, first):
        """구절 하나: 목록식 (A와 B와 C), '의' 이음, 그다음 조사.

        와/과 이음이 여기 있는 까닭은 `first` 가 방금 줄인 호출일 수 있어서다.
        따로 두면 'A에서 B를 뺀 값과 C를'의 '과'를 그 호출의 격조사로 읽는다.
        """
        items = [self.chain(first)]
        while (self.at("particle") and self.peek().extra == "conj"
               and self.starts_value(self.peek(1))
               and not self.starts_predicate(1)):
            self.next()
            items.append(self.chain(self.primary()))
        value = items[0] if len(items) == 1 else ListExpr(items=items)

        slots.append((None, value))
        if self.at("particle"):
            particle = self.next()
            if (particle.value == "의" and isinstance(value, Name)
                    and value.name in self.module_names):
                slots[-1] = ("모듈", value)
            else:
                slots[-1] = (particle.value, value)
        return slots

    def starts_predicate(self, offset):
        """'3이 3과 짝인지' 의 '짝'은 이어지는 값이 아니라 술어의 이름이다."""
        token, after = self.peek(offset), self.peek(offset + 1)
        return (token.kind == "name" and after.kind == "copula"
                and token.value + "이다" in self.signatures)

    @classmethod
    def starts_value(cls, token):
        """값을 시작할 수 있는 토큰인가. 와/과가 목록을 잇는지 가른다."""
        if token.kind in ("number", "string", "template", "name"):
            return True
        if token.kind == "keyword":
            return token.value in cls.VALUE_KEYWORDS
        return token.kind == "symbol" and token.value == "["

    def chain(self, value):
        """'의' 로 이어지는 필드를 목록식 전체가 아니라 원소 하나에 붙인다.

        모듈 이름은 건드리지 않는다. '12와 18의 수학의 최대공약수구한 값'의 두 번째
        '의'는 18의 필드가 아니라 이름공간 표지다. '3의 배수인지' 는 술어이고
        '목록의 개수이다' 는 속성이다.
        """
        while (self.at("particle") and self.peek().value == "의"
               and self.peek(1).kind == "name" and self.peek(1).value not in CALL_TAILS
               and self.peek(1).value not in self.module_names
               and not (self.peek(2).kind == "copula"
                        and self.peek(2).extra[1] != "final")):
            self.next()
            field = self.next()
            value = Property(owner=value, field=field.value, **self.where(field))
        return value

    def split_slots(self, verb, slots):
        """이 용언이 가져갈 수 있는 구절은 몇 개인가.

        앞에 쌓인 구절이 바깥 용언의 것일 수도 있다. 시그니처에 들어맞는 가장 긴
        꼬리만 넘기고 나머지는 남긴다. 그래서 '학생들에 줄들을 해석한 값을 더한다'가
        '줄들을'은 해석하다에, '학생들에'는 더하다에 간다.
        """
        signatures = self.signatures.get(verb)
        if not signatures:
            return [], slots
        structural = [(p, e) for p, e in slots if p in STRUCTURAL]
        arguments = [(p, e) for p, e in slots if p not in STRUCTURAL]
        for count in range(len(arguments), -1, -1):
            tail = arguments[len(arguments) - count:]
            names = [p for p, _ in tail]
            if any(fits(names, signature) for signature in signatures):
                return arguments[:len(arguments) - count], structural + tail
        return arguments, structural

    @staticmethod
    def copula_slots(slots):
        """'X가 Y가 아니다' 는 이중주격이다. 뒤의 '가'가 보어이므로 조사를 뗀다."""
        subjects = [index for index, (particle, _) in enumerate(slots)
                    if particle == "가"]
        if len(subjects) < 2:
            return slots
        slots = list(slots)
        last = subjects[-1]
        slots[last] = (None, slots[last][1])
        return slots

    def takes_every_slot(self, info, adverbs):
        """'이다'가 어떤 술어로 풀릴지는 실행 때 갈리고, 피동은 머리 명사에서,
        모음 부사는 '~들을' 자리에서 대상을 받는다. 어느 쪽도 조사 자리를
        미리 나눌 수 없다."""
        return (info.name == "이다" or info.pos == "passive"
                or bool(self.COLLECTION_ADVERBS & set(adverbs)))

    def reduce(self, slots, adverbs, info):
        """쌓인 구절과 관형형 용언 하나를 식으로 만든다."""
        if self.takes_every_slot(info, adverbs):
            kept = []
        else:
            kept, slots = self.split_slots(info.name, slots)
        self._kept = kept
        if info.name == "이다":
            slots = self.copula_slots(slots)
        clause = Call(verb=info.name, slots=slots, adverbs=adverbs,
                      negated=info.negated, tail=None, **self.where_verb(info))

        token = self.peek()
        follows_name = token.kind == "name"
        tail = token.value if follows_name and token.value in CALL_TAILS else None

        if (follows_name and token.value in ("것", "것들")
                and any(particle == "중" for particle, _ in slots)):
            tail = None

        if follows_name and token.value == "순":
            self.next()
            key = [expr for particle, expr in slots if particle == "가"]
            return SortSpec(key=key[0] if key else None,
                            descending=(info.name == "크다"), line=info.line)

        if info.name == "실패하다" and follows_name and token.value == "이유":
            self.next()
            return Name(name="이유")

        if follows_name and tail is None:
            head = self.next().value
            partitive = [expr for particle, expr in slots if particle == "중"]
            rest = [(p, e) for p, e in slots if p != "중"]
            if info.pos == "passive":
                return PassiveCall(verb=info.name, head=Name(name=head),
                                   slots=rest, line=info.line)
            source = partitive[0] if partitive else Name(name=head)
            item = head[:-1] if head.endswith("들") else head
            clause.slots = rest
            return Filter(source=source, item=item, clause=clause, line=info.line)

        if tail is not None:
            self.next()
        clause.tail = tail or "값"

        if info.pos == "passive":
            target = [expr for particle, expr in slots if particle == "를"]
            rest = [(p, e) for p, e in slots if p != "를"]
            if target:
                return PassiveCall(verb=info.name, head=target[0], slots=rest,
                                   line=info.line)

        return self.apply_adverbs(clause, adverbs, info)

    def apply_adverbs(self, clause, adverbs, info):
        def take(particle):
            picked = [e for p, e in clause.slots if p == particle]
            clause.slots = [(p, e) for p, e in clause.slots if p != particle]
            return picked[0] if picked else None

        if "각각" in adverbs:
            source = take("를")
            if source is None:
                raise SyntaxError_("'각각'에 '~을' 자리가 없음", info.line)
            return MapExpr(source=source, clause=clause, line=info.line)

        if "모두" in adverbs:
            if info.ending == "interrogative":
                source = take("가")
                return QuantExpr(kind="all", source=source, clause=clause, line=info.line)
            source = take("를")
            if source is None:
                raise SyntaxError_("'모두'에 '~을' 자리가 없음", info.line)
            return FoldExpr(source=source, clause=clause, line=info.line)

        if "하나라도" in adverbs:
            source = take("중") or take("가")
            return QuantExpr(kind="any", source=source, clause=clause, line=info.line)

        if "가장" in adverbs:
            source = take("중") or take("가")
            if source is None:
                raise SyntaxError_("'가장'에 '~ 중' 자리가 없음", info.line)
            return SelectExpr(source=source, clause=clause, line=info.line)

        return clause

    def primary(self):
        token = self.peek()
        if token.kind in ("number", "string"):
            self.next()
            return Literal(value=token.value)
        if token.kind == "template":
            self.next()
            return Template(parts=[
                Literal(value=text) if kind == "text"
                else self.fragment(text, token)
                for kind, text, _, _ in token.value], **self.where(token))
        if token.kind == "keyword":
            if token.value == "참":
                self.next(); return Literal(value=True)
            if token.value == "거짓":
                self.next(); return Literal(value=False)
            if token.value == "빈목록":
                self.next(); return ListExpr(items=[])
            if token.value in ("번째", "줄", "이유", "결과"):
                self.next(); return Name(name=token.value, **self.where(token))
        if token.kind == "name":
            self.next()
            return Name(name=token.value, **self.where(token))
        if token.kind == "symbol" and token.value == "[":
            self.next()
            items = []
            if not self.at("symbol", "]"):
                items.append(self.bracket_item())
                while self.accept("symbol", ","):
                    items.append(self.bracket_item())
            self.expect("symbol", "]")
            return ListExpr(items=items)
        raise SyntaxError_(f"값이 아님: {self.describe(token)}", **self.where(token))

    def reduce_until(self, stop, what):
        """Run the slot machine until `stop`, then require one value."""
        slots, adverbs = [], []
        while True:
            token = self.peek()
            if stop(token):
                if len(slots) != 1:
                    raise SyntaxError_(f"{what}이(가) 하나가 아님", token.line)
                return slots[0][1]
            if token.kind in ("verb", "copula"):
                info = self.take_verb()
                value = self.reduce(slots, adverbs, info)
                slots = self.push(self._kept, value)
                adverbs = []
                continue
            if token.kind == "adverb":
                adverbs.append(token.value)
                self.next()
                continue
            slots = self.push(slots, self.primary())

    def bracket_item(self):
        """Inside [ ] a full expression may appear, so reduce until , or ]."""
        return self.reduce_until(
            lambda t: t.kind == "symbol" and t.value in ",]", "목록의 항")

    def fragment(self, source, token):
        """Parse one {...} of a 보간 string as a standalone expression.

        The inner parse restarts at line 1, so we stamp the outer string's
        position back on -- otherwise a call made inside a 보간 reports the
        wrong line in the 호출 스택.
        """
        inner = type(self)(tokenize(source, self.known))
        inner.known = self.known
        inner.signatures = self.signatures
        inner.types = self.types
        inner.module_names = self.module_names
        inner.base_dir = self.base_dir
        try:
            node = inner.reduce_until(lambda t: t.kind in ("newline", "eof"),
                                      "끼워 넣은 값")
        except SaeromError as error:
            raise SyntaxError_(f"{{{source}}} 안: {error.message}",
                               **self.where(token))
        return self.restamp(node, token)

    @classmethod
    def restamp(cls, node, token):
        seen = set()

        def walk(value):
            if isinstance(value, Node):
                if id(value) in seen:
                    return
                seen.add(id(value))
                if hasattr(value, "line"):
                    value.line, value.col, value.end = token.line, token.col, token.end
                for inner in list(value.__dict__.values()):
                    walk(inner)
            elif isinstance(value, (list, tuple)):
                for inner in value:
                    walk(inner)

        walk(node)
        return node

    def condition(self):
        """Coordinated predicates share only the subject: '1보다 작거나 1과 같으면'
        gives 같다 the 가 slot of 작다, but never its 보다 slot."""
        left, joiner = None, AND
        subject = None
        slots, adverbs = [], []
        while True:
            token = self.peek()

            if token.kind == "keyword" and token.value == "아니면" and slots:
                token = Token("verb", "아니다", token.line, token.col,
                              ("descriptive", "conditional", "아니면"), token.end)
                self.tokens[self.pos] = token

            if token.kind in ("verb", "copula"):
                info = self.take_verb()
                if info.ending in ("adnominal_past", "adnominal_pres"):
                    value = self.reduce(slots, adverbs, info)
                    slots = self.push(self._kept, value)
                    adverbs = []
                    continue

                if not any(p == "가" for p, _ in slots) and subject is not None:
                    slots = [("가", subject)] + slots
                for particle, expr in slots:
                    if particle == "가":
                        subject = expr

                if info.name == "이다":
                    slots = self.copula_slots(slots)
                piece = self.apply_adverbs(
                    Call(verb=info.name, slots=slots, adverbs=adverbs,
                         negated=info.negated, tail=None, **self.where_verb(info)),
                    adverbs, info)
                slots, adverbs = [], []
                left = piece if left is None else Call(
                    verb=joiner, slots=[(None, left), (None, piece)], adverbs=[],
                    negated=False, tail=None, line=info.line)
                if info.ending == "conditional":
                    return left
                if info.ending == "conjunctive":
                    joiner = AND
                    continue
                if info.ending == "alternative":
                    joiner = OR
                    continue
                raise SyntaxError_(
                    f"조건에 쓸 수 없는 어미: {ending_name(info.ending)}", info.line)

            if token.kind == "adverb":
                adverbs.append(token.value)
                self.next()
                continue

            slots = self.push(slots, self.primary())

    def value_until_copula(self):
        """Right-hand side of a 선언문: read until the closing 이다."""
        slots, adverbs = [], []
        while True:
            token = self.peek()

            if token.kind == "copula" and token.extra[1] == "final":
                self.next()
                if len(slots) != 1:
                    raise SyntaxError_("선언문의 값이 하나가 아님", token.line)
                return slots[0][1]

            if self.looks_like_record_end():
                return self.record_literal(slots)

            if token.kind in ("verb", "copula"):
                info = self.take_verb()
                if info.ending in ("adnominal_past", "adnominal_pres", "interrogative"):
                    value = self.reduce(slots, adverbs, info)
                    slots = self.push(self._kept, value)
                    adverbs = []
                    continue
                raise SyntaxError_(
                    f"선언문에 쓸 수 없는 어미: {ending_name(info.ending)}", token.line)

            if token.kind == "adverb":
                adverbs.append(token.value)
                self.next()
                continue

            slots = self.push(slots, self.primary())
