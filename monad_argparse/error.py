"""
This package contains definitions for errors which can be raised by parsers.
"""
from dataclasses import dataclass
from typing import Generic, TypeVar


@dataclass
class ArgumentError(Exception):
    pass


A = TypeVar("A")


@dataclass
class UnequalError(ArgumentError, Generic[A]):
    left: A
    right: A


@dataclass
class MissingError(ArgumentError):
    missing: str


@dataclass
class ZeroError(ArgumentError):
    pass


@dataclass
class UnexpectedError(ArgumentError):
    unexpected: str
