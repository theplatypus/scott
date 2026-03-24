# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Scott computes canonical tree representatives of labelled (edge and node) graphs for graph isomorphism detection. Unlike nauty/bliss/traces, it handles both edge-labelled and vertex-labelled graphs, making it suitable for chemical structure analysis. The canonical tree can be serialized to a string (canonical trace) or adjacency matrix.

## Build & Development Commands

### Rust core
```bash
cargo build --release
cargo build --features parallel --release   # with rayon parallelism
```

### Python extension (PyO3 via maturin)
```bash
uv venv && source .venv/bin/activate
uv pip install -e .
uv run maturin develop --release             # build Rust extension for Python
```

### Testing
```bash
# Unified test runner (supports engines: py, rs)
python3 test/cli/test_runner.py --interactive
python3 test/cli/test_runner.py validity --engine rs
python3 test/cli/test_runner.py cfi-rigid --engine rs -n 30 --release

# Performance baseline
cargo run --release --bin perf_baseline -- --max-n 30
cargo run --release --features parallel --bin perf_baseline -- --max-n 30
```

### Linting
```bash
uv run lint
uv run format
```

### Backend selection at runtime
```bash
SCOTT_BACKEND=legacy python3 script.py   # pure-Python fallback
```

### Docker
```bash
docker build -t scott .                                              # default (CPython + Rust)
docker build -t scott:pypy -f dockerfiles/pypy/Dockerfile .          # PyPy standalone (legacy backend)
docker build -t scott:pypy-jupyter -f dockerfiles/pypy-jupyter/Dockerfile .  # PyPy + Jupyter
```

## Architecture

Two backends: Rust core (`src/`, default) and legacy Python (`scott_legacy/`, fallback). The Python package (`scott/`) auto-detects the Rust extension; if unavailable and `SCOTT_BACKEND=legacy` is set, falls back to the pure-Python implementation. Format parsers (`scott/parse.py`) produce `scott.graph.Graph` objects that bridge transparently to Rust via `graph_from_edges()`.

### Rust core (`src/`) — the primary implementation

The canonization pipeline is a 3-step process:

1. **`dag.rs`** (largest module, ~1,080 LOC) — Converts the input graph to a DAG via iterative rewriting. Partitions vertices into floors, selects cobound/inbound candidates with deterministic scoring (`CoboundScore`, `InboundScore`), and applies magnet-based tie-breaking with MD5-hashed caches. This is the performance-critical module.

2. **`tree.rs`** — Serializes the DAG to a canonical tree string. Uses iterative DFS with Arc<str> interning for memory efficiency. Children are sorted by depth, modality, and lexicographic order.

3. **`canonize.rs`** — Orchestrates the pipeline: graph → DAG → tree → `CGraph` (canonical string). Entry point is `to_cgraph()`.

Supporting modules:
- **`graph.rs`** — `GraphWrap` around petgraph's `StableUnGraph`, with `NodeData`/`EdgeData`/`NodeMeta` structs
- **`dot.rs`** — Line-based DOT format parser (no regex)
- **`py.rs`** — PyO3 bindings exposing `PyGraph`, `PyCGraph`, and parsing functions
- **`bin/`** — Benchmark and debug binaries (`perf_baseline`, `test_cfi_rigid`, `debug_canonize`)

### Key dependencies
- `petgraph` for graph data structures
- `md5` for magnet hash computation
- `pyo3` (optional) for Python bindings
- `rayon` (optional) for parallelism

## Coding Conventions

- **Python**: tabs for indentation, `snake_case` functions, `CapWords` classes
- **Rust**: standard idiomatic style
- **Commits**: short imperative messages with prefix tags: `[doc]`, `[perf]`, `[feat]`, `[fix]`, `[misc]`

## Test Data

Test fixtures (CFI-rigid benchmark graphs in DOT format) live under `data/isotest/cfi-rigid-t2-dot/`. Results are written to `results/`.
