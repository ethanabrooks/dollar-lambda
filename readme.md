# [$λ](https://ethanabrooks.github.io/dollar-lambda/)
## Not the parser that we need, but the parser we deserve.

`$λ` is an argument parser for python.
It was built with minimal dependencies from functional first principles.
As a result, it is the most

- versatile
- type-safe
- and concise

argument parser on the market.

### Versatile
`$λ` provides high-level functionality equivalent to other parsers. But unlike other parsers,
it permits low-level customization to handle arbitrarily complex parsing patterns.
### Type-safe
`$λ` uses type annotations as much as Python allows. Types are checked
using [`MyPy`](https://mypy.readthedocs.io/en/stable/index.html#) and exported with the package
so that users can also benefit from the type system.
### Concise
`$λ` provides a variety of syntactic sugar options that enable users
to write parsers with minimal boilerplate.

## [Documentation](https://ethanabrooks.github.io/dollar-lambda/)
## Installation
```
pip install -U dollar-lambda
```
## Example Usage
For simple settings,`@command` can infer the parser for the function signature:


```python
from dollar_lambda import command


@command()
def main(foo: int = 0, bar: str = "hello", baz: bool = False):
    return dict(foo=foo, bar=bar, baz=baz)


main("-h")
```

    usage: --foo FOO --bar BAR --baz


This handles defaults:


```python
main()
```




    {'foo': 0, 'bar': 'hello', 'baz': False}



And of course allows the user to supply arguments:


```python
main("--foo", "1", "--bar", "goodbye", "--baz")
```




    {'foo': 1, 'bar': 'goodbye', 'baz': True}



`$λ` can also handle far more complex parsing patterns:


```python
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
```

You can run this parser with one set of args:


```python
p.parse_args("--many", "2", "--args", "abc")
```




    {'many': 2, 'args': ['a', 'b', 'c']}



Or the other set of args:


```python
p.parse_args("--args", "123", "--different")  # order doesn't matter
```




    {'args': {1, 2, 3}, 'different': True}



But not both:


```python
p.parse_args("--many", "2", "--different", "--args", "abc")
```

    usage: [--many MANY --args ARGS | --different --args ARGS]
    args: this is a set!
    Expected '--args'. Got '--different'


### Thanks
Special thanks to ["Functional Pearls"](https://www.cs.nott.ac.uk/~pszgmh/pearl.pdf) by Graham Hutton and Erik Meijer for bringing these topics to life.
