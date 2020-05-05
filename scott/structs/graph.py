#from __future__ import annotations

from .node import Node, Virtual_Node, Mirror_Node
from .edge import Edge
from .tree import Tree, def_tree_fn

import json
import pprint

import re
import math
import copy
import hashlib
import random 

#import numpy as np

from typing import Callable, List, Tuple

# Types aliases
Node_Callback = Callable[[Node, Node, str], bool]
Comparator = Callable[[Tuple, Tuple], int]
Scoring = Callable[[Node, 'Graph'], Tuple]

verbose = False
verbosity = 4

def trace(msg, indent=1, f=" ", override = False):
	if ((verbose and indent <= verbosity) or override):
		print("[graph.py]" + f + indent*"\t" + msg)

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

def def_node_fn(rule: str) -> (Scoring):
	"""
		node_function

		Define a Node scoring function in a Graph context.
		Scoring = Callable[[Node, Graph], Tuple]
	"""
	args = [ arg.strip() for arg in rule.split(">") ]
	return lambda id_node, graph : tuple([ graph.__eval__(str(arg), id_node) for arg in args ])

attributes_definitions = {
	"$degree" : "len(graph.R[id_node])",
	"$label" : "graph.V[id_node].label",
	"$bounds" : "tuple([ -i for i in graph.evaluate_bounds(id_node)])"
}

def empty_copy(obj):
	class Empty(obj.__class__):
		def __init__(self): pass
	newcopy = Empty( )
	newcopy.__class__ = obj.__class__
	return newcopy


class Graph :
	"""
		Fetchable Graph
		================

		A general pupose Graph representation, under the form G = (V, E)

		Fields
			- id
			- V (nodes)
			- E (edges)
			- R (router)

		A dictionnary-like structure is preferred over a Matrix representation,
		despite the last being more space-efficient, because of the algorithm
		capability of using data and metadata, which in any way have to be
		indexed in a dictionnary.

		Once the computation is finished, it is well-suited to compress this
		Graph into a CGraph.

		NOTE [complexity] : replace R by a Matrix
	"""

	def __init__(self, id = None):
		self.id = str(id)
		self.meta = {}
		self.V = {}
		self.E = {}
		self.R = {}

	def __iter__(self):
		pass

	def next(self):
		"""
			>>> for node: Node in graph: Graph
		"""
		pass

	def __str__(self):
		return self.__repr__()

	def __repr__(self):
		# hack
		# "json.decoder.JSONDecodeError: Key name must be string at char"
		if "floors" in self.meta :
			self.meta["floors"] = pprint.pformat(self.meta["floors"])

		# first, resolve references into a string format with pprint
		# otherwise, general indent is break
		str_dump = pprint.pformat(self.__dict__).replace("'", "\"")
		
		#print(str_dump)
		return json.dumps(json.loads(str_dump), indent=4, sort_keys=True)

	def __copy__(self):
		fcopy = Graph(self.id)
		fcopy.meta = copy.deepcopy(self.meta)
		fcopy.add_nodes([self.V[id_node] for id_node in self.V])
		fcopy.add_edges([self.E[id_edge] for id_edge in self.E])
		return fcopy

		#newcopy = empty_copy(self)
		#newcopy.__dict__.update(self.__dict__)
		#return newcopy
		#return copy.deepcopy(self)

	def __eval__(self, arg: str, id_node: int) -> float:
		"""
			evaluate_arg : Get and evaluate actual values

			Allow to translate the formal definition of an attribute (e.g -$degree)
			into actual scalar or litteral values.
			This implementation uses the `eval()` function, and so is quite unsafe,
			because destructive operations are allowed.
			(assumption is made that we are between responsible adults)
		"""
		# aliases for expression
		graph = self
		node = graph.V[id_node]

		# replace definitions
		defs = re.findall('\$\w*', arg)
		for definition in defs:
			definition = str(definition)
			if definition in attributes_definitions:
				formal_def = attributes_definitions[definition]
				arg = arg.replace(definition, formal_def)
			else :
				raise AttributeError("Unknown Attribute definition : " + definition)

		return eval(arg)

	##
	### CONSTRUCTION FUNCTIONS
	##

	def add_node(self, node: Node) -> bool:
		"""
		Add a Node to V
		"""
		if node.id in self.V :
			return False
		else :
			self.V[node.id] = node
			self.R[node.id] = []
			return True

	def add_nodes(self, nodes: list) -> bool:
		"""
		Add several nodes to V
		"""
		if all(isinstance(node, Node) for node in nodes):
			for node in nodes:
				if not self.add_node(node):
					return False
			return True
		else :
			return False

	def remove_node(self, id_node: str) -> bool:
		"""
		Remove a Node from V, given its id
		"""

		# TODO : speedup by caching edges from router instead of iterating on E
		for id_edge in list(self.E):
			if ((self.E[id_edge].id_a == id_node) or (self.E[id_edge].id_b == id_node)) :
				#self.E.pop(id_edge, None)
				self.remove_edge(id_edge)
		self.R.pop(id_node, None)
		return True if self.V.pop(id_node, None) else False

	def add_edge(self, edge: Edge) -> bool:
		"""
		Add an Edge to E
		"""
		id_edge = edge.id
		if id_edge in self.E :
			print("Edge_id " + id_edge + " already exists in this graph")
			return False
		else :
			if edge.id_a in self.V and edge.id_b in self.V :
				self.E[id_edge] = edge
				ends = [ { "from" : edge.id_a, "to" : edge.id_b} ]
				if edge.directed == False :
					ends.append({ "from" : edge.id_b, "to" : edge.id_a})
				for end in ends :
					if end["from"] in self.R :
						self.R[end["from"]].append({"edge" : edge, "to" : end["to"] })
					else :
						self.R[end["from"]] = [ {"edge" : edge, "to" : end["to"] } ]
				return True
			else :
				print("an id is unknown")
				return False

	def add_edges(self, edges: list) -> bool:
		"""
		Add several Edges to E
		"""
		if all(isinstance(edge, Edge) for edge in edges):
			for edge in edges:
				if not self.add_edge(edge):
					return False
			return True
		else :
			return False

	def remove_edge(self, id_edge: str) -> bool:
		"""
		Remove an Edge from E, given its id
		"""
		nodes = [ self.E[id_edge].id_a, self.E[id_edge].id_b ]
		for id_node in nodes :
			self.R[id_node] = [ route for route in self.R[id_node]
				if route["edge"].id != id_edge
			]
		return True if self.E.pop(id_edge, None) else False

	def switch_edge(self, id_edge: str, id_node_old: str, id_node_new: str) -> bool:
		"""

		"""
		trace("switching edge between %s => %s" % (id_node_old, id_node_new))
		edge = self.E[id_edge].__copy__()
		if edge.id_a == id_node_old :
			edge.id_a = id_node_new
		elif edge.id_b == id_node_old:
			edge.id_b = id_node_new
		else :
			return False
		self.remove_edge(id_edge)
		self.add_edge(edge)
		return True

	def include_graph(self, graph, suffix: str = None):
		"""
		include_graph
		==============

		Include a graph to `self`
			- add every node in R, and resolve id conflicts
			- add every edge in E, and resolve id conflicts

		parameters 
			suffix: str = None - base suffix to use to resolve id conflicts
		"""
		new_to_old = {}
		old_to_new = {}

		for id_node in graph.V :

			# find a new node id
			new_id = id_node + "@" + suffix
			while new_id in self.V :
				random_id = new_id + str(random.random())
				new_id = id_node + "@" + suffix + "-" + str(hashlib.md5(random_id.encode('utf-8')).hexdigest())

			# remember id translation 
			new_to_old[new_id] = id_node
			old_to_new[id_node] = new_id
			
			# insert a node copy
			node = graph.V[id_node].__copy__()
			node.id = new_id
			self.add_node(node)

		for id_edge in graph.E :

			# find a new edge id
			new_id = id_edge + "@" + suffix
			while new_id in self.E :
				random_id = new_id + str(random.random())
				new_id = id_edge + "@" + suffix + "-" + str(hashlib.md5(random_id.encode('utf-8')).hexdigest())
			
			# translate node ids
			edge = graph.E[id_edge].__copy__()
			edge.id = new_id
			edge.id_a = old_to_new[edge.id_a]
			edge.id_b = old_to_new[edge.id_b]

			self.add_edge(edge)

		return old_to_new

	def enumerate_simple_paths(self, id_src: str, id_dst: str):
		"""
		Enumerate all minimal length paths between two nodes on a graph

		TODO : not efficient
		"""
		floors = self.__copy__().group_by_floor(id_src)

		# reverse the floors struct
		id_floors = {}
		for floor in floors.keys():
			for id_node in floors[floor]:
				id_floors[id_node] = floor

		# prune the floors so we dont go beyond the dst floor
		floor_max = id_floors[id_dst]
		floors_to_use = {}
		for floor in range(0, floor_max):
			floors_to_use[floor] = floors[floor]

		def build_path(id_current: str, to_ignore: List) -> List[str]:

			trace('id_current : ' + id_current)
			if id_floors[id_current] == floor_max :
				trace(str(id_current) + ' done ! returning ' + str([[ str(id_current) ]]))
				return [[ str(id_current) ]]
			else :
				neighbors = [ entry['to'] for entry in self.R[id_current] ]
				neighbors = set(neighbors) - set(to_ignore)
				# we consider only neighbors of upper floors to avoid loops
				neighbors = [ n for n in neighbors if id_floors[n] == id_floors[id_current] + 1 ]

				trace('neighbors to fetch : ' + str(neighbors))
				if not neighbors:
					return [[ str(id_current) ]]
				else :
					srcs = [ build_path(id_neighbor, to_ignore + [id_current]) for id_neighbor in neighbors ]
					trace('received ' + str(srcs))
					paths_c = []
					for paths in srcs :
							for path in paths :
								path.append(id_current)
								paths_c.append(path)
					trace(str(id_current) + ' done ! returning ' + str(paths_c))
					return paths_c

		return [ path for path in build_path(id_src, [id_src]) if id_src in path and id_dst in path ]
	
	##
	### SHORTCUTS
	##

	def ordered_nodes_ids(self) :
		return sorted([ node.id for node in self.V.values() ])

	def adjacency_matrix(self, canonic = False, fast = False) -> List :
		"""
		If not canonic, use node id as order relation to write A
		"""
		N = len(self.V)
		A = [ [0]* N for i in range(N)]
		#A = np.zeros((len(self.V), len(self.V)), dtype=int)
		if canonic :
			from .. import canonize
			import itertools

			for id_node in self.V :
				self.V[id_node].meta["id_origin"] = self.V[id_node].id
				#print(self.V[id_node].meta["id_origin"])
			
			def flatten(l): 
				return flatten(l[0]) + (flatten(l[1:]) if len(l) > 1 else []) if type(l) is list else [l]

			def filt(i) :
				if '@' in i :
					l = i[:i.index('@')]
					return l if (not '#' in l and not '*' in l) else None
				elif not '#' in i and not '*' in i :
					return i
				else :
					return None
			
			tree = canonize.to_canonic_tree(self)

			scored_nodes = tree.map_node()
			#print(scored_nodes)
			id_to_score = scored_nodes
			score_to_id = {}

			for k in scored_nodes :
				if scored_nodes[k] in score_to_id :
					score_to_id[scored_nodes[k]].append(k)
				else : 
					score_to_id[scored_nodes[k]] = [k]
			
			#print(score_to_id)

			permut = []

			for k in score_to_id :
				if len(score_to_id[k]) > 1 : 
					#permut = permut + list(itertools.combinations(score_to_id[k], 2))
					#print("Damned ! Look at %s ! %s" % (k, score_to_id[k]))
					for pseudo_root in score_to_id[k] :
						#print("computing tree rooted on %s" % (pseudo_root))
						tree_r = self.to_dag(pseudo_root).to_tree(pseudo_root)
						tree_r.score_tree()
						#print(str(tree_r.hashtree()))
						id_to_score[pseudo_root] = str(tree_r.hashtree())

			score_to_id = {}
			for k in scored_nodes :
				if scored_nodes[k] in score_to_id :
					score_to_id[scored_nodes[k]].append(k)
				else : 
					score_to_id[scored_nodes[k]] = [k]
			
			#print(score_to_id)
			#print("Scores updated")

			permut = []
			for k in score_to_id :
				if len(score_to_id[k]) > 1 : 
					#permut = permut + list(itertools.combinations(score_to_id[k], 2))
					#print("We will need to study permutations on %s" % (score_to_id[k]))
					#permut.append(score_to_id[k])
					permut.append(list(itertools.combinations(score_to_id[k], 2)))
					 

			#print("PERMUT")
			permut = flatten(permut)
			#print(permut)

			id_to_score_tup = [ (k, v) for i, (k, v) in enumerate(id_to_score.items())]
			V_index = [ node_id for (node_id, minhash) in sorted(id_to_score_tup, key = lambda tup : tup[1]) ]
			#print(V_index)

			if permut and not fast :

				allpermut = []

				for i in range(0, len(permut)+1) :
					allpermut = allpermut + list(itertools.combinations(permut, i))
				
				def valid_permut(permutset):
					permutset = list(permutset)
					vertices = []
					for (u, v) in permutset :
						vertices = vertices + [u, v]
					return len(vertices) == len(set(vertices))
				
				permutations = [ list(i) for i in allpermut ]#if valid_permut(i)]

				scored_matrices = []
				def hashex(string): 
					return hashlib.sha224(string.encode()).hexdigest()

				for permut_set in permutations :
					#print(permut_set)
					V_index_i = [i for i in V_index]
					#print("----------------------")
					for (u, v) in permut_set :
						#print("swapping %s and %s" % (u, v))
						i = V_index_i.index(u)
						j = V_index_i.index(v)
						V_index_i[i] = v
						V_index_i[j] = u
						#print(V_index)
					#print("%s -> %s" % (V_index, V_index_i))
					Ai = [ [0]* N for i in range(N)]
					for id_edge in self.E :
						edge = self.E[id_edge]
						i = V_index_i.index(edge.id_a)
						j = V_index_i.index(edge.id_b)
						Ai[i][j] = str_to_int(edge.modality)
						Ai[j][i] = str_to_int(edge.modality)
					#print(str(permut_set))
					#if V_index_i == ['6', '17', '4', '16', '12', '3', '20', '5', '7', '8', '11', '13', '2', '19', '9', '15', '1', '18', '10', '14'] or V_index_i == ['13', '19', '1', '17', '16', '3', '4', '12', '2', '6', '11', '5', '8', '20', '9', '18', '7', '10', '14', '15'] :
					#	print("\n\n\n%s\n\n\n" % (str(Ai)))
					scored_matrices.append((hashex(str(Ai)), V_index_i, str(permut_set)))

				scored_matrices = sorted(scored_matrices)
				#print(scored_matrices)
				A_winner, V_index, permut_set = min(scored_matrices, key = lambda AV : str(A[0]))

			
			#seq_id = tree.get_order_sequence()
			#print("flatten :")
			#print(sorted(flatten(seq_id)))
			#flatten_seq_id = filter(bool, [ i for i in flatten(seq_id) ])
			#V_index = [ ]
			#for i in flatten_seq_id :
			#	i = filt(i)
			#	if i and i not in V_index :
			#		V_index.append(i)
			#print("V_index")
			#print(V_index)

		else :
			V_index = self.ordered_nodes_ids()

		for id_edge in self.E :
			edge = self.E[id_edge]
			i = V_index.index(self.V[edge.id_a].id)
			j = V_index.index(self.V[edge.id_b].id)
			A[i][j] = str_to_int(edge.modality)
			A[j][i] = str_to_int(edge.modality)
		return A

	def n_degree(self, id_node: str, order: int = 0) -> int:
		degree = len(self.R[id_node])
		ids_n_base = [id_node]
		for extra_stage in range(1, order+1):
			ids_n_neighbors = [ 
				route['to'] for route in [ 
					routes for routes in 
					sum([ self.R[id_base] for id_base in ids_n_base ], [])
				]
			]
			ids_n_base = ids_n_neighbors
			degree += sum([ len(self.R[id_neighbor]) for id_neighbor in ids_n_neighbors])
		return degree 
	
	def degree(self, id_node: str) -> int:
		"""
			get a Node's degree
		"""
		return len(self.R[id_node])

	def is_leaf(self, id_node: str) -> bool:
		"""
			is_leaf
		"""
		return self.degree(id_node) == 1

	def is_floored(self) -> bool:
		"""
			is_floored
			-----------
		"""
		return not False in [ 'floor' in self.graph.V[id_node].meta for id_node in self.graph.V.keys() ]

	def split_connex_compounds(self) -> List :

		number_connex_compound = self.mark_connex_compounds()

		if number_connex_compound == 1 : 
			return [self]
		else :
			sub_graphs = []
			for connex_compound_index in range(1, number_connex_compound+1) :
				#print(connex_compound_index)
				sub_graph = self.__copy__()
				outside_nodes = [ id_node for id_node in sub_graph.V if sub_graph.V[id_node].meta['connex_compounds'] != str(connex_compound_index) ]
				for id_node in outside_nodes :
					if sub_graph.V[id_node].meta['connex_compounds'] != str(connex_compound_index):
						sub_graph.remove_node(id_node)
				sub_graphs.append(sub_graph)
			return sub_graphs

	##
	### NODE FUNCTIONS
	##

	def score_nodes(self, rule: str = "$degree", meta_attr: str = "score") -> bool:
		"""
			score_nodes

			Annotates the Graph's Nodes with a `meta.candidate_score` attribute.
			This score is under the form of a tuple, whose dimension and value
			are defined by a `rule`.

			Rule Grammar is a python expression with following bindings :
				- graph
				- node
				- id_node
		"""

		trace("## Substep 1 : Define a node function", 2)

		score = def_node_fn(rule)
		trace("`" + rule + "`" + " => " + str(score),3)

		trace("## Substep 2 : Score nodes", 2)

		for id_node in self.V :
			score_res = score(id_node, self)
			self.V[id_node].meta[meta_attr] = score_res
			trace("Node #" +id_node + " :\t" + str(score_res), 3)

		return True

	def mark_connex_compounds(self, meta_attr: str = "connex_compounds"):

		# reset 
		for id_node in self.V :
			if meta_attr in self.V[id_node].meta :
				 self.V[id_node].meta[meta_attr] = None
		
		connex_compound_index = 0

		def mark_connex_compounds_cb(node_from : Node, node_to : Node, msg: str) :
			#print(node_to.meta)
			if not meta_attr in node_to.meta :
				node_to.meta[meta_attr] = msg
				#print(node_to)
				self.broadcast(id_node_from = node_to.id, id_origin = node_from.id, msg = msg, callback = mark_connex_compounds_cb)
				
		while not all( [ meta_attr in self.V[id_node].meta for id_node in self.V ]):
			connex_compound_index += 1
			#print("Compound #%s" % (connex_compound_index))
			not_connected = [ id_node for id_node in self.V if not meta_attr in self.V[id_node].meta ]
			#print("not connected : %s" % (not_connected))
			#print("node %s := cc #%s" % (not_connected[0], connex_compound_index))
			self.V[not_connected[0]].meta[meta_attr] = str(connex_compound_index)
			#print(self.V[not_connected[0]])
			#print("discovering from %s" % (not_connected[0]))
			self.broadcast(not_connected[0], None, str(connex_compound_index), mark_connex_compounds_cb)

		return connex_compound_index

	##
	### MESSAGING FUNCTIONS
	##

	def msg(self, id_node_from: str, id_node_to: str, msg: str, callback: Node_Callback) -> bool:
		"""
			msg

			Perform a message sending between two nodes
		"""
		if id_node_to in self.R[id_node_from] :
			return callback(self.V[id_node_to], self.V[id_node_from], msg)
		else :
			raise AssertionError("There is no link from " + id_node_from + " to " + id_node_to)

	def broadcast(self, id_node_from: str, id_origin: str, msg: str, callback: Node_Callback) -> (bool, List[bool]):
		"""
			broadcast
		"""
		acks = []
		for edge in self.R[id_node_from] :
			id_node_to = edge["to"]
			if id_node_to != id_origin:
				acks.append(callback(self.V[id_node_from], self.V[id_node_to], msg))
		return (not False in acks, acks)

	##
	### NEUWICK-FORM FUNCTIONS
	##

	def evaluate_bounds(self, id_node) :
		"""
			Ev aluate the number of in/co bounds to treat if id_node is a root
			Could be a very good invaraint to use
		"""
		graph = self.__copy__()
		graph.reset_floor()
		floors = graph.group_by_floor(id_node)
		graph.meta["floors"] = floors
		return (len(graph.find_inbounds()), len(graph.find_cobounds()))

	def cobounds_by_floor(self) :
		trace("Substep 2.1 : Co--bound detection", 2)
		cobounds = self.find_cobounds()
		trace(str(len(cobounds)) + " cobounds found : ", 3)

		trace("Substep 2.2 : Co--bound flooring", 2)
		cobounds_by_floor = {}
		cobound_floors = []
		for id_edge in cobounds : 
			floor = self.V[self.E[id_edge].id_a].meta['floor']
			if floor in cobounds_by_floor : 
				cobounds_by_floor[floor].append(id_edge)
			else: 
				cobounds_by_floor[floor] = [ id_edge ]
				cobound_floors.append(floor)
		cobound_floors = sorted(cobound_floors)
		cobound_floors.reverse()
		trace("cobounds_by_floor : %s" % (str(cobounds_by_floor)), 3)

		return (cobounds_by_floor, cobound_floors)

	def inbounds_by_floor(self):
		trace("Substep 3 : In--bound detection", 2)

		inbounds = self.find_inbounds()
		inbounds.sort(reverse=True)
		trace(str(len(inbounds)) + " inbounds found : ", 3)

		#if compact_form :
		#	trace("Substep 3.0 : In--bound scoring", 2)
		#	print("\n------------------     inbound sorting")
		#	scored_inbounds = graph.score_inbounds(inbounds)
		#	scored_inbounds.sort(reverse=True)
			#print(scored_inbounds)
		#	inbounds = [ inbound for (score, inbound) in scored_inbounds ]
		#	print("\n")
		#	#print(inbounds)

		trace("Substep 3.1 : In--bound flooring", 2)
		inbounds_by_floor = {}
		inbound_floors = []
		for (floor, id_node, upstairs) in inbounds : 
			if floor in inbounds_by_floor : 
				inbounds_by_floor[floor].append((floor, id_node, upstairs))
			else :
				inbounds_by_floor[floor] = [ (floor, id_node, upstairs) ]
				inbound_floors.append(floor)
		inbound_floors = sorted(inbound_floors)
		inbound_floors.reverse()

		trace("inbounds_by_floor : %s" % (str(inbounds_by_floor)), 3)

		return (inbounds_by_floor, inbound_floors)

	def to_dag(self, id_root: str, branch_rule: str = "$root.label > $depth > $lexic", ids_ignore: List = [], compact_form = False, allow_hashes = True) -> "Graph":
		"""
			to_dag
			-------

			Transforms an unconstrained graph into a directional acyclic graph.
				- regroup nodes following their distance from the root_node
				- replaces co--bound with virtual nodes
				- replaces in--bound with mirror nodes

			Return a new graph (does not mutate original graph)
		"""
		trace("Converting to a Directed Acyclic Graph (DAG)")
		graph = self.__copy__()

		trace("Removing ignored nodes", 3)
		for id_node in ids_ignore :
			graph.remove_node(id_node)

		trace("Substep 1 : group nodes following their distance from root", 2)
		graph.reset_floor()
		floors = graph.group_by_floor(id_root)
		graph.meta["floors"] = floors

		trace("Nodes ordered by floors", 3)
		trace(json.dumps(floors, indent=4, sort_keys=True), 4)

		trace("Remove isolated components", 3)
		for id_node in list(graph.V):
			if not 'floor' in graph.V[id_node].meta or graph.V[id_node].meta['floor'] is None :
				trace("removing " + id_node, 4)
				graph.remove_node(id_node)

		trace("Substep 2 : Extra-edges detection", 2)

		cobounds_nb = len(graph.find_cobounds())
		inbounds_nb = len(graph.find_inbounds())
		edit_nb =  cobounds_nb + inbounds_nb
		#print("%s edits to compute (%s cobounds, %s inbounds)" % (str(edit_nb), str(cobounds_nb), str(inbounds_nb)))

		trace("Substep 3 : Rewritings ", 2)

		id_virtual = 0
		id_mirror = 1
		lvl_done = 1
		ordering_fn = def_tree_fn(branch_rule)
		mode = "elect" if compact_form else "duplicate"

		for i in range(0, edit_nb) :

			#print("editing bound %s/%s" % (str(i+1), str(edit_nb)))

			cobounds_nb_i = len(graph.find_cobounds())
			inbounds_nb_i = len(graph.find_inbounds())
			#print("now (%s cobounds, %s inbounds)" % (str(cobounds_nb_i), str(inbounds_nb_i)))

			(cobounds_by_floor, cobound_floors) = graph.cobounds_by_floor()
			(inbounds_by_floor, inbound_floors) = graph.inbounds_by_floor()

			#print("cobounds : %s" % (str(cobounds_by_floor)))
			#print("inbounds : %s" % (str(inbounds_by_floor)))
			assert cobounds_nb_i <= cobounds_nb and inbounds_nb_i <= inbounds_nb

			floors = sorted(list(set(inbound_floors).union(cobound_floors)))
			floors.reverse()
			trace("floors needing rewritings : %s" % (str(floors)), 3)

			floor = floors[0]

			if floor in cobounds_by_floor :
				# cobounds left, we resolve a cobound
				scored_cobounds = sorted(graph.score_cobounds(cobounds_by_floor[floor]), reverse = True)
				(score, cobound) = scored_cobounds[0]
				#print("fixing cobound %s" % (str(cobound)))
				graph.fix_cobound(cobound, "*%s" % (id_virtual), "*%s" % (id_virtual+1))
				id_virtual += 2

			else :
				# no cobounds left to this floor, we resolve an inbound
				scored_inbounds = sorted(graph.score_inbounds(inbounds_by_floor[floor]), reverse = True)
				(score, inbound) = scored_inbounds[0]
				#print("fixing inbound %s" % (str(inbound)))
				assert inbound[1] in graph.V
				graph.fix_inbound(inbound, "#%s" % (str(id_mirror)), scoring = ordering_fn, mode = mode)
				id_mirror += 1

		assert len(graph.find_cobounds()) == 0
		assert len(graph.find_inbounds()) == 0


		# try :
		# 	# multi thread
		# 	raise ImportError()
		# 	from joblib import Parallel, delayed
		# 	import os

		# 	def compute_ordering(bound, mode) : 
		# 		if mode == "cobound" :
		# 			return graph.score_cobounds([bound])
		# 		else :
		# 			return graph.score_inbounds([bound])

		# 	for floor in floors :
		# 		#print("Floor %s : %s nodes - %s" % (str(floor), str(len([id_node for id_node in self.V ])), str(sorted([id_node for id_node in self.V ]))))
		# 		trace("Rewriting floor %s %s/%s" % (str(floor), str(lvl_done), str(len(floors))), 3)
		# 		if floor in cobounds_by_floor :
		# 			trace("Substep 4.%s.1 : Co--bound ordering of floor %s " % (str(lvl_done), str(lvl_done)), 3)
		# 			scored_cobounds = Parallel(
		# 				n_jobs = os.cpu_count())(delayed(compute_ordering)(bound, "cobound") for bound in cobounds_by_floor[floor])
		# 			scored_cobounds = sorted([x for xs in scored_cobounds for x in xs], reverse = True)
		# 			trace("Scored cobounds : " + str(scored_cobounds), 3)
					
		# 			trace("Substep 4.%s.2 : Co--bound correction of floor %s" % (str(lvl_done), str(floor)), 2)
					
		# 			for (score, cobound) in scored_cobounds :
		# 				graph.fix_cobound(cobound, "*%s" % (id_virtual), "*%s" % (id_virtual+1))
		# 				id_virtual += 2
		# 		else :
		# 			trace("No co-bounds to rewrite on floor %s " % (str(floor)), 3)

		# 		if floor in inbounds_by_floor :
		# 			trace("Substep 4.%s.3 : In--bound ordering of floor %s " % (str(lvl_done), str(lvl_done)), 3)
		# 			scored_inbounds = Parallel(
		# 				n_jobs = os.cpu_count())(delayed(compute_ordering)(bound, "inbound") for bound in inbounds_by_floor[floor])
		# 			scored_inbounds = sorted([x for xs in scored_inbounds for x in xs], reverse = True)
					
		# 			trace("Scored inbounds : " + str(scored_inbounds), 3)
					
		# 			trace("Substep 4.%s.4 : In--bound correction of floor %s" % (str(lvl_done), str(floor)), 2)
					
		# 			for (score, inbound) in scored_inbounds :
		# 				graph.fix_inbound(inbound, "#%s" % (str(id_mirror)), scoring = ordering_fn, mode = mode)
		# 				id_mirror += 1

		# 		else :
		# 			trace("No in-bounds to rewrite on floor %s " % (str(floor)), 3)

		# 		lvl_done += 1

		# except ImportError :
		# 	# mono thread
		# 	print(str(floors))
		# 	for floor in floors :
		# 		print("Floor %s " % (str(floor)))
		# 		print("Before : %s nodes - %s" % (str(len([id_node for id_node in graph.V ])), str(sorted([id_node for id_node in graph.V ]))))
		# 		trace("Rewriting floor %s %s/%s" % (str(floor), str(lvl_done), str(len(floors))), 3)
		# 		if floor in cobounds_by_floor :
		# 			trace("Substep 4.%s.1 : Co--bound ordering of floor %s " % (str(lvl_done), str(lvl_done)), 3)
		# 			scored_cobounds = sorted(graph.score_cobounds(cobounds_by_floor[floor]), reverse = True)
		# 			trace("Scored cobounds : " + str(scored_cobounds), 3)
					
		# 			trace("Substep 4.%s.2 : Co--bound correction of floor %s" % (str(lvl_done), str(floor)), 2)
					
		# 			for (score, cobound) in scored_cobounds :
		# 				graph.fix_cobound(cobound, "*%s" % (id_virtual), "*%s" % (id_virtual+1))
		# 				id_virtual += 2
		# 		else :
		# 			trace("No co-bounds to rewrite on floor %s " % (str(floor)), 3)

		# 		if floor in inbounds_by_floor :
		# 			trace("Substep 4.%s.3 : In--bound ordering of floor %s " % (str(lvl_done), str(lvl_done)), 3)
		# 			scored_inbounds = sorted(graph.score_inbounds(inbounds_by_floor[floor]), reverse = True)
		# 			trace("Scored inbounds : " + str(scored_inbounds), 3)
					
		# 			trace("Substep 4.%s.4 : In--bound correction of floor %s" % (str(lvl_done), str(floor)), 2)
					
		# 			for (score, inbound) in scored_inbounds :
		# 				graph.fix_inbound(inbound, "#%s" % (str(id_mirror)), scoring = ordering_fn, mode = mode)
		# 				id_mirror += 1

		# 		else :
		# 			trace("No in-bounds to rewrite on floor %s " % (str(floor)), 3)
		# 		print("After : %s nodes - %s" % (str(len([id_node for id_node in graph.V ])), str(sorted([id_node for id_node in graph.V ]))))

		# 		lvl_done += 1
		
		trace("Substep 5 : Cleanup", 2)
		graph.reset_floor()

		floors = graph.group_by_floor(id_root)
		graph.meta["floors"] = floors
		for id_node in list(graph.V):
			if not 'floor' in graph.V[id_node].meta or graph.V[id_node].meta['floor'] is None :
				trace("removing " + id_node, 4)
				graph.remove_node(id_node)
		#print("returning a graph of %s nodes " % (str(len(graph.V))))

		return graph

	def reset_floor(self) -> bool :
		for id_node in self.V :
			self.V[id_node].meta["floor"] = None
			trace("resetting floor for %s" % (id_node))
		self.meta["floored_by"] = None
		return True

	def group_by_floor(self, id_root: int):
		"""
		TODO : add a limit parameter, to avoid sending too much messages when not useful
		"""
		floors = {}

		def floorgroup_propagation(node_from: Node, node_to: Node, msg: str) -> bool:
			trace("Node #" + node_to.id + " received '" + str(msg) + "' from #" + node_from.id, 3)
			floor = int(msg)
			if not "floor" in node_to.meta or node_to.meta["floor"] is None :
				trace(node_to.id + " : I join floor " + str(floor), 4)
				node_to.meta["floor"] = floor
				if floor in floors:
					floors[floor].append(node_to.id)
				else :
					floors[floor] = [node_to.id]
				return self.broadcast(id_node_from = node_to.id, id_origin = node_from.id, msg = floor + 1, callback = floorgroup_propagation)

			elif floor < node_to.meta["floor"]:
				trace(node_to.id + " : I go down to this floor", 4)
				floors[node_to.meta["floor"]].remove(node_to.id)
				node_to.meta["floor"] = floor
				if floor in floors :
					floors[floor].append(node_to.id)
				else :
					floors[floor] = [node_to.id]
				return self.broadcast(id_node_from = node_to.id, id_origin = node_from.id, msg = floor + 1, callback = floorgroup_propagation)

			else :
				trace(node_to.id + " : I'm already at a lower floor, so I stop the propagation", 4)
				return False

		floors[0] = [id_root]
		self.V[id_root].meta["floor"] = 0
		self.broadcast(id_node_from = id_root, id_origin = None, msg = "1", callback = floorgroup_propagation)

		# filter empty floors
		floors = { str(k) : v for k, v in floors.items() if v }
		self.meta["floored_by"] = id_root
		return floors

	def find_cobounds(self):
		"""
			cobound == id_edge
		"""
		cobounds = [ id_edge for id_edge in self.E.keys()
			if self.V[self.E[id_edge].id_a].meta.get('floor') == self.V[self.E[id_edge].id_b].meta.get('floor') ]
		trace(str(len(cobounds)) + " cobounds found", 4)
		return cobounds

	def score_cobounds(self, cobounds, allow_hashes : bool = True) -> List:
		"""
		score a list of cobounds (typically of the same floor)
		the underlying floors must have been treated
		returns a list of (score, cobound)
		"""	
		ret = []
		done = 1
		for id_edge in cobounds :
			trace("scoring cobound : %s [%s-%s] - (%s/%s)" % (id_edge, self.E[id_edge].id_a, self.E[id_edge].id_b, str(done), str(len(cobounds))), 3)
			sep = "-%s-" % (self.E[id_edge].modality)
			magnet = sep.join(sorted([
				self.get_magnet(self.E[id_edge].id_a, allow_hashes = allow_hashes), 
				self.get_magnet(self.E[id_edge].id_b, allow_hashes = allow_hashes)
				]))
			done += 1
			#magnet = "_" + sep.join(sorted([ hashlib.md5(self.get_magnet(self.E[id_edge].id_a).encode('utf-8')).hexdigest(), hashlib.md5(self.get_magnet(self.E[id_edge].id_b).encode('utf-8')).hexdigest()])) + "_"

			ret.append((magnet, id_edge))
			self.E[id_edge].meta["magnet"] = magnet
		return sorted(ret)

	def fix_cobound(self, cobound_edge_id: str, id_virtual_a: str, id_virtual_b: str) -> bool:
		"""
			fix_cobound
			------------
							  ( * )
							 /
		--( A )--		--( A )--
		    |		=>
		--( B )--		--( B )--
							 \
							  ( * )

		"""
		edge = self.E[cobound_edge_id]
		trace("Fixing cobound centered on " + str(edge.id_a) + " , " + str(edge.id_b), 3)
		#print(edge)
		#print(self.V[edge.id_a])
		#print(self.V[edge.id_b])
		floor_virtual = int(self.V[edge.id_a].meta.get('floor')) + 1
		fingerprint = edge.meta['magnet']
		trace("fingerprint : ", 3)
		trace(fingerprint, 3)
		# remove the edge
		self.remove_edge(cobound_edge_id)


		# compute the magnet signature
		#magnet_a = self.get_magnet(id_node = edge.id_a, ignore_virtuals = True)
		#magnet_b = self.get_magnet(id_node = edge.id_b, ignore_virtuals = True)
		#magnets = [ magnet_a, magnet_b ]
		#magnets.sort()
		#fingerprint = "[" + magnets[0] + "-" + edge.modality + "-" + magnets[1] + "]"
		

		#if edge.id_a == '6' or edge.id_b == '6' :
		#	print("SIGNATURE : ")
			#print(magnets)
		#	print(hashlib.md5(str.encode(fingerprint)).hexdigest())
		#fingerprint = fingerprint[-5:]
		#print(fingerprint)

		# create 2 virtual nodes
		virtual_node_a = Virtual_Node(id_virtual_a, magnet = fingerprint)
		virtual_node_a.meta["floor"] = floor_virtual
		virtual_node_b = Virtual_Node(id_virtual_b, magnet = fingerprint)
		virtual_node_b.meta["floor"] = floor_virtual

		#print(self.meta.get("floors"))
		if not floor_virtual in self.meta.get("floors"):
			self.meta.get("floors")[floor_virtual] = []

		self.meta.get("floors")[floor_virtual].append(id_virtual_a)
		self.meta.get("floors")[floor_virtual].append(id_virtual_b)

		edge_a_va = edge.__copy__()
		edge_a_va.id_b = id_virtual_a
		edge_a_va.id = "*%s_a" % (edge.id)
		edge_b_vb = edge.__copy__()
		edge_b_vb.id_a = id_virtual_b
		edge_b_vb.id = "*%s_b" % (edge.id)

		# updates the graph
		self.add_nodes([virtual_node_a, virtual_node_b])
		self.add_edges([ edge_a_va, edge_b_vb ])

		return True

	def find_inbounds(self) -> List :
		"""
			inbound == (floor, id_node, upstairs)
		"""
		inbounds = []
		for id_node in self.V.keys() :
			#trace('Finding inbounds in node #' + str(id_node) + " (level " + str(graph.V[id_node].meta.get('floor')) + ")", 3)
			routes = [ route for route in self.R[id_node] ]
			#upstairs = [ (self.V[route["to"]].meta.get('floor'), route["edge"])
			upstairs = [ route["edge"].id
				for route in routes
				if int(self.V[route["to"]].meta.get('floor')) < int(self.V[id_node].meta.get('floor')) ] #ascending only (avoid duplicate)
			if(len(upstairs) > 1 ):
				inbounds.append((int(self.V[id_node].meta.get('floor')), id_node, upstairs))
		trace(str(len(inbounds)) + " inbounds found", 4)
		return inbounds

	def score_inbounds(self, inbounds) -> List:
		"""
			score_inbounds
			---------------
		"""
		scored = []
		for inbound in inbounds :
			trace("scoring inbound %s" % (str(inbound)), 4)
			#print("scoring inbound %s" % (str(inbound)))
			(floor, id_node, id_edges) = inbound
			arity = len(id_edges)
			floor_roots = floor - 1
			main_magnet = self.get_magnet(id_node)

			roots_ids = [ self.E[id_edge].id_a if self.E[id_edge].id_a != id_node else self.E[id_edge].id_b 
				for id_edge in id_edges ]
			trace("roots : %s" % (str(roots_ids)), 4)
			#print("roots : %s" % (str(roots_ids)))
			root_magnets = [ hashlib.md5(self.get_magnet(id_root).encode('utf-8')).hexdigest() for id_root in roots_ids ] 
			#root_magnets = [ self.get_magnet(id_root) for id_root in roots_ids ]
			trace("roots_magnets : %s" % (str(root_magnets)), 4)
			#print("roots_magnets : %s" % (str(root_magnets)))
			score = (arity, main_magnet, ' '.join(sorted(root_magnets) ))
			scored.append( (score, inbound) )
		return scored

	def fix_inbound(self, inbound, id_mirror: str, scoring: "TreeScoring" = "$lexic", mode: str = "duplicate") -> bool:
		"""
			fix_inbound
			------------
		--	...					-- ... --( #C' )--
				\
		--( A )--( C )--	=>	--( A )--( #C' )--
				/
		--( B )/				--( B )--( #C' )--
		"""
		trace(str(inbound), 3)
		floor, id_node, id_edges = inbound
		trace("Fixing inbound centered on %s, floor %s" % (str(id_node), self.V[id_node].meta['floor']), 3)
		arity = len(id_edges)
		node = self.V[id_node]
		#floor_base = floor
		#floor_mirror = floor_base + 1
		floor_mirror = floor
		floor_sub = floor_mirror + 1
		floor_roots = floor_mirror - 1

		outgoing_edges = [ route["edge"]
			for route in [ route for route in self.R[id_node] ]
			if int(self.V[route["to"]].meta.get('floor')) > int(self.V[id_node].meta.get('floor')) ]
		
		roots_nodes = [ node_id 
			for node_id in list(self.V) 
			if self.V[node_id].meta.get('floor') <= floor_roots ]

		magnet = self.get_magnet(id_node)

		if mode == "duplicate" :
			# make a clone of the subtree
			subtree = self.__copy__().to_tree(id_node, ids_ignore = roots_nodes)
			ids_children = [ child.id for (child, level) in subtree.enumerate_nodes() ]
			trace("id_node : %s" % (str(id_node)), 3)
			trace("Descendants nodes : %s" % (str(ids_children)), 3)
			ids_to_ignore = [ id_node for id_node in self.V if not id_node in ids_children ]
			trace("To ignore nodes : %s" % (str(ids_to_ignore)), 3)
			#ids_to_ignore.remove(id_node)
			subdag = self.__copy__().to_dag(id_root = id_node, ids_ignore = ids_to_ignore)
			#trace("sub-dag : %s" % (str(subdag)))

			for id_descendant in ids_children :
				trace("lowering floor of %s to %s" % (id_descendant, str(subdag.V[id_descendant].meta["floor"] + floor_sub)), 4)
				subdag.V[id_descendant].meta["floor"] = subdag.V[id_descendant].meta["floor"] + floor_sub

			for (i, id_edge) in enumerate(id_edges):

				# create a mirror node 
				edge = self.E[id_edge].__copy__()
				root = self.V[edge.other_end(id_node)]

				id_n_mirror = id_mirror + "_" + str(i)
				mirror = Mirror_Node(id_n_mirror, arity = arity, label = ".", magnet = magnet)
				#mirror.meta = copy.deepcopy(node.meta)
				mirror.meta["floor"] = floor_mirror

				self.add_node(mirror)

				# intercept root-node edge with mirror 
				trace("id_node : %s" % (str(id_node)), 4)
				trace("id_root : %s" % (str(root.id)), 4)
				trace("id_n_mirror : %s" % (str(id_n_mirror)), 4)
				self.switch_edge(id_edge, id_node, id_n_mirror)

				# attach the subtree copy to the mirror

				translating = self.include_graph(subdag.__copy__(), id_n_mirror)
				new_edge = Edge(id_edge = "e" + id_n_mirror, a = mirror, b = self.V[translating[subtree.root.id]] )
				self.add_edge(new_edge)
				#self.R[id_n_mirror]
		else :
			roots_candidates = []

			for (i, id_edge) in enumerate(id_edges):

				edge = self.E[id_edge].__copy__()
				root = self.V[edge.other_end(id_node)]

				id_n_mirror = id_mirror + "_" + str(i)
				mirror = Mirror_Node(id_n_mirror, arity = arity, label = node.label, magnet = magnet)
				mirror.data = copy.deepcopy(node.data)
				mirror.meta = copy.deepcopy(node.meta)
				mirror.meta["floor"] = floor_mirror
				mirror.meta["is_mirror"] = True

				if not floor_mirror in self.meta.get("floors"):
					self.meta.get("floors")[floor_mirror] = []

				self.meta.get("floors")[floor_mirror].append(id_n_mirror)

				self.add_node(mirror)
				edge.replace_end(id_node, id_n_mirror)
				edge.id = "#%s" % (id_n_mirror)
				self.remove_edge(id_edge)
				self.add_edge(edge)

				associated_candidate = self.__copy__().to_tree(root.id, ids_ignore = roots_nodes)
				associated_candidate.score_tree(scoring)
				roots_candidates.append( (associated_candidate.meta.get("score"), root.id, id_n_mirror) )

			roots_candidates.sort()
			trace("Roots candidates : " + str(roots_candidates), indent=2)

			for outgoing_edge in outgoing_edges :
				main_root = roots_candidates[0]
				self.switch_edge(outgoing_edge.id, id_node, main_root[2])

			self.remove_node(id_node)

		return True

	def score_dag(self) -> bool:
		"""
			On a floored graph, attributes to each node its "score",
			i.e a tuple (floor, str()), excluding neighbors

			Is is similar to get a magnet to each node
		"""
		# ensure graph is floored 
		if not 'floored_by' in self.meta or self.meta['floored_by'] is None : 
			raise Exception("Cannot compute score_dag in unfloored graph")
		
		for id_node in self.V :
			# place ourselves in a context where the nodes only communicates with its lower floors
			ignore = [ id_remote
				for id_remote in self.V.keys()
				if (self.V[id_remote].meta.get('floor') <= self.V[id_node].meta.get('floor')) ]
			tree = self.to_tree(id_root = id_node, ids_ignore = ignore)
			tree.score_tree()
			self.V[id_node].meta['dag_score'] = (self.V[id_node].meta.get('floor'), str(tree))
		
		return True


	def get_magnet(self, id_node: str, ignore_virtuals: bool = False, allow_hashes: bool = True) -> str:
		"""

		"""
		trace("getting magnet for node #%s, ignore_virtuals = %s, allow_hashes = %s" % (id_node, ignore_virtuals, allow_hashes) ,3)
		# ensure graph is floored 
		if not 'floored_by' in self.meta or self.meta['floored_by'] is None : 
			trace("error : graph is not floored !", 3)
			raise Exception("Cannot compute magnet in unfloored graph")

		elif "magnet" in self.V[id_node].meta and self.meta['floored_by'] in self.V[id_node].meta['magnet'] : 
			trace("magnet already known : %s" % (self.V[id_node].meta['magnet'].get(self.meta['floored_by'])) ,3)
			return self.V[id_node].meta['magnet'].get(self.meta['floored_by'])
		else :
			trace("computing the magnet...", 3)
			# place ourselves in a context where the nodes only communicates with its lower floors
			ignore = [ id_remote
				for id_remote in self.V.keys()
				if (self.V[id_remote].meta.get('floor') <= self.V[id_node].meta.get('floor')) ]
			#print(self.meta["floors"])
			trace("building a tree  rooted on %s ; ignoring %s" % (id_node, str(ignore)), 3)
			tree = self.to_tree(id_root = id_node, ids_ignore = ignore)
			tree.score_tree()

			magnet = "_" + str(tree) + "_"
			trace("magnet computed : %s" % (magnet), 3)
			if allow_hashes : 
				magnet = "_" + str(hashlib.md5(magnet.encode('utf-8')).hexdigest()) + "_"
			
			if "magnet" in self.V[id_node].meta : 
				self.V[id_node].meta["magnet"][str(self.meta['floored_by'])] = magnet
			else :
				self.V[id_node].meta["magnet"] = { str(self.meta['floored_by']) : magnet }
			return magnet

	def to_tree(self, id_root: str, id_origin: str = None, modality_origin: str = None, ids_ignore: List[str] = []) -> Tree:
		"""
			to_tree
			--------

			Translates an acyclic subgraph into an "agnostic" (unordered) neuwick tree form
			A neuwick form is :
				- node centered (root)
				- which itself may have a "parent" (origin == "real-root")
				- this origin is in all cases excluded from the writing
				- this origin is generally the caller node
				- a leaf is a tuple (label?, parent_modality_link)
				- a non-leaf (branch) is a list of others branches/leafs
		"""
		#print("Root #" + id_root)
		#print("Origin :" + str(id_origin))
		#print("Ignore : " +str(ids_ignore))
		trace("building a tree rooted on %s (lvl %s), initiated by %s (lvl %s)" % (id_root, str(self.V[id_root].meta.get('floor')), id_origin, str(self.V[id_origin].meta.get('floor')) if id_origin is not None else "none"), 3)
		if self.is_leaf(id_root) and id_origin is not None:
			# leaf
			return Tree(self.V[id_root], None, modality_origin)
		else :
			ids_ignore.append(id_origin)
			ids_ignore = list(set(ids_ignore))
			children = [ (self.to_tree(id_root = link["to"], id_origin = id_root,  modality_origin = link["edge"].modality, ids_ignore = ids_ignore), link["edge"].modality)
			 			for link in self.R[id_root]
			 			if link["to"] != id_origin and not link["to"] in ids_ignore ]
			#trace("tree rooted on %s, initied by %s ;  #children = %s" % (id_root, id_origin, str(len(children))), 3)
			return Tree(self.V[id_root], children, modality_origin)
