import abc
from typing import Generic, TypeVar

from monad_argparse.monad.monad import Monad

A = TypeVar("A", covariant=True)
MA = TypeVar("MA")


class Monoid(Generic[A, MA]):
    @abc.abstractmethod
    def __or__(self, other: MA) -> MA:
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def zero(cls) -> MA:
        raise NotImplementedError


class MonadPlus(Monad[A, MA], Monoid[A, MA]):
    pass
