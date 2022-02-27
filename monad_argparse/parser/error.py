from dataclasses import dataclass
from typing import Optional


@dataclass
class ArgumentError(Exception):
    token: Optional[str] = None
    description: Optional[str] = None
