Why ``$λ``?
===========

``$λ`` can handle many kinds of argument-parsing patterns that are
either very awkward, difficult, or impossible with other parsing
libraries. In particular, we emphasize the following qualities:

Versatile
---------

``$λ`` provides high-level functionality equivalent to other parsers.
But unlike other parsers, it permits low-level customization to handle
arbitrarily complex parsing patterns. There are many parsing patterns
that ``$λ`` can handle which are not possible with other parsing
libraries.

Type-safe
---------

``$λ`` uses type annotations as much as Python allows. Types are checked
using `MyPy <https://mypy.readthedocs.io/en/stable/index.html#>`__
and exported with the package so that users can also benefit from the
type system. Furthermore, with rare exceptions, ``$λ`` avoids mutations
and side-effects and preserves `referential
transparency <https://en.wikipedia.org/wiki/Referential_transparency>`__.
This makes it easier for the type-checker *and for the user* to reason
about the code.

Concise
-------

``$λ`` provides many syntactic shortcuts for cutting down boilerplate:

-  the :py:func:`@command <dollar_lambda.decorators.command>` decorator
-  the :py:class:`CommandTree<dollar_lambda.decorators.CommandTree>` object for
   automatically building parsers from function signatures (see :doc:`command_tree`)
-  the :py:func:`@parser <dollar_lambda.decorators.parser>` decorator (see :ref:`groupingwithparser`)

Lightweight
-----------

``$λ`` is written in pure python with no dependencies (excepting
`pytypeclass <https://github.com/ethanabrooks/pytypeclass>`__ which
was written expressly for this library and has no dependencies). ``$λ``
will not introduce dependency conflicts and it installs in a flash.
