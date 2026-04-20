"""Canonization shim: delegates to Rust or legacy Python backend."""

from ._backend import resolve_backend
from .graph import Graph


def _as_rs_graph(graph, module):
	if isinstance(graph, Graph):
		return graph.as_rs()
	if hasattr(graph, "V") and hasattr(graph, "E"):
		nodes = [(node.id, node.label) for node in graph.V.values()]
		edges = [(edge.id_a, edge.id_b, edge.modality) for edge in graph.E.values()]
		return module.graph_from_edges(nodes, edges)
	return graph


def _as_legacy_graph(graph):
	"""Convert a scott.graph.Graph to a scott_legacy Graph."""
	if not isinstance(graph, Graph):
		return graph
	from scott_legacy.structs.graph import Graph as LegacyGraph
	from scott_legacy.structs.node import Node as LegacyNode
	from scott_legacy.structs.edge import Edge as LegacyEdge

	lg = LegacyGraph(graph.id)
	for node in graph.V.values():
		lg.add_node(LegacyNode(node.id, node.label))
	for edge in graph.E.values():
		a = lg.V[edge.id_a]
		b = lg.V[edge.id_b]
		lg.add_edge(LegacyEdge(edge.id, a, b, modality=str(edge.modality)))
	return lg


def to_cgraph(
	graph,
	candidate_rule="$degree",
	branch_rule="$depth > tree.parent_modality > $lexic",
	allow_hashes=True,
	compress=True,
	compact=False,
):
	backend, module = resolve_backend()
	if backend == "py":
		return module.canonize.to_cgraph(
			_as_legacy_graph(graph),
			candidate_rule=candidate_rule,
			branch_rule=branch_rule,
			allow_hashes=allow_hashes,
			compress=compress,
			compact=compact,
		)
	graph = _as_rs_graph(graph, module)
	return module.to_cgraph_py(
		graph,
		candidate_rule,
		branch_rule,
		allow_hashes,
		compress,
		compact,
	)


def scott_trace(
	graph,
	delimiter="|",
	candidate_rule="$degree",
	branch_rule="$depth > tree.parent_modality > $lexic",
	allow_hashes=True,
	compress=True,
	compact=False,
):
	backend, module = resolve_backend()
	if backend == "py":
		return module.canonize.scott_trace(
			_as_legacy_graph(graph),
			delimiter=delimiter,
			candidate_rule=candidate_rule,
			branch_rule=branch_rule,
			allow_hashes=allow_hashes,
			compress=compress,
			compact=compact,
		)
	cgraph = to_cgraph(
		graph,
		candidate_rule=candidate_rule,
		branch_rule=branch_rule,
		allow_hashes=allow_hashes,
		compress=compress,
		compact=compact,
	)
	return str(cgraph)
