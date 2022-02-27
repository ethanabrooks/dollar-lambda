import typing
from typing import Callable, Generator

from monad_argparse.monad.monad import A, B, M, Monad


class L(M[typing.List[A]]):
    def __ge__(self, f: Callable[[A], typing.List[A]]):  # type: ignore[override]
        return L(List.bind(self.a, f))

    def __iter__(self):
        yield from self.a

    @classmethod
    def return_(cls, a: A) -> "L[typing.List[A]]":
        return L(List.return_(a))


class List(Monad[A, typing.List[A]]):
    """
    >>> def lists():
    ...     x = yield []
    ...     y = yield [2, 3]
    ...     yield [x + y]
    ...
    >>> List.do(lists)
    []
    >>> def lists():
    ...     x = yield [1]
    ...     y = yield [2, 3]
    ...     yield [x + y]
    ...
    >>> List.do(lists)
    [3, 4]
    >>> def lists():
    ...     x = yield [1, 2]
    ...     y = yield [2, 3]
    ...     yield [x + y]
    ...
    >>> List.do(lists)
    [3, 4, 4, 5]
    """

    @classmethod
    def bind(  # type: ignore[override]
        cls, x: typing.List[A], f: Callable[[A], typing.List[B]]
    ) -> typing.List[B]:
        def g() -> Generator[B, None, None]:
            for y in x:
                for z in f(y):
                    yield z

        return list(g())

    @classmethod
    def return_(cls, a: A) -> typing.List[A]:
        return [a]
