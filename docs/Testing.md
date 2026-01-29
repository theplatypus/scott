# Testing

This repo ships three implementations:

- `py`: legacy pure-Python (`scott_legacy`)
- `nx`: NetworkX-native (`scott-nx`)
- `rs`: Rust core (CLI via Cargo; Python bindings pending)

## Unified test runner

Use `test_runner.py` for all test flows. It supports both CLI flags and an interactive prompt.

Examples:

```bash
# Interactive menu
python3 test_runner.py --interactive

# Validity checks (pair matches + mismatch)
python3 test_runner.py validity --engine py
python3 test_runner.py validity --engine nx
python3 test_runner.py validity --engine rs --release

# cfi-rigid benchmark (writes CSV under results/)
python3 test_runner.py cfi-rigid --engine py -n 30
python3 test_runner.py cfi-rigid --engine nx -n 30
python3 test_runner.py cfi-rigid --engine rs -n 30 --release

# Compare traces (normalized diff by default)
python3 test_runner.py compare-traces --left nx --right rs --dot data/isotest/cfi-rigid-t2-dot/cfi-rigid-t2-0020-01-1.dot
python3 test_runner.py compare-traces --left py --right nx --dot data/isotest/cfi-rigid-t2-dot/cfi-rigid-t2-0020-01-1.dot --raw
```

Outputs:

- `results/results_cfi-rigid-py.csv`
- `results/results_cfi-rigid-nx.csv`
- `results/results_cfi-rigid-rs.csv`

## Compatibility wrappers

These remain available and simply forward to the unified runner:

- `test_isomorphism.py` → `test_runner.py validity --engine py`
- `test_cfi-rigid.py` → `test_runner.py cfi-rigid --engine py`

## Backend selection

The `scott` Python package is a shim that can target a backend via `SCOTT_BACKEND`:

- `SCOTT_BACKEND=legacy` (default)
- `SCOTT_BACKEND=nx`
- `SCOTT_BACKEND=rs`
