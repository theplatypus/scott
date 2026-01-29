class Node:
	def __init__(self, node_id, label=""):
		self.id = str(node_id)
		self.label = label

	def __repr__(self):
		return "Node(id=%s, label=%s)" % (self.id, self.label)


class Edge:
	def __init__(self, edge_id, node_a, node_b, modality="1"):
		self.id = str(edge_id)
		self.id_a = node_a
		self.id_b = node_b
		self.modality = str(modality)

	def __repr__(self):
		return "Edge(id=%s, a=%s, b=%s, modality=%s)" % (
			self.id,
			self.id_a,
			self.id_b,
			self.modality,
		)


class Graph:
	def __init__(self, rs_graph):
		self._rs_graph = rs_graph
		self.V = {}
		self.E = {}
		self._load_from_rs()

	def _load_from_rs(self):
		self.V.clear()
		self.E.clear()
		for node_id, label in self._rs_graph.node_labels():
			self.V[str(node_id)] = Node(node_id, label)
		for edge_id, id_a, id_b, modality in self._rs_graph.edges():
			self.E[str(edge_id)] = Edge(edge_id, id_a, id_b, modality)

	def as_rs(self):
		return self._rs_graph

	def __repr__(self):
		return "Graph(nodes=%d, edges=%d)" % (
			self._rs_graph.node_count,
			self._rs_graph.edge_count,
		)
