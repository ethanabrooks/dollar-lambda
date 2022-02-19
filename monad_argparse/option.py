from typing import Callable, Generic, Optional

from monad_argparse.monad import MB, A, B, BaseMonad, M


class O(M, Generic[A]):
    def __ge__(self, f: Callable[[A], MB]):
        return Option.bind(self.a, f)

    @classmethod
    def return_(cls, a: A) -> "O[Optional[A]]":
        return O(Option.return_(a))


class Option(BaseMonad[A, Optional[A], Optional[B]]):
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
