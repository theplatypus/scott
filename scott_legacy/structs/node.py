import json
import copy

class Node :
	"""
		Node
		=====

	"""

	def __init__(self, id_node: str, label: str = ""):
		"""
			NOTE : id_node is encode in str to keep the actual maximum number of
			nodes free and to ensure JSON serialization,
			but it would be a good idea to use numeric values.
		"""
		self.id = str(id_node)
		self.label = str(label)
		self.meta = {"is_mirror" : False, "is_virtual" : False }
		self.data = {}
	
	def __str__(self):
		return self.__repr__()

	def __repr__(self):
		return json.dumps(self.__dict__, indent=4, sort_keys=True)

	def __copy__(self):
		return copy.deepcopy(self)


class Virtual_Node(Node) :

	def __init__(self, id_node: str, magnet: str = ""):
		Node.__init__(self, id_node = id_node, label = "")
		self.meta = { "is_mirror" : False, "is_virtual" : True }
		self.data = {}
		self.magnet = magnet

	def __str__(self):
		return self.__repr__()

	def __repr__(self):
		return json.dumps(self.__dict__, indent=4, sort_keys=True)

class Mirror_Node(Node) :

	def __init__(self, id_node: str, arity: int, label: str = "", magnet: str = ""):
		Node.__init__(self, id_node = id_node, label = label)
		self.meta = { "is_mirror" : True, "is_virtual" : False }
		self.data = {}
		self.arity = arity
		self.magnet = magnet

	def __str__(self):
		return self.__repr__()

	def __repr__(self):
		return json.dumps(self.__dict__, indent=4, sort_keys=True)
