"""
Defines `KeyValue` which stores pairs of variable names (keys) and values.
"""
from dataclasses import dataclass
from typing import Any, Generic, NamedTuple, TypeVar

A = TypeVar("A", covariant=True)


@dataclass
class KeyValue(Generic[A]):
    key: str
    value: A


class KeyValueTuple(NamedTuple):
    key: str
    value: Any

    def __repr__(self):
        return repr(tuple(self))
