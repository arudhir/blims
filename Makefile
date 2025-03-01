.PHONY: setup clean lint test coverage run dev format check reformat docker-build docker-up docker-down docker-logs docker-shell help test-data aws aws-validate aws-deploy

# Default target
help:
	@echo "Available targets:"
	@echo "  setup        - Create virtual environment and install dependencies"
	@echo "  clean        - Remove temporary files"
	@echo "  lint         - Run linters"
	@echo "  format       - Format code with Black and isort"
	@echo "  check        - Check code style without modifying files"
	@echo "  reformat     - Run format, check, and lint in sequence"
	@echo "  test         - Run all tests"
	@echo "  test-verbose - Run tests with verbose output"
	@echo "  test-unit    - Run only unit tests (skipping API tests)"
	@echo "  coverage     - Run tests with coverage report"
	@echo "  run          - Run the application"
	@echo "  dev          - Run the application in development mode with auto-reload"
	@echo "  dev-setup    - Set up development environment with additional tools"
	@echo "  install-hooks - Install git pre-commit hooks"
	@echo "  test-data    - Create test data for development"
	@echo ""
	@echo "AWS commands:"
	@echo "  aws          - Interactive AWS deployment menu"
	@echo "  aws-validate - Validate AWS CloudFormation templates"
	@echo "  aws-deploy   - Deploy AWS infrastructure"
	@echo ""
	@echo "Docker commands:"
	@echo "  docker-build - Build the Docker image"
	@echo "  docker-up    - Start the Docker containers"
	@echo "  docker-down  - Stop the Docker containers"
	@echo "  docker-logs  - View Docker container logs"
	@echo "  docker-shell - Open a shell in the API container"
	@echo "  docker-dev   - Build and start the development environment"
	@echo ""
	@echo "Common workflows:"
	@echo "  make check test     - Validate code style and run tests"
	@echo "  make reformat       - Format code and run linters"

all: check test

# Environment and dependencies
setup:
	python -m venv venv
	. venv/bin/activate && uv pip install -r requirements.txt
	. venv/bin/activate && uv pip install pytest pytest-cov black isort mypy flake8

# Cleanup
clean:
	rm -rf __pycache__
	rm -rf *.pyc
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf .mypy_cache
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/

# Linting and code style
lint:
	. venv/bin/activate && flake8 blims
	. venv/bin/activate && mypy blims

format:
	. venv/bin/activate && black blims
	. venv/bin/activate && isort blims

check:
	. venv/bin/activate && black --check blims
	. venv/bin/activate && isort --check-only blims
	. venv/bin/activate && flake8 blims
	. venv/bin/activate && mypy blims

reformat: format check lint

# Testing
test:
	. venv/bin/activate && python -m pytest

test-verbose:
	. venv/bin/activate && python -m pytest -vv
	
test-unit:
	. venv/bin/activate && python -m pytest tests/test_sample.py tests/test_repository.py tests/test_service.py -v

coverage:
	. venv/bin/activate && python -m pytest --cov=blims --cov-report=html tests/

# Run application
run:
	. venv/bin/activate && python main.py

dev:
	. venv/bin/activate && uvicorn main:app --reload --host 0.0.0.0 --port 8000

# DB migration (placeholder for future)
db-init:
	@echo "Database initialization placeholder"

# Install development tools
dev-setup: setup
	. venv/bin/activate && uv pip install -e ".[dev]"

# Install pre-commit hooks
install-hooks:
	. venv/bin/activate && pre-commit install
	
# Create test data
test-data:
	. venv/bin/activate && python create_test_data.py
	
# AWS infrastructure setup commands
aws-validate:
	./aws/deploy.sh dev --dry-run

aws-deploy:
	./aws/deploy.sh dev

aws:
	@echo "AWS Infrastructure Commands:"
	@echo "  - make aws-validate: Validate AWS CloudFormation templates"
	@echo "  - make aws-deploy:   Deploy AWS infrastructure for BLIMS"
	@echo ""
	@read -p "Which command do you want to run? (validate/deploy): " cmd; \
	case $$cmd in \
		validate) make aws-validate ;; \
		deploy) make aws-deploy ;; \
		*) echo "Invalid command. Use 'validate' or 'deploy'." ;; \
	esac

# Docker commands
docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-shell:
	docker-compose exec api bash

# All-in-one docker development command
docker-dev: docker-build docker-up
	@echo "Docker development environment is running"
	@echo "API is available at http://localhost:8000"
	@echo "API docs are available at http://localhost:8000/docs"
	@echo "UI is available at http://localhost:8501"
	@echo "Use 'make docker-logs' to see logs"
	@echo "Use 'make docker-down' to stop the environment"

