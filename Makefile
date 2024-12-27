# Default target
.DEFAULT_GOAL := help

# Silent mode
MAKEFLAGS += -s

# Variables
BASE_BRANCH ?= main
COVERAGE_FILE ?= coverage.xml

# Help target
help:
	@echo "Available commands:"
	@echo "⚈ install		---> 📦 Install all dependencies"
	@echo "⚈ install-build		---> 🔧 Install build dependencies"
	@echo "⚈ test			---> 🧪 Run tests with coverage"
	@echo "⚈ benchmark		---> 📊 Run performance benchmarks"
	@echo "⚈ tox			---> 🔄 Run tests in multiple Python environments"
	@echo "⚈ tox-py-%		---> 🐍 Run tox for specific Python version (e.g., tox-py-39)"
	@echo "⚈ diff-cover		---> 📊 Run tests and check coverage diff against base branch"
	@echo "⚈ diff-cover-only	---> 🔍 Check coverage diff only against base branch"
	@echo "⚈ fmt			---> 🎨 Format code using black"
	@echo "⚈ sort			---> ⬇️  Sort requirements and env files alphabetically"
	@echo "⚈ freeze		---> 🧊 Freeze requirements to their exact versions"
	@echo "⚈ clean			---> 🧹 Remove all build, test, and cache files"
	@echo "⚈ clean-build		---> 🗑️  Remove build artifacts"
	@echo "⚈ build			---> 📦 Build package distribution"
	@echo "⚈ publish		---> 🚀 Build and publish package to main repository"
	@echo "⚈ publish-test		---> 🧪 Build and publish package to test repository"
	@echo "⚈ bump-patch		---> 📎 Bump patch version (0.0.x)"
	@echo "⚈ bump-minor		---> 📌 Bump minor version (0.x.0)"
	@echo "⚈ bump-major		---> 📈 Bump major version (x.0.0)"

# Installation targets
install:
	@echo "📦 Installing dependencies..."
	pip install -r requirements.txt -r requirements-test.txt -r requirements-dev.txt

install-build:
	@echo "🔧 Installing build dependencies..."
	pip install -r requirements-build.txt

# Testing targets
test:
	@echo "\n> 🧪 Running tests...\n"
	cd src && python -m pytest ../tests -vv --cov=./ --cov-report=xml --cov-config=../.coveragerc -m "not performance"

benchmark:
	@echo "\n> 📊 Running performance tests...\n"
	cd src && python -m pytest ../tests --cov=./ --cov-report=xml --cov-config=../.coveragerc -m "performance" --benchmark-only

tox:
	@echo "🔄 Running tox tests..."
	cd src && tox

tox-py-%:
	@echo "🐍 Running tox for Python $*..."
	cd src && tox -e py$*

# Coverage targets
ensure-diff-cover:
	@echo "\n> 🔍 Checking for diff-cover...\n"
	@if ! command -v diff-cover &> /dev/null; then \
		echo "diff-cover not found. Installing..."; \
		pip install diff-cover; \
	else \
		echo "diff-cover is already installed."; \
	fi

diff-cover-only: ensure-diff-cover
	@echo "\n> 📊 Running diff-cover on existing coverage file...\n"
	@echo "Comparing against base branch: $(BASE_BRANCH)"
	@echo "Using coverage file: $(COVERAGE_FILE)"
	@if [ ! -f "$(COVERAGE_FILE)" ]; then \
		echo "Error: Coverage file $(COVERAGE_FILE) does not exist."; \
		echo "* Suggestion: Run 'make diff-cover' to generate coverage file first."; \
		exit 1; \
	fi
	@git fetch origin $(BASE_BRANCH)
	@diff-cover "$(COVERAGE_FILE)" --compare-branch="$(BASE_BRANCH)" --fail-under=80 \
		--exclude="**/test_*.py" --exclude="**/tests/**" --exclude="**/examples/**"

diff-cover: test diff-cover-only
	@echo "\n> 🎉 Tests and diff-cover completed.\n"

# Code formatting and organization
fmt:
	@echo "🎨 Formatting code..."
	black --line-length 120 .

sort:
	@echo "\n> ⬇️ Sorting requirements and env files...\n"
	@for file in requirements*.txt; do \
		if [ -f $$file ]; then \
			sort --ignore-case -u -o $$file{,}; \
			echo "Sorted $$file"; \
		fi \
	done
	@for file in .env*; do \
		if [ -f $$file ]; then \
			sort --ignore-case -u -o $$file{,}; \
			echo "Sorted $$file"; \
		fi \
	done

freeze:
	@echo "\n> 🧊 Freezing requirements...\n"
	@for file in requirements*.txt; do \
		if [ -f $$file ]; then \
			pip3 freeze -q -r $$file | sed '/freeze/,$$ d' > requirements-froze.txt && mv requirements-froze.txt $$file; \
			echo "Froze requirements in $$file"; \
		fi \
	done
	@python src/update_pyproject.py

# Cleanup targets
clean-build:
	@echo "🗑️ Cleaning build artifacts..."
	rm -rf src/dist build dist *.egg-info

clean: clean-build
	@echo "🧹 Cleaning all artifacts..."
	rm -rf __pycache__ .tox .pytest_cache .coverage
	find . -type d -name "__pycache__" -exec rm -r {} +

# Build and publish targets
build: clean-build
	@echo "📦 Building package..."
	python -m build src

publish-test: build
	@echo "🧪 Publishing to test repository..."
	python -m twine upload --repository harbour-orm-test src/dist/*

publish: build
	@echo "🚀 Publishing to main repository..."
	python -m twine upload --repository harbour-orm src/dist/*

# Version bump targets
bump-patch:
	@echo "📎 Bumping patch version..."
	bump2version patch --verbose

bump-minor:
	@echo "📌 Bumping minor version..."
	bump2version minor --verbose

bump-major:
	@echo "📈 Bumping major version..."
	bump2version major --verbose

.PHONY: help install install-build test benchmark tox tox-py-% diff-cover diff-cover-only \
	fmt sort freeze clean clean-build build publish publish-test \
	bump-patch bump-minor bump-major