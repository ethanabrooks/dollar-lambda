from dataclasses import dataclass
from typing import Optional, TypeVar

from monad_argparse.monad.monoid import Monoid

A = TypeVar("A", bound=Monoid)


@dataclass
class ArgumentError(Exception):
    token: Optional[str] = None
    description: Optional[str] = None
