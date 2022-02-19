import typing
from typing import Callable, Generator, Union

from monad_argparse.monad import A, B, BaseMonad, M


class L(M, typing.Generic[A]):
    def __ge__(self, f: Callable[[A], typing.List[A]]):  # type: ignore[override]
        return List.bind(self.a, f)

    @classmethod
    def return_(cls, a: A) -> "L[typing.List[A]]":
        return L(List.return_(a))


class List(BaseMonad[A, typing.List[A], Union[typing.List[A], typing.List[B]]]):
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
    def return_(cls, a: A) -> Union[typing.List[A], typing.List[B]]:
        return [a]
