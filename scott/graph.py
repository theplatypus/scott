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

	def adjacency_matrix(self, canonic=False):
		"""Return the adjacency matrix as a list of lists.

		If *canonic* is True, the node ordering is derived from the
		canonical tree so that isomorphic graphs produce identical matrices.
		"""
		N = len(self.V)

		if canonic:
			from ._backend import resolve_backend
			_, module = resolve_backend()
			rs_graph = self.as_rs()
			node_order = module.canonical_node_order_py(rs_graph)
		else:
			node_order = sorted(self.V.keys())

		A = [[0] * N for _ in range(N)]
		for edge in self.E.values():
			i = node_order.index(self.V[edge.id_a].id)
			j = node_order.index(self.V[edge.id_b].id)
			mod = _str_to_int(edge.modality)
			A[i][j] = mod
			A[j][i] = mod

		if canonic:
			A = _stabilize_matrix(A)
		return A

	def __repr__(self):
		return "Graph(nodes=%d, edges=%d)" % (len(self.V), len(self.E))


def _str_to_int(val):
	try:
		return int(val)
	except (ValueError, TypeError):
		return sum(ord(c) for c in str(val))


def _stabilize_matrix(A):
	"""Resolve remaining ties in the canonical adjacency matrix.

	Groups of rows with identical patterns are sorted lexicographically
	so that structurally equivalent nodes always get the same position.
	"""
	N = len(A)
	# Build a sortable key per row: the row itself as a tuple
	indexed = list(range(N))
	# Iteratively refine: sort rows by their pattern, apply the permutation
	# to both rows and columns, repeat until stable.
	for _ in range(N):
		keys = [tuple(A[i]) for i in range(N)]
		perm = sorted(range(N), key=lambda i: keys[i])
		if perm == indexed:
			break
		# Apply permutation to rows and columns
		B = [[0] * N for _ in range(N)]
		for new_i, old_i in enumerate(perm):
			for new_j, old_j in enumerate(perm):
				B[new_i][new_j] = A[old_i][old_j]
		A = B
	return A
