.PHONY: help install run run-dev worker test clean

help:
	@echo "Available commands:"
	@echo "  make install      Install dependencies"
	@echo "  make run         Run production server"
	@echo "  make run-dev     Run development server with reload"
	@echo "  make worker      Run Celery worker"
	@echo "  make test        Run tests"
	@echo "  make clean       Clean up cache files"

install:
	pip install -r requirements.txt

run:
	uvicorn app.main:app --host 0.0.0.0 --port 8000

run-dev:
	uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

worker:
	celery -A app.worker.celery worker --loglevel=info

test:
	pytest

clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete 