$ErrorActionPreference = "Stop"
python -m pytest -q
python -m ruff check .
python -m ruff format --check .
python -m mypy app
python -m pip_audit
