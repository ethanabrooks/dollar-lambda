"""
Defines errors which can be raised by parsers.
"""
from dataclasses import dataclass
from typing import Generic, TypeVar


@dataclass
class ArgumentError(Exception):
    usage: str


A = TypeVar("A")


@dataclass
class ExceptionError(ArgumentError):
    exception: Exception


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


@dataclass
class HelpError(ArgumentError):
    usage: str
