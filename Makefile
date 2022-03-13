.PHONY: mypy
mypy:
	mypy --show-error-codes --exclude=readme.py dollar_lambda

.PHONY: test
test:
	python -m unittest test.py

.PHONY: readme.md
readme.md: readme.py
	rm -rf readme.rst
	jupytext --sync readme.py
	DOLLAR_LAMBDA_TESTING=1 jupyter nbconvert --to markdown --execute readme.ipynb

.PHONY: docs
docs: dollar_lambda/
	rm -rf docs/
	pdoc3 --template-dir template --html dollar_lambda
	mv html/dollar_lambda docs/
	cp -r woff2 docs/woff2
	rm -rf html
