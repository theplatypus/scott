from typing import Dict, Tuple, List

from .structs.graph import Graph
from .structs.node import Node
from .structs.edge import Edge

from .fragmentation import map_cgraph

from copy import deepcopy

verbose = True

def trace(msg):
	if (verbose):
		print("[export.py] " + msg)

def to_txt():
	return None

def str_to_int(val): 
	try:
		val = int(val)
	except :
		i = 0 
		for c in val : 
			i = i + ord(c)
		val = i
	finally:
		return val

def to_dot(graph: Graph, file_path: str, compress_magnets = True) :

	magnets = {}
	cpt = 1

	with open(file_path, 'a') as output_file:

		# head
		output_file.write('graph %s {\n\n' % (graph.id))
		
		# vertices block 
		for id_node in graph.V.keys() :
			node = graph.V[id_node]
			if node.meta["is_mirror"] or node.meta["is_virtual"] :
				magnet = str(node.magnet)
				if not magnet in magnets :
					if compress_magnets :
						magnets[magnet] = "$" + str(cpt) 
						cpt = cpt + 1
					else :
						magnets[magnet] = magnet
				output_file.write('"%s" [label=%s] ;\n' % (node.id, "#"+ str(magnets[magnet]) if node.meta["is_mirror"] else "*" + str(magnets[magnet])))
			else :
				output_file.write('"%s" [label=%s] ;\n' % (node.id, str(node.label) or "."))
		output_file.write('\n')
		
		# edges block
		for id_edge in graph.E.keys() :
			edge = graph.E[id_edge]
			output_file.write('"%s" -- "%s" ;\n' % (edge.id_a, edge.id_b))
		output_file.write('\n')
		
		# tail
		output_file.write('}\n')
	
	return True

def to_AXE(graph: Graph, frag_size : int = 1, edge_embedding: callable = lambda edge : [ str_to_int(edge.modality) ] ) : 
	ordered_nodes = graph.ordered_nodes_ids()
	frag_map = map_cgraph(graph, size = frag_size)

	A = graph.adjacency_matrix()
	X = [ frag_map[node_id] for node_id in ordered_nodes ]
	E = deepcopy(A)

	dim = None
	for id_edge in graph.E :
		edge = graph.E[id_edge]
		i = ordered_nodes.index(edge.id_a)
		j = ordered_nodes.index(edge.id_b)
		embedding = edge_embedding(edge)
		E[i][j] = embedding
		E[j][i] = embedding
		if dim is None :
			dim = len(embedding)

	N = len(graph.V)
	for i in range(N):
		for j in range(N):
			if type(E[i][j]) == int :
				E[i][j] = [0] * dim
	
	return (A, X, E)
