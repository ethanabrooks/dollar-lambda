mypy:
	mypy --show-error-codes --exclude=readme.py monad_argparse

test:
	python -m unittest test.py

docs:
	rm -f readme.md
	jupytext --sync readme.py
	TESTING=1 jupyter nbconvert --to markdown --execute readme.ipynb
	pdoc3 --html monad_argparse --force
	mv html/monad_argparse docs/
	rm -rf html
