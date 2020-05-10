import scott as st
import scott as st

from urllib.request import urlopen


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

# 2.2 Intermediary step : get a canonical graph for an arbitrary root 

dag = simple.to_dag(id_root = '3')

# 2.3 Intermediary step : get the canonical tree

tree = dag.to_tree(id_root = '3', id_origin = None, modality_origin = None) 

# score the tree so we can print it
tree.score_tree()

# print the raw tree, with hashed markers
print(tree)



# 4. Graph Fragmentation 

# You can use Scott to fragment a graph into several subgraphes

# 4.1 Extract an arbitrary sub-graph of size 1 (caffeine)

cafeine = st.parse.from_sdf(file_path='./data/molecule/cafeine.sdf', ignore_hydrogens = True)[0]
sub = st.fragmentation.extract_subgraph(cafeine, id_root = "1", size = 1)
print("G' = (V', E'), |V| = " + str(len(sub.V)) + ", |E| = " + str(len(sub.V)))
print(sub)

# 4.2 Map each node with a node-centered fragment (size 2)

frags = st.fragmentation.map_cgraph(cafeine, size = 2)
print("CGraphs :")
print(frags)

# 4.3 Project the cafeine into a fragment space (size 1)

dico = st.fragmentation.fragment_projection(cafeine, size = 1)
print("Projection :")
print(dico)

# 4.4 Get n-grams from a graph

ngrams = st.fragmentation.enum_ngrams(cafeine, mode = 'linear', window_size = 2, fragment_size = 1)
print("Linear NGrams :")
print(ngrams)

# 4.5 Get radial n-grams from a graph

ngrams = st.fragmentation.enum_ngrams(cafeine, mode = 'radial', window_size = 3, fragment_size = 1)
print("Radial NGrams :")
print(ngrams)
