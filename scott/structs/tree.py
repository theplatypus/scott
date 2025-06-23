
from .node import Node

import re
import math
import copy

import json
import pprint

import hashlib

from typing import List, Tuple, Callable

TreeScoring = Callable[['Tree'], Tuple]

verbose = False

def trace(msg, indent=1, f=" "):
	if (verbose == True):
		print("[tree.py]" + f + indent*"\t" + msg)

def def_tree_fn(rule: str = "$depth > $lexic") -> TreeScoring:
	"""
		def_branch_fn

		Define branch function
	"""
	args = [ arg.strip() for arg in rule.split(">") ]
	return lambda tree : tuple([ tree.__eval__(str(arg)) for arg in args ])

def hashex(string): 
	return hashlib.sha224(string.encode()).hexdigest()

attributes_definitions = {
	"$depth" : "tree.depth()",
	"$size" : "len(tree.enumerate_nodes())",
	"$lexic" : "str(tree)",
	#"$lexic" : "hashlib.sha512(str(tree).encode('utf-8')).hexdigest()",
	
	"$root" : "tree.root"
}

class Tree :
	"""
		TREE
		======

		A neuwick form is :
			- node centered (root)
			- which itself may have a "parent" (origin == "real-root")
			- this origin is in all cases excluded from the writing
			- this origin is generally the caller node
			- a leaf is a tuple (label?, parent_modality_link)
			- a non-leaf (branch) is a list of others branches/leafs

		As the order in which we arrange sub-branches, and thus its representation
	"""

	def __init__(self, root: Node, children: List['Tree'], parent_modality: str):
		self.root = root
		self.children = children
		self.parent_modality = parent_modality
		self.meta = {}

	def __str__(self):
		return self.__repr__()

	def __repr__(self):
		if "trace" in self.meta: 
			return self.meta['trace']
		else :
			lbl = self._get_label()
			#print("\n++++++++++++++\nreturning tree centered on %s (%s):" % (str(self.root.id), self.root.meta))
			#if lbl == "R":
				#print("printing the root")
				#print(sorted([ child[0].meta['score'] for child in self.children ]))
			if self.is_leaf() :
				#print("leaf")
				#print(lbl)
				self.meta['trace'] = lbl
				return lbl
			elif not self.is_scored():
				raise Exception("you're doing some shit, boi")
				return "(" + ', '.join([ str(branch) + ":" + str(modality) for (branch, modality) in sorted(self.children, key = lambda child: (child[1], child[0].root.label )) ]) + ")" + lbl
			else :
				#print("(" + ', '.join( [ str(branch) + ":" + str(modality) for (branch, modality) in sorted(self.children, key = lambda child: child[0].meta['score']) ] ) + ")" + lbl)
				trace = "(" + ', '.join( [ str(branch) + ":" + str(modality) for (branch, modality) in sorted(self.children, key = lambda child: child[0].meta['score']) ] ) + ")" + lbl
				self.meta['trace'] = trace
				return trace

	def __copy__(self):
		return copy.deepcopy(self)

	def __eval__(self, arg: str):
		"""

		"""
		# more convenient alias for self
		tree = self

		defs = re.findall('\$\w*', arg) 	# replace definitions
		for definition in defs:
			definition = str(definition)
			if definition in attributes_definitions:
				formal_def = attributes_definitions[definition]
				arg = arg.replace(definition, formal_def)
			else :
				raise AttributeError("Unknown Attribute definition : " + definition)

		return eval(arg)

	def _get_label(self):
		if type(self.root).__name__ == "Mirror_Node" :
			return self.root.label + "#" + str(self.root.arity) + "{" + str(self.root.magnet) +"}"
		elif type(self.root).__name__ == "Virtual_Node" :
			return self.root.label + "*{" + str(self.root.magnet) +"}"
		else :
			return self.root.label

	def hashtree(self): 
		return hashlib.sha224(str(self).encode()).hexdigest()

	def get_order_sequence(self, prop = None):

		self.score_tree()
		#print(" ! " + self.root.id + " !")
		if prop == None :
			lbl = self.root.id
		else:
			lbl = self.root.meta[prop] if prop in self.root.meta else None

		if self.is_leaf() :
			return lbl
		elif not self.is_scored():
			self.score_tree()
			seq = [lbl, [ branch.get_order_sequence(prop) for (branch, modality) in sorted(self.children, key = lambda child: child[0].meta['score']) ]]
		else :
			seq = [lbl, [ branch.get_order_sequence(prop) for (branch, modality) in sorted(self.children, key = lambda child: child[0].meta['score']) ]]
		return seq

	def map_node(self, node_fn = hashtree) :

		def filt(i) :
			if '@' in i :
				l = i[:i.index('@')]
				return l if (not '#' in l and not '*' in l) else None
			elif not '#' in i and not '*' in i :
				return i
			else :
				return None

		def flatten(l): 
				return flatten(l[0]) + (flatten(l[1:]) if len(l) > 1 else []) if type(l) is list else [l]

		mapping = { self.root.id : node_fn(self) }

		if not self.is_leaf():
			submaps = [ branch.map_node(node_fn) for (branch, modality) in self.children ]

			for submap in submaps :
				for id_node in submap :
					id_node_sanitized = filt(id_node)
					#print(id_node_sanitized)
					if id_node_sanitized :
						if id_node_sanitized in mapping :
							#print("merging %s with %s" % ([mapping[id_node_sanitized]], [submap[id_node]]))
							#mapping[id_node] = min([mapping[id_node], submap[id_node]])
							mapping[id_node_sanitized] = sorted(flatten([mapping[id_node_sanitized]] + [submap[id_node]]))
							#print(mapping[id_node_sanitized])
						else :
							mapping[id_node_sanitized] = submap[id_node]
							#print("new challenger - mapping[%s] := %s " % (id_node_sanitized, submap[id_node]))
		for k in mapping :
			mapping[k] = str(mapping[k])
		
		return mapping


	def is_scored(self) -> bool:
		"""
			is_scored
			---------
		"""
		return not False in [ 'score' in child.meta for (child, modality) in self.children ]

	def is_leaf(self) -> bool:
		"""
			is_leaf
			-------
		"""
		return self.children == None

	def depth(self) -> int:
		"""
			depth
			-----
		"""
		if self.is_leaf() :
			return 1
		else :
			# we had zero to avoid an isolated node to return an error.
			# in this case, this node is equivalent to a leaf
			return 1 + max([0] + [ child.depth() for (child, modality) in self.children ])


	def enumerate_nodes_recursive(self, depth_max: int = -1, current_depth: int = 0) -> List[Tuple[Node, int]]:
		"""Recursive version of ``enumerate_nodes`` kept for benchmarking."""
		enum = [ (self.root, current_depth) ]
		if not self.is_leaf() and depth_max != 0:
		        depth_max -= 1
		        for (child, modality) in self.children:
		                enum += child.enumerate_nodes_recursive(depth_max, current_depth + 1)
		return enum


	def score_tree_recursive(self, fn: TreeScoring = def_tree_fn()) -> bool:
		"""Recursive version of ``score_tree`` kept for benchmarking."""
		if self.is_leaf():
		        self.meta['score'] = fn(self)
		        trace("score[ " + str(self) + " ] = " + str(fn(self)), 3)
		        return True
		else:
		        statuses = [child.score_tree_recursive(fn) for (child, modality) in self.children]
		        self.meta['score'] = fn(self)
		        trace("score[ " + str(self) + " ] = " + str(fn(self)), 3)
		        return not False in statuses

	def score_tree(self, fn: TreeScoring = def_tree_fn()) -> bool:
		"""Iterative version of ``score_tree``."""
		stack = [(self, False)]
		while stack:
		        node, visited = stack.pop()
		        if not visited:
		                stack.append((node, True))
		                if not node.is_leaf():
		                        for (child, modality) in reversed(node.children):
		                                stack.append((child, False))
		        else:
		                node.meta['score'] = fn(node)
		return True
	def enumerate_nodes(self, depth_max: int = -1, current_depth: int = 0) -> List[Tuple[Node, int]]:
		"""Iterative version of ``enumerate_nodes``."""
		enum = []
		stack = [(self, current_depth, depth_max)]
		while stack:
		        tree, depth, dmax = stack.pop()
		        enum.append((tree.root, depth))
		        if not tree.is_leaf() and dmax != 0:
		                ndmax = dmax - 1
		                for (child, modality) in reversed(tree.children):
		                        stack.append((child, depth + 1, ndmax))
		return enum


def iter_dfs(tree: 'Tree'):
	"""Iterative DFS traversal yielding ``Tree`` objects."""
	stack = [tree]
	while stack:
		node = stack.pop()
		yield node
		if not node.is_leaf():
			for (child, modality) in reversed(node.children):
				stack.append(child)


def iter_bfs(tree: 'Tree'):
	"""Iterative BFS traversal yielding ``Tree`` objects."""
	from collections import deque
	queue = deque([tree])
	while queue:
		node = queue.popleft()
		yield node
		if not node.is_leaf():
		        for (child, modality) in node.children:
		                queue.append(child)



