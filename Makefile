include .env

default: run
MAKEFLAGS += -s

help:
	@echo "⚈ run			---> 🎮 Run project locally (default)."
	@echo "⚈ debug			---> 🕵️  Debug project locally."
	@echo "⚈ test			---> 🧪 Run tests."
	@echo "⚈ diff-cover		---> 📊 Run tests and diff-cover."
	@echo "⚈ diff-cover-only	---> 🔍 Run diff-cover only."
	@echo "⚈ freeze		---> 🧊 Freeze requirements."
	@echo "⚈ sort			---> ⬇️  Sort requirements and env files alphabetically."
	@echo "⚈ publish		---> 🚀 Build and publish a new package version."

run:
	@echo "\n> 🎮 Running the project locally... (default)\n"

debug:
	@echo "\n> 🕵️  Debugging the project locally...\n"

test:
	@echo "\n> 🧪 Running tests...\n"
	python -m pytest tests --cov=./ --cov-report=xml --cov-config=.coveragerc

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
	$(eval BASE_BRANCH ?= main)
	$(eval COVERAGE_FILE ?= coverage.xml)
	@echo "Comparing against base branch: $(BASE_BRANCH)"
	@echo "Using coverage file: $(COVERAGE_FILE)"
	@if [ ! -f "$(COVERAGE_FILE)" ]; then \
		echo "Error: Coverage file $(COVERAGE_FILE) does not exist."; \
		echo "* Suggestion: If you haven't run the tests yet, please run the full diff-cover command:"; \
		echo "    make diff-cover BASE_BRANCH=$(BASE_BRANCH)"; \
		echo "This will run the tests and generate the coverage file before running diff-cover."; \
		echo ""; \
		exit 1; \
	fi
	@git fetch origin $(BASE_BRANCH)
	@diff-cover "$(COVERAGE_FILE)" --compare-branch="$(BASE_BRANCH)" --fail-under=80 \
    --exclude="**/test_*.py" --exclude="**/tests/**" --exclude="**/examples/**"

diff-cover: test diff-cover-only
	@echo "\n> 🎉 Tests and diff-cover completed.\n"

freeze:
	@echo "\n> 🧊 Freezing the requirements...\n"
	@for file in requirements*.txt; do \
		if [ -f $$file ]; then \
			pip3 freeze -q -r $$file | sed '/freeze/,$$ d' > requirements-froze.txt && mv requirements-froze.txt $$file; \
			echo "Froze requirements in $$file"; \
		else \
			echo "$$file not found, skipping..."; \
		fi \
	done
	@python src/update_pyproject.py

sort:
	@echo "\n> ⬇️ Sorting requirements and env files alphabetically...\n"
	@for file in requirements*.txt; do \
		if [ -f $$file ]; then \
			sort --ignore-case -u -o $$file{,}; \
			echo "Sorted $$file"; \
		else \
			echo "$$file not found, skipping..."; \
		fi \
	done
	@for file in .env*; do \
		if [ -f $$file ]; then \
			sort --ignore-case -u -o $$file{,}; \
			echo "Sorted $$file"; \
		else \
			echo "$$file not found, skipping..."; \
		fi \
	done

publish:
	@echo "\n> 🚀 Building and publishing a new package version...\n"
	@echo "\n> 📦 Installing build dependencies...\n"
	pip install -r requirements-build.txt
	@echo "\n> 🗑️ Erasing previous build...\n"
	rm -rf src/dist
	@echo "\n> ⬆️ Bumping package version...\n"
	bump2version patch --verbose
	@echo "\n> 🔨 Building package...\n"
	python -m build src
	@echo "\n> 🌐 Uploading package to Test PyPi...\n"
	python -m twine upload --repository usepolvo-cli src/dist/*
