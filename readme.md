# $λ
`$λ` is an argument parser for python.
It was built from functional first principles.
As a result, it is the most

- versatile
- type-safe
- intuitive (with a little practice)
- and (in many cases) concise

argument parser on the market.
### Help yourself to the [docs](https://ethanabrooks.github.io/dollar-lambda/)!

Special thanks to ["Functional Pearls"](https://www.cs.nott.ac.uk/~pszgmh/pearl.pdf) by Graham Hutton and Erik Meijer for bringing these topics to life for me.
## Installing
```
pip install -U dollar-lambda
```
## An Example


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
p.parse_args("--many", "--different", "--args", "abc")
```

    usage: [--many MANY --args ARGS | --different --args ARGS]
    args: this is a set!
    argument Sequence(get=[KeyValue(key='many', value='--different')]): raised exception invalid literal for int() with base 10: '--different'
