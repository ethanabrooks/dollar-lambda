Nesting output
==============

By default introducing a ``.`` character into the name of an
:py:func:`argumnet <dollar_lambda.parser.argument>`, :py:func:`option <dollar_lambda.parser.option>`,
or :py:func:`flag <dollar_lambda.parser.flag>` will induce nested output:

>>> from dollar_lambda import argument, flag, option
>>> argument("a.b", type=int).parse_args("1")
{'a': {'b': 1}}
>>> option("a.b", type=int).parse_args("--a.b", "1")
{'a': {'b': 1}}
>>> flag("a.b").parse_args("--a.b")
{'a': {'b': True}}

This mechanism handles collisions:

>>> from dollar_lambda import flag
>>> (flag("a.b") >> flag("a.c")).parse_args("--a.b", "--a.c")
{'a': {'b': True, 'c': True}}

even when mixing nested and unnested output:

>>> (flag("a") >> flag("a.b")).parse_args("-a", "--a.b")
{'a': [True, {'b': True}]}

It can also go arbitrarily deep:

>>> (flag("a.b.c") >> flag("a.b.d")).parse_args("-a.b.c", "-a.b.d")
{'a': {'b': {'c': True, 'd': True}}}

This behavior can always be disabled by setting ``nesting=False`` (or
just not using ``.`` in the name).

Nesting with the :py:func:`@parser <dollar_lambda.decorators.parser>` decorator
===============================================================================

A common situation when processing command line arguments is to send one subset of
arguments to one function, another subset to another, and so on.
`$λ` provides a convenient syntax for doing this.

Suppose ``f`` is the function that will require some subset of our command line arguments:

>>> from dollar_lambda import parser
>>> @parser("args")
... def f(x: int, y: float):
...     print(dict(x=x, y=y))

A function wrapped with :py:func:`@parser <dollar_lambda.decorators.parser>` can still be called
like normal:

>>> f(1, 2.0)
{'x': 1, 'y': 2.0}

However, it now has a ``.parser`` property:

>>> f.parser.parse_args("--args.x", "1", "--args.y", "2.0")
{'args': {'x': 1, 'y': 2.0}}

This parser can be used to easily feed arguments to ``f`` as follows:

>>> from dollar_lambda import command
>>> @command(parsers=dict(args=f.parser))  # or parsers=f.parser_dict
... def main(z: bool, args: dict):
...     print(dict(z=z))
...     f(**args)
...
>>> main("-z", "--args.x", "1", "--args.y", "2.0")
{'z': True}
{'x': 1, 'y': 2.0}
