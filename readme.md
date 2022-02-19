---
jupyter:
  jupytext:
    formats: ipynb,py:percent,md
    text_representation:
      extension: .md
      format_name: markdown
      format_version: '1.3'
      jupytext_version: 1.13.7
  kernelspec:
    display_name: Python 3 (ipykernel)
    language: python
    name: python3
---

# An alternative to `argparse` based on [Functional Pearls: Monadic Parsing in Haskell](https://www.cs.nott.ac.uk/~pszgmh/pearl.pdf)

<!-- #region pycharm={"name": "#%% md\n"} -->
Arguments
<!-- #endregion -->

```python pycharm={"name": "#%%\n"}
from monad_argparse import Argument

Argument("name").parse_args("Ethan")
```

Flags

```python
from monad_argparse import Flag

Flag("verbose").parse_args("--verbose")
```

Options

```python pycharm={"name": "#%%\n"}
from monad_argparse import Option

Option("value").parse_args("--value", "x")
```

Failure

```python pycharm={"name": "#%%\n"}
Option("value").parse_args("--value")
```

Alternatives (or "Sums")

```python pycharm={"name": "#%%\n"}
p = Flag("verbose") | Option("value")
p.parse_args("--verbose")
```

```python pycharm={"name": "#%%\n"}
p.parse_args("--value", "x")
```

Sequencing

```python pycharm={"name": "#%%\n"}
p = Argument("first") >> Argument("second")
p.parse_args("a", "b")
```

This is shorthand for the following:

```python pycharm={"name": "#%%\n"}
from monad_argparse import Parser


def g():
    x1 = yield Argument("first")
    x2 = yield Argument("second")
    yield Parser.return_([x1, x2])


Parser.do(g).parse_args("a", "b")
```

Variable arguments

```python pycharm={"name": "#%%\n"}
p = Argument("many").many()
p.parse_args("a", "b")
```

```python pycharm={"name": "#%%\n"}
p = (Flag("verbose") | Flag("quiet")).many()
p.parse_args("--verbose", "--quiet")
```

```python pycharm={"name": "#%%\n"}
p.parse_args("--quiet", "--verbose")
```

```python pycharm={"name": "#%%\n"}
p.parse_args("--quiet")
```

```python pycharm={"name": "#%%\n"}
p.parse_args("--quiet", "--quiet", "--quiet")
```

Combine sequences and sums

```python pycharm={"name": "#%%\n"}
p1 = Flag("verbose") | Flag("quiet") | Flag("yes")
p = p1 >> Argument("a")
p.parse_args("--verbose", "value")
```

What about doing this many times?

```python pycharm={"name": "#%%\n"}
p2 = p1.many()
p = p2 >> Argument("a")
p.parse_args("--verbose", "value")
```

The result is awkwardly nested. To deal with this, we use `Parser.do`:

```python pycharm={"name": "#%%\n"}
def g():  # type: ignore[no-redef]
    xs = yield p2
    x = yield Argument("a")
    yield Parser.return_(xs + [x])


Parser.do(g).parse_args("--verbose", "--quiet", "value")
```

A common pattern is to alternate checking for positional arguments with checking for non-positional arguments:

```python pycharm={"name": "#%%\n"}
def g():  # type: ignore[no-redef]
    xs1 = yield p2
    x1 = yield Argument("first")
    xs2 = yield p2
    x2 = yield Argument("second")
    xs3 = yield p2
    yield Parser.return_(xs1 + [x1] + xs2 + [x2] + xs3)


Parser.do(g).parse_args("a", "--verbose", "b", "--quiet")
```

A simpler way to do this is with the `interleave` method:

```python pycharm={"name": "#%%\n"}
def g():  # type: ignore[no-redef]
    return (Flag("verbose") | Flag("quiet") | Flag("yes")).interleave(
        Argument("first"), Argument("second")
    )


Parser.do(g).parse_args("a", "--verbose", "b", "--quiet")
```

or `build`:

```python pycharm={"name": "#%%\n"}
Parser.build(
    Flag("verbose") | Flag("quiet") | Flag("yes"), Argument("first"), Argument("second")
).parse_args("a", "--verbose", "b", "--quiet")
```
