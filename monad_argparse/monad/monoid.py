import abc
from typing import Generic, TypeVar, Union

from monad_argparse.monad.monad import Monad

A = TypeVar("A", covariant=True)
MA = TypeVar("MA")
MB = TypeVar("MB")


class Monoid(Generic[A, MA]):
    def __add__(self, other: MB) -> Union[MA, MB]:
        return self | other

    @abc.abstractmethod
    def __or__(self, other: MB) -> Union[MA, MB]:
        raise NotImplementedError

    @classmethod
    @abc.abstractmethod
    def zero(cls) -> MA:
        raise NotImplementedError


class MonadPlus(Monad[A, MA], Monoid[A, MA]):
    pass
