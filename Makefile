.PHONY: install test lint run migrate demo

install:
	python3.11 -m venv .venv
	.venv/bin/python -m pip install -e '.[dev]'

test:
	.venv/bin/python -m pytest tests -q

lint:
	.venv/bin/ruff check .

run:
	.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

migrate:
	.venv/bin/alembic upgrade head

demo:
	curl -s http://127.0.0.1:8000/health
