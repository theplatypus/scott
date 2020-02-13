import itertools
from os import path
import zlib
import re
import gzip

from typing import Dict, Tuple, List

from .structs.graph import Graph
from .structs.node import Node
from .structs.edge import Edge

from .utils import smiles2mol

verbose = False

def trace(msg):
	if (verbose):
		print("[parse.py] " + msg)

# Type ALIASES
Atom = str
Bond = Tuple[str, str, str]
Mapping_ID_Graph = Tuple[str, Graph]

def flatmap(func, *iterable):
	return itertools.chain.from_iterable(map(func, *iterable))

def decompress(val):
	try:
		s = zlib.decompress(val, 16 + zlib.MAX_WBITS)
	except:
		return val
	return s

def decode_utf8(binary_str) :
	try:
		return binary_str.decode("utf-8")
	except Exception as e:
		print(e)
		return None

def stripcomments(txt):
	return re.sub('//.*?\n|/\*.*?\*/', '', txt, flags=re.S)

def from_abstract(file_path: str) -> List[Graph]:
	"""
		Abstract method

	For signature purpose, do not use
	"""
	raise NotImplementedError()

#–––––––––––––––––––– PARSE FUNCTIONS ; CONSUME STRINGS

def parse_dimacs(text_content) -> Graph :
	directed = False
	graph_id = ""
	graph_strict = False

	lines = text_content.split("\n")
	header = lines.pop(0)
	while not header.startswith('p '):
		header = lines.pop(0)
	(vertices, edges) = (int(header.split(' ')[2]), int(header.split(' ')[3]))
	ids_nodes = [ str(id_node) for id_node in range(1, vertices+1)]

	graph = Graph(id = "")

	nodes = [ Node(str(id_node), ".") for id_node in ids_nodes ]
	graph.add_nodes(nodes)

	edges = []
	id_edge = 1
	for line in lines : 
		if len(line.split(' ')) == 3 :
			tokens = line.split(' ')
			id_a = tokens[1]
			id_b = tokens[2]
			edges.append(Edge(id_edge, graph.V[id_a], graph.V[id_b], 1))
			id_edge += 1
	
	graph.add_edges(edges)

	return graph

def parse_dot(text_content) -> Graph :

	directed = False
	graph_id = ""
	graph_strict = False

	lines = text_content.split("\n")
	line = ""

	# trim first line
	while line == "" :
		line = lines.pop(0)

	# FIRST LINE

	tokens = line.split()
	token = tokens.pop(0)

	if token == "strict":
		graph_strict = True
		token = tokens.pop(0)

	if token == "digraph" :
		directed = True
		token = tokens.pop(0)
	elif token == "graph":
		token = tokens.pop(0)
	else :
		raise Exception('graph|digraph token not found')

	if token != "{" :
		graph_id = token
		token = tokens.pop(0)

	if token != "{" :
		raise Exception('expected "{" not found')

	# BODY

	edgeop = "->" if directed else "--"
	nodes = []
	edges = []

	while lines[0].strip() != "}":
		line = lines.pop(0)
		if len(line.strip()) == 0 :
			pass
		line = stripcomments(line)
		opts = re.search(r"\[(.*)\]", line)
		opts_dict = {}
		if opts :
			for opt in opts.group(1).split(','):
				k = opt.split("=")[0].strip()
				v = opt.split("=")[1].strip()
				opts_dict[k] = v
		tokens = line.split()

		if edgeop in tokens : # edge declaration
			id_a = tokens.pop(0)
			assert tokens.pop(0) == edgeop
			id_b = tokens.pop(0)
			mod = str(opts_dict["weight"]) if "weight" in opts_dict else "1"
			edges.append((id_a, id_b, mod))

		elif tokens : # node declaration
			id_node = tokens.pop(0)
			label = str(opts_dict["label"]) if "label" in opts_dict else ""
			nodes.append((id_node, label))

	#print(nodes)
	#print(edges)
	graph = Graph(id = graph_id)

	nodes = [ Node(str(id_node), label) for (id_node, label) in nodes ]
	graph.add_nodes(nodes)
	edges = [ Edge(i, graph.V[a], graph.V[b], mod) for (i, (a, b, mod)) in enumerate(edges, 1)]
	graph.add_edges(edges)

	#print(graph)
	return graph

def parse_smiles(smiles: str, ignore_hydrogens = False) -> Graph:
	"""
		parse method from_dot

	"""
	mol_block = "Fake_ID" + smiles2mol.to_mol_block(smiles)
	mol = parse_Mol(mol_block, ignore_hydrogens)

	return Mol_to_Graph(mol[0], mol[1])


def parse_Mol(mol_content: str, ignore_hydrogens = False) -> (List[Atom], List[Bond]):
	"""
		parseMol

	Parse a Mol block into two lists
		- atoms
		- bonds
	"""
	trace("[parse_Mol]")
	trace(str(mol_content))
	try:
		lines = mol_content.split('\n')
		while not lines[0] :
			lines.pop(0)
		trace("""\tMOL HEADER
		{0}
		{1}
		{2}
		{3}
		""".format(lines[0].split(), lines[1].split(), lines[2].split(), lines[3].split()))

		# following the standard, the two first integers on the 4th line are respectively atoms_nb and bonds_nb
		(atoms_nb, bonds_nb) = tuple([ int(i) for i in lines[3].split() if i.isdigit() ][:2])
		#atoms = lines[ 4 : 4 + atoms_nb ]
		atoms = [ line for line in lines if len(line.split()) >= 4 and line.split()[3].isalpha() ]
		#trace(str(atoms))
		#bonds = lines[ 4 + atoms_nb : 4 + atoms_nb + bonds_nb ]
		bonds = [ line for line in lines if len(line.split()) == 4 and all([ float(i).is_integer() for i in line.split()])]
		#trace(str(bonds))
		atoms =  [ atom.split()[3] for atom in atoms ]
		bonds = [ tuple(bond.split()[:3]) for bond in bonds ]

		trace("""\t{0} ATOMS annouced ; {1} ATOMS found
		{2}
		\n
		{3} BONDS annouced ; {4} BONDS found
		{5}
		""".format(str(atoms_nb), len(atoms), atoms, str(bonds_nb), len(bonds), bonds))

		#assert len(atoms) == atoms_nb
		#assert len(bonds) == bonds_nb

		if ignore_hydrogens:
			H_indexes = [ str(i) for (i, atom_symbol) in enumerate(atoms,1) if str(atom_symbol) == "H" ]
			atoms = [ atom for atom in atoms if atom != "H" ]
			bonds = [ bond for bond in bonds if (bond[0] not in H_indexes and bond[1] not in H_indexes) ]

			trace("""\t{0} ATOMS != H
			{1}
			\n
			{2} BONDS !== H
			{3}
			H_indexes : {4}
			""".format(len(atoms), atoms,len(bonds), bonds, H_indexes))

		return (atoms, bonds)
	except Exception as e :
		print(str(e))
		raise(e)
		return (None, None)

def is_Mol(block: str) -> bool:
		"""
			isMol

		Read the first character of a SDF file block
		If the fist char is a ">", then it's not a Mol block
		"""
		trace("[isMol]")
		trace(str(block))
		trace(str((not ">" in block) ))
		return not ">" in block

def Mol_to_Graph(atoms: List[Atom], bonds: List[Bond]) -> Graph :
	"""

	NOTE : enumerate are used with an offset 1, because obiously, chemists start indexing from 1
	"""
	trace("[Mol_to_Graph]")
	trace(str(atoms))
	trace(str(bonds))
	if not atoms and not bonds :
		return None
	
	graph = Graph()
	nodes = [ Node(str(i), label) for (i, label) in enumerate(atoms, 1) ]
	graph.add_nodes(nodes)
	edges = [ Edge(i, graph.V[a], graph.V[b], mod) for (i, (a, b, mod)) in enumerate(bonds, 1) ]
	graph.add_edges(edges)
	return graph

#–––––––––––––––––––– FROM FUNCTIONS ; CONSUME FILES

def from_dimacs(dimacs_content: str = None, file_path: str = None) -> List[Graph]:
	"""
		parse method from_dot

	Parses a dimacs file
	"""

	if file_path :
		if (file_path.endswith('.gz')):
			fp = gzip.open(file_path, 'rt', encoding='utf-8')
			dimacs_content = fp.read()
		else :
			with open(file_path, 'r') as content_file:
				dimacs_content = content_file.read()
	return [ parse_dimacs(dimacs_content) ]

def from_dot(dot_content: str = None, file_path: str = None) -> List[Graph]:
	"""
		parse method from_dot

	Parses a dot file
	"""

	if file_path :
		if (file_path.endswith('.gz')):
			fp = gzip.open(file_path, 'rt', encoding='utf-8')
			dot_content = fp.read()
		else :
			with open(file_path, 'r') as content_file:
				dot_content = content_file.read()
	dots = dot_content.split('}')
	return [ parse_dot(dot + '}') for dot in dots[:-1:] ]

def from_sdf(sdf_content: str = None, file_path: str = None, ignore_hydrogens = False) -> List[Graph]:
	"""
		parse graph from_sdf

	Read chemical files and parses them into instances of `Graph`.

	As this function is not meant to be called in a loop,
	inner functions only relative to chemical files parsing are declared.

	Type Aliases :
	Atom = str
	Bond = List[str]
	"""

	if file_path :
		if (file_path.endswith('.gz')):
			fp = gzip.open(file_path, 'rt', encoding='utf-8')
			sdf_content = fp.read()
		else :
			with open(file_path, 'r') as content_file:
				sdf_content = content_file.read()

	return [ 
		Mol_to_Graph(mol[0], mol[1])
		for mol
		in [
			parse_Mol(mol_file, ignore_hydrogens)
			for mol_file
			in [
				part[0] 
				for part 
				in [
					compound.split('M  END')
					for compound 
					in sdf_content.split("$$$$")
					if (compound.strip(' \t\n\r') != '')
				]
				if is_Mol(part)
			]
		]
	]

def from_pubchem_xml(xml_content: str = None, file_path: str = None, ignore_hydrogens = False, ensure_uq_covalent_unit = True) -> List[Graph]:
	return [ t[1] for t in map_pubchem_xml(xml_content, file_path, ignore_hydrogens, ensure_uq_covalent_unit)]

def map_pubchem_xml(xml_content: str = None, file_path: str = None, ignore_hydrogens = False, ensure_uq_covalent_unit = True) -> List[Mapping_ID_Graph]:
	"""
		parse graph from pubchem xml

	Read chemical files and parses them into instances of `Graph`.

	schema = http://www.ncbi.nlm.nih.gov ftp://ftp.ncbi.nlm.nih.gov/pubchem/specifications/pubchem.xsd
	"""
	import xml.etree.cElementTree as ET
	#from lxml import etree as ET

	# Type ALIASES
	Atom = str
	Bond = Tuple[str, str, str]

	def parse_pc_compound(pc_compound: "Element '{http://www.ncbi.nlm.nih.gov}PC-Compound'") -> (str, Graph):
		"""
			parseMol

		Parse a Mol block into two lists
			- atoms
			- bonds
		"""
		try:
			atoms = []
			bonds = []
			h_index = []

			pc_id = pc_compound.find('{http://www.ncbi.nlm.nih.gov}PC-Compound_id')\
			.find('{http://www.ncbi.nlm.nih.gov}PC-CompoundType')\
			.find('{http://www.ncbi.nlm.nih.gov}PC-CompoundType_id')\
			.find('{http://www.ncbi.nlm.nih.gov}PC-CompoundType_id_cid')
			
			pc_id = next(pc_id.iter()).text
			trace("Cid : #" + pc_id)

			covalent_units = pc_compound.find('{http://www.ncbi.nlm.nih.gov}PC-Compound_count')\
			.find('{http://www.ncbi.nlm.nih.gov}PC-Count')\
			.find('{http://www.ncbi.nlm.nih.gov}PC-Count_covalent-unit')

			covalent_units = next(covalent_units.iter()).text
			trace(covalent_units + " covalent units")

			if ensure_uq_covalent_unit :
				assert int(covalent_units) == 1

			pc_atoms = pc_compound.find('{http://www.ncbi.nlm.nih.gov}PC-Compound_atoms').find('{http://www.ncbi.nlm.nih.gov}PC-Atoms')

			atoms_aid = pc_atoms.find('{http://www.ncbi.nlm.nih.gov}PC-Atoms_aid')
			atoms_elements = pc_atoms.find('{http://www.ncbi.nlm.nih.gov}PC-Atoms_element')

			assert len(atoms_aid) == len(atoms_elements)
			trace(str(len(atoms_aid)) + " atoms found")

			for (i, id_node) in enumerate(atoms_aid):
				if atoms_elements[i].attrib["value"].capitalize() == "H" :
					h_index.append(id_node.text)
				if not ignore_hydrogens or atoms_elements[i].attrib["value"].capitalize() != "H" :
					atoms.append((id_node.text, atoms_elements[i].attrib["value"].capitalize()))

			trace(str(len(atoms)) + " atoms stored")
			trace(str(atoms))
			trace(str(h_index))

			pc_bonds = pc_compound.find('{http://www.ncbi.nlm.nih.gov}PC-Compound_bonds').find('{http://www.ncbi.nlm.nih.gov}PC-Bonds')

			bonds_aid_a = pc_bonds.find('{http://www.ncbi.nlm.nih.gov}PC-Bonds_aid1')
			bonds_aid_b = pc_bonds.find('{http://www.ncbi.nlm.nih.gov}PC-Bonds_aid2')
			bonds_order = pc_bonds.find('{http://www.ncbi.nlm.nih.gov}PC-Bonds_order')

			assert len(bonds_aid_a) == len(bonds_aid_b) and len(bonds_aid_a) == len(bonds_order)
			trace(str(len(bonds_aid_a)) + " bonds found")

			for (i, aid_a) in enumerate(bonds_aid_a):
				if (not ignore_hydrogens or (aid_a.text not in h_index and bonds_aid_b[i].text not in h_index)):
					bonds.append((aid_a.text, bonds_aid_b[i].text, bonds_order[i].text))

			trace(str(len(bonds)) + " bonds stored")
			trace(str(bonds))

			graph = Graph(pc_id)

			nodes = [ Node(str(id_atom), label) for (id_atom, label) in atoms ]
			graph.add_nodes(nodes)
			edges = [ Edge(i, graph.V[a], graph.V[b], mod) for (i, (a, b, mod)) in enumerate(bonds, 1)]
			graph.add_edges(edges)

			return (pc_id, graph)

		except Exception as e :
			trace(str(e))
			#raise e
			return (pc_id, None)

	def parse_xml(text):
		try:
			return ET.XML(text)
		except Exception as e:
			trace(str(e))
			#raise e
			return None

	# if file is provided, and it might be huge, and thus require smart parsing
	if file_path :
		trace("parsing " + file_path)
		if (file_path.endswith('.gz')) :
			fp = gzip.open(file_path, 'rt', encoding='utf-8')
			xml_content = fp.read()
			trace(xml_content)
		else :
			fp = open(file_path, 'r', encoding='utf-8')
		
		def compound_gen():
			fp.seek(0)
			# get an iterable
			context = ET.iterparse(fp, events=("start", "end"))
			# turn it into an iterator
			context = iter(context)
			# get the root element
			event, root = context.__next__()
			for event, elem in context:
				#print(event)
				#print(elem.tag)
				if event == "end" and elem.tag == "{http://www.ncbi.nlm.nih.gov}PC-Compound":
					yield parse_pc_compound(elem)
					root.clear()
		
		return compound_gen()
	
	else : # keep it simple and stupid otherwise
		return [ parse_pc_compound(pc_compound) for pc_compound in parse_xml(xml_content) ]
		
