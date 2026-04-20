# Repository Guidelines

## Project Structure & Module Organization
- `scott/` is the core package; `structs/` holds graph data types, `utils/` helpers, and modules like `parse.py`, `canonize.py`, and `fragmentation.py` implement features.
- `test/` contains the runnable test script `test/tests.py` and benchmarks under `test/bench/`.
- `data/` stores sample graphs, molecules, and fixtures used by tests and examples.
- `docs/` hosts the documentation site content and images.
- `usage.py` and `usage_advanced.py` are example entry points.
- `Dockerfile` and `dockerfiles/` provide container builds.

## Build, Test, and Development Commands
- `python3 setup.py install` installs the package from source for local use.
- `python3 usage.py` runs the basic example workflow.
- `python3 usage_advanced.py` runs the advanced example workflow.
- `python3 test/tests.py` runs the scripted test suite; toggle sections via the `if True` / `if False` blocks.
- `docker build -t scott .` builds the default container image.

## Coding Style & Naming Conventions
- Python code uses tabs for indentation; keep indentation consistent with existing files.
- Modules and functions use `snake_case`; classes use `CapWords` (e.g., `Graph`, `Node`).
- No formatter or linter is configured; keep changes minimal and readable.

## Testing Guidelines
- Tests are a runnable script rather than a framework; add new checks to `test/tests.py` with clear console output.
- Benchmarks live in `test/bench/`; name them by purpose (e.g., `bench_cfi-rigid.py`).
- Test data and fixtures should live under `data/` and be referenced by relative paths.

## Commit & Pull Request Guidelines
- Commit messages are short and imperative; common patterns include `Update ...`, `Fix #1`, `ADD ...`, and `FIX ...`.
- PRs should include a summary, linked issues when applicable, and test results (commands + outcomes).
- For documentation or visual updates under `docs/`, include before/after screenshots.

## Dependencies & Configuration Notes
- SMILES parsing depends on RDKit; call this out when adding features that require it.
- Docker images provide optional stacks (Jupyter, PySpark); keep Docker changes scoped to their target image.
