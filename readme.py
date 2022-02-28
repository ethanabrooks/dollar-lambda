# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:percent,md
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.13.7
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---
# type: ignore[import]

# %% [markdown]
# # Monad Argparse
#
# ### An alternative to `argparse` based on [Functional Pearls: Monadic Parsing in Haskell](https://www.cs.nott.ac.uk/~pszgmh/pearl.pdf)

# %% [markdown] pycharm={"name": "#%% md\n"}
# Arguments

# %% pycharm={"name": "#%%\n"}
from monad_argparse import Argument

Argument("name").parse_args("Ethan")

# %% [markdown]
# Flags

# %%
from monad_argparse import Flag

Flag("verbose").parse_args("--verbose")

# %% [markdown]
# Options

# %% pycharm={"name": "#%%\n"}
from monad_argparse import Option

Option("value").parse_args("--value", "x")

# %% [markdown]
# Failure

# %% pycharm={"name": "#%%\n"}
Option("value").parse_args("--value")

# %% [markdown]
# Alternatives (or "Sums")

# %% pycharm={"name": "#%%\n"}
p = Flag("verbose") | Option("value")
p.parse_args("--verbose")

# %% pycharm={"name": "#%%\n"}
p.parse_args("--value", "x")

# %% [markdown]
# Sequencing

# %% pycharm={"name": "#%%\n"}
p = Argument("first") >> Argument("second")
p.parse_args("a", "b")

# %% [markdown]
# Variable arguments

# %% pycharm={"name": "#%%\n"}
p = Argument("many").many()
p.parse_args("a", "b")

# %% pycharm={"name": "#%%\n"}
p = (Flag("verbose") | Flag("quiet")).many()
p.parse_args("--verbose", "--quiet")

# %% pycharm={"name": "#%%\n"}
p.parse_args("--quiet", "--verbose")

# %% pycharm={"name": "#%%\n"}
p.parse_args("--quiet")

# %% pycharm={"name": "#%%\n"}
p.parse_args("--quiet", "--quiet", "--quiet")

# %% [markdown]
# Combine sequences and sums

from typing import Sequence, Union

# %% pycharm={"name": "#%%\n"}
p1 = Flag("verbose") | Flag("quiet") | Flag("yes")
p2 = Argument("a")
p = p1 >> Argument("a")
p.parse_args("--verbose", "value")

# %% [markdown]
# What about doing this many times?

# %% pycharm={"name": "#%%\n"}
p2 = p1.many()
p = p2 >> Argument("a")
p.parse_args("--verbose", "value")

# %% [markdown]
# `monad_argparse` of course defines a utility, `Parser.nonpositional` for handling non-positional arguments as well. But seeing how easy it is to implement such a parser illustrates the power of this approach to parsing.
# First let's introduce a simple utility function: `empty()`. This parser always returns the empty list.

# %% pycharm={"name": "#%%\n"}
from monad_argparse import Parser

p = Parser.empty()
p.parse_args("any", "arguments")

# %% [markdown]
# Using this function, we can define a parser for nonpositional arguments.

# %% pycharm={"name": "#%%\n"}
from functools import reduce


def nonpositional(*parsers):
    if not parsers:
        return Parser.empty()

    def get_alternatives():
        """
        For each parser in `parsers`, this function returns a new parser,
        sequencing that parser with `nonpositional` applied to the rest of the parsers.
        """
        for i, head in enumerate(parsers):
            tail = [
                p for j, p in enumerate(parsers) if j != i
            ]  # get the parsers not including `head`
            yield head >> Parser.nonpositional(*tail)

    return reduce(
        lambda a, b: a | b, get_alternatives()
    )  # This applies the `|` operator to all the parsers in `get_alternatives()`


# %% [markdown]
# Let's test it:


# %% pycharm={"name": "#%%\n"}
p = nonpositional(Flag("verbose"), Flag("debug"))
p.parse_args("--verbose", "--debug")

# %% pycharm={"name": "#%%\n"}
p = nonpositional(Flag("verbose"), Flag("debug"))
p.parse_args("--debug", "--verbose")

# %% pycharm={"name": "#%%\n"}
p = Parser.nonpositional(Flag("verbose"), Flag("debug"), Argument("a"))
p.parse_args("--debug", "hello", "--verbose")
