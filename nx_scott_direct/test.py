import networkx as nx

from nx_scott_direct import to_cgraph

H = nx.Graph(nx.nx_pydot.read_dot("./data/isotest/cfi-rigid-t2-dot/cfi-rigid-t2-0020-01-1.dot"))
G = nx.Graph(nx.nx_pydot.read_dot("./data/isotest/cfi-rigid-t2-dot/cfi-rigid-t2-0020-01-2.dot"))

str(to_cgraph(H)) == str(to_cgraph(G))

nx.vf2pp_is_isomorphic(G, H, node_label=None)


E = nx.Graph(nx.nx_pydot.read_dot("./data/isotest/cfi-rigid-t2-dot/cfi-rigid-t2-0020-02-1.dot"))
F = nx.Graph(nx.nx_pydot.read_dot("./data/isotest/cfi-rigid-t2-dot/cfi-rigid-t2-0020-02-2.dot"))

str(to_cgraph(E)) == str(to_cgraph(F))

nx.vf2pp_is_isomorphic(E, F, node_label=None)

# False
str(to_cgraph(G)) == str(to_cgraph(E))

nx.vf2pp_is_isomorphic(G, E, node_label=None)
