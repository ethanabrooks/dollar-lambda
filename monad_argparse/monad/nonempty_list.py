from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TypeVar

from monad_argparse.monad.monad import Monad
from monad_argparse.monad.option import Option

A = TypeVar("A", covariant=True)
B = TypeVar("B", contravariant=True)


@dataclass
class NonemptyList(Monad[A]):
    head: A
    tail: NonemptyList[A] | None = None

    def __add__(self, other: NonemptyList[B]):
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

    def bind(self, f):
        def g():
            for y in self:
                yield from f(y)

        return NonemptyList.make(list(g()))

    @staticmethod
    def _make(*xs: B) -> Option["NonemptyList[B]"]:
        if xs:
            head, *tail = xs
            if not tail:
                return Option(NonemptyList(head))

            return NonemptyList._make(*tail) >= (lambda tl: NonemptyList(head, tl))
        return Option(None)

    @staticmethod
    def make(*xs: B) -> None | "NonemptyList[B]":
        return NonemptyList._make(*xs).get

    @classmethod
    def return_(cls, a: B) -> NonemptyList[B]:
        return NonemptyList(a)
