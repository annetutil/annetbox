.PHONY: help venv install test lint transform format fixtures docker

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

venv: ## Create virtual environment
	python3 -m venv .venv
	@echo "Virtual environment created. Activate with: source .venv/bin/activate"

install: ## Install dependencies
	python3 -m pip install -e '.[sync,async]'
	python3 -m pip install -r requirements_dev.txt

test: ## Run all tests
	pytest

lint: ## Run linter
	ruff check .

format: ## Auto-fix linting issues
	ruff check . --fix

transform:  ## Convert async client to sync
	python transform_to_sync.py src/annetbox/v37/client_async.py > src/annetbox/v37/client_sync.py
	python transform_to_sync.py src/annetbox/v41/client_async.py > src/annetbox/v41/client_sync.py
	python transform_to_sync.py src/annetbox/v42/client_async.py > src/annetbox/v42/client_sync.py

fixtures: ## Generate integration test fixtures
	python -m tests.integration.generate_fixtures

docker: ## Start Docker Compose (fetches demo data if needed)
	@if [ ! -f netbox-demo-data/README.md ]; then \
		echo "Fetching netbox-demo-data submodule..."; \
		git submodule update --init --recursive; \
	fi
	docker compose up -d --wait --wait-timeout 120
