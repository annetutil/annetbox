# AGENTS.md

This file provides guidance to AI coding agents when working with code in this repository.

## Project Overview

Annetbox is a Netbox API client library for Python used by annet and related projects. It implements a subset of Netbox API methods with support for multiple Netbox versions (v24, v37, v41, v42). The library provides both synchronous and asynchronous clients.

## Development Commands

### Setup
```bash
# Install for sync client development
pip install '.[sync]' -r requirements_dev.txt

# Install for async client development
pip install '.[async]' -r requirements_dev.txt

# Install for both
pip install '.[sync,async]' -r requirements_dev.txt
```

### Testing
```bash
# Run all tests
make test
# or
pytest

# Run a specific test file
pytest tests/base/test_client_sync.py

# Run a specific test
pytest tests/base/test_client_sync.py::test_collect_all
```

### Integration Testing

**Run tests** (no Docker needed):
```bash
pytest tests/integration/ -v
```

**Add new test case**:
1. Edit `tests/integration/definitions.yaml`:
   ```yaml
   - id: my_test_01
     method: dcim_devices
     versions: ["v42"]
     args: {limit: 5}
   ```
2. Start Netbox with Docker and generate fixtures:
   ```bash
   python -m tests.integration.generate_fixtures
   ```
3. Run tests to verify:
   ```bash
   pytest tests/integration/ -v
   ```

**Test structure**:
- `test_consistency.py` - Validates fixture integrity (SHA256 hashes, definition consistency)
- `test_declarative.py` - Tests API client behavior using recorded cassettes
- Uses **VCR.py** to record/replay HTTP interactions
- Each test case has its own directory with `cassette.yaml` and `expected.yaml`
- `lock.yaml` contains SHA256 hashes to detect manual tampering

### Linting
```bash
# Run ruff linter
ruff check .

# Auto-fix linting issues
ruff check . --fix
```

**IMPORTANT: Do NOT modify global linter configuration!**
- Never add global rules to `pyproject.toml` or `.ruff.toml`
- Never change global line length, ignore rules, or other settings
- If code violates linting rules:
  1. Fix the code (preferred)
  2. Split long lines
  3. Use inline `# noqa: RULE` comments as last resort
- Global linter config changes affect the entire codebase and must be reviewed by maintainers

### Building
```bash
# Build distribution packages
python -m build
```

## Code Architecture

### Version-based Structure
The codebase is organized by Netbox API versions, each in its own module (`v24/`, `v37/`, `v41/`, `v42/`). Each version module contains:
- `models.py` - Dataclass models for API responses/requests
- `client_async.py` - Async client implementation
- `client_sync.py` - Sync client (auto-generated from async)

### Base Client Architecture
The `base/` module provides the foundation:
- `client_async.py` / `client_sync.py` - Base client classes with HTTP handling and pagination
- `models.py` - Common models like `PagingResponse`, `Status`
- `exceptions.py` - Custom exceptions

### Key Patterns

**Pagination handling**: The `collect()` decorator (defined in base clients) wraps API methods to automatically handle pagination. It supports two modes:
1. Page-based collection - fetches all pages sequentially
2. Batched field collection - splits large filter lists into batches to avoid URL length limits

**Async-to-Sync transformation**: Sync clients are NOT manually maintained. They are generated from async clients using `transform_to_sync.py`, which removes `async`/`await` keywords and swaps base client imports.

**API method pattern**: Methods use `dataclass-rest` decorators (`@get`, `@post`, `@delete`) with pass-through implementations. The actual HTTP logic is in the base client and decorators.

## Adding New API Methods

Follow this workflow when adding new Netbox API endpoints:

1. **Read the OpenAPI spec** for the target version (e.g., `netbox-rest-api-v42.yaml`)

2. **Edit `models.py`** in the version directory to add/update dataclass models for the endpoint

3. **Edit `client_async.py`** to add the new method:
   - Add `@get`/`@post`/`@delete` decorator with endpoint path
   - Include all filter parameters with type hints
   - Always include `limit: int = 20` and `offset: int = 0` for paginated endpoints
   - Add a `pass` body (implementation is in decorator)
   - Add a `collect()` variant if needed (e.g., `dcim_all_devices = collect(dcim_devices, field="id")`)

4. **Generate sync client** by running:
   ```bash
   python transform_to_sync.py src/annetbox/v42/client_async.py > src/annetbox/v42/client_sync.py
   ```
   Repeat for all modified versions (v37, v41, v42 as needed)

5. **Test the changes** with pytest

## Testing Strategy

**Unit tests** (`tests/base/`):
- Test pagination logic and collection behavior
- Use mock data, no external dependencies
- Fast, run on every commit

**Integration tests** (`tests/integration/`):
- Test model deserialization against real API responses
- Use VCR.py to record/replay HTTP interactions
- Cassettes (YAML files) committed to git as test data
- No Docker needed for test execution
- Fast (2-3 seconds), deterministic, run in CI
- When API changes, re-record with `make fixtures` (requires Docker)

## Git Commit Guidelines

**CRITICAL**: Only commit files related to your changes. Never use `git add -A` or `git add .`

**Files to commit** (for code changes):
- `src/annetbox/**/*.py` - Source code changes
- `tests/**/*.py` - Test code
- `tests/integration/definitions.yaml` - Shared test definitions
- `tests/integration/fixtures/**/*.yaml` - Test fixtures (cassettes, expected.yaml, lock.yaml)
- `README.md` - Documentation updates
- `AGENTS.md` - This file if updated

**Files to NEVER commit** (user-specific, auto-generated, or temporary):
- `.env*` - Environment files
- `docker-compose.yml` - User's local Docker config
- `Makefile` - User's local build scripts (unless adding new features)
- `*.log`, `*.tmp`, `*~` - Temporary files
- `NOTES` - Personal notes
- `netbox-rest-api-*.yaml` - Debug/reference files

**Commit workflow**:
```bash
# Stage only specific files/directories
git add src/annetbox/v42/
git add tests/integration/test_consistency.py
git add tests/integration/definitions.yaml
git add tests/integration/fixtures/v42/

# Review what will be committed
git status

# Commit with descriptive message
git commit -m "Add consistency tests for v42 fixtures"
```

## Important Notes

- The main branch for PRs is `develop`, not `main`
- Sync clients are auto-generated - never edit them directly
- The `collect()` decorator's default batch size is 100 (calculated to fit UUIDs in 4KB URL length)
- Methods with heavy responses should use smaller batch sizes (e.g., `batch_size=10` for interfaces)
- The library uses `adaptix` for serialization with custom name mapping and type loaders
- Both client types use connection pooling (ThreadPool for sync, connection limits for async)
- Docker is only needed for generating new fixtures (`make docker` + `make fixtures`)
