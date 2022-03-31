<p align="center">
  <img height="300" src="https://ethanabrooks.github.io/dollar-lambda/logo.png">
</p>

[$λ](https://ethanabrooks.github.io/dollar-lambda/) provides an alternative to [`argparse`](https://docs.python.org/3/library/argparse.html)
based on parser combinators and functional first principles. Arguably, `$λ` is way more expressive than any reasonable
person would ever need... but even if it's not the parser that we need, it's the parser we deserve.

# Installation
```
pip install dollar-lambda
```

# [Documentation](https://ethanabrooks.github.io/dollar-lambda/dollar_lambda/)

# Highlights
`$λ` comes with syntactic sugar that came make building parsers completely boilerplate-free.
However, with more concise syntax comes less flexibility. For more complex parsing situations,
there are modular building blocks that lie behind the syntactic sugar which enable parsers to
handle any reasonable amount of logical complexity.

## The [`@command`](https://ethanabrooks.github.io/dollar-lambda/dollar_lambda/#dollar_lambda.command) decorator
This syntax is best for simple parsers that take a set of unordered arguments:


```python
from dollar_lambda import command


@command()
def main(x: int, dev: bool = False, prod: bool = False):
    return dict(x=x, dev=dev, prod=prod)
```

Here is the help text generated by this parser:


```python
main("-h")
```

    usage: -x X --dev --prod



```python
main("-x", "1", "--dev")
```




    {'x': 1, 'dev': True, 'prod': False}



Use the `parsers` argument do add custom logic to this parser:


```python
from dollar_lambda import flag


@command(parsers=dict(kwargs=(flag("dev") | flag("prod"))))
def main(x: int, **kwargs):
    return dict(x=x, **kwargs)


main("-h")
```

    usage: -x X [--dev | --prod]


This parser requires either a `--dev` or `--prod` flag and maps them to the `kwargs` argument:


```python
main("-x", "1", "--dev")
```




    {'x': 1, 'dev': True}




```python
main("-x", "1", "--prod")
```




    {'x': 1, 'prod': True}




```python
main("-x", "1")
```

    usage: -x X [--dev | --prod]
    The following arguments are required: --dev


## `CommandTree` for dynamic dispatch
For many programs, a user will want to use one entrypoint for one set of
arguments, and another for another set of arguments. Returning to our example,
let's say we wanted to execute `prod_function` when the user provides the
`--prod` flag, and `dev_function` when the user provides the `--dev` flag:


```python
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
```

Let's see how this parser handles different inputs.
If we provide the `--prod` flag, `$λ` automatically invokes
 `prod_function` with the parsed arguments:


```python
tree("-x", "1", "--prod")
```

    Ran prod_function with arguments: {'x': 1, 'prod': True}


If we provide the `--dev` flag, `$λ` invokes `dev_function`:


```python
tree("-x", "1", "--dev")
```

    Ran dev_function with arguments: {'x': 1, 'dev': True}


With this configuration, the parser will run `base_function` if neither
`--prod` nor `--dev` are given:


```python
tree("-x", "1")
```

    Ran base_function with arguments: {'x': 1}


As with `main` in the previous example, you would ordinarily provide `tree` no arguments and it would get them
from the command line.

There are many other ways to use `CommandTree`,
including some that make use of the `base_function`.
To learn more, we recommend the [`CommandTree` tutorial](https://ethanabrooks.github.io/dollar-lambda/dollar_lambda/#commandtree-tutorial).

## Lower-level syntax
[`@command`](https://ethanabrooks.github.io/dollar-lambda/dollar_lambda/#dollar_lambda.command) and `CommandTree` cover many use cases,
but they are both syntactic sugar for a lower-level interface that is far
more expressive.

Suppose you want to implement a parser that first tries to parse an option
(a flag that takes an argument),
`-x X` and if that fails, tries to parse the input as a variadic sequence of
floats:


```python
from dollar_lambda import argument, option

p = option("x", type=int) | argument("y", type=float).many()
```

We go over this syntax in greater detail in the [tutorial](https://ethanabrooks.github.io/dollar-lambda/dollar_lambda/#tutorial).
For now, suffice to say that `argument` defines a positional argument,
[`many`](https://ethanabrooks.github.io/dollar-lambda/dollar_lambda/#dollar_lambda.Parser.many) allows parsers to be applied
zero or more times, and [`|`](https://ethanabrooks.github.io/dollar-lambda/dollar_lambda/#dollar_lambda.Parser.__or__) expresses alternatives.

Here is the help text:


```python
p.parse_args("-h")
```

    usage: [-x X | [Y ...]]


As promised, this succeeds:


```python
p.parse_args("-x", "1")
```




    {'x': 1}



And this succeeds:


```python
p.parse_args("1", "2", "3", return_dict=False)
```




    [('y', 1.0), ('y', 2.0), ('y', 3.0)]



Again, you would ordinarily provide `parse_args` no arguments and it would get the.
from the command line.

### Thanks
Special thanks to ["Functional Pearls"](https://www.cs.nott.ac.uk/~pszgmh/pearl.pdf) by Graham Hutton and Erik Meijer for bringing these topics to life.
