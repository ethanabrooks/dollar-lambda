mypy:
	mypy --show-error-codes --exclude=readme.py dollar_lambda

test:
	python -m unittest test.py

readme: readme.py
	rm -rf readme.rst
	jupytext --sync readme.py
	TESTING=1 jupyter nbconvert --to rst --execute readme.ipynb
	mv readme.rst README.rst

docs: dollar_lambda/
	rm -rf docs/
	pdoc3 --html dollar_lambda --force
	mv html/dollar_lambda docs/
	rm -rf html
