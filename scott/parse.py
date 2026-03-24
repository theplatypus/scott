"""Graph format parsers (DOT, DIMACS, SDF, SMILES, PubChem XML, NetworkX)."""

import gzip
import re

from .graph import Graph, Node, Edge


# ---------------------------------------------------------------------------
#  DOT
# ---------------------------------------------------------------------------

def _stripcomments(txt):
	return re.sub(r'//.*?\n|/\*.*?\*/', '', txt, flags=re.S)


def parse_dot(text_content):
	"""Parse a single DOT graph string into a Graph."""
	directed = False
	graph_id = ""

	lines = text_content.split("\n")
	line = ""

	while line == "":
		line = lines.pop(0)

	tokens = line.split()
	token = tokens.pop(0)

	if token == "strict":
		token = tokens.pop(0)

	if token == "digraph":
		directed = True
		token = tokens.pop(0)
	elif token == "graph":
		token = tokens.pop(0)
	else:
		raise ValueError("graph|digraph token not found")

	if token != "{":
		graph_id = token
		token = tokens.pop(0)

	if token != "{":
		raise ValueError('expected "{" not found')

	edgeop = "->" if directed else "--"
	raw_nodes = []
	raw_edges = []

	def _unquote(s):
		if len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
			return s[1:-1]
		return s.rstrip(";")

	while lines and lines[0].strip() != "}":
		line = lines.pop(0)
		if len(line.strip()) == 0:
			continue
		line = _stripcomments(line)
		opts = re.search(r"\[(.*)\]", line)
		opts_dict = {}
		if opts:
			for opt in opts.group(1).split(","):
				parts = opt.split("=", 1)
				if len(parts) == 2:
					opts_dict[parts[0].strip()] = _unquote(parts[1].strip())
		tokens = line.split()

		if edgeop in tokens:
			id_a = _unquote(tokens[0])
			id_b = _unquote(tokens[2])
			mod = str(opts_dict.get("weight", "1"))
			raw_edges.append((id_a, id_b, mod))
		elif tokens:
			id_node = _unquote(tokens[0])
			label = str(opts_dict.get("label", ""))
			raw_nodes.append((id_node, label))

	graph = Graph(id=graph_id)
	nodes = [Node(str(nid), label) for nid, label in raw_nodes]
	graph.add_nodes(nodes)
	edges = [Edge(i, graph.V[a], graph.V[b], mod)
			 for i, (a, b, mod) in enumerate(raw_edges, 1)]
	graph.add_edges(edges)
	return graph


def from_dot(dot_content=None, file_path=None):
	"""Parse DOT file(s) into a list of Graphs.

	Uses the Rust parser when the rs backend is available,
	otherwise falls back to the Python parser.
	"""
	from ._backend import resolve_backend
	backend, module = resolve_backend()

	if backend == "rs":
		if file_path is not None:
			rs_graph = module.parse_dot(file_path)
		elif dot_content is not None:
			rs_graph = module.parse_dot_string(dot_content)
		else:
			raise ValueError("dot_content or file_path is required")
		return [Graph(rs_graph)]

	# Python fallback (legacy or no Rust)
	if file_path is not None:
		if file_path.endswith(".gz"):
			with gzip.open(file_path, "rt", encoding="utf-8") as fp:
				dot_content = fp.read()
		else:
			with open(file_path, "r") as fp:
				dot_content = fp.read()
	if dot_content is None:
		raise ValueError("dot_content or file_path is required")
	parts = dot_content.split("}")
	return [parse_dot(part + "}") for part in parts[:-1]]


# ---------------------------------------------------------------------------
#  DIMACS
# ---------------------------------------------------------------------------

def parse_dimacs(text_content):
	"""Parse a DIMACS graph string into a Graph."""
	lines = text_content.split("\n")
	header = lines.pop(0)
	while not header.startswith("p "):
		header = lines.pop(0)
	parts = header.split(" ")
	vertices = int(parts[2])

	graph = Graph(id="")
	nodes = [Node(str(i), ".") for i in range(1, vertices + 1)]
	graph.add_nodes(nodes)

	edge_list = []
	id_edge = 1
	for line in lines:
		tokens = line.split(" ")
		if len(tokens) == 3:
			id_a = tokens[1]
			id_b = tokens[2]
			edge_list.append(Edge(id_edge, graph.V[id_a], graph.V[id_b], "1"))
			id_edge += 1
	graph.add_edges(edge_list)
	return graph


def from_dimacs(dimacs_content=None, file_path=None):
	"""Parse a DIMACS file into a list of Graphs."""
	if file_path is not None:
		if file_path.endswith(".gz"):
			with gzip.open(file_path, "rt", encoding="utf-8") as fp:
				dimacs_content = fp.read()
		else:
			with open(file_path, "r") as fp:
				dimacs_content = fp.read()
	return [parse_dimacs(dimacs_content)]


# ---------------------------------------------------------------------------
#  SDF / MOL
# ---------------------------------------------------------------------------

def parse_Mol(mol_content, ignore_hydrogens=False):
	"""Parse a MOL block into (atoms, bonds) lists."""
	lines = mol_content.split("\n")
	while lines and not lines[0]:
		lines.pop(0)

	# Line 4 (index 3) is the counts line: atoms_nb bonds_nb ...
	counts = [int(x) for x in lines[3].split() if x.isdigit()]
	atoms_nb, bonds_nb = counts[0], counts[1]

	atom_lines = lines[4:4 + atoms_nb]
	bond_lines = lines[4 + atoms_nb:4 + atoms_nb + bonds_nb]

	atoms = [line.split()[3] for line in atom_lines]
	bonds = [tuple(line.split()[:3]) for line in bond_lines]

	if ignore_hydrogens:
		h_indexes = [str(i) for i, sym in enumerate(atoms, 1) if sym == "H"]
		atoms = [a for a in atoms if a != "H"]
		bonds = [b for b in bonds if b[0] not in h_indexes and b[1] not in h_indexes]

	return (atoms, bonds)


def _is_Mol(block):
	return ">" not in block


def Mol_to_Graph(atoms, bonds):
	"""Convert (atoms, bonds) to a Graph."""
	if not atoms and not bonds:
		return None
	graph = Graph()
	nodes = [Node(str(i), label) for i, label in enumerate(atoms, 1)]
	graph.add_nodes(nodes)
	edges = [Edge(i, graph.V[a], graph.V[b], mod)
			 for i, (a, b, mod) in enumerate(bonds, 1)]
	graph.add_edges(edges)
	return graph


def from_sdf(sdf_content=None, file_path=None, ignore_hydrogens=False):
	"""Parse an SDF file into a list of Graphs."""
	if file_path is not None:
		if file_path.endswith(".gz"):
			with gzip.open(file_path, "rt", encoding="utf-8") as fp:
				sdf_content = fp.read()
		else:
			with open(file_path, "r") as fp:
				sdf_content = fp.read()

	return [
		Mol_to_Graph(mol[0], mol[1])
		for mol in [
			parse_Mol(mol_file, ignore_hydrogens)
			for mol_file in [
				part[0]
				for part in [
					compound.split("M  END")
					for compound in sdf_content.split("$$$$")
					if compound.strip() != ""
				]
				if _is_Mol(part)
			]
		]
	]


# ---------------------------------------------------------------------------
#  SMILES
# ---------------------------------------------------------------------------

def parse_smiles(smiles, ignore_hydrogens=False):
	"""Parse a SMILES string into a Graph. Requires rdkit or pybel."""
	from ._smiles import to_mol_block
	mol_block = "Fake_ID" + to_mol_block(smiles)
	atoms, bonds = parse_Mol(mol_block, ignore_hydrogens)
	return Mol_to_Graph(atoms, bonds)


# ---------------------------------------------------------------------------
#  PubChem XML
# ---------------------------------------------------------------------------

def from_pubchem_xml(xml_content=None, file_path=None,
					 ignore_hydrogens=False, ensure_uq_covalent_unit=True):
	"""Parse PubChem XML into a list of Graphs."""
	return [t[1] for t in map_pubchem_xml(
		xml_content, file_path, ignore_hydrogens, ensure_uq_covalent_unit)]


def map_pubchem_xml(xml_content=None, file_path=None,
					ignore_hydrogens=False, ensure_uq_covalent_unit=True):
	"""Parse PubChem XML into a list of (id, Graph) tuples."""
	import xml.etree.ElementTree as ET

	NS = "{http://www.ncbi.nlm.nih.gov}"

	def _parse_compound(pc_compound):
		try:
			atoms = []
			bonds = []
			h_index = []

			pc_id_el = (pc_compound
				.find(NS + "PC-Compound_id")
				.find(NS + "PC-CompoundType")
				.find(NS + "PC-CompoundType_id")
				.find(NS + "PC-CompoundType_id_cid"))
			pc_id = next(pc_id_el.iter()).text

			covalent_el = (pc_compound
				.find(NS + "PC-Compound_count")
				.find(NS + "PC-Count")
				.find(NS + "PC-Count_covalent-unit"))
			covalent_units = int(next(covalent_el.iter()).text)

			if ensure_uq_covalent_unit:
				assert covalent_units == 1

			pc_atoms = (pc_compound
				.find(NS + "PC-Compound_atoms")
				.find(NS + "PC-Atoms"))
			atoms_aid = pc_atoms.find(NS + "PC-Atoms_aid")
			atoms_elements = pc_atoms.find(NS + "PC-Atoms_element")
			assert len(atoms_aid) == len(atoms_elements)

			for i, id_node in enumerate(atoms_aid):
				element = atoms_elements[i].attrib["value"].capitalize()
				if element == "H":
					h_index.append(id_node.text)
				if not ignore_hydrogens or element != "H":
					atoms.append((id_node.text, element))

			pc_bonds = (pc_compound
				.find(NS + "PC-Compound_bonds")
				.find(NS + "PC-Bonds"))
			bonds_a = pc_bonds.find(NS + "PC-Bonds_aid1")
			bonds_b = pc_bonds.find(NS + "PC-Bonds_aid2")
			bonds_order = pc_bonds.find(NS + "PC-Bonds_order")
			assert len(bonds_a) == len(bonds_b) == len(bonds_order)

			for i, aid_a in enumerate(bonds_a):
				if not ignore_hydrogens or (
					aid_a.text not in h_index
					and bonds_b[i].text not in h_index
				):
					bonds.append((aid_a.text, bonds_b[i].text, bonds_order[i].text))

			graph = Graph(id=pc_id)
			nodes = [Node(str(aid), label) for aid, label in atoms]
			graph.add_nodes(nodes)
			edges = [Edge(i, graph.V[a], graph.V[b], mod)
					 for i, (a, b, mod) in enumerate(bonds, 1)]
			graph.add_edges(edges)
			return (pc_id, graph)
		except Exception:
			return (None, None)

	if file_path is not None:
		if file_path.endswith(".gz"):
			fp = gzip.open(file_path, "rt", encoding="utf-8")
		else:
			fp = open(file_path, "r", encoding="utf-8")

		def compound_gen():
			fp.seek(0)
			context = iter(ET.iterparse(fp, events=("start", "end")))
			_, root = next(context)
			for event, elem in context:
				if event == "end" and elem.tag == NS + "PC-Compound":
					yield _parse_compound(elem)
					root.clear()

		return compound_gen()

	return [_parse_compound(el) for el in ET.XML(xml_content)]


# ---------------------------------------------------------------------------
#  NetworkX
# ---------------------------------------------------------------------------

def from_networkx(nx_graph):
	"""Convert a networkx.Graph into a scott Graph.

	Requires: pip install scott[nx]

	Node labels are read from the ``label`` attribute (default: ``""``).
	Edge modalities are read from the ``weight`` attribute (default: ``"1"``).
	"""
	try:
		import networkx as nx
	except ImportError:
		raise ImportError(
			"networkx is required for from_networkx(). "
			"Install it with: pip install scott[nx]"
		)
	if not isinstance(nx_graph, nx.Graph):
		raise TypeError("expected a networkx.Graph, got %s" % type(nx_graph).__name__)

	graph = Graph()
	for node_id, data in nx_graph.nodes(data=True):
		label = str(data.get("label", ""))
		graph.add_node(Node(str(node_id), label))

	for i, (u, v, data) in enumerate(nx_graph.edges(data=True), 1):
		mod = str(data.get("weight", "1"))
		graph.add_edge(Edge(i, graph.V[str(u)], graph.V[str(v)], mod))

	return graph
