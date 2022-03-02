from dataclasses import dataclass
from typing import Any, Generic, NamedTuple, TypeVar, Union

A = TypeVar("A", covariant=True)


@dataclass
class Missing(Generic[A]):
    default: A


@dataclass
class KeyValue(Generic[A]):
    key: str
    value: Union[A, Missing[A]]

    def get_value(self) -> A:
        if isinstance(self.value, Missing):
            value: Missing[A] = self.value
            return value.default
        return self.value


class KeyValueTuple(NamedTuple):
    key: str
    value: Any

    def __repr__(self):
        return repr(tuple(self))
