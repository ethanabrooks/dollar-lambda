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
# ### An alternative to `dollar_lambda` based on [Functional Pearls: Monadic Parsing in Haskell](https://www.cs.nott.ac.uk/~pszgmh/pearl.pdf)
#
# Arguments

# %%
from dollar_lambda import argument

argument("name").parse_args("Ethan")

# %% [markdown]
# Flags

# %%
from dollar_lambda import flag

flag("verbose").parse_args("--verbose")
# %% [markdown]
# Options

# %%
from dollar_lambda import option

option("value").parse_args("--value", "x")
# %% [markdown]
# Failure

# %%
from dollar_lambda import Parser

option("value").parse_args("--value")
# %% [markdown]
# Alternatives (or "Sums")

# %%
p = flag("verbose") | option("value")
p.parse_args("--verbose")

# %%
p.parse_args("--value", "x")
# %% [markdown]
# Sequencing

# %%
p = argument("first") >> argument("second")
p.parse_args("a", "b")
# %% [markdown]
# Variable arguments

# %%
p = argument("many").many()
p.parse_args("a", "b")
# %% [markdown]
#
# %%
p = (flag("verbose") | flag("quiet")).many()
p.parse_args("--verbose", "--quiet")
# %% [markdown]
#
# %%
p.parse_args("--quiet", "--verbose")
# %% [markdown]
#
# %%
p.parse_args("--quiet")
# %% [markdown]
#
# %%
p.parse_args("--quiet", "--quiet", "--quiet")
# %% [markdown]
# Combine sequences and sums

# %%
p1 = flag("verbose") | flag("quiet") | flag("yes")
p2 = argument("a")
p = p1 >> argument("a")
p.parse_args("--verbose", "value")
# %% [markdown]
# What about doing this many times?

# %%
p2 = p1.many()
p = p2 >> argument("a")
p.parse_args("--verbose", "value")
# %% [markdown]
# `monad_monad_argparse` of course defines a `nonpositional` utility for handling non-positional arguments as well. But seeing how easy it is to implement such a parser illustrates the power and flexibility of this library.
# First let's introduce a simple utility function: `empty()`. This parser always returns the empty list.

# %%
from dollar_lambda import empty

p = empty()
p.parse_args("any", "arguments")
import operator

# %% [markdown]
# Using this function, we can define a parser for nonpositional arguments.
#
# %%
from functools import reduce


def nonpositional(*parsers):
    if not parsers:
        return empty()

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

    return reduce(operator.or_, get_alternatives())


# %% [markdown]
# Let's test it:

# %%
from dollar_lambda import done

p = (
    nonpositional(flag("verbose", default=False), flag("debug", default=False))
    >> done()
)
p.parse_args("--verbose", "--debug")
# %% [markdown]
#
# %%
p.parse_args("--debug", "--verbose")
# %%
p.parse_args("--debug")
# %%
p.parse_args("--verbose")
# %% [markdown]
#
# %%
p = nonpositional(flag("verbose"), flag("debug"), argument("a"))
p.parse_args("--debug", "hello", "--verbose")
# %% [markdown]
#
