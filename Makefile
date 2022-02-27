test:
	python -m unittest test.py

docs:
	jupytext --sync readme.py
	jupyter nbconvert --to markdown --execute readme.ipynb
	pdoc3 --html monad_argparse --force
