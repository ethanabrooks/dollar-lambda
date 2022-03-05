"""
Argument parsers generate a sequence of `KeyValue` pairs that store mappings from variable names to values.
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
