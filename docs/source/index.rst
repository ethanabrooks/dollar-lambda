.. $λ documentation master file, created by
   sphinx-quickstart on Mon Apr  4 12:45:01 2022.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to $λ
==============

This package provides an alternative to
`argparse <https://docs.python.org/3/library/argparse.html>`_ based
on parser combinators and functional first principles. Arguably, ``$λ``
is way more expressive than any reasonable person would ever need... but
even if it's not the parser that we need, it's the parser we deserve.

Installation
============

.. code-block:: console

  pip install dollar-lambda

Highlights
==========

``$λ`` comes with syntactic sugar that came make building parsers
completely boilerplate-free. For complex parsing situations that exceed
the expressive capacity of this syntax, the user can also drop down to
the lower-level syntax that lies behind the sugar, which can handle any
reasonable amount of logical complexity.

The :py:func:`@command <dollar_lambda.decorators.command>` decorator
--------------------------------------------------------------------------

For the vast majority of parsing patterns, :py:class:`@command <dollar_lambda.decorators.command>` is the most
concise way to define a parser:

.. tabs::

  .. tab:: ``@command`` syntax

      >>> from dollar_lambda import command
      >>> @command()
      ... def main(x: int, dev: bool = False, prod: bool = False):
      ...     print(dict(x=x, dev=dev, prod=prod))
      ...
      >>> main("-h")
      usage: -x X --dev --prod
      dev: (default: False)
      prod: (default: False)
      >>> main("-x", "1", "-dev")
      {'x': 1, 'dev': True, 'prod': False}

  .. tab:: lower-level syntax

      >>> from dollar_lambda import nonpositional, option, flag
      ...
      >>> p = nonpositional(
      ...    option("x", type=int),
      ...    flag("dev", default=False),
      ...    flag("prod", default=False),
      ... )
      ...
      >>> def main(x: int, dev: bool = False, prod: bool = False):
      ...    print(dict(x=x, dev=dev, prod=prod))
      ...
      >>> p.parse_args("-h")
      usage: -x X --dev --prod
      dev: (default: False)
      prod: (default: False)
      >>> main(**p.parse_args("-x", "1", "-dev"))
      {'x': 1, 'dev': True, 'prod': False}

.. Note::

   Ordinarily you would provide ``main`` no arguments and it would get them
   from the command line.

Add custom logic with the ``parsers`` argument:

.. tabs::

  .. tab:: ``@command`` syntax

      >>> @command(parsers=dict(kwargs=(flag("dev") | flag("prod"))))
      ... def main(x: int, **kwargs):
      ...     print(dict(x=x, **kwargs))
      ...
      >>> main("-h")
      usage: -x X [--dev | --prod]
      >>> main("-x", "1", "-dev")
      {'x': 1, 'dev': True}
      >>> main("-x", "1", "-prod")
      {'x': 1, 'prod': True}
      >>> main("-x", "1")
      usage: -x X [--dev | --prod]
      The following arguments are required: --dev

  .. tab:: lower-level syntax

      >>> p = nonpositional(
      ...    option("x", type=int), flag("dev") | flag("prod"),
      ... )
      ...
      >>> def main(x: int, **kwargs):
      ...    print(dict(x=x, **kwargs))
      ...
      >>> p.parse_args("-h")
      usage: -x X [--dev | --prod]
      >>> main(**p.parse_args("-x", "1", "-dev"))
      {'x': 1, 'dev': True}
      >>> main(**p.parse_args("-x", "1", "-dev"))
      {'x': 1, 'dev': True}
      >>> main(**p.parse_args("-x", "1", "-prod"))
      {'x': 1, 'prod': True}
      >>> p.parse_args("-x", "1")
      usage: -x X [--dev | --prod]
      The following arguments are required: --dev

.. _DynamicDispatch:

:py:class:`CommandTree<dollar_lambda.decorators.CommandTree>` for dynamic dispatch
-----------------------------------------------------------------------------------

Execute ``prod_function`` for one set of command line arguments and ``dev_function``
for another:

>>> from dollar_lambda import CommandTree
...
>>> tree = CommandTree()
...
...
>>> @tree.command()
... def base_function(x: int):
...     print("Ran base_function with arguments:", dict(x=x))
...
>>> @base_function.command()
... def prod_function(x: int, prod: bool):
...     print("Ran prod_function with arguments:", dict(x=x, prod=prod))
...
>>> @base_function.command()
... def dev_function(x: int, dev: bool):
...     print("Ran dev_function with arguments:", dict(x=x, dev=dev))
...
>>> tree("-x", "1", "--prod")  # runs prod_function because of --prod
Ran prod_function with arguments: {'x': 1, 'prod': True}
>>> tree("-x", "1", "--dev")  # runs dev_function because of --dev
Ran dev_function with arguments: {'x': 1, 'dev': True}
>>> tree("-x", "1")  # runs base_function because of no flags
Ran base_function with arguments: {'x': 1}


.. Note::

   As with ``main`` in the previous example, you would ordinarily provide
   ``tree`` no arguments and it would get them from the command line.

Lower-level syntax
------------------

Use lower-level syntax for more complex parsers:

>>> from dollar_lambda import argument
>>> p = option("x", type=int) | argument("y", type=float).many()
...
>>> p.parse_args("-h")
usage: [-x X | [Y ...]]
>>> p.parse_args("-x", "1")  # execute parser on left side of |
{'x': 1}
>>> p.parse_args("1", "2", "3")  # execute parser on right side of |
{'y': [1.0, 2.0, 3.0]}

.. Note::

   Again, :py:meth:`parse_args <dollar_lambda.parsers.Parser.parse_args>`
   takes arguments from the command line when given no arguments.


.. toctree::
   :hidden:

   tutorial
   variations
   command_tree
   config
   nesting
   ignoring
   why
   api
