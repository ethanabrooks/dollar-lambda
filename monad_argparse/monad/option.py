from typing import Callable, Optional

from monad_argparse.monad.monad import A, B, M, Monad


class O(M[Optional[A]]):
    def __ge__(self, f: Callable[[A], Optional[A]]):
        return O(Option.bind(self.a, f))

    @classmethod
    def return_(cls, a: A) -> "O[Optional[A]]":
        return O(Option.return_(a))


class Option(Monad[A, Optional[A]]):
    """
    >>> def options():
    ...     x = yield 1
    ...     y = yield 2
    ...     yield x + y
    ...
    >>> Option.do(options)
    3
    >>> def options():
    ...     x = yield 1
    ...     y = yield None
    ...     yield x + y
    ...
    >>> print(Option.do(options))  # added `print` in order to get None to show up
    None
    """

    @classmethod
    def bind(  # type: ignore[override]
        cls,
        x: Optional[A],
        f: Callable[[A], Optional[B]],
    ) -> Optional[B]:
        if x is None:
            return None
        return f(x)

    @classmethod
    def return_(cls, a: A) -> Optional[A]:
        return a
