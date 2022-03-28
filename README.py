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
# <p align="center">
#   <img height="300" src="https://ethanabrooks.github.io/dollar-lambda/logo.png">
# </p>
#
# [$λ](https://ethanabrooks.github.io/dollar-lambda/) provides an alternative to [`argparse`](https://docs.python.org/3/library/argparse.html)
# based on parser combinators and functional first principles. Arguably, `$λ` is way more expressive than any reasonable
# person would ever need... but even if it's not the parser that we need, it's the parser we deserve.
#
# # Installation
# ```
# pip install dollar-lambda
# ```
#
# # [Documentation](https://ethanabrooks.github.io/dollar-lambda/dollar_lambda/)
#
# # Highlights
# `$λ` comes with syntactic sugar that came make building parsers completely boilerplate-free.
# However, with more concise syntax comes less flexibility. For more complex parsing situations,
# there are modular building blocks that lie behind the syntactic sugar which enable parsers to
# handle any reasonable amount of logical complexity.
#
# ## The [`@command`](#dollar_lambda.command) decorator
# This syntax is best for simple parsers that take a set of unordered arguments:


# %%
from dollar_lambda import command


@command()
def main(x: int, dev: bool = False, prod: bool = False):
    return dict(x=x, dev=dev, prod=prod)


# %% [markdown]
# Here is the help text generated by this parser:

# %%
main("-h")

# %% [markdown]
# Note that ordinarily you would call `main` with no arguments and it would get arguments from the command line (`sys.argv[1:]`).
# In this tutorial we feed arguments explicitly for demonstration purposes only.

# %%
main("-x", "1", "--dev")

# %% [markdown]
# `command` takes arguments that allow you to supply
# help strings and custom types:

# %%
@command(
    types=dict(x=lambda x: int(x) + 1), help=dict(x="A number that gets incremented.")
)
def main(x: int, dev: bool = False, prod: bool = False):
    return dict(x=x, dev=dev, prod=prod)


main("-h")

# %%
main("-x", "1", "--dev")

# %% [markdown]
# ## `CommandTree` for dynamic dispatch
# For many programs, a user will want to use one entrypoint for one set of
# arguments, and another for another set of arguments. Returning to our example,
# let's say we wanted to execute `prod_function` when the user provides the
# `--prod` flag, and `dev_function` when the user provides the `--dev` flag:

# %%
from dollar_lambda import CommandTree

tree = CommandTree()


@tree.command()
def base_function(x: int):
    print("Ran base_function with arguments:", dict(x=x))


@base_function.command()
def prod_function(x: int, prod: bool):
    print("Ran prod_function with arguments:", dict(x=x, prod=prod))


@base_function.command()
def dev_function(x: int, dev: bool):
    print("Ran dev_function with arguments:", dict(x=x, dev=dev))


# %% [markdown]
# Let's see how this parser handles different inputs.
# If we provide the `--prod` flag, `$λ` automatically invokes
#  `prod_function` with the parsed arguments:

# %%
tree("-x", "1", "--prod")

# %% [markdown]
# If we provide the `--dev` flag, `$λ` invokes `dev_function`:

# %%
tree("-x", "1", "--dev")

# %% [markdown]
# With this configuration, the parser will run `base_function` if neither
# `--prod` nor `--dev` are given:

# %%
tree("-x", "1")

# %% [markdown]
# There are many other ways to use `CommandTree`,
# including some that make use of the `base_function`.
# To learn more, we recommend the [`CommandTree` tutorial](#commandtree-tutorial).
#
# ## Lower-level syntax
# [`@command`](#dollar_lambda.command) and `CommandTree` cover many use cases,
# but they are both syntactic sugar for a lower-level interface that is far
# more expressive.
#
# Suppose you want to implement a parser that first tries to parse an option
# (a flag that takes an argument),
# `-x X` and if that fails, tries to parse the input as a variadic sequence of
# floats:

# %%
from dollar_lambda import argument, option

p = option("x", type=int) | argument("y", type=float).many()

# %% [markdown]
# We go over this syntax in greater detail in the [tutorial](#tutorial).
# For now, suffice to say that `argument` defines a positional argument,
# [`many`](#dollar_lambda.Parser.many) allows parsers to be applied
# zero or more times, and [`|`](#dollar_lambda.Parser.__or__) expresses alternatives.
#
# Here is the help text:

# %%
p.parse_args("-h")

# %% [markdown]
# As promised, this succeeds:

# %%
p.parse_args("-x", "1")

# %% [markdown]
# And this succeeds:

# %%
p.parse_args("1", "2", "3", return_dict=False)

# %% [markdown]
# ### Thanks
# Special thanks to ["Functional Pearls"](https://www.cs.nott.ac.uk/~pszgmh/pearl.pdf) by Graham Hutton and Erik Meijer for bringing these topics to life.
