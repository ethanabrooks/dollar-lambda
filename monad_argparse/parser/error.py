from dataclasses import dataclass
from typing import Generic, TypeVar

from monad_argparse.monad.monoid import Monoid

A = TypeVar("A", bound=Monoid)


@dataclass
class ArgumentError(Exception):
    pass


B = TypeVar("B")


@dataclass
class UnequalError(ArgumentError, Generic[B]):
    left: B
    right: B


@dataclass
class MissingError(ArgumentError):
    missing: str


@dataclass
class ZeroError(ArgumentError):
    pass


@dataclass
class UnexpectedError(ArgumentError):
    unexpected: str
