# Testing

This repo ships three implementations:

- `py`: legacy pure-Python (`scott_legacy`)
- `nx`: NetworkX-native (`scott-nx`)
- `rs`: Rust core (CLI via Cargo; Python bindings pending)

## Dev setup

Install dev tools via uv:

```bash
uv pip install -e '.[dev]'
# optional extras
uv pip install -e '.[dev,nx]'
uv pip install -e '.[dev,py]'
```

Run shortcuts (provided as project scripts):

```bash
uv run test
uv run unit
uv run canonization
uv run lint
uv run format
```

## Unified test runner

Use `test/cli/test_runner.py` for all test flows. It supports both CLI flags and an interactive prompt.

Examples:

```bash
# Interactive menu
python3 test/cli/test_runner.py --interactive

# Validity checks (pair matches + mismatch)
python3 test/cli/test_runner.py validity --engine py
python3 test/cli/test_runner.py validity --engine nx
python3 test/cli/test_runner.py validity --engine rs --release

# cfi-rigid benchmark (writes CSV under results/)
python3 test/cli/test_runner.py cfi-rigid --engine py -n 80
python3 test/cli/test_runner.py cfi-rigid --engine nx -n 80
python3 test/cli/test_runner.py cfi-rigid --engine rs -n 80 --release

# alternative interpreter for pure-python suite
uv run --python pypy@3.11 -- python test/cli/test_runner.py cfi-rigid --engine py -n 80
uv run --python pypy@3.11 -- python test/cli/test_runner.py cfi-rigid --engine nx -n 80
```

Outputs:

- `results/results_cfi-rigid-py.csv`
- `results/results_cfi-rigid-nx.csv`
- `results/results_cfi-rigid-rs.csv`

## Performance baseline

Generate a repeatable baseline for the Rust engine:

```bash
cargo run --bin perf_baseline -- --max-n 30
```

Optional parallel mode (higher memory usage):

```bash
cargo run --features parallel --bin perf_baseline -- --max-n 30
```

This writes:

- `results/perf_baseline.json`
- `results/perf_baseline.csv`

## Compatibility wrappers

These remain available and simply forward to the unified runner:

- `test/scripts/test_isomorphism.py` → `test/cli/test_runner.py validity --engine py`
- `test/scripts/test_cfi_rigid.py` → `test/cli/test_runner.py cfi-rigid --engine py`

## Backend selection

The `scott` Python package is a shim that can target a backend via `SCOTT_BACKEND`:

- `SCOTT_BACKEND=rs` (default when the extension is available)
- `SCOTT_BACKEND=legacy`
- `SCOTT_BACKEND=nx`

Note: the Rust backend requires the extension built via `maturin develop` (CPython only).
