"""
λ This package provides an alternative to [`argparse`](https://docs.python.org/3/library/argparse.html) based on functional first principles.
This means that this package can handle many kinds of argument-parsing patterns that are either very awkward, difficult, or impossible with `argparse`.

# Example
Here is an example developed in the `argparse` tutorial:

>>> import argparse

>>> parser = argparse.ArgumentParser(description="calculate X to the power of Y")
... group = parser.add_mutually_exclusive_group()
... group.add_argument("-v", "--verbose", action="store_true")
... group.add_argument("-q", "--quiet", action="store_true")
... parser.add_argument("x", type=int, help="the base")
... parser.add_argument("y", type=int, help="the exponent")
... args = parser.parse_args()

Here is the equivalent in this package:

>>> p = nonpositional(
...     (
...         defaults(verbose=False, quiet=False)
...         | flag("verbose") + defaults(quiet=False)
...         | flag("quiet") + defaults(verbose=False)
...     ),
...     option("x"),
...     option("y"),
... ) >> done()
>>> p.parse_args("-x", "1", "-y", "2")
{'verbose': False, 'quiet': False, 'x': '1', 'y': '2'}
>>> p.parse_args("-x", "1", "-y", "2", "--verbose")
{'x': '1', 'y': '2', 'verbose': True, 'quiet': False}
>>> p.parse_args("-x", "1", "-y", "2", "--verbose", "--quiet")
UnexpectedError(unexpected='--verbose')
"""


from monad_argparse.argument_parsers import (
    Args,
    apply,
    apply_item,
    argument,
    defaults,
    done,
    equals,
    flag,
    item,
    nonpositional,
    option,
    sat,
    sat_item,
    type_,
)
from monad_argparse.parser import Parser

__all__ = [
    "Parser",
    "apply",
    "apply_item",
    "argument",
    "done",
    "equals",
    "flag",
    "item",
    "nonpositional",
    "option",
    "sat",
    "sat_item",
    "type_",
    "Args",
    "defaults",
]
