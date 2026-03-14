"""Test retro-compatibility of the st.structs.{graph,node,edge} API."""

import pytest


@pytest.mark.unit
def test_build_graph_readme_syntax():
	"""Reproduces the 'Build a Graph' snippet from ReadMe.md."""
	import scott as st

	graph = st.structs.graph.Graph()
	n1 = st.structs.node.Node("1", "C")
	n2 = st.structs.node.Node("2", "O")
	n3 = st.structs.node.Node("3", "H")
	n4 = st.structs.node.Node("4", "H")

	e1 = st.structs.edge.Edge("1", n1, n2, modality=2)
	e2 = st.structs.edge.Edge("2", n1, n3)
	e3 = st.structs.edge.Edge("3", n1, n4)

	graph.add_node(n1)
	graph.add_nodes([n2, n3, n4])
	graph.add_edge(e1)
	graph.add_edge(e2)
	graph.add_edge(e3)

	assert len(graph.V) == 4
	assert len(graph.E) == 3
	assert graph.V["1"].label == "C"
	assert graph.V["2"].label == "O"
	assert graph.E["1"].modality == "2"

	# The graph should be canonizable
	cgraph = st.canonize.to_cgraph(graph)
	trace = str(cgraph)
	assert len(trace) > 0


@pytest.mark.unit
def test_node_edge_direct_import():
	"""Node and Edge are also accessible from scott.graph directly."""
	from scott.graph import Node, Edge, Graph

	n1 = Node("a", "X")
	n2 = Node("b", "Y")
	e = Edge("e1", n1, n2, modality=3)

	assert e.id_a == "a"
	assert e.id_b == "b"
	assert e.modality == "3"

	g = Graph()
	g.add_nodes([n1, n2])
	g.add_edge(e)
	assert len(g.V) == 2
	assert len(g.E) == 1
