#!/bin/bash
set -e

# Activate virtual environment
. venv/bin/activate

# Install dependencies
uv pip install -e .
uv pip install -e ".[dev]"
uv pip install httpx

# Run tests
python -m pytest -v