
from typing import Tuple, Callable, List

from .structs.graph import Graph
from .structs.cgraph import CGraph
from .structs.node import Node

from .canonize import to_cgraph

verbose = False

def trace(msg, indent=1, f=" "):
	if (verbose == True):
		print("[fragmentation.py]" + f + indent*"\t" + msg)

def fragment_projection(graph: Graph, size: int = 1, candidate_rule: str = "$degree", branch_rule: str = "$depth > tree.parent_modality > $lexic") -> List[CGraph]:
	"""
		fragment_projection
		====================
	"""
	frags = [ to_cgraph(subgraph, candidate_rule = candidate_rule, branch_rule = branch_rule)
	 		for (id_node, subgraph) in fragment_graph(graph, size) ]
	projection = {}
	for frag in frags :
		frag = str(frag)
		if frag in projection :
			projection[frag] = projection[frag] + 1
		else :
			projection[frag] = 1
	return projection

def map_cgraph(graph: Graph, size: int = 1, candidate_rule: str = "$degree", branch_rule: str = "$depth > tree.parent_modality > $lexic") -> List[Tuple[str, CGraph]]:
	"""
		fragment_projection
		====================
	"""
	mappings = [ (id_node, to_cgraph(subgraph, candidate_rule = candidate_rule, branch_rule = branch_rule))
	 		for (id_node, subgraph) in fragment_graph(graph, size) ]
	dic = {}
	for (id_node, cgraph) in mappings :
		dic[id_node] = str(cgraph)
	return dic

def fragment_graph(graph: Graph, size: int = 1) -> List[Tuple[str, Graph]]:
	"""
		fragment_graph
		===============
	"""
	return [ (id_node, extract_subgraph(graph, id_node, size)) for id_node in graph.V ]

def extract_subgraph(graph: Graph, id_root: str, size: int  = 1) -> Graph:
	"""
		extract_subgraph
		=================

	"""
	graph.reset_floor()
	#print("id_root : %s" % (id_root))
	#print(type(id_root))
	floors = graph.__copy__().group_by_floor(id_root)
	#print(floors)
	floors_int = { int(k): [ i for i in v ] for k,v in floors.items() }
	#print(floors_int)
	max_level = min(size, max(floors_int))

	ids_node = []
	for level in range(0, max_level + 1):
		ids_node = ids_node + floors_int[level]
	nodes = [ graph.V[id_node] for id_node in ids_node ]

	trace(str(nodes))

	edges = [ graph.E[id_edge] for id_edge in graph.E if graph.E[id_edge].id_a in ids_node
	and graph.E[id_edge].id_b in ids_node ]
	trace(str(edges))

	subgraph = Graph()
	subgraph.add_nodes(nodes)
	subgraph.add_edges(edges)

	return subgraph

def extract_ngrams(graph: Graph, id_root: str, window_size: int  = 1, fragment_size: int = 1,
	candidate_rule = "$degree", branch_rule = "$depth > tree.parent_modality > $lexic") -> List[List[CGraph]]:
	"""
		extract_ngram
		==============
	"""
	floors = graph.__copy__().group_by_floor(id_root)
	frags = {}
	ngrams = []

	for floor in range(0, window_size):
		frags[floor] = {}
		for id_node in floors[floor]:
			if (id_node in graph.meta['cgraph_map']):
				cgraph = graph.meta.get('cgraph_map')[id_node]
			else:
				subgraph = extract_subgraph(graph, id_node, size = fragment_size)
				cgraph = to_cgraph(subgraph, candidate_rule = candidate_rule, branch_rule = branch_rule)
			frags[id_node] = str(cgraph)
	
	for floor in range(1, window_size):
		for id_node in floors[floor]:
			paths = graph.enumerate_simple_paths(id_root, id_node)
			for path in paths :
				ngrams.append([ frags[id_node] for id_node in path])

	return ngrams


def enum_ngrams(graph: Graph, window_size = 2, fragment_size = 1,
	candidate_rule = "$degree", branch_rule = "$depth > tree.parent_modality > $lexic") -> List[List[CGraph]]:

	# speed-up : pre-compute each cgraph
	graph.meta['cgraph_map'] = map_cgraph(graph, 
		size = fragment_size, 
		candidate_rule = candidate_rule, 
		branch_rule = branch_rule)
	
	return [ ngram for ngrams
		in [ extract_ngrams(graph, id_node, window_size, fragment_size, candidate_rule, branch_rule)
			for id_node in graph.V ]
		for ngram in ngrams ]
