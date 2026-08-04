.PHONY: help install run migrate makemigrations test lint format clean

help:
	@echo "Available tasks:"
	@echo "  install          Install dependencies with uv and setup pre-commit"
	@echo "  run              Start Django development server"
	@echo "  migrate          Apply database migrations"
	@echo "  makemigrations   Create new database migrations"
	@echo "  test             Run pytest test suite"
	@echo "  lint             Run ruff linter"
	@echo "  format           Format code with ruff"
	@echo "  clean            Remove cache and temporary files"

install:
	uv sync
	uv run pre-commit install

run:
	uv run python src/trigger_engine/manage.py runserver 0.0.0.0:8000

migrate:
	uv run python src/trigger_engine/manage.py migrate

makemigrations:
	uv run python src/trigger_engine/manage.py makemigrations

test:
	uv run pytest tests/ -v

lint:
	uv run ruff check src/ tests/

format:
	uv run ruff format src/ tests/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
