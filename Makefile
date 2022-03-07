mypy:
	mypy --show-error-codes --exclude=readme.py dollar_lambda

test:
	python -m unittest test.py

docs: readme.py dollar_lambda
	rm -rf readme.md docs/
	jupytext --sync readme.py
	TESTING=1 jupyter nbconvert --to markdown --execute readme.ipynb
	pdoc3 --html dollar_lambda --force
	mv html/dollar_lambda docs/
	rm -rf html
