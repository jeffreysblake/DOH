.PHONY: help lint format test install-dev setup-hooks clean coverage

help:		## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install-dev:	## Install development dependencies
	conda install flake8 black pytest pytest-cov -y
	pip install -e .

setup-hooks:	## Setup git hooks for code quality
	git config core.hooksPath .githooks
	chmod +x .githooks/pre-commit

lint:		## Run flake8 linting on all Python files
	flake8 src/ tests/

format:		## Format code with black
	black src/ tests/ --line-length=88

format-check:	## Check if code is properly formatted
	black src/ tests/ --line-length=88 --check

test:		## Run all tests
	python -m pytest tests/ -v

test-cov:	## Run tests with coverage
	python -m pytest tests/ --cov=src/doh --cov-report=html --cov-report=term-missing

test-changed:	## Run tests for recently changed files
	@echo "Finding changed files..."
	@changed_files=$$(git diff --name-only HEAD~1 HEAD | grep -E '\\.py$$' | grep -E '^(src|tests)/' || true); \
	if [ -n "$$changed_files" ]; then \
		echo "Changed files: $$changed_files"; \
		python -m pytest $$(echo "$$changed_files" | grep '^tests/' || true) -v; \
	else \
		echo "No Python files changed"; \
	fi

check:		## Run all quality checks (format, lint, test)
	@echo "🔍 Running code quality checks..."
	$(MAKE) format-check
	$(MAKE) lint
	$(MAKE) test

fix:		## Auto-fix formatting and run checks
	@echo "🔧 Auto-fixing code issues..."
	$(MAKE) format
	$(MAKE) lint
	$(MAKE) test

clean:		## Clean up build artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage .pytest_cache/ build/ dist/

coverage:	## Generate coverage report and open in browser
	$(MAKE) test-cov
	@if command -v xdg-open >/dev/null 2>&1; then \
		xdg-open htmlcov/index.html; \
	elif command -v open >/dev/null 2>&1; then \
		open htmlcov/index.html; \
	else \
		echo "Coverage report generated in htmlcov/index.html"; \
	fi

# Development workflow targets
dev-setup:	## Complete development environment setup
	$(MAKE) install-dev
	$(MAKE) setup-hooks
	@echo "✅ Development environment ready!"

commit-check:	## Run checks before committing (simulates pre-commit hook)
	@python .githooks/pre-commit
