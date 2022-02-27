from dataclasses import dataclass, replace
from typing import Generator, Generic, Optional, TypeVar

from monad_argparse.monad.option import Option as OptionMonad

A = TypeVar("A", covariant=True)
B = TypeVar("B", contravariant=True)


@dataclass
class NonemptyList(Generic[A]):
    head: A
    tail: "Optional[NonemptyList[A]]" = None

    def __add__(self, other: "NonemptyList"):
        if self.tail is None:
            return replace(self, tail=other)
        if other.tail is None:
            return replace(self, tail=self.tail + NonemptyList(other.head))
        return replace(self, tail=(self.tail + NonemptyList(other.head) + other.tail))

    def __iter__(self):
        yield self.head
        if self.tail:
            yield from self.tail

    def __repr__(self):
        return repr(list(self))

    @staticmethod
    def make(*xs: B) -> Optional["NonemptyList[B]"]:
        if xs:
            head, *maybe_tail = xs
            if not maybe_tail:
                return NonemptyList(head)

            def options() -> Generator[
                Optional[NonemptyList[B]], NonemptyList[B], None
            ]:
                tail = yield NonemptyList.make(*maybe_tail)
                yield NonemptyList(head, tail)

            return OptionMonad.do(options)
        return None