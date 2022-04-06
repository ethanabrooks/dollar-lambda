Use with config files
=====================

A common use case is to have a config file with default values that
arguments should fall back to if not provided on the command line.
Instead of implementing specific functionality itself, ``$λ``
accommodates this situation by simply getting out of the way, thereby
affording the user the most flexibility in terms of accessing and using
the config file. Here is a simple example:

.. literalinclude:: ../example-config.json
   :caption: example-config.json
   :language: json

Define a parser with optional values where you want to be able to fall
back to the config file:

>>> from dollar_lambda import option, argument
>>> p = option("x", type=int).optional() >> argument("y", type=int)
>>> p.parse_args("-h")
usage: -x X Y

In this example, ``-x X`` can be omitted, falling back to the config,
but the positional argument ``Y`` will be required.

Make sure that the optional arguments do not have default values or else
the config value will always be overridden. Inside main, load the config
and update with any arguments provided on the command line:

>>> import json
>>> def main(**kwargs):
...     with open("example-config.json") as f:
...         config = json.load(f)
...
...     config.update(kwargs)
...     print(config)

Override ``x``'s value in the config by providing an explicit argument:

>>> main(**p.parse_args("-x", "0", "1"))
{'x': 0, 'y': 1}

Fall back to the value in the config by not providing an argument for ``x``:

>>> main(**p.parse_args("2"))
{'x': 1, 'y': 2}

Here is a version written with :py:func:`@command <dollar_lambda.decorators.command>` syntax:

>>> from dollar_lambda import command
>>> @command(
...     parsers=dict(
...         y=argument("y", type=int),
...         kwargs=option("x", type=int).optional(),
...     )
... )
... def main(y: int, **kwargs):
...     with open("example-config.json") as f:
...         config = json.load(f)
...
...     config.update(**kwargs, y=y)
...     print(config)
...
>>> main("-x", "0", "1")  # override config value for x
{'x': 0, 'y': 1}
>>> main("2")  # fallback to config value for x
{'x': 1, 'y': 2}
