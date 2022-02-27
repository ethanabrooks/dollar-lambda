import abc
from typing import TypeVar

from monad_argparse.monad.monad import Monad

A = TypeVar("A", covariant=True)
MA = TypeVar("MA")


class MonadZero(Monad[A, MA]):
    @classmethod
    @abc.abstractmethod
    def zero(cls) -> MA:
        raise NotImplementedError


class MonadPlus(MonadZero[A, MA]):
    @abc.abstractmethod
    def __add__(self, other: MA) -> MA:
        raise NotImplementedError
