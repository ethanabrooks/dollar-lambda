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

# %% [markdown]
# # Monad Argparse
#
# ### An alternative to `monad_argparse` based on [Functional Pearls: Monadic Parsing in Haskell](https://www.cs.nott.ac.uk/~pszgmh/pearl.pdf)
#
# Arguments
#
#
#
#
#

# %%
from monad_argparse import argument

argument("name").parse_args("Ethan")
# %% [markdown]
#
#
#
#
#     [('name', 'Ethan')]
#
#
#
#
#
#
#
#     [('name', 'Ethan')]
#
#
#
#
#
#
#
#     [('name', 'Ethan')]
#
#
#
#
#
#
#
#     [('name', 'Ethan')]
#
#
#
#
#
#
#
#     [('name', 'Ethan')]
#
#
#
# Flags
#
#
#
#
#

# %%
from monad_argparse import flag

flag("verbose").parse_args("--verbose")
# %% [markdown]
#
#
#
#
#     [('verbose', True)]
#
#
#
#
#
#
#
#     [('verbose', True)]
#
#
#
#
#
#
#
#     [('verbose', True)]
#
#
#
#
#
#
#
#     [('verbose', True)]
#
#
#
#
#
#
#
#     [('verbose', True)]
#
#
#
# Options
#
#
#
#
#

# %%
from monad_argparse import option

option("value").parse_args("--value", "x")
# %% [markdown]
#
#
#
#
#     [('value', 'x')]
#
#
#
#
#
#
#
#     [('value', 'x')]
#
#
#
#
#
#
#
#     [('value', 'x')]
#
#
#
#
#
#
#
#     [('value', 'x')]
#
#
#
#
#
#
#
#     [('value', 'x')]
#
#
#
# Failure
#
#
#
#
#

# %%
option("value").parse_args("--value")
# %% [markdown]
#
#
#
#
#     MissingError(missing='value')
#
#
#
#
#
#
#
#     MissingError(missing='value')
#
#
#
#
#
#
#
#     MissingError(missing='value')
#
#
#
#
#
#
#
#     MissingError(missing='value')
#
#
#
#
#
#
#
#     MissingError(missing='value')
#
#
#
# Alternatives (or "Sums")
#
#
#
#
#

# %%
p = flag("verbose") | option("value")
p.parse_args("--verbose")
# %% [markdown]
#
#
#
#
#     [('verbose', True)]
#
#
#
#
#
#
#
#     [('verbose', True)]
#
#
#
#
#
#
#
#     [('verbose', True)]
#
#
#
#
#
#
#
#     [('verbose', True)]
#
#
#
#
#
#
#
#     [('verbose', True)]
#
#
#
#
#
#
#
#
#
#
#
#
# %%
p.parse_args("--value", "x")
# %% [markdown]
#
#
#
#
#     [('value', 'x')]
#
#
#
#
#
#
#
#     [('value', 'x')]
#
#
#
#
#
#
#
#     [('value', 'x')]
#
#
#
#
#
#
#
#     [('value', 'x')]
#
#
#
#
#
#
#
#     [('value', 'x')]
#
#
#
# Sequencing
#
#
#
#
#

# %%
p = argument("first") >> argument("second")
p.parse_args("a", "b")
# %% [markdown]
#
#
#
#
#     [('first', 'a'), ('second', 'b')]
#
#
#
#
#
#
#
#     [('first', 'a'), ('second', 'b')]
#
#
#
#
#
#
#
#     [('first', 'a'), ('second', 'b')]
#
#
#
#
#
#
#
#     [('first', 'a'), ('second', 'b')]
#
#
#
#
#
#
#
#     [('first', 'a'), ('second', 'b')]
#
#
#
# Variable arguments
#
#
#
#
#

# %%
p = argument("many").many()
p.parse_args("a", "b")
# %% [markdown]
#
#
#
#
#     [('many', 'a'), ('many', 'b')]
#
#
#
#
#
#
#
#     [('many', 'a'), ('many', 'b')]
#
#
#
#
#
#
#
#     [('many', 'a'), ('many', 'b')]
#
#
#
#
#
#
#
#     [('many', 'a'), ('many', 'b')]
#
#
#
#
#
#
#
#     [('many', 'a'), ('many', 'b')]
#
#
#
#
#
#
#
#
#
#
#
#
# %%
p = (flag("verbose") | flag("quiet")).many()
p.parse_args("--verbose", "--quiet")
# %% [markdown]
#
#
#
#
#     [('verbose', True), ('quiet', True)]
#
#
#
#
#
#
#
#     [('verbose', True), ('quiet', True)]
#
#
#
#
#
#
#
#     [('verbose', True), ('quiet', True)]
#
#
#
#
#
#
#
#     [('verbose', True), ('quiet', True)]
#
#
#
#
#
#
#
#     [('verbose', True), ('quiet', True)]
#
#
#
#
#
#
#
#
#
#
#
#
# %%
p.parse_args("--quiet", "--verbose")
# %% [markdown]
#
#
#
#
#     [('quiet', True), ('verbose', True)]
#
#
#
#
#
#
#
#     [('quiet', True), ('verbose', True)]
#
#
#
#
#
#
#
#     [('quiet', True), ('verbose', True)]
#
#
#
#
#
#
#
#     [('quiet', True), ('verbose', True)]
#
#
#
#
#
#
#
#     [('quiet', True), ('verbose', True)]
#
#
#
#
#
#
#
#
#
#
#
#
# %%
p.parse_args("--quiet")
# %% [markdown]
#
#
#
#
#     [('quiet', True)]
#
#
#
#
#
#
#
#     [('quiet', True)]
#
#
#
#
#
#
#
#     [('quiet', True)]
#
#
#
#
#
#
#
#     [('quiet', True)]
#
#
#
#
#
#
#
#     [('quiet', True)]
#
#
#
#
#
#
#
#
#
#
#
#
# %%
p.parse_args("--quiet", "--quiet", "--quiet")
# %% [markdown]
#
#
#
#
#     [('quiet', True), ('quiet', True), ('quiet', True)]
#
#
#
#
#
#
#
#     [('quiet', True), ('quiet', True), ('quiet', True)]
#
#
#
#
#
#
#
#     [('quiet', True), ('quiet', True), ('quiet', True)]
#
#
#
#
#
#
#
#     [('quiet', True), ('quiet', True), ('quiet', True)]
#
#
#
#
#
#
#
#     [('quiet', True), ('quiet', True), ('quiet', True)]
#
#
#
# Combine sequences and sums
#
#
#
#
#

# %%
p1 = flag("verbose") | flag("quiet") | flag("yes")
p2 = argument("a")
p = p1 >> argument("a")
p.parse_args("--verbose", "value")
# %% [markdown]
#
#
#
#
#     [('verbose', True), ('a', 'value')]
#
#
#
#
#
#
#
#     [('verbose', True), ('a', 'value')]
#
#
#
#
#
#
#
#     [('verbose', True), ('a', 'value')]
#
#
#
#
#
#
#
#     [('verbose', True), ('a', 'value')]
#
#
#
#
#
#
#
#     [('verbose', True), ('a', 'value')]
#
#
#
# What about doing this many times?
#
#
#
#
#

# %%
p2 = p1.many()
p = p2 >> argument("a")
p.parse_args("--verbose", "value")
# %% [markdown]
#
#
#
#
#     [('verbose', True), ('a', 'value')]
#
#
#
#
#
#
#
#     [('verbose', True), ('a', 'value')]
#
#
#
#
#
#
#
#     [('verbose', True), ('a', 'value')]
#
#
#
#
#
#
#
#     [('verbose', True), ('a', 'value')]
#
#
#
#
#
#
#
#     [('verbose', True), ('a', 'value')]
#
#
#
# `monad_monad_argparse` of course defines a `nonpositional` utility for handling non-positional arguments as well. But seeing how easy it is to implement such a parser illustrates the power and flexibility of this library.
# First let's introduce a simple utility function: `empty()`. This parser always returns the empty list.
#
#
#
#
#

# %%
from monad_argparse import Parser

p = Parser.empty()
p.parse_args("any", "arguments")
# %% [markdown]
#
#
#
#
#     []
#
#
#
#
#
#
#
#     []
#
#
#
#
#
#
#
#     []
#
#
#
#
#
#
#
#     []
#
#
#
#
#
#
#
#     []
#
#
#
# Using this function, we can define a parser for nonpositional arguments.
#
#
#
#
#

# %%
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
            yield head >> nonpositional(*tail)

    return reduce(
        lambda a, b: a | b, get_alternatives()
    )  # This applies the `|` operator to all the parsers in `get_alternatives()`


# %% [markdown]
# Let's test it:
#
#
#
#
#

# %%
p = nonpositional(flag("verbose"), flag("debug"))
p.parse_args("--verbose", "--debug")
# %% [markdown]
#
#
#
#
#     [('verbose', True), ('debug', True)]
#
#
#
#
#
#
#
#     [('verbose', True), ('debug', True)]
#
#
#
#
#
#
#
#     [('verbose', True), ('debug', True)]
#
#
#
#
#
#
#
#     [('verbose', True), ('debug', True)]
#
#
#
#
#
#
#
#     [('verbose', True), ('debug', True)]
#
#
#
#
#
#
#
#
#
#
#
#
# %%
p.parse_args("--debug", "--verbose")
# %% [markdown]
#
#
#
#
#     [('debug', True), ('verbose', True)]
#
#
#
#
#
#
#
#     [('debug', True), ('verbose', True)]
#
#
#
#
#
#
#
#     [('debug', True), ('verbose', True)]
#
#
#
#
#
#
#
#     [('debug', True), ('verbose', True)]
#
#
#
#
#
#
#
#     [('debug', True), ('verbose', True)]
#
#
#
#
#
#
#
#
#
#
#
#
# %%
p = nonpositional(flag("verbose"), flag("debug"), argument("a"))
p.parse_args("--debug", "hello", "--verbose")
# %% [markdown]
#
#
#
#
#     [('debug', True), ('a', 'hello'), ('verbose', True)]
#
#
#
#
#
#
#
#     [('debug', True), ('a', 'hello'), ('verbose', True)]
#
#
#
#
#
#
#
#     [('debug', True), ('a', 'hello'), ('verbose', True)]
#
#
#
#
#
#
#
#     [('debug', True), ('a', 'hello'), ('verbose', True)]
#
#
#
#
#
#
#
#     [('debug', True), ('a', 'hello'), ('verbose', True)]
