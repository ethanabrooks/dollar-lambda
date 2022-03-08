# ---
# jupyter:
#   jupytext:
#     formats: py:percent,ipynb
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
# # [$λ](https://ethanabrooks.github.io/dollar-lambda/)
# ## Not the parser that we need, but the parser we deserve.
#
# `$λ` is an argument parser for python.
# It was built with minimal dependencies from functional first principles.
# As a result, it is the most
#
# - versatile
# - type-safe
# - intuitive (with a little practice)
# - and (in many cases) concise
#
# argument parser on the market.
#
# ### Versatile
# `$λ` provides high-level functionality equivalent to other parsers. But unlike other parsers,
# it permits low-level customization to handle arbitrarily complex parsing patterns.
# ### Type-safe
# `$λ` uses type annotations as much as Python allows. Types are checked
# using [`MyPy`](https://mypy.readthedocs.io/en/stable/index.html#) and exported with the package
# so that users can also benefit from the type system.
# ### Intuitive
# The way that `$λ` parsers are written, they almost look like the "usage" messages
# that we are all used to.
# ### Concise
# `$λ` uses Python's builtin operators and [`dataclasses`](https://docs.python.org/3/library/dataclasses.html)
# to enable users to write parsers with minimal boilerplate.
#
#
# Special thanks to ["Functional Pearls"](https://www.cs.nott.ac.uk/~pszgmh/pearl.pdf) by Graham Hutton and Erik Meijer for bringing these topics to life.
# ## [Docs](https://ethanabrooks.github.io/dollar-lambda/)
# ## Installation
# ```
# pip install -U dollar-lambda
# ```
# ## Example Usage
# %%
from dataclasses import dataclass, field

from dollar_lambda import Args, done


@dataclass
class Args1(Args):
    many: int
    args: list = field(default_factory=list)


from dollar_lambda import field


@dataclass
class Args2(Args):
    different: bool
    args: set = field(type=lambda s: {int(x) for x in s}, help="this is a set!")


p = (Args1.parser() | Args2.parser()) >> done()
# %% [markdown]
# You can run this parser with one set of args:
# %%
p.parse_args("--many", "2", "--args", "abc")
# %% [markdown]
# Or the other set of args:
# %%
p.parse_args("--args", "123", "--different")  # order doesn't matter
# %% [markdown]
# But not both:
# %%
p.parse_args("--many", "2", "--different", "--args", "abc")
