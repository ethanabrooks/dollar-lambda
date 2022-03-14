all:
    @just docs mypy prettier readme test

mypy:
	mypy --show-error-codes --exclude=readme.py dollar_lambda

prettier:
    prettier --write .

test:
	python -m unittest test.py

readme:
	rm -rf readme.rst
	jupytext --sync readme.py
	DOLLAR_LAMBDA_TESTING=1 jupyter nbconvert --to markdown --execute readme.ipynb

docs:
	rm -rf docs/
	pdoc3 --html dollar_lambda --force
	mv html/dollar_lambda docs/
	rm -rf html
