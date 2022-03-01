from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, TypeVar

from monad_argparse.monad.monad import Monad

A = TypeVar("A", covariant=True)
B = TypeVar("B", contravariant=True)


@dataclass
class Option(Monad[A]):
    """
    >>> def options():
    ...     x = yield Option(1)
    ...     y = yield Option(2)
    ...     yield Option(x + y)
    ...
    >>> Option.do(options)
    Option(3)
    >>> def options():
    ...     x = yield Option(1)
    ...     y = yield Option(None)
    ...     yield Option(x + y)
    ...
    >>> print(Option.do(options))  # added `print` in order to get None to show up
    Option(None)
    """

    get: A | None

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({repr(self.get)})"

    def bind(
        self,
        f: Callable[[A], Option[B]],
    ) -> Option[B]:
        if self.get is None:
            return Option(None)
        return f(self.get)

    @classmethod
    def return_(cls, a: B) -> Option[B]:
        return Option(a)


class O(Option[A]):
    pass
