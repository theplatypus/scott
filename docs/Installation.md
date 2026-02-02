# Installation

Scott ships a Rust backend by default when the extension is available, with optional
NetworkX and legacy pure-Python backends.

## From PyPI

```bash
pip install scott

# optional extras
pip install 'scott[nx]'  # NetworkX backend + pydot
pip install 'scott[py]'  # legacy pure-Python backend
```

Use `SCOTT_BACKEND=nx` or `SCOTT_BACKEND=legacy` to select the backend at runtime.

To use the Rust backend from source installs, build the extension once (CPython only):

```bash
maturin develop --release
```

## From source (local repo)

```bash
# clone and enter the repo
git clone https://github.com/theplatypus/scott.git
cd scott

# install editable (uv)
uv venv
uv pip install -e .

# optional extras
uv pip install -e '.[nx]'
uv pip install -e '.[py]'
```

If you are not using uv, you can use pip directly:

```bash
python -m pip install -e .
python -m pip install -e '.[nx]'
python -m pip install -e '.[py]'
```

To enable the Rust backend locally:

```bash
uv run maturin develop --release
```

## Backend selection

The Rust backend is the default when the extension is available. Select a backend
at runtime using the `SCOTT_BACKEND` environment variable:

- `SCOTT_BACKEND=legacy`
- `SCOTT_BACKEND=nx`
- `SCOTT_BACKEND=rs`
