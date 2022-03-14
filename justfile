pre-commit:
    nixfmt --check flake.nix || nixfmt flake.nix
    prettier --write .
    isort --profile black .
    flake8 dollar_lambda
    mypy --show-error-codes --exclude=readme.py dollar_lambda
    python -m unittest test.py
    @just readme
    @just docs

readme:
    jupytext --sync readme.py
    DOLLAR_LAMBDA_TESTING=1 jupyter nbconvert --to markdown --execute readme.ipynb
    prettier --write readme.md

docs:
    rm -rf docs/
    pdoc3 --html dollar_lambda --force
    mv html/dollar_lambda docs/
    rm -rf html
    prettier --write docs
