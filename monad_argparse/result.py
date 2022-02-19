from typing import Callable, Generic, Union

from monad_argparse.monad import A, BaseMonad, M


class R(M, Generic[A]):
    def __ge__(self, f: Callable[[A], Union[Exception, A]]):  # type: ignore[override]
        return Result.bind(self.a, f)

    @classmethod
    def return_(cls, a: A) -> "R[Union[A, Exception]]":
        return R(Result.return_(a))


class Result(BaseMonad[A, Union[A, Exception], Union[A, Exception]]):
    """
    >>> def results():
    ...     x = yield 1
    ...     y = yield 2
    ...     yield x + y
    ...
    >>> Result.do(results)
    3
    >>> def results():
    ...     x = yield 1
    ...     y = yield RuntimeError("Oh no!")
    ...     yield x + y
    ...
    >>> Result.do(results)
    RuntimeError('Oh no!')
    """

    @classmethod
    def bind(  # type: ignore[override]
        cls,
        x: Union[A, Exception],
        f: Callable[[A], Union[A, Exception]],
    ) -> Union[A, Exception]:
        if isinstance(x, Exception):
            return x
        y = f(x)  # type: ignore[arg-type]
        return y
