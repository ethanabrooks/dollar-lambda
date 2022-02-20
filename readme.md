# Monad Argparse

### An alternative to `argparse` based on [Functional Pearls: Monadic Parsing in Haskell](https://www.cs.nott.ac.uk/~pszgmh/pearl.pdf)

Arguments


```python
from monad_argparse import Argument

Argument("name").parse_args("Ethan")
```

Flags


```python
from monad_argparse import Flag

Flag("verbose").parse_args("--verbose")
```

Options


```python
from monad_argparse import Option

Option("value").parse_args("--value", "x")
```

Failure


```python
Option("value").parse_args("--value")
```

Alternatives (or "Sums")


```python
p = Flag("verbose") | Option("value")
p.parse_args("--verbose")
```


```python
p.parse_args("--value", "x")
```

Sequencing


```python
p = Argument("first") >> Argument("second")
p.parse_args("a", "b")
```

This is shorthand for the following:


```python
from monad_argparse import Parser


def g():
    x1 = yield Argument("first")
    x2 = yield Argument("second")
    yield Parser.return_(x1 + x2)


Parser.do(g).parse_args("a", "b")
```

Variable arguments


```python
p = Argument("many").many()
p.parse_args("a", "b")
```


```python
p = (Flag("verbose") | Flag("quiet")).many()
p.parse_args("--verbose", "--quiet")
```


```python
p.parse_args("--quiet", "--verbose")
```


```python
p.parse_args("--quiet")
```


```python
p.parse_args("--quiet", "--quiet", "--quiet")
```

Combine sequences and sums


```python
p1 = Flag("verbose") | Flag("quiet") | Flag("yes")
p = p1 >> Argument("a")
p.parse_args("--verbose", "value")
```

What about doing this many times?


```python
p2 = p1.many()
p = p2 >> Argument("a")
p.parse_args("--verbose", "value")
```
