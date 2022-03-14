default:

init-poetry:
    [ -d .venv ] || python -m venv .venv
    .venv/bin/pip install --upgrade pip
    .venv/bin/pip install poetry
    .venv/bin/poetry install

clean:
    rm -rf .venv .mypy_cache .flake8 .tmp

pre-commit:
    @just build

just build:
    ./build
