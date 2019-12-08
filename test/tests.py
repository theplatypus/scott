if __name__ == '__main__' and __package__ is None:
	from os import sys, path
	sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))

HEADER = '\033[95m'
OKBLUE = '\033[94m'
OKGREEN = '\033[92m'
WARNING = '\033[93m'
FAIL = '\033[91m'
ENDC = '\033[0m'
BOLD = "\033[1m"

def disable():
	HEADER = ''
	OKBLUE = ''
	OKGREEN = ''
	WARNING = ''
	FAIL = ''
	ENDC = ''

def boldok(msg):
	print(BOLD + OKGREEN + msg + ENDC + ENDC)

def ok(msg):
	print(OKGREEN  + msg+ "\n" + ENDC)

def info(msg):
	print(OKBLUE  + msg + ENDC)

def warn(msg):
	print(WARNING + msg + ENDC)

def fail(msg):
	print(FAIL + msg + ENDC)

def header(txt):
	info("""
######################################################
%s
######################################################
""" % (txt))


header("Step 1 : Importing package ")

import scott as st

if True:
	header("Step 2 : Parsing ")

	if False :
		info("""
	Parse an incorrect string :
	============================
		""")

		# should fail
		try:
			compounds = st.parse.from_sdf("some random string")
		except Exception as e:
			print("Failed as expected")
			print(e)

	if False :
		info("""
	Create arbitrary Graph :
	==========================
	""")

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

		print(type(n1))
		print(n1)
		print(type(e1))
		print(e1)
		print(type(graph))
		print(graph)

	if False :
		info("""
	Iterate over a  Graph :
	========================
	""")

		for id, node in graph.V.items() :
			print(node)

	if False :
		info("""
	Parse a .sdf file (chemical file standard) :
	================================================
	""")

		print("\t>>> compounds = st.parse.from_sdf(file_path = './data/simple_test.sdf')\n")

		compounds = st.parse.from_sdf(file_path = "./data/simple_test.sdf", ignore_hydrogens = False)
		print(compounds)
		compounds = st.parse.from_sdf(file_path = "./data/complete_test.sdf", ignore_hydrogens = False)
		for i in compounds :
			print(str(type(i)))

	if False :
		info("""
	Parse a .xml file (pubchem flavour)
	====================================
	""")

		print("\t>>> compounds = st.parse.from_pubchem_xml('./data/simple.xml', ignore_hydrogens = False)\n")

		compounds = st.parse.from_pubchem_xml(file_path = './data/simple.xml', ignore_hydrogens = False)
		print(compounds)

	if True :
		info("""
	Parse a .dot file
	==================
	""")

		print("\t>>> compounds = st.parse.from_dot('./data/test.dot')\n")

		compounds = st.parse.from_dot(file_path = './data/test.dot')
		print(compounds)

	ok("Parsing OK ")

	if True :
		info("""
	Parse SMILES
	==================
	""")

		print("\t>>> compounds = st.parse.parse_smiles('CCOCOCC=CCONC')\n")

		compound = st.parse.parse_smiles('CCOCOCC=CCONC')
		print(compound)

	ok("Parsing OK ")

if False :
	header("Step 3 : Canonization ")

	if True :
		info(
		"""
	Resolve simple Co-bound
	========================
		""")

		cobound = st.parse.from_dot(file_path = "./data/bound_cases/cobound.dot")[0]
		cobound = st.canonize.to_cgraph(cobound, candidate_rule = "1/(ord($label[0]))")
		print(cobound)

		assert str(cobound) == "(((*{$1}:1)C:1, (*{$1}:1)D:1)B:1)A"
		ok("✓")

		info(
		"""
	Resolve simple In-bound
	========================
		""")

		inbound = st.parse.from_dot(file_path = "./data/bound_cases/simple_inbound.dot")[0]
		inbound = st.canonize.to_cgraph(inbound, candidate_rule = "1/(ord($label[0]))")
		print(inbound)

		assert str(inbound) == "((D#2{$1}:1)C:1, ((E:1)D#2{$1}:1)B:1)A"
		ok("✓")

		info(
		"""
	Resolve multiple In-bound
	==========================
		""")

		inbound2 = st.parse.from_dot(file_path = "./data/bound_cases/multiple_inbound.dot")[0]
		inbound2 = st.canonize.to_cgraph(inbound2, candidate_rule = "1/(ord($label[0]))", branch_rule = "-$depth")
		print(inbound2)

		assert str(inbound2) == "(((E:1)D#3{$1}:1)B:1, (D#3{$1}:1)C:1, (D#3{$1}:1)F:1)A"
		ok("✓")

	if True :
		info(
		"""
	Convert a simple Graph to CGraph
	=================================
		""")

		compounds = st.parse.from_sdf(file_path = "./data/simple_test.sdf", ignore_hydrogens = False)
		molecule = compounds[0]

		print(st.canonize.to_cgraph(molecule))
		ok("✓")

	if True :
		info("""
	Obtain other CGraph computation with different injected functions
	===================================================================
		""")

		print("\t# 2 candidates, 2-tie")
		print('\t>>> print(cf.canonize.to_cgraph(molecule, branch_rule = "$depth"))\n')
		print(st.canonize.to_cgraph(molecule, branch_rule = "$depth"))

		print()

		print("\t# 3 candidates, pruning -> no slaves")
		print('\t>>> print(cf.canonize.to_cgraph(molecule, candidate_rule="-math.log($degree) > $label"))\n')
		print(st.canonize.to_cgraph(molecule, candidate_rule="-math.log($degree) > $label"))

	if True :
		info("""
	Assert canonical form is not dependent of the graph encoding
	=============================================================
		""")

		#cf.canonize.verbose = False
		#cf.structs.graph.verbose = False
		#cf.structs.tree.verbose = False
		#cf.parse.verbose = False

		info("=> elaic acid (easy)")

		elaic = st.parse.from_sdf(file_path = "./data/acid_elaic.sdf", ignore_hydrogens = True)[0]
		elaic_h = st.parse.from_sdf(file_path = "./data/acid_elaic_h.sdf", ignore_hydrogens = True)[0]

		elaic_canonical = st.canonize.to_cgraph(elaic)
		elaic_h_canonical = st.canonize.to_cgraph(elaic_h)

		print(elaic_canonical)
		print(elaic_h_canonical)

		if elaic_canonical.is_equal(elaic_h_canonical):
			ok("✓")
		else :
			fail("X")


		info("=> cafeine (not so easy)")

		cafeine = st.parse.from_sdf(file_path = "./data/cafeine.sdf", ignore_hydrogens = True)[0]
		cafeine_canonical = st.canonize.to_cgraph(cafeine, compress = True)

		caffeine = st.parse.from_sdf(file_path = "./data/caffeine.sdf", ignore_hydrogens = True)[0]
		caffeine_canonical = st.canonize.to_cgraph(caffeine, compress = True)

		print(cafeine_canonical)
		print(caffeine_canonical)

		if cafeine_canonical.is_equal(caffeine_canonical):
			ok("✓")
		else :
			fail("X")

	if True :
		info("=> arsphenamine (difficult)")

		anti = st.parse.from_sdf(file_path = "./data/antibiotic.sdf", ignore_hydrogens = True)[0]
		anti_canonical = st.canonize.to_cgraph(anti,
			candidate_rule = "1/(ord($label[0])) > $degree",
			branch_rule = "-$depth > tree.parent_modality > $lexic",
			compress = True)
	
		anti3 = st.parse.from_sdf(file_path = "./data/antibiotic3.sdf", ignore_hydrogens = True)[0]
		anti_canonical3 = st.canonize.to_cgraph(anti3,
			candidate_rule = "1/(ord($label[0])) > $degree",
			branch_rule = "-$depth > tree.parent_modality > $lexic",
			compress = True)

		print(anti_canonical)
		print()
		print(anti_canonical3)

		if anti_canonical.is_equal(anti_canonical3):
			ok("✓")
		else :
			fail("X")

	if False :
		info("=> graphene (diabolic)")

		graphene = st.parse.from_sdf(file_path = "./data/graphene.sdf", ignore_hydrogens = True)[0]
		graphene_canonical = st.canonize.to_cgraph(graphene,
			candidate_rule = "$label > -$degree",
			branch_rule = "-$depth > tree.parent_modality > $lexic",
			compress = True)

		graphene2 = st.parse.from_sdf(file_path = "./data/graphene2.sdf", ignore_hydrogens = True)[0]
		graphene_canonical2 = st.canonize.to_cgraph(graphene2,
			candidate_rule = "$label > -$degree",
			branch_rule = "-$depth > tree.parent_modality > $lexic",
			compress = True)

		print(graphene_canonical)
		print()
		print(graphene_canonical2)

		if graphene_canonical.is_equal(graphene_canonical2):
			ok("✓")
		else :
			fail("X")

	if True :
		info("""
	Detect false positive cases of isomorphims
	===========================================
		""")

		info("=> trapped arsphenamine (double bonds misplaced in aromatic cycles)")

		anti = st.parse.from_sdf(file_path = "./data/antibiotic.sdf", ignore_hydrogens = True)[0]
		anti_canonical = st.canonize.to_cgraph(anti, candidate_rule = "1/(ord($label[0])) > $degree", branch_rule = "-$depth > tree.parent_modality > $lexic", compress = True)

		anti2 = st.parse.from_sdf(file_path = "./data/antibiotic2.sdf", ignore_hydrogens = True)[0]
		anti_canonical2 = st.canonize.to_cgraph(anti2, candidate_rule = "1/(ord($label[0])) > $degree", branch_rule = "-$depth > tree.parent_modality > $lexic", compress = True)

		print()
		print(anti_canonical)
		print()
		print(anti_canonical2)

		if not anti_canonical.is_equal(anti_canonical2):
			ok("✓")
		else :
			fail("X")

	ok("Canonization OK")


if True :
	header("Step 4 : Fragmentation ")

	if True :
		info(
		"""
	Extract an arbitrary sub-graph of size 1 (caffeine)
	====================================================
		""")
	cafeine = st.parse.from_sdf(file_path = "./data/cafeine.sdf", ignore_hydrogens = True)[0]
	sub = st.fragmentation.extract_subgraph(cafeine, id_root = "1", size = 1)
	print("G' = (V', E'), |V| = " + str(len(sub.V)) + ", |E| = " + str(len(sub.V)))
	print(sub)

	ok("✓")

	if True :
		info(
		"""
	Map each node with a node-centered fragment (size 2)
	=====================================================
		""")
	frags = st.fragmentation.map_cgraph(cafeine, size = 2)
	print("CGraphs :")
	print(frags)

	if len(frags) == len(cafeine.V):
		print("We obtain as many cgraph as |V| (" + str(len(frags)) + ")" )
		ok("✓")
	else :
		print("We do not obtain as many cgraph as |V|")
		fail("X")

	if True :
		info(
		"""
	Project the cafeine into a fragment space (size 1)
	===================================================
		""")
	dico = st.fragmentation.fragment_projection(cafeine, size = 1)
	print("Projection :")
	print(dico)

	ok("✓")

	if True :
		info(
		"""
	Get n-grams from a node
	=========================
		""")
	ngrams = st.fragmentation.extract_ngrams(cafeine, "3", window_size = 2, fragment_size = 1)
	print("NGrams :")
	print(ngrams)

	if True :
		info(
		"""
	Get n-grams from a graph
	=========================
		""")

	ngrams = st.fragmentation.enum_ngrams(cafeine, window_size = 2, fragment_size = 1)
	print("NGrams :")
	print(ngrams)
