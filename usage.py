"""
usage.py — end-to-end tour of the Scott API

Covers:
  1. Building and parsing graphs
  2. Canonical traces (core feature)
  3. Canonical adjacency matrices
  4. Pipeline internals — DAG and tree steps  [legacy backend only]
  5. Graph fragmentation                       [legacy backend only]

Run with the default (Rust) backend:
    python usage.py

Run with the pure-Python legacy backend:
    SCOTT_BACKEND=legacy python usage.py
"""

import hashlib
import scott as st


# ─── 1. Building and Parsing Graphs ──────────────────────────────────────────
#
# Scott supports both node labels and edge labels (colors/weights).
# This is the key difference from tools like nauty/bliss, which ignore edge
# labels by default.  All parsing functions return a list, even for a single
# graph, so index with [0] when you only expect one result.


# 1.1  Build a graph programmatically
# ------------------------------------
# Edge `modality` is the edge color/weight.  Here we use bond order semantics:
# modality=2 means a double bond, omitting it (default) means a single bond.

graph = st.structs.graph.Graph()

n1 = st.structs.node.Node("1", "C")
n2 = st.structs.node.Node("2", "O")
n3 = st.structs.node.Node("3", "H")
n4 = st.structs.node.Node("4", "H")

e1 = st.structs.edge.Edge("1", n1, n2, modality=2)  # C=O double bond
e2 = st.structs.edge.Edge("2", n1, n3)              # C-H single bond
e3 = st.structs.edge.Edge("3", n1, n4)              # C-H single bond

graph.add_node(n1)
graph.add_nodes([n2, n3, n4])
graph.add_edge(e1)
graph.add_edge(e2)
graph.add_edge(e3)

print(n1)
print(e1)
print(graph)


# 1.2  SDF (chemical structure)
# ------------------------------

# With hydrogens (full molecular graph)
compounds = st.parse.from_sdf(file_path='./data/molecule/cafeine.sdf', ignore_hydrogens=False)
cafeine = compounds[0]
print(cafeine)

# Without hydrogens — the heavy-atom skeleton is often sufficient and faster to canonize
cafeine_no_h = st.parse.from_sdf(file_path='./data/molecule/cafeine.sdf', ignore_hydrogens=True)[0]
print(cafeine_no_h)


# 1.3  PubChem XML (batch)
# -------------------------
# PubChem XML files contain a batch of compounds; the parser always returns a list.

compounds = st.parse.from_pubchem_xml(
	file_path='./data/batch/xml/Compound_134600001_134625000.xml',
	ignore_hydrogens=True,
)
assert len(compounds) == 8
print(compounds[3])


# 1.4  SMILES  [requires: pip install scott[rdkit]]
# --------------------------------------------------

mol = st.parse.parse_smiles('CCOCOCC=CCONC')

for id_node in mol.V:
	print("Node #%s : %s" % (str(id_node), str(mol.V[id_node].label)))

# Disconnected SMILES (multiple components separated by '.')
multi = st.parse.parse_smiles('CC.C')


# 1.5  DOT format
# ----------------
# CFI-rigid graphs (https://arxiv.org/abs/1705.03686) are a standard benchmark
# for isomorphism solvers.  File name encodes graph properties:
#   cfi-rigid-t2-  NNNN  -CC  -I
#                   |      |    └─ instance id
#                   |      └───── isomorphism class
#                   └──────────── number of vertices

cfi_dot = st.parse.from_dot(file_path='./data/isotest/cfi-rigid-t2-dot/cfi-rigid-t2-0016-04-1.dot')[0]
assert len(cfi_dot.V) == 16


# 1.6  DIMACS format
# -------------------
# The same graph is also available in DIMACS format.

cfi_dimacs = st.parse.from_dimacs(file_path='./data/isotest/cfi-rigid-t2/cfi-rigid-t2-0016-04-1')[0]
assert len(cfi_dimacs.V) == len(cfi_dot.V)


# 1.7  NetworkX  [requires: pip install scott[nx]]
# -------------------------------------------------

import networkx as nx

nxg = nx.Graph()
nxg.add_node("a", label="C")
nxg.add_node("b", label="O")
nxg.add_edge("a", "b", weight=2)
g_from_nx = st.parse.from_networkx(nxg)

# Works on large random graphs too
large = st.parse.from_networkx(nx.random_geometric_graph(200, 0.125, seed=896803))


# ─── 2. Canonical Traces ─────────────────────────────────────────────────────
#
# A canonical trace is a plain string that uniquely identifies an isomorphism
# class.  Two graphs are isomorphic iff their traces are equal.
#
# Because it is just a string, the trace can be stored in a database, used as a
# dictionary key, hashed to a fixed-size fingerprint, or compared across
# processes and machines — no graph library required on the reading side.


# 2.1  Basic canonization
# ------------------------

simple = st.parse.from_pubchem_xml(file_path='./data/molecule/simple.xml')[0]

# `to_cgraph` returns a CGraph object; str() produces the canonical trace
simple_cgraph = st.canonize.to_cgraph(simple)
simple_trace  = str(simple_cgraph)

assert simple_trace == (
	'(H:1, H:1, (H:1, H:1, ((((C:1).#2{$1}:2)C:2)C:2, '
	'((((C:1).#2{$1}:2)C:2)C:1).#2{$2}:1)C:1)C:1, '
	'(O:2, (((((C:1).#2{$1}:2)C:2)C:1).#2{$2}:1)O:1)C:1)C'
)

# SMILES canonization (requires rdkit extra)
mol_trace = str(st.canonize.to_cgraph(st.parse.parse_smiles('CCOCOCC=CCONC', ignore_hydrogens=True)))
assert mol_trace == '(C:1, (((((((((C:1)N:1)O:1)C:1)C:2)C:1)C:1)O:1)C:1)O:1)C'

# For disconnected graphs, `scott_trace` handles multiple components and
# returns a string directly without wrapping in a CGraph object.
multi_trace = st.canonize.scott_trace(st.parse.parse_smiles('CC.C'))


# 2.2  Hashing the trace
# -----------------------
# Apply any string hash to get a compact, fixed-size graph fingerprint.
# sha256 is a good default; sha224 is slightly shorter.

fingerprint = hashlib.sha256(simple_trace.encode()).hexdigest()
# Stable across runs, machines, and Python versions.

assert hashlib.sha224(simple_trace.encode()).hexdigest() == \
	'a90f308ea4c2cd8a1003a32507b4769f5ef5f31bb4f2602856200982'


# 2.3  Pairwise isomorphism via string comparison
# ------------------------------------------------
# CFI file nomenclature:  cfi-rigid-t2-NNNN-CC-I
#   NNNN = vertex count, CC = isomorphism class, I = instance id
#
# So G and H (class 01, different instances) are isomorphic,
# while E and F (class 02) belong to a different class.

G = st.parse.from_dimacs(file_path='./data/isotest/cfi-rigid-t2/cfi-rigid-t2-0020-01-1')[0]
H = st.parse.from_dimacs(file_path='./data/isotest/cfi-rigid-t2/cfi-rigid-t2-0020-01-2')[0]
E = st.parse.from_dimacs(file_path='./data/isotest/cfi-rigid-t2/cfi-rigid-t2-0020-02-1')[0]
F = st.parse.from_dimacs(file_path='./data/isotest/cfi-rigid-t2/cfi-rigid-t2-0020-02-2')[0]

# Canonize once …
Gc, Hc, Ec, Fc = [st.canonize.to_cgraph(x) for x in (G, H, E, F)]

# … then compare as strings — no repeated isomorphism work needed.
assert str(Gc) == str(Hc)   # same class → equal traces
assert str(Ec) == str(Fc)
assert str(Gc) != str(Ec)   # different classes → different traces
assert str(Hc) != str(Fc)


# ─── 3. Canonical Adjacency Matrices ─────────────────────────────────────────
#
# An adjacency matrix encodes pairwise connectivity as an N×N array.
# Without a canonical vertex ordering, two isomorphic graphs will generally
# produce different matrices.  Passing `canonic=True` induces an ordering from
# Scott's canonical tree, guaranteeing a unique matrix per isomorphism class.
# This is useful for graph neural networks and other pipelines that need a
# stable, comparable tensor representation.

G = st.parse.from_dimacs(file_path='./data/isotest/cfi-rigid-t2/cfi-rigid-t2-0016-04-1')[0]
H = st.parse.from_dimacs(file_path='./data/isotest/cfi-rigid-t2/cfi-rigid-t2-0016-04-2')[0]

# Raw matrices differ because vertex insertion order is arbitrary.
assert G.adjacency_matrix() != H.adjacency_matrix()

# Canonical matrices are identical for isomorphic graphs.
Ag = G.adjacency_matrix(canonic=True)
Ah = H.adjacency_matrix(canonic=True)
assert Ag == Ah

# And distinct for non-isomorphic graphs.
G2 = st.parse.from_dimacs(file_path='./data/isotest/cfi-rigid-t2/cfi-rigid-t2-0020-01-1')[0]
H2 = st.parse.from_dimacs(file_path='./data/isotest/cfi-rigid-t2/cfi-rigid-t2-0020-02-2')[0]
assert G2.adjacency_matrix(canonic=True) != H2.adjacency_matrix(canonic=True)


# ─── 4. Pipeline Internals  [legacy backend only] ────────────────────────────
#
# The canonization pipeline has two internal steps that are exposed in the
# legacy (pure-Python) backend: graph → DAG → tree → trace.
# These are useful for debugging or research, but not needed for normal use.
# They are NOT available in the default Rust backend.
#
# To run this section:  SCOTT_BACKEND=legacy python usage.py

import os
if os.environ.get('SCOTT_BACKEND') == 'legacy':
	simple = st.parse.from_pubchem_xml(file_path='./data/molecule/simple.xml')[0]

	# Step 1: convert the graph to a DAG rooted at a chosen vertex
	dag = simple.to_dag(id_root='3')

	# Step 2: serialize the DAG to a canonical tree
	tree = dag.to_tree(id_root='3', id_origin=None, modality_origin=None)
	tree.score_tree()
	print(tree)


# ─── 5. Graph Fragmentation  [legacy backend only] ───────────────────────────
#
# Scott can decompose a graph into node-centered subgraphs and compute
# fragment-based representations.  This module is only available in the
# legacy backend (`scott_legacy` / `SCOTT_BACKEND=legacy`).
#
# To run this section:  SCOTT_BACKEND=legacy python usage.py

if os.environ.get('SCOTT_BACKEND') == 'legacy':
	cafeine = st.parse.from_sdf(file_path='./data/molecule/cafeine.sdf', ignore_hydrogens=True)[0]

	# 5.1  Extract an ego subgraph of radius 1 around a chosen root node
	sub = st.fragmentation.extract_subgraph(cafeine, id_root="1", size=1)
	print("G' = (V', E'), |V'| = %d, |E'| = %d" % (len(sub.V), len(sub.E)))
	print(sub)

	# 5.2  Map every node to its node-centered fragment of radius 2
	frags = st.fragmentation.map_cgraph(cafeine, size=2)
	print("CGraphs:", frags)

	# 5.3  Project the graph into a fragment-frequency vector (bag-of-fragments)
	dico = st.fragmentation.fragment_projection(cafeine, size=1)
	print("Projection:", dico)

	# 5.4  Linear n-grams: sliding window of width 2 over paths of fragment size 1
	ngrams_linear = st.fragmentation.enum_ngrams(cafeine, mode='linear', window_size=2, fragment_size=1)
	print("Linear n-grams:", ngrams_linear)

	# 5.5  Radial n-grams: window of radius 3, same fragment size
	ngrams_radial = st.fragmentation.enum_ngrams(cafeine, mode='radial', window_size=3, fragment_size=1)
	print("Radial n-grams:", ngrams_radial)
