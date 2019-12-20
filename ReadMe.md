# Scott 

Scott is a software able to compute, for **any labelled (edge and node) graph**, a **canonical tree representative of its isomorphism class**, that we can derive to a **canonical trace** (string) or **adjacency matrix**.

# Table of contents

This repository summary aims to be synthetic and straight to the goal. For more informations about the graph isomorphism problem, algorithm details, please refer to the [repo page](https://theplatypus.github.io/scott/).

- [Getting started](#getting-started)
  * [From source code](#from-source-code)
  * [From Pypi](#from-pypi)
  * [From Docker](#from-docker)
- [Usage](#usage)
  * [Import Graphs](#import-graphs)
  * [Canonical traces](#from-source-code)
  * [Canonical Adjacency Matrices](#canonical-adjacency-matrices)
- [Citation](#citation)
- [Licence](#licence)
- [References](#references)

## Getting started 

### From source code

Simply clone the repo in a local repertory

```bash
# get the code
git clone https://github.com/theplatypus/scott.git
cd ./scott

# (optionnal) install using setuptools
python3 setup.py install
```

Then you should be able to import `scott` package from python :

```python
import scott as st
```

### From Pypi

```bash
pip install <todo>
```

### From Docker

To get `scott` in an environment with additional dependencies installed (chemical librabries, jupyter notebooks,etc.), a Docker container is available :

```bash
# Build the image containing all the stuff for a simple standalone install
docker build -t scott .
# or pull it
docker pull docker.pkg.github.com/theplatypus/scott/scott:latest

# run an interactive shell, where you can import scott in python default interpreter
docker run --rm -it scott

# or run a jupyter notebook including scott
docker run -it -p 8888:8888 scott /bin/bash -c "jupyter notebook --notebook-dir=/opt/notebooks --ip='*' --port=8888 --no-browser --allow-root"
```

For specific uses, you have access to alternative `Dockerfiles` in `/dockerfiles`, each of them being a tag that you can also pull.

#### Pypy 

An image including the [Pypy](https://pypy.org/) interpreter, a high-performance alternative to the classic CPython. Use it with `ipython` or launch a jupyter server.

```bash
docker build -t scott:pypy -f dockerfiles/pypy/Dockerfile .
docker run -it --rm -p 8888:8888 scott:pypy

# > ipython 
# > jupyter notebook --notebook-dir=/opt/notebooks --ip='*' --port=8888 --no-browser --allow-root
```

#### Debian 

A debian-based image, if you are not an Anaconda supporter.

```bash
docker build -t scott:debian -f dockerfiles/debian/Dockerfile .
docker run -it --rm -p 8888:8888 scott:debian

# > ipython 
# > jupyter notebook --notebook-dir=/opt/notebooks --ip='*' --port=8888 --no-browser --allow-root
```

#### PySpark

An image designed to run inside a [Spark](https://spark.apache.org/) cluster. 

```bash
docker build -t scott:spark -f dockerfiles/pyspark/Dockerfile .

docker run -it -v $(pwd):/home/scott scott:spark pyspark --master local[*]
```

---

## Usage

For more informations about code usage, please refer to `usage.py` and `usage_advanced.py`.

### Build a Graph

You can describe a `Graph` algorithmically.

```python
import scott as st

# describe a graph from scratch

graph = st.structs.graph.Graph()
n1 = st.structs.node.Node("1", "C")
n2 = st.structs.node.Node("2", "O")
n3 = st.structs.node.Node("3", "H")	
n4 = st.structs.node.Node("4", "H")

e1 = st.structs.edge.Edge("1", n1, n2, modality=2)
e2 = st.structs.edge.Edge("2", n1, n3)
e3 = st.structs.edge.Edge("3", n1, n4)

graph.add_node(n1)
graph.add_nodes([n2, n3, n4])
graph.add_edge(e1)
graph.add_edge(e2)
graph.add_edge(e3)

print(n1)
print(e1)
print(graph)
```

### Import Graphs

Scott is also able to parse a few graph formats files. Note that a parsing function always returns a list, even if there is one molecule in the file.

```python
# Parse a .sdf file (chemical file standard) :

# from blob...
CAFEINE_URL = "https://drive.google.com/uc?id=1lXeFVGS77oK_qL3NESDV_UjJknPyiICx"
file_content = urlopen(CAFEINE_URL).read().decode()

compounds = st.parse.from_sdf(file_content, ignore_hydrogens = False)
cafeine = compounds[0]
print(cafeine)

# ... or from file path - note we ignore hydrogens this time
compounds = st.parse.from_sdf(file_path='./data/molecule/cafeine.sdf', ignore_hydrogens = True)
cafeine_without_H = compounds[0]
print(cafeine_without_H)

# Parse a SMILES string (RDKit required)
smile = st.parse.parse_smiles('CCOCOCC=CCONC')

# we can iterate over graph vertices
for id_node in smile.V :
	print("Node #%s : %s" % (str(id_node), str(smile.V[id_node].label)))

# Parse a .dot file
cfi1 = st.parse.from_dot(file_path = './data/isotest/cfi-rigid-t2-dot/cfi-rigid-t2-0016-04-1.dot')[0]

# Parse a .dimacs file
cfi2 = st.parse.from_dimacs(file_path = './data/isotest/cfi-rigid-t2/cfi-rigid-t2-0016-04-1')[0]
```

### Canonical traces

A canonical trace is a string representation of the tree representative of an isomorphism class. This is the main feature of `Scott`.

```python
simple = st.parse.from_pubchem_xml(file_path= './data/molecule/simple.xml')[0]

# we get a CGraph object from the function `st.canonize.to_cgraph`...
simple_cgraph = st.canonize.to_cgraph(simple)

# ...that we can print directly or convert to string
simple_canon = str(simple_cgraph)

assert simple_canon == '(H:1, H:1, (H:1, H:1, ((((C:1).#2{$1}:2)C:2)C:2, ((((C:1).#2{$1}:2)C:2)C:1).#2{$2}:1)C:1)C:1, (O:2, (((((C:1).#2{$1}:2)C:2)C:1).#2{$2}:1)O:1)C:1)C'
```

If you only need a [hash function](https://en.wikipedia.org/wiki/Hash_function) for graphs, you can apply a string hash function (`md5`, `sha`, etc.) to the trace obtained.

```python
import hashlib 

assert hashlib.sha224(simple_canon.encode()).hexdigest() == 'a90f308ea4c2cd8a1003a32507b4769f5ef5f31bb4f2602856200982'
```

```python
G = st.parse.from_dimacs(file_path = './data/isotest/cfi-rigid-t2/cfi-rigid-t2-0020-01-1')[0]
H = st.parse.from_dimacs(file_path = './data/isotest/cfi-rigid-t2/cfi-rigid-t2-0020-01-2')[0]

E = st.parse.from_dimacs(file_path = './data/isotest/cfi-rigid-t2/cfi-rigid-t2-0020-02-2')[0]
F = st.parse.from_dimacs(file_path = './data/isotest/cfi-rigid-t2/cfi-rigid-t2-0020-02-2')[0]

# Can take few seconds
Gc = st.canonize.to_cgraph(G)
Hc = st.canonize.to_cgraph(H)
Ec = st.canonize.to_cgraph(E)
Fc = st.canonize.to_cgraph(F)

# So, following the nomenclature G == H and E == F, ...

assert str(Gc) == str(Hc)
assert str(Ec) == str(Fc)

# ... but G != E/F and H != E/F 
assert str(Gc) != str(Ec)
assert str(Hc) != str(Fc)
```

### Canonical Adjacency Matrices

On a graph `G` of `N` vertices, an adjacency matrix `A` is a `N*N` array describing the link between two vertices. `Scott` can help to get a standardized adjacency matrix, such as isomophic graph will have the exact same adjacency matrices, which can help learning process by bringing the "same elements towards the same neurons".

```python
# Let g and h be two isomorphic graphs
g = st.parse.from_dot(file_path="./data/isotest/cfi-rigid-t2-dot/cfi-rigid-t2-0020-02-2.dot")[0]
h = st.parse.from_dot(file_path="./data/isotest/cfi-rigid-t2-dot/cfi-rigid-t2-0020-02-1.dot")[0]

# if we compare their adjacency matrix, it is very unlikely to get the two exact same matrices,
# as there is no order on vertices
g.adjacency_matrix() == h.adjacency_matrix()
# False

# but if we induce an order based on the representant tree given by scott,
# there is only one canonical adjacecny matrix
assert g.adjacency_matrix(canonic = True) == h.adjacency_matrix(canonic = True)

```

## Citation

If you use or fork `scott` in further works, please cite the following :

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

The Python source code we provide is available on the [GitHub repo](https://github.com/theplatypus/scott), under the MIT public licence. 

Feel free to improve it.

Written and developed by :

- Nicolas BLOYET **([See-d](https://www.see-d.fr/), [IRISA Expression](https://www-expression.irisa.fr/fr/), [LMBA](http://web.univ-ubs.fr/lmba/))**
- Pierre-François MARTEAU **([IRISA Expression](https://www-expression.irisa.fr/fr/))**
- Emmanuel FRÉNOD **([See-d](https://www.see-d.fr/), [LMBA](http://web.univ-ubs.fr/lmba/))**

![logos](https://raw.githubusercontent.com/theplatypus/test-pages/master/docs/logos/logos.png "Institutions")
