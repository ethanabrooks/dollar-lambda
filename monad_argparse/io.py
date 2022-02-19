from typing import Callable, Generator, Generic, TypeVar

from monad_argparse.monad import BaseMonad, M

A = TypeVar("A", contravariant=True)
B = TypeVar("B", covariant=True)
C = TypeVar("C")


class I(M, Generic[A]):
    def __ge__(self, f: Callable[[A], Callable[[], B]]):  # type: ignore[override]
        return IO.bind(self.a, f)

    @classmethod
    def return_(cls, a: A) -> "I[None]":
        return I(IO.return_(a))

    def __eq__(self, other):
        try:
            return self.unwrap(self)() == self.unwrap(other)()
        except TypeError:
            breakpoint()


class IO(BaseMonad[A, Callable[[], A], Callable[[], B]]):
    """
    >>> def returns_1_with_side_effects():
    ...     print("foo")
    ...     return 1
    ...
    >>> def returns_2_with_side_effects():
    ...     print("bar")
    ...     return 2

    >>> def io():
    ...     x = yield returns_1_with_side_effects
    ...     y = yield returns_2_with_side_effects
    ...     yield lambda: print(x + y)
    ...
    >>> IO.do(io)
    foo
    bar
    3
    """

    @classmethod
    def bind(cls, x: Callable[[], A], f: Callable[[A], Callable[[], B]]) -> Callable[[], B]:  # type: ignore[override]
        return f(x())

    @classmethod
    def do(  # type: ignore[override]
        cls,
        generator: Callable[[], Generator[Callable[[], A], A, None]],
        *args,
        **kwargs,
    ):
        it = generator(*args, **kwargs)

        def f(y: A) -> Callable[[], B]:
            try:
                z = it.send(y)
            except StopIteration:
                return y  # type:ignore[return-value] # pyre-ignore[7]

            return cls.bind(z, f)

        return f(next(it)())

    @classmethod
    def return_(cls, a):
        return lambda: a
