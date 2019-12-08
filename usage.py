import scott as st

from urllib.request import urlopen

# 1. - Parsing Graphs
# =====================================

# Scott can handle a few graphs formats, among the (big) variety of formats existing

# 1.1 - describe a graph from scratch

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


# 1.2 Parse a .sdf file (chemical file standard) :

# from blob
CAFEINE_URL = "https://drive.google.com/uc?id=1lXeFVGS77oK_qL3NESDV_UjJknPyiICx"
file_content = urlopen(CAFEINE_URL).read().decode()

compounds = st.parse.from_sdf(file_content, ignore_hydrogens = False)
cafeine = compounds[0]
print(cafeine)

# from file path - note we ignore hydrogens this time
compounds = st.parse.from_sdf(file_path='./data/molecule/cafeine.sdf', ignore_hydrogens = True)
cafeine_without_H = compounds[0]
print(cafeine_without_H)

# Note, `parse.from_sdf` always returns a list, even if there is one molecule in the file


# 1.3 Parse a PubChem .xml file :

compounds = st.parse.from_pubchem_xml(file_path = './data/batch/xml/Compound_134600001_134625000.xml', ignore_hydrogens = True)

# PubChems XML contain a batch of graphs.
# That's why the `parse.from_pubchem_xml` function will always return a list, even for  a unique graph,
# just like `parse.from_sdf`
assert len(compounds) == 8

# access to a member of the batch as a list element
print(compounds[3])


# 1.4 Parse a SMILES string 

# To finish with molecular graphs, Scott can directly handle SMILES string
# if `rdkit` library is intalled, otherwise it will raise an ImportError
# If you're interested in that feature, you should use the Docker package

smile = st.parse.parse_smiles('CCOCOCC=CCONC')

# we can iterate over graph vertices
for id_node in smile.V :
	print("Node #%s : %s" % (str(id_node), str(smile.V[id_node].label)))


# 1.5 Parse a .dot file

# We now quit chemistry field to parse graph files which are generic, like the .dot format 
# this graph is part of the family cfi-rigid-t2, used for isomorphism test 

cfi1 = st.parse.from_dot(file_path = './data/isotest/cfi-rigid-t2-dot/cfi-rigid-t2-0016-04-1.dot')[0]

# as its name suggests it, this graph has 16 vertices
assert len(cfi1.V) == 16


# 1.5 Parse a .dimacs file

# We finally parse a .dimacs file, very common as well
# The above graph is also available in this format 
# (also avaible at  "https://drive.google.com/uc?id=1b9zcVQ4WrV68GkzkRpTPn05GZRFsl8cJ" )

cfi2 = st.parse.from_dimacs(file_path = './data/isotest/cfi-rigid-t2/cfi-rigid-t2-0016-04-1')[0]




# 2. - Get canonical traces of graphs
# =====================================

# The core feature of Scott is to compute for a graph a canonical trace based on 
# the canonical tree representant of its isomorphism class


# 2.1 Compute a CGraph (Compressed Graph)

# We take the example of a small molecule
simple = st.parse.from_pubchem_xml(file_path= './data/molecule/simple.xml')[0]

# we get a CGraph object from the function `st.canonize.to_cgraph`...
simple_cgraph = st.canonize.to_cgraph(simple)

# ...that we can print directly or convert to string
simple_canon = str(simple_cgraph)

assert simple_canon == '(H:1, H:1, (H:1, H:1, ((((C:1).#2{$1}:2)C:2)C:2, ((((C:1).#2{$1}:2)C:2)C:1).#2{$2}:1)C:1)C:1, (O:2, (((((C:1).#2{$1}:2)C:2)C:1).#2{$2}:1)O:1)C:1)C'

# if you only need a short, fixed sized hash :
import hashlib 

assert hashlib.sha224(simple_canon.encode()).hexdigest() == 'a90f308ea4c2cd8a1003a32507b4769f5ef5f31bb4f2602856200982'


# 2.2 Validity test 

# We ensure here that isomorphic graph lead to the same trace
# cfi graphs are perfect for that exercice :
# 
# Some details on file nomenclature : 
#  (src : https://arxiv.org/abs/1705.03686 ; https://www.lics.rwth-aachen.de/go/id/rtok/ )
# 	cfi-rigid-t2-	0020	-01		-1
#									- id
#							- isomorphism class
#					- number of vertices

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



# 3. - Get canonical adjacency matrices of graphs (beta feature)
# ===============================================================

# Once we can obtain a canonical tree for each graph, we can induce an order of the vertice set
# of the original graph by seeing node_id appareance order in the tree
# We can thus deduce an adjacency matrix unique for an isomophism class

G = st.parse.from_dimacs(file_path = './data/isotest/cfi-rigid-t2/cfi-rigid-t2-0016-04-1')[0]
H = st.parse.from_dimacs(file_path = './data/isotest/cfi-rigid-t2/cfi-rigid-t2-0016-04-2')[0]


# By default, as vertices are not declared in the same order, it is very likely 
# that adjacency matrices won't be equal

G.adjacency_matrix() == H.adjacency_matrix()
# > False

# But if we use the `canonic` argument, graphs are canonicalized before computing the adjacency matrix
# and so we get a consistent vertice ordering
Ag = G.adjacency_matrix(canonic = True)
Ah = H.adjacency_matrix(canonic = True)

assert Ag == Ah

G = st.parse.from_dimacs(file_path = './data/isotest/cfi-rigid-t2/cfi-rigid-t2-0020-01-1')[0]
H = st.parse.from_dimacs(file_path = './data/isotest/cfi-rigid-t2/cfi-rigid-t2-0020-02-2')[0]

Ag = G.adjacency_matrix(canonic=True)
Ah = H.adjacency_matrix(canonic=True)

assert Ag != Ah
