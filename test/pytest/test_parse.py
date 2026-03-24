"""Tests for scott.parse format parsers."""

import os

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.mark.unit
def test_from_dot():
	import scott
	graphs = scott.parse.from_dot(
		file_path=os.path.join(REPO_ROOT, "data/isotest/cfi-rigid-t2-dot/cfi-rigid-t2-0016-04-1.dot"),
	)
	assert len(graphs) == 1
	g = graphs[0]
	assert len(g.V) > 0
	assert len(g.E) > 0
	# should be canonizable
	trace = str(scott.canonize.to_cgraph(g))
	assert len(trace) > 0


@pytest.mark.unit
def test_from_dot_isomorphism():
	import scott
	g1 = scott.parse.from_dot(
		file_path=os.path.join(REPO_ROOT, "data/isotest/cfi-rigid-t2-dot/cfi-rigid-t2-0016-04-1.dot"),
	)[0]
	g2 = scott.parse.from_dot(
		file_path=os.path.join(REPO_ROOT, "data/isotest/cfi-rigid-t2-dot/cfi-rigid-t2-0016-04-2.dot"),
	)[0]
	t1 = str(scott.canonize.to_cgraph(g1))
	t2 = str(scott.canonize.to_cgraph(g2))
	assert t1 == t2


@pytest.mark.unit
def test_from_dimacs():
	import scott
	graphs = scott.parse.from_dimacs(
		file_path=os.path.join(REPO_ROOT, "data/isotest/cfi-rigid-t2/cfi-rigid-t2-0016-04-1"),
	)
	assert len(graphs) == 1
	g = graphs[0]
	assert len(g.V) > 0
	assert len(g.E) > 0
	trace = str(scott.canonize.to_cgraph(g))
	assert len(trace) > 0


@pytest.mark.unit
def test_from_sdf():
	import scott
	graphs = scott.parse.from_sdf(
		file_path=os.path.join(REPO_ROOT, "data/molecule/cafeine.sdf"),
	)
	assert len(graphs) >= 1
	g = graphs[0]
	assert len(g.V) > 0
	assert len(g.E) > 0
	trace = str(scott.canonize.to_cgraph(g))
	assert len(trace) > 0


@pytest.mark.unit
def test_from_sdf_ignore_hydrogens():
	import scott
	full = scott.parse.from_sdf(
		file_path=os.path.join(REPO_ROOT, "data/molecule/simple.sdf"),
		ignore_hydrogens=False,
	)[0]
	no_h = scott.parse.from_sdf(
		file_path=os.path.join(REPO_ROOT, "data/molecule/simple.sdf"),
		ignore_hydrogens=True,
	)[0]
	assert len(no_h.V) < len(full.V)


@pytest.mark.unit
def test_from_pubchem_xml():
	xml_path = os.path.join(REPO_ROOT, "data/molecule/simple.xml")
	if not os.path.exists(xml_path):
		pytest.skip("simple.xml fixture not found")
	import scott
	graphs = scott.parse.from_pubchem_xml(file_path=xml_path)
	# from_pubchem_xml returns a generator, consume it
	graphs = list(graphs)
	assert len(graphs) >= 1
	g = graphs[0]
	assert g is not None
	assert len(g.V) > 0


@pytest.mark.unit
def test_parse_dot_python():
	"""Test the pure-Python DOT parser directly."""
	from scott.parse import parse_dot

	dot = """graph test {
		"1" [label=A] ;
		"2" [label=B] ;
		"1" -- "2" ;
	}"""
	g = parse_dot(dot)
	assert len(g.V) == 2
	assert len(g.E) == 1
	assert g.V["1"].label == "A"
	assert g.V["2"].label == "B"


@pytest.mark.unit
def test_from_networkx():
	"""Test converting a networkx.Graph to a scott Graph."""
	nx = pytest.importorskip("networkx")
	from scott.parse import from_networkx

	nxg = nx.Graph()
	nxg.add_node("a", label="C")
	nxg.add_node("b", label="O")
	nxg.add_node("c", label="H")
	nxg.add_edge("a", "b", weight=2)
	nxg.add_edge("a", "c")

	g = from_networkx(nxg)
	assert len(g.V) == 3
	assert len(g.E) == 2
	assert g.V["a"].label == "C"
	assert g.V["b"].label == "O"
	assert g.V["c"].label == "H"
	# check modalities
	mods = sorted(e.modality for e in g.E.values())
	assert mods == ["1", "2"]
	# should be canonizable
	import scott
	trace = str(scott.canonize.to_cgraph(g))
	assert len(trace) > 0
