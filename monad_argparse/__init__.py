"""
λ This package provides an alternative to [`argparse`](https://docs.python.org/3/library/argparse.html) based on functional first principles.
This means that this package can handle many kinds of argument-parsing patterns that are either very awkward, difficult, or impossible with `argparse`.

# Example
Here is an example developed in the `argparse` tutorial:

>>> import argparse
>>> parser = argparse.ArgumentParser(description="calculate X to the power of Y")
... group = parser.add_mutually_exclusive_group(required=True)
... group.add_argument("-v", "--verbose", action="store_true")
... group.add_argument("-q", "--quiet", action="store_true")
... parser.add_argument("x", type=int, help="the base")
... parser.add_argument("y", type=int, help="the exponent")
... args = parser.parse_args()

Here is the equivalent in this package:

>>> p = nonpositional(
...     (
...         flag("verbose") + defaults(quiet=False)
...         | flag("quiet") + defaults(verbose=False)
...     ),
...     option("x", type=int),
...     option("y", type=int),
... ) >> done()

Let's see it in action:
>>> p.parse_args("-x", "1", "-y", "2", "--verbose")
{'x': 1, 'y': 2, 'verbose': True, 'quiet': False}
>>> p.parse_args("-x", "1", "-y", "2", "--verbose", "--quiet")
UnexpectedError(unexpected='--quiet')

For `add_mutually_exclusive_group(required=False)`:

>>> p = nonpositional(
...     (
...         defaults(quiet=False, verbose=False)
...         | flag("verbose") + defaults(quiet=False)
...         | flag("quiet") + defaults(verbose=False)
...     ),
...     option("x", type=int),
...     option("y", type=int),
... ) >> done()

Now you can omit both `--quiet` and `--verbose`:
>>> p.parse_args("-x", "1", "-y", "2")
{'quiet': False, 'verbose': False, 'x': 1, 'y': 2}

Here is something you cannot do with argparse: what if there was a special argument, `verbosity`,
that only makes sense if the user chooses `--verbose`?

>>> p = nonpositional(
...     (
...         defaults(verbose=False, quiet=False)
...         | (
...             flag("verbose")
...             + option("verbosity", type=int)
...             + defaults(quiet=False)
...         )
...         | flag("quiet") + defaults(verbose=False)
...     ),
...     option("x", type=int),
...     option("y", type=int),
... ) >> done()

Now:
>>> p.parse_args("-x", "1", "-y", "2", "--quiet")
{'x': 1, 'y': 2, 'quiet': True, 'verbose': False}
>>> p.parse_args("-x", "1", "-y", "2", "--verbose", "--verbosity", "3")
{'x': 1, 'y': 2, 'verbose': True, 'verbosity': 3, 'quiet': False}
>>> p.parse_args("-x", "1", "-y", "2", "--verbose")
UnexpectedError(unexpected='--verbose')

What if we want to specify verbosity by the number of times that `--verbose` or `-v` appears?

>>> p = nonpositional(
...     (
...         flag("verbose").many1() + defaults(quiet=False)  # note .many1()
...         | flag("quiet") + defaults(verbose=False)
...     ),
...     option("x", type=int),
...     option("y", type=int),
... ) >> done()
>>> args = p.parse_args("-x", "1", "-y", "2", "-v", "--verbose", return_dict=False)
>>> args
[('x', 1), ('y', 2), ('verbose', True), ('verbose', True), ('quiet', False)]
>>> verbosity = args.count(('verbose', True))
>>> verbosity
2

You can also customize the order of the arguments:
>>> p = (
...     (
...         flag("verbose") + defaults(quiet=False)
...         | flag("quiet") + defaults(verbose=False)
...     )
...     >> option("x", type=int)  # note >> on this line
...     >> option("y", type=int)  # and this line
...     >> done()
... )

Now `--quiet` and `--verbose` must appear before `-x`, and `-x` must appear before `-y`:
>>> p.parse_args("--verbose", "-x", "1", "-y", "2")
{'verbose': True, 'quiet': False, 'x': 1, 'y': 2}
>>> p.parse_args("-x", "1", "--verbose", "-y", "2")
UnequalError(left='--verbose', right='-x')
>>> p.parse_args("--verbose", "-y", "2", "-x", "1")
UnequalError(left='-x', right='-y')
"""

from monad_argparse.argument_parsers import (
    Args,
    apply,
    apply_item,
    argument,
    defaults,
    done,
    empty,
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
    "empty",
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
