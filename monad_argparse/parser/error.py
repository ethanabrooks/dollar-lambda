from dataclasses import dataclass
from typing import Generic, Optional, TypeVar

from monad_argparse.monad.monoid import Monoid

A = TypeVar("A", bound=Monoid)


@dataclass
class MissingError(Exception, Generic[A]):
    default: A


@dataclass
class ArgumentError(Exception):
    token: Optional[str] = None
    description: Optional[str] = None
