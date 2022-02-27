from typing import Callable, Union

from monad_argparse.monad.monad import A, M, Monad


class R(M[Union[Exception, A]]):
    def __ge__(self, f: Callable[[A], Union[Exception, A]]):  # type: ignore[override]
        return R(Result.bind(self.a, f))

    @staticmethod
    def return_(a: A) -> "R[Union[Exception, A]]":
        return R(a)


class Result(Monad[A, Union[A, Exception]]):
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

    @classmethod
    def return_(cls, a: A) -> Union[A, Exception]:
        return a
