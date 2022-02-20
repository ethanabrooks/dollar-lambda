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
# This is shorthand for the following:

# %% pycharm={"name": "#%%\n"}
from monad_argparse import Parser


def g():
    x1 = yield Argument("first")
    x2 = yield Argument("second")
    yield Parser.return_(x1 + x2)


Parser.do(g).parse_args("a", "b")

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

# %% pycharm={"name": "#%%\n"}
p1 = Flag("verbose") | Flag("quiet") | Flag("yes")
p = p1 >> Argument("a")
p.parse_args("--verbose", "value")

# %% [markdown]
# What about doing this many times?

# %% pycharm={"name": "#%%\n"}
p2 = p1.many()
p = p2 >> Argument("a")
p.parse_args("--verbose", "value")
