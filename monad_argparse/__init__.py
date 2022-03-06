"""
λ This package provides an alternative to [`argparse`](https://docs.python.org/3/library/argparse.html) based on functional first principles.
This means that this package can handle many kinds of argument-parsing patterns that are either very awkward, difficult, or impossible with `argparse`.

# Example
Here is an example developed in the `argparse` tutorial:
```
>>> import argparse

>>> parser = argparse.ArgumentParser(description="calculate X to the power of Y")
... group = parser.add_mutually_exclusive_group()
... group.add_argument("-v", "--verbose", action="store_true")
... group.add_argument("-q", "--quiet", action="store_true")
... parser.add_argument("x", type=int, help="the base")
... parser.add_argument("y", type=int, help="the exponent")
... args = parser.parse_args()
... dict(args)

```
Here is the equivalent in this package:
```
>>> from dataclasses import dataclass

>>> @dataclass
... class MyArgs(Args):
...     x: int = 0
...     y: int = 0

>>> p1 = MyArgs().parser
>>> p = nonpositional(
...     p1, flag("verbose", default=False)
... ) | nonpositional(
...     p1, flag("debug", default=False)
... )
>>> p.parse_args("-x", "1", "-y", "2")
{'x': 1, 'y': 2, 'verbose': False}
"""


from monad_argparse.argument_parsers import (
    Args,
    apply,
    apply_item,
    argument,
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
]
