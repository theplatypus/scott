class Node:
	def __init__(self, node_id, label=""):
		self.id = str(node_id)
		self.label = str(label)

	def __repr__(self):
		return "Node(id=%s, label=%s)" % (self.id, self.label)


class Edge:
	def __init__(self, edge_id, node_a, node_b, modality="1"):
		self.id = str(edge_id)
		self.id_a = str(node_a.id) if isinstance(node_a, Node) else str(node_a)
		self.id_b = str(node_b.id) if isinstance(node_b, Node) else str(node_b)
		self.modality = str(modality)

	def __repr__(self):
		return "Edge(id=%s, a=%s, b=%s, modality=%s)" % (
			self.id,
			self.id_a,
			self.id_b,
			self.modality,
		)


class Graph:
	def __init__(self, rs_graph=None, id=""):
		self.id = id
		self._rs_graph = rs_graph
		self.V = {}
		self.E = {}
		if rs_graph is not None:
			self._load_from_rs()

	def _load_from_rs(self):
		self.V.clear()
		self.E.clear()
		for node_id, label in self._rs_graph.node_labels():
			self.V[str(node_id)] = Node(node_id, label)
		for edge_id, id_a, id_b, modality in self._rs_graph.edges():
			self.E[str(edge_id)] = Edge(edge_id, id_a, id_b, modality)

	def _build_rs_graph(self):
		from ._backend import resolve_backend
		_, module = resolve_backend()
		nodes = [(n.id, n.label) for n in self.V.values()]
		edges = [(e.id_a, e.id_b, e.modality) for e in self.E.values()]
		self._rs_graph = module.graph_from_edges(nodes, edges)

	def add_node(self, node):
		self.V[node.id] = node
		self._rs_graph = None

	def add_nodes(self, nodes):
		for node in nodes:
			self.V[node.id] = node
		self._rs_graph = None

	def add_edge(self, edge):
		self.E[edge.id] = edge
		self._rs_graph = None

	def add_edges(self, edges):
		for edge in edges:
			self.E[edge.id] = edge
		self._rs_graph = None

	def as_rs(self):
		if self._rs_graph is None:
			self._build_rs_graph()
		return self._rs_graph

	def __repr__(self):
		return "Graph(nodes=%d, edges=%d)" % (len(self.V), len(self.E))
