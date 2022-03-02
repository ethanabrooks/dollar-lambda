from __future__ import annotations

import abc
from typing import Protocol, Type, TypeVar

from monad_argparse.monad.monad import Monad

A = TypeVar("A", covariant=True)
B = TypeVar("B", covariant=True)
C = TypeVar("C", bound="Monoid")


class Monoid(Protocol[A]):
    @abc.abstractmethod
    def __add__(self: C, other: C) -> C:
        raise NotImplementedError

    def __or__(self, other):
        return self + other

    @classmethod
    @abc.abstractmethod
    def zero(cls: Type[C]) -> C:
        raise NotImplementedError


class MonadPlus(Monad[A], Monoid[A]):
    pass
