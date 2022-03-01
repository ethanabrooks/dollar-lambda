from dataclasses import dataclass
from typing import (
    Any,
    Callable,
    Generator,
    Generic,
    NamedTuple,
    Sequence,
    TypeVar,
    Union,
    overload,
)

from monad_argparse.monad.monad_plus import MonadPlus

A = TypeVar("A", covariant=True)


@dataclass
class KeyValue(Generic[A]):
    key: str
    value: A


B = TypeVar("B")


@dataclass
class KeyValues(MonadPlus[KeyValue[A], "KeyValues[A]"], Sequence[KeyValue[A]]):
    get: Sequence[KeyValue[A]]

    @overload
    def __getitem__(self, i: int) -> KeyValue[A]:
        ...

    @overload
    def __getitem__(self, i: slice) -> Sequence[KeyValue[A]]:
        ...

    def __getitem__(
        self, i: Union[int, slice]
    ) -> Union[KeyValue[A], Sequence[KeyValue[A]]]:
        return self.get[i]

    def __iter__(self) -> Generator[KeyValue[A], None, None]:
        yield from self.get

    def __len__(self) -> int:
        return len(self.get)

    def __or__(self, other: "KeyValues[B]") -> "KeyValues[Union[A,B]]":
        return KeyValues([*self.get, *other.get])

    @staticmethod
    def bind(  # type: ignore[override]
        x: "KeyValues[A]", f: Callable[[KeyValue[A]], "KeyValues[B]"]
    ) -> "KeyValues[B]":
        def g() -> Generator[KeyValue[B], None, None]:
            for kv in x.get:
                yield from f(kv).get

        return KeyValues(list(g()))

    @staticmethod
    def return_(a: KeyValue[A]) -> "KeyValues[A]":
        return KeyValues([a])

    @staticmethod
    def zero() -> "KeyValues[A]":
        return KeyValues([])


class KeyValueTuple(NamedTuple):
    key: str
    value: Any

    def __repr__(self):
        return repr(tuple(self))
