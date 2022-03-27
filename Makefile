.PHONY: mypy
mypy:
	mypy --show-error-codes --exclude=readme.py dollar_lambda

.PHONY: test
test:
	python -m unittest test.py

.PHONY: readme
readme: README.py
	rm -rf README.rst
	jupytext --sync README.py
	DOLLAR_LAMBDA_TESTING=1 jupyter nbconvert --to markdown --execute README.ipynb

.PHONY: docs
docs: dollar_lambda/
	rm -rf docs/
	pdoc3 --html dollar_lambda
	mv html/dollar_lambda docs/
	rm -rf html
