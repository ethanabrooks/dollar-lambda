from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, TypeVar

from monad_argparse.monad.monad import Monad

A = TypeVar("A", covariant=True)
B = TypeVar("B", contravariant=True)


@dataclass
class Result(Monad[A]):
    """
    >>> def results():
    ...     x = yield Result(1)
    ...     y = yield Result(2)
    ...     yield Result(x + y)
    ...
    >>> Result.do(results)
    Result(3)
    >>> def results():
    ...     x = yield Result(1)
    ...     y = yield Result(RuntimeError("Oh no!"))
    ...     yield Result(x + y)
    ...
    >>> Result.do(results)
    Result(RuntimeError('Oh no!'))
    """

    get: A | Exception

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({repr(self.get)})"

    def bind(
        self,
        f: Callable[[A], Result[B]],
    ) -> Result[B]:
        if isinstance(self.get, Exception):
            return Result(self.get)
        return f(self.get)

    @classmethod
    def return_(cls, a: B) -> Result[B]:
        return Result(a)


class R(Result):
    pass
