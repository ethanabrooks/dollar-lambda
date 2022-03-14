default:

init-poetry:
    # TODO fix installed Python package versions.
    # TODO can this be any faster?
    # TODO it seems like importlib-metadata, zipp, and packaging keep getting
    #      reinstalled.
    # TODO if this script changes, .envrc doesn’t notice and reload. Maybe
    #      .envrc should use Ninja to set this up.
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
