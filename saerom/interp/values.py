"""실행 중에 오가는 값."""
from ..errors import ValueError_

class Break(Exception):
    """반복을 빠져나간다."""


class Continue(Exception):
    """다음 차례로 넘어간다."""

class Return(Exception):
    def __init__(self, value):
        self.value = value

class Module:
    """A 가져온 모듈. Its members are reached with 의, like any 속성."""
    def __init__(self, name, values, functions, types):
        self.name, self.values = name, values
        self.functions, self.types = functions, types

    def __repr__(self):
        return f"모듈 {self.name}"

_SIGNATURES = {}


def signature_of(particles):
    """조사의 갯수까지 담은 시그니처. 몇 가지 안 되므로 셈한 것을 두고 쓴다.

    같은 조사를 두 번 쓰는 정의는 부를 때도 두 번 써야 하고, 값은 적은 순서대로
    묶인다. 조사가 서로 다르면 순서는 상관없다.
    """
    key = particles if type(particles) is tuple else tuple(particles)
    found = _SIGNATURES.get(key)
    if found is None:
        counts = {}
        for particle in key:
            counts[particle] = counts.get(particle, 0) + 1
        found = _SIGNATURES[key] = frozenset(counts.items())
    return found

class Function:
    def __init__(self, name, kind, params, body, module=None):
        self.name, self.kind, self.params, self.body = name, kind, params, body
        self.module = module
        particles = [particle for particle, _ in params]
        self.signature = signature_of(tuple(particles))
        self.distinct = len(set(particles)) == len(particles)

    def bind(self, pairs):
        """부를 때 적은 값을 매개변수에 묶는다. 같은 조사끼리는 적은 순서대로."""
        if self.distinct:
            given = dict(pairs)
            return {name: given[particle] for particle, name in self.params}
        waiting = {}
        for particle, value in pairs:
            waiting.setdefault(particle, []).append(value)
        scope, used = {}, {}
        for particle, name in self.params:
            index = used.get(particle, 0)
            used[particle] = index + 1
            scope[name] = waiting[particle][index]
        return scope

class NativeFunction(Function):
    """파이썬으로 적은 동사. 조사를 적은 차례대로 매개변수에 들어간다."""
    def __init__(self, name, kind, particles, call, module=None):
        super().__init__(name, kind,
                         [(particle, index) for index, particle
                          in enumerate(particles)], None, module)
        self.call = call

class Record:
    def __init__(self, type_name, fields):
        self.type_name = type_name
        self.fields = dict(fields)

    def __repr__(self):
        inner = ", ".join(f"{k}={to_text(v)}" for k, v in self.fields.items())
        return f"{self.type_name}({inner})"

class SortKey:
    """A 줄 세우는 기준 handed to 정렬하다 as its '~로' argument."""
    def __init__(self, interp, key, descending, item_name):
        self.interp, self.key = interp, key
        self.descending, self.item_name = descending, item_name

    def of(self, item):
        if self.key is None:
            return item
        return self.interp.with_item(self.item_name, item,
                                     lambda: self.interp.evaluate_clause(self.key, item))

class Handle:
    """자원문이 열어 둔 파일. 읽기와 쓰기를 모두 한다."""
    def __init__(self, stream):
        self.stream = stream
        self.written = False

    def __repr__(self):
        return f"파일 {self.stream.name}"

def to_text(value):
    if isinstance(value, bool):
        return "참" if value else "거짓"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    if isinstance(value, float):
        return f"{value:.12g}"
    if isinstance(value, list):
        return "[" + ", ".join(to_text(v) for v in value) + "]"
    if isinstance(value, Record):
        return repr(value)
    return str(value)

def truthy(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, (str, list)):
        return len(value) > 0
    return True

def show(value):
    """오류에 보일 값. 문자열은 따옴표를 붙여 경계를 드러낸다."""
    return f'"{value}"' if isinstance(value, str) else to_text(value)

def kind_of(value):
    if isinstance(value, bool):
        return "논리값"
    if isinstance(value, (int, float)):
        return "수"
    if isinstance(value, str):
        return "문자열"
    if isinstance(value, list):
        return "목록"
    if isinstance(value, Record):
        return f"구조체 '{value.type_name}'"
    if isinstance(value, Module):
        return f"모듈 '{value.name}'"
    if isinstance(value, Handle):
        return "파일"
    return "값"

def check_numbers(verb, *values):
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError_(
                f"'{verb}'의 인자가 수가 아님: {kind_of(value)} {show(value)}")


ORDINALS = {name: index for index, name in enumerate(
    ("첫째", "둘째", "셋째", "넷째", "다섯째",
     "여섯째", "일곱째", "여덟째", "아홉째", "열째"))}
