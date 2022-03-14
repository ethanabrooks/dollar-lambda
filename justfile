default:

init-poetry:
    # TODO fix installed Python package versions.
    # TODO can this be any faster?
    # TODO it seems like importlib-metadata, zipp, and packaging keep getting
    #      reinstalled.
    [ -d .venv ] || python -m venv .venv
    .venv/bin/pip install --upgrade pip
    .venv/bin/pip install poetry
    .venv/bin/poetry install

clean:
    rm -rf .venv .mypy_cache .flake8 .tmp

pre-commit:
    @just build

build:
    ./build
