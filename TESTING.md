# Testing

Install development dependencies with `python -m pip install -r requirements-dev.txt`.

The focused unit suite covers webhook HMAC verification, text payload parsing,
memory safety policy, deterministic calculator behavior, and language-neutral
intent resolution. Run `pytest -q` after installing `requirements.txt`.

Run `ruff check .` and `ruff format --check .` for style. Run `alembic upgrade head`
against a disposable PostgreSQL database. Integration checks should exercise Redis
stream retry/reclaim, duplicate webhook delivery, API signature rejection, worker
outbound requests using HTTP mocks, and the simulator with a mocked model. Real Meta
or model credentials are not required for automated tests.
