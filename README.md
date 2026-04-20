# Scott

Scott computes a **canonical tree representative** of any **labelled (edge and node) graph**, derivable to a **canonical trace** (string) or **canonical adjacency matrix**.

Unlike classical isomorphism tools (nauty, bliss, Traces), Scott natively handles **both node labels and edge labels**, making it particularly well suited for chemical graphs and any domain where edge colors carry semantic meaning.

# Table of contents

This repository aims to be concise and practical. For background on the graph isomorphism problem and algorithm details, see the [project page](https://theplatypus.github.io/scott/).

- [When to use Scott](#when-to-use-scott)
- [Getting started](#getting-started)
  * [From Pypi](#from-pypi)
  * [From Docker](#from-docker)
  * [From source code](#from-source-code)
- [Usage](#usage)
  * [Build a Graph](#build-a-graph)
  * [Import Graphs](#import-graphs)
  * [Canonical traces](#canonical-traces)
  * [Indexing a graph database](#indexing-a-graph-database)
  * [Canonical Adjacency Matrices](#canonical-adjacency-matrices)
- [Testing](#testing)
- [Citation](#citation)
- [Licence](#licence)

## When to use Scott

Scott's canonical trace is a **reusable, serializable fingerprint** for a graph. This makes it the right tool when you need to:

- **Work with edge-colored graphs** — bond orders, relation types, weighted edges. Tools like nauty/bliss/Traces ignore edge labels by default; Scott treats them as first-class citizens.
- **Index or deduplicate a collection of graphs** — store the trace as a string key in a database, dictionary, or search index. Isomorphic graphs always produce the exact same trace, so a lookup replaces a full isomorphism test at query time.
- **Normalize inputs for machine learning** — canonical adjacency matrices put isomorphic graphs in the same form, which stabilizes downstream models.

**When Scott is not the right choice:** if you only need a one-off pairwise isomorphism test on large, unlabeled graphs, dedicated solvers like [nauty](https://pallini.di.uniroma1.it/) or [bliss](https://users.aalto.fi/~tjunttil/bliss/) will be faster. Scott's overhead comes from producing a fully reusable canonical object rather than a single yes/no answer.

---

## Getting started

See `docs/Installation.md` for a complete install guide (PyPI + local).

### From Pypi

```bash
pip install scott

# optional extras
pip install 'scott[rdkit,nx]'
```

Available extras:
- `rdkit`: parse molecular input (SMILES, Mol files)
- `nx`: NetworkX integration
- `legacy`: pure-Python implementation (slower, no Rust required)
- `dev`: development tools

Notes:
- The Rust backend is the default and requires a Rust toolchain when building from source (CPython only).
- A pure-Python fallback is available via `SCOTT_BACKEND=legacy`.

### From Docker

The default image is based on `python:latest`, builds the Rust extension, and installs all extras (rdkit, dev tools):

```bash
# Build the default image (CPython + Rust backend)
docker build -t scott .

# Run an interactive shell
docker run --rm -it scott
```

Alternative Dockerfiles are available under `dockerfiles/`.

#### Jupyter

CPython + Rust backend with a Jupyter notebook server.

```bash
docker build -t scott:jupyter -f dockerfiles/jupyter/Dockerfile .
docker run --rm -it -p 8888:8888 scott:jupyter
```

#### PyPy (standalone)

PyPy images use the pure-Python legacy backend (`SCOTT_BACKEND=legacy`) since PyPy cannot build PyO3 extensions.

A [PyPy](https://pypy.org/)-based image with `ipython`. Useful for benchmarking the legacy backend on a JIT interpreter.

```bash
docker build -t scott:pypy -f dockerfiles/pypy/Dockerfile .
docker run --rm -it scott:pypy
# > ipython
```

#### PyPy (Jupyter)

Same as above, with a Jupyter notebook server.

```bash
docker build -t scott:pypy-jupyter -f dockerfiles/pypy-jupyter/Dockerfile .
docker run --rm -it -p 8888:8888 scott:pypy-jupyter
```

### From source code

Simply clone the repo in a local repertory

```bash
# get the code
git clone https://github.com/theplatypus/scott.git
cd ./scott

# create a virtualenv (uv)
uv venv
source .venv/bin/activate
uv pip install -e .

# build the Rust extension (requires a Rust toolchain)
uv run maturin develop --release

# optional extras
uv pip install -e '.[rdkit]'  # SMILES parsing via RDKit
```

```python
import scott as st
print(st.__version__)
```

A pure-Python fallback is available for environments where building the Rust extension is not possible:

```bash
SCOTT_BACKEND=legacy python3 script.py
```

---

## Usage

For extended examples see `usage.py` and `usage_advanced.py`.

### Build a Graph

Scott graphs carry labels on both nodes **and** edges. The `modality` parameter on an edge is its color/weight — this is what distinguishes Scott from tools that only support vertex labels.

```python
import scott as st

# A small molecule-like graph: C connected to O by a double bond,
# and to two H by single bonds.
# Edge modality encodes bond order (1 = single, 2 = double).

graph = st.structs.graph.Graph()

n1 = st.structs.node.Node("1", "C")
n2 = st.structs.node.Node("2", "O")
n3 = st.structs.node.Node("3", "H")
n4 = st.structs.node.Node("4", "H")

e1 = st.structs.edge.Edge("1", n1, n2, modality=2)  # double bond
e2 = st.structs.edge.Edge("2", n1, n3)              # single bond
e3 = st.structs.edge.Edge("3", n1, n4)              # single bond

graph.add_node(n1)
graph.add_nodes([n2, n3, n4])
graph.add_edge(e1)
graph.add_edge(e2)
graph.add_edge(e3)

print(graph)
```

Edge labels matter: two graphs that are identical except for one bond order will produce **different** canonical traces, correctly distinguishing them as non-isomorphic.

### Import Graphs

Scott is also able to parse a few graph formats files. Note that a parsing function always returns a list, even if there is one molecule in the file.

```python
# Parse a .sdf file (chemical file standard) :

# from file path
compounds = st.parse.from_sdf(file_path='./data/molecule/cafeine.sdf')
cafeine = compounds[0]
print(cafeine)

# ignore hydrogens
compounds = st.parse.from_sdf(file_path='./data/molecule/simple.sdf', ignore_hydrogens=True)
simple_without_H = compounds[0]
print(simple_without_H)

# Parse a SMILES string (requires: pip install scott[rdkit])
smile = st.parse.parse_smiles('CCOCOCC=CCONC')

# we can iterate over graph vertices
for id_node in smile.V :
	print("Node #%s : %s" % (str(id_node), str(smile.V[id_node].label)))

# Parse a .dot file
cfi1 = st.parse.from_dot(file_path='./data/isotest/cfi-rigid-t2-dot/cfi-rigid-t2-0016-04-1.dot')[0]

# Parse a .dimacs file
cfi2 = st.parse.from_dimacs(file_path='./data/isotest/cfi-rigid-t2/cfi-rigid-t2-0016-04-1')[0]

# Parse a PubChem XML file
compounds = st.parse.from_pubchem_xml(file_path='./data/molecule/simple.xml')

# Convert a NetworkX graph 
import networkx as nx
nxg = nx.Graph()
nxg.add_node("a", label="C")
nxg.add_node("b", label="O")
nxg.add_edge("a", "b", weight=2)
g = st.parse.from_networkx(nxg)

G = st.parse.from_networkx(nx.random_geometric_graph(200, 0.125, seed=896803))
```

### Canonical traces

A canonical trace is a string that uniquely identifies an isomorphism class. Two graphs are isomorphic if and only if their traces are equal. Because it is a plain string, it can be stored, compared, hashed, or indexed like any other string — with no graph library required on the reading side.

```python
import scott as st

simple = st.parse.from_pubchem_xml(file_path='./data/molecule/simple.xml')[0]

# to_cgraph returns a CGraph object — str() gives the trace string
simple_cgraph = st.canonize.to_cgraph(simple)
simple_trace  = str(simple_cgraph)

assert simple_trace == '(H:1, H:1, (H:1, H:1, ((((C:1).#2{$1}:2)C:2)C:2, ((((C:1).#2{$1}:2)C:2)C:1).#2{$2}:1)C:1)C:1, (O:2, (((((C:1).#2{$1}:2)C:2)C:1).#2{$2}:1)O:1)C:1)C'

# SMILES (requires rdkit extra)
mol = st.parse.parse_smiles('CCOCOCC=CCONC', ignore_hydrogens=True)
assert str(st.canonize.to_cgraph(mol)) == '(C:1, (((((((((C:1)N:1)O:1)C:1)C:2)C:1)C:1)O:1)C:1)O:1)C'
```

Because the trace is a plain string, any standard hash function applies directly:

```python
import hashlib

fingerprint = hashlib.sha256(simple_trace.encode()).hexdigest()
# deterministic across runs, machines, and Python versions
```

Pairwise isomorphism — compute once per graph, then compare strings:

```python
G = st.parse.from_dimacs(file_path='./data/isotest/cfi-rigid-t2/cfi-rigid-t2-0020-01-1')[0]
H = st.parse.from_dimacs(file_path='./data/isotest/cfi-rigid-t2/cfi-rigid-t2-0020-01-2')[0]
E = st.parse.from_dimacs(file_path='./data/isotest/cfi-rigid-t2/cfi-rigid-t2-0020-02-1')[0]
F = st.parse.from_dimacs(file_path='./data/isotest/cfi-rigid-t2/cfi-rigid-t2-0020-02-2')[0]

Gc, Hc, Ec, Fc = [st.canonize.to_cgraph(x) for x in (G, H, E, F)]

assert str(Gc) == str(Hc)   # G and H are isomorphic
assert str(Ec) == str(Fc)   # E and F are isomorphic
assert str(Gc) != str(Ec)   # but the two classes are distinct
```

### Indexing a graph database

The canonical trace is a stable, serializable key. Store it in a dictionary, a SQL column, or any key-value store — querying then costs a single lookup instead of running a new isomorphism test for each candidate.

```python
import scott as st
import hashlib

def graph_key(g):
	"""Deterministic string key for any labelled graph."""
	return str(st.canonize.to_cgraph(g))

# --- Build an index offline (once per corpus) ---

index = {}  # trace -> list of graph IDs; swap for any DB

corpus = [
	("mol_001", st.parse.from_sdf(file_path='./data/molecule/cafeine.sdf')[0]),
	("mol_002", st.parse.from_sdf(file_path='./data/molecule/simple.sdf')[0]),
	# ... thousands more
]

for gid, graph in corpus:
	key = graph_key(graph)
	index.setdefault(key, []).append(gid)

# All entries with more than one ID are duplicate structures
duplicates = {k: v for k, v in index.items() if len(v) > 1}

# --- Query at runtime (no isomorphism test needed) ---

query = st.parse.parse_smiles('CN1C=NC2=C1C(=O)N(C(=O)N2C)C')  # caffeine via SMILES
matches = index.get(graph_key(query), [])
print("Identical structures in corpus:", matches)
```

For a compact fixed-size key (SQL index, Bloom filter, embedding store), hash the trace:

```python
def graph_hash(g, algorithm='sha256'):
	return hashlib.new(algorithm, graph_key(g).encode()).hexdigest()

# Same hash  <=>  same isomorphism class (collision probability negligible)
assert graph_hash(G) == graph_hash(H)
assert graph_hash(G) != graph_hash(E)
```

### Canonical Adjacency Matrices

On a graph `G` of `N` vertices, an adjacency matrix is an `N×N` array describing pairwise connectivity. Without a canonical vertex ordering, two isomorphic graphs yield different matrices. Scott's canonical ordering fixes this — particularly useful for graph neural networks and other learning pipelines where the same structure should map to the same input tensor.

```python
import scott as st

g = st.parse.from_dot(file_path="./data/isotest/cfi-rigid-t2-dot/cfi-rigid-t2-0020-02-2.dot")[0]
h = st.parse.from_dot(file_path="./data/isotest/cfi-rigid-t2-dot/cfi-rigid-t2-0020-02-1.dot")[0]

# raw matrices differ because vertex order is arbitrary
assert g.adjacency_matrix() != h.adjacency_matrix()

# canonical matrices are identical for isomorphic graphs
assert g.adjacency_matrix(canonic=True) == h.adjacency_matrix(canonic=True)
```

---

## Testing

```bash
# run all tests
python -m pytest test/pytest/ -v

# unit tests only
python -m pytest test/pytest/ -v -m unit

# canonization benchmarks
python -m pytest test/pytest/ -v -m canonization
```

Cross-engine comparison via the unified test runner:

```bash
python3 test/cli/test_runner.py --interactive
python3 test/cli/test_runner.py validity --engine rs
python3 test/cli/test_runner.py cfi-rigid --engine rs --release -n 30
```

Results are written under `results/`. For more detail, see `docs/Testing.md`.

---

## Citation

If you use or fork `scott` in further works, please cite:

```
@inproceedings{bloyet2019scott,
  title={Scott: A method for representing graphs as rooted trees for graph canonization},
  author={Bloyet, Nicolas and Marteau, Pierre-Fran{\c{c}}ois and Frenod, Emmanuel},
  booktitle={International Conference on Complex Networks and Their Applications},
  pages={578--590},
  year={2019},
  organization={Springer}
}
```

## Licence

Available under the MIT licence. See the [GitHub repo](https://github.com/theplatypus/scott).

Written and developed by:

- Nicolas BLOYET **([See-d](https://www.see-d.fr/), [IRISA Expression](https://www-expression.irisa.fr/fr/), [LMBA](http://web.univ-ubs.fr/lmba/))**
- Pierre-François MARTEAU **([IRISA Expression](https://www-expression.irisa.fr/fr/))**
- Emmanuel FRÉNOD **([See-d](https://www.see-d.fr/), [LMBA](http://web.univ-ubs.fr/lmba/))**

![logos](https://raw.githubusercontent.com/theplatypus/test-pages/master/docs/logos/logos.png "Institutions")
