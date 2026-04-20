# Installation

Scott ships a Rust backend by default (CPython only). A pure-Python legacy backend
is available as a fallback via `SCOTT_BACKEND=legacy`.

## From PyPI

```bash
pip install scott

# optional extras
pip install 'scott[rdkit]'  # SMILES parsing via RDKit
pip install 'scott[nx]'     # NetworkX graph conversion
```

To use the Rust backend from source installs, build the extension once:

```bash
maturin develop --release
```

## From source (local repo)

```bash
# clone and enter the repo
git clone https://github.com/theplatypus/scott.git
cd scott

# create a virtualenv and install editable (uv)
uv venv
source .venv/bin/activate
uv pip install -e .

# build the Rust extension
uv run maturin develop --release

# optional extras
uv pip install -e '.[rdkit]'
uv pip install -e '.[nx]'
uv pip install -e '.[dev]'   # pytest, ruff
```

If you are not using uv, you can use pip directly:

```bash
python -m pip install -e .
python -m pip install -e '.[rdkit]'
python -m pip install -e '.[nx]'
```

## Building wheels locally

```bash
# build a wheel for the current platform into dist/
maturin build --release --out dist
```

## Backend selection

The Rust backend is the default and requires a Rust toolchain when building from
source. If the Rust extension is not available, scott will raise an `ImportError`
with build instructions.

A pure-Python fallback is available for environments where building the extension
is not possible (e.g. PyPy):

```bash
SCOTT_BACKEND=legacy python3 script.py
```
