from typing import Callable, Generator, TypeVar

from monad_argparse.monad.monad import M, Monad

A = TypeVar("A")
B = TypeVar("B", covariant=True)
C = TypeVar("C")


class IO(Monad[A, Callable[[], A]]):
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

        def f(y: A):
            try:
                z = it.send(y)
            except StopIteration:
                return y  # type:ignore[return-value]

            return cls.bind(z, f)

        return f(next(it)())

    @classmethod
    def return_(cls, a: C) -> Callable[[], C]:
        return lambda: a


class I(M[Callable[[], A]]):
    def __ge__(self, f: Callable[[A], Callable[[], B]]):  # type: ignore[override]
        return IO.bind(self.a, f)

    @classmethod
    def return_(cls, a: A) -> "I[A]":
        return I(IO[A].return_(a))

    def __eq__(self, other) -> bool:
        if isinstance(other, I):
            return self.unwrap(self.a)() == other.unwrap(other)()
        return False
