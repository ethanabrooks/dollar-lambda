from dataclasses import dataclass
from typing import Any, Callable, Generator, Generic, NamedTuple, Type, TypeVar, Union

from monad_argparse.parser.sequence import Sequence

A = TypeVar("A", covariant=True)


@dataclass
class Missing(Generic[A]):
    default: A


@dataclass
class KeyValue(Generic[A]):
    key: str
    value: Union[A, Missing[A]]

    def get_value(self) -> A:
        if isinstance(self.value, Missing):
            value: Missing[A] = self.value
            return value.default
        return self.value


B = TypeVar("B")


@dataclass
class KeyValues(Sequence[KeyValue[A]]):
    get: Sequence[KeyValue[A]]

    def __or__(self, other: "KeyValues[B]") -> "KeyValues[Union[A,B]]":  # type: ignore[override]
        return KeyValues(Sequence([*self.get, *other.get]))

    @staticmethod
    def bind(  # type: ignore[override]
        x: "KeyValues[A]", f: Callable[[KeyValue[A]], "KeyValues[B]"]
    ) -> "KeyValues[B]":
        def g() -> Generator[KeyValue[B], None, None]:
            for kv in x.get:
                yield from f(kv).get

        return KeyValues(Sequence(list(g())))

    @classmethod
    def return_(cls: Type["KeyValues[A]"], a: KeyValue[A]) -> "KeyValues[A]":  # type: ignore[override]
        return KeyValues(Sequence([a]))

    @staticmethod
    def zero() -> "KeyValues[A]":
        return KeyValues(Sequence([]))


class KeyValueTuple(NamedTuple):
    key: str
    value: Any

    def __repr__(self):
        return repr(tuple(self))
