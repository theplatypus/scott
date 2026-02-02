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
			graph,
			candidate_rule=candidate_rule,
			branch_rule=branch_rule,
			allow_hashes=allow_hashes,
			compress=compress,
			compact=compact,
		)
	if backend == "nx":
		return module.to_cgraph(
			graph,
			candidate_rule=candidate_rule,
			branch_rule=branch_rule,
			allow_hashes=allow_hashes,
			compress=compress,
			compact=compact,
		)
	if backend == "rs":
		graph = _as_rs_graph(graph, module)
		return module.to_cgraph_py(
			graph,
			candidate_rule,
			branch_rule,
			allow_hashes,
			compress,
			compact,
		)

	raise ImportError("unknown backend '%s'" % backend)


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
			graph,
			delimiter=delimiter,
			candidate_rule=candidate_rule,
			branch_rule=branch_rule,
			allow_hashes=allow_hashes,
			compress=compress,
			compact=compact,
		)
	if backend == "nx":
		return module.scott_trace(
			graph,
			delimiter=delimiter,
			candidate_rule=candidate_rule,
			branch_rule=branch_rule,
			allow_hashes=allow_hashes,
			compress=compress,
			compact=compact,
		)
	if backend == "rs":
		cgraph = to_cgraph(
			graph,
			candidate_rule=candidate_rule,
			branch_rule=branch_rule,
			allow_hashes=allow_hashes,
			compress=compress,
			compact=compact,
		)
		return str(cgraph)

	raise ImportError("unknown backend '%s'" % backend)
