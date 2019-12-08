
from . import node

import json
import copy

class Edge : 
	"""
		Edge
		======
		
		A simple edge, embedding a `id_a`, a `id_b` and a `modality`.
		
	"""
	def __init__(self, id_edge: str, a: node.Node, b: node.Node, modality: str = "1", directed: bool = False):
		"""
		Nodes are given instead of just their `id`, so we can ensure each id correspond to an actual node,
		even if we only store their id in the struct
		"""
		self.id = str(id_edge)
		self.id_a = str(a.id)
		self.id_b = str(b.id)
		self.modality = str(modality)
		self.directed = directed
		self.meta = {}
		self.data = {}
	
	def __str__(self):
		return self.__repr__()
		
	def __repr__(self):
		return json.dumps(self.__dict__, indent=4, sort_keys=True)
	
	def __copy__(self):
		return copy.deepcopy(self)
	
	def other_end(self, id_base):
		if self.id_a == id_base :
			return self.id_b
		elif self.id_b == id_base :
			return self.id_a
		else : 
			return None
	
	def replace_end(self, id_old:str, id_new) -> bool:
		if self.id_a == id_old :
			self.id_a = id_new
			return True
		elif self.id_b == id_old :
			self.id_b = id_new
			return True
		else : 
			return False
	
