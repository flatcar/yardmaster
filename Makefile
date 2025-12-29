.PHONY: help install dev-install test lint format check build clean run docs serve-docs
.DEFAULT_GOAL := help

help: ## 📋 Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## 📦 Install the package in production mode
	uv sync

dev-install: ## 🛠️ Install the package with development dependencies
	uv sync --extra dev

test: dev-install ## 🧪 Run tests with coverage
	uv run pytest

test-quick: dev-install ## ⚡ Run tests without coverage
	uv run pytest --no-cov

lint: dev-install ## 🔍 Run linting checks
	uv run ruff check yardmaster/ tests/

lint-fix: dev-install ## 🔧 Run linting and fix auto-fixable issues
	uv run ruff check --fix yardmaster/ tests/

format: dev-install ## 🎨 Format code with ruff
	uv run ruff format yardmaster/ tests/

format-check: dev-install ## ✅ Check code formatting without making changes
	uv run ruff format --check yardmaster/ tests/

type-check: dev-install ## 🏷️ Run type checking with mypy
	uv run mypy yardmaster/ tests/

docs: dev-install ## 📚 Build Sphinx docs
	uv run sphinx-build -b html docs docs/_build/html

serve-docs: dev-install ## 🌐 Serve docs with live reload
	uv run sphinx-autobuild docs docs/_build/html --watch yardmaster --port 8000

all: ## 🎯 Run complete workflow (setup, fix, check, build)
	@echo "🎯 Running complete workflow..."
	@echo "⚙️ Setting up development environment..."
	$(MAKE) dev-install
	@echo "🔧 Fixing code issues..."
	$(MAKE) fix
	@echo "🔎 Running all checks..."
	$(MAKE) check
	@echo "📦 Building package..."
	$(MAKE) build
	@echo "🎉 Complete workflow finished successfully!"

check: dev-install ## 🔎 Run all checks (lint, format-check, type-check, test)
	@echo "🔍 Running all checks..."
	@echo "📝 Checking code formatting..."
	uv run ruff format --check yardmaster/ tests/
	@echo "🔍 Running linting..."
	uv run ruff check yardmaster/ tests/
	@echo "🏷️  Running type checking..."
	uv run mypy yardmaster/ tests/
	@echo "🧪 Running tests..."
	uv run pytest
	@echo "✅ All checks passed!"

fix: dev-install ## 🔧 Fix formatting and auto-fixable linting issues
	@echo "🔧 Fixing code formatting..."
	uv run ruff format yardmaster/ tests/
	@echo "🔧 Fixing linting issues..."
	uv run ruff check --fix yardmaster/ tests/
	@echo "✅ Code fixes applied!"

build: ## 📦 Build the package
	uv build

clean: ## 🧹 Clean build artifacts
	rm -rf dist/
	rm -rf build/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Development workflow shortcuts
dev: dev-install ## 🚀 Alias for dev-install

setup: dev-install ## ⚙️ Set up development environment (alias for dev-install)

ci: check ## 🤖 Run all CI checks locally
