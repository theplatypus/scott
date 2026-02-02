
from typing import Tuple, Callable, List

from .structs.graph import Graph
from .structs.cgraph import CGraph
from .structs.node import Node
from .structs.tree import Tree, def_tree_fn

import re
import math
import json

verbose = False
verbosity = 2

def trace(msg, indent = 1, f = " "):
	if (verbose == True and indent <= verbosity):
		print("[canonize.py]" + f + indent*"\t" + msg)

def to_canonic_tree(graph: Graph, candidate_rule: str = "$degree", branch_rule: str = "$depth > tree.parent_modality > $lexic", allow_hashes = True, compact = False) -> Tree : 

	trace("# Step 1 : Root Candidates")	
	
	graph.score_nodes(rule = candidate_rule, meta_attr = "candidate_score")
	
	candidates = []
	max_score = ()
	for id_node, node in graph.V.items() :
		node_score = node.meta["candidate_score"]
		if node_score == max_score :
			candidates.append(id_node)
		elif node_score > max_score :
			max_score = node_score
			candidates = [ id_node ]
	
	trace("Candidates : " + str(candidates) + "\n", 2)
	
	trace("# Step 2 : Pruning")
	
	prune_graph(graph, candidates)
	trace("\n")
	
	trace("# Step 3 : Election")
	
	trace("## Substep 1 : Define a Tree ordering function", 2)
	
	tree_function = def_tree_fn(branch_rule)
	trace("`" + branch_rule + "` => " + str(tree_function), 3)
	
	trace("## Substep 2 : Get and score candidates rooted-Tree", 2)
	
	unmastered = graph.meta["prune_result"]["None"] if "None" in graph.meta["prune_result"] else []
	unmastered += candidates
	
	# in the case where all candidates are nodes, we cannot ignore nodes
	unmastered = unmastered if False in [ graph.is_leaf(i) for i in candidates ] else []
	
	trees = {}
	elected = []
	max_score = ()

	try:
		raise ImportError()
		from joblib import Parallel, delayed
		import os

		def compute_candidate(id_candidate, id_task, nb_tasks) :
			trace("computing candidate %s for restricted election... (%s/%s)" % (id_candidate, str(id_task), str(nb_tasks)), 2)
			dag = graph.to_dag(id_root = id_candidate, branch_rule = branch_rule, allow_hashes = allow_hashes)
			tree = dag.to_tree(id_root = id_candidate, id_origin = None, modality_origin = None, ids_ignore = unmastered)
			tree.score_tree(tree_function)
			trace("\n", 3)
			trace("Tree-" + str(tree.depth()) + " for candidate #" + id_candidate + " / " + str(len(candidates)) + " : " + str(tree), 3)
			
			trace("Ordered tree : " + str(tree) + " ; score : " + str(tree.meta['score']), 3)
			#trees[id_candidate] = tree
			return (id_candidate, tree)
			
		candidate_tuples = Parallel(n_jobs = os.cpu_count())(delayed(compute_candidate)(id_candidate, i+1, len(candidates)) for (i, id_candidate) in enumerate(candidates))
		
		for (id_candidate, tree) in candidate_tuples:
			trees[id_candidate] = tree
			if tree.meta['score'] == max_score : 
				elected.append(id_candidate)
			elif tree.meta['score'] > max_score : 
				elected = [id_candidate]
				max_score = tree.meta['score']

	except ImportError :
		done = 1 
		for id_candidate in candidates :

			trace("computing candidate %s for restricted election... (%s/%s)" % (id_candidate, str(done), str(len(candidates))), 2)
			dag = graph.to_dag(id_root = id_candidate, branch_rule = branch_rule, allow_hashes = allow_hashes)
			tree = dag.to_tree(id_root = id_candidate, id_origin = None, modality_origin = None, ids_ignore = unmastered)
			tree.score_tree(tree_function)
			trace("\n", 3)
			trace("Tree-" + str(tree.depth()) + " for candidate #" + id_candidate + " / " + str(len(candidates)) + " : " + str(tree), 3)
			
			trace("Ordered tree : " + str(tree) + " ; score : " + str(tree.meta['score']), 3)
			trees[id_candidate] = tree

			done += 1
			
			if tree.meta['score'] == max_score : 
				elected.append(id_candidate)
			elif tree.meta['score'] > max_score : 
				elected = [id_candidate]
				max_score = tree.meta['score']

	trace("\n")
	trace(" --- Election winner(s) : " + str(elected) + " with score " + str(max_score), 3)

	#if len(elected) > 1 :
	#	trace("# [Step 4] : Election-tie")
		# iteratively construct the k-neighboring of candidates nodes 
		# exclude from account nodes present in several neihborings
		
		# speed-up, we constuct two candidate-based roots, and we keep 
		# the winner once we have one
	#todo = len(elected)
	done = 1
	try:
		raise ImportError()
		from joblib import Parallel, delayed
		import os

		def compute_candidate(id_candidate, id_task, nb_tasks) :
			"""
			worst function ever (non-pure, side effects, useless), but convenient for multi thread
			"""
			nonlocal done
			trace("computing candidate %s... (%s/%s)" % (id_candidate, str(id_task), str(nb_tasks)), 2)
			ret = graph.to_dag(id_root = id_candidate, compact_form = compact, allow_hashes = allow_hashes).to_tree(id_root = id_candidate, id_origin = None, modality_origin = None)
			#todo -= 1
			#print("%s candidates remaining" % (str(todo)))
			done += 1
			return ret
		
		#candidate_trees = [ compute_candidate(id_candidate) for id_candidate in elected ]
		candidate_trees = Parallel(n_jobs = os.cpu_count())(delayed(compute_candidate)(id_candidate, i+1, len(elected)) for (i, id_candidate) in enumerate(elected))
	except ImportError :
		candidate_trees = [
			graph.to_dag(id_root = id_candidate, compact_form = compact, allow_hashes = allow_hashes).to_tree(id_root = id_candidate, id_origin = None, modality_origin = None)
			for id_candidate in elected
		]
	
	res = []
	#print("THERE ARE %s CANDIDATES TREES " % (str(len(candidate_trees))))
	for tree in candidate_trees:
		tree.score_tree(tree_function)
		res.append((str(tree), tree))
		seq = tree.get_order_sequence()
	winner = sorted(res, key = lambda i : i[0])[0][1]
	
	#print("Winner : %s" % (winner.root.id))
	
	winner.get_order_sequence()
	
	return winner

def to_cgraph(graph: Graph, candidate_rule: str = "$degree", branch_rule: str = "$depth > tree.parent_modality > $lexic", allow_hashes = True, compress = True, compact = False) -> CGraph : 
	"""
		to_cgraph
		Compress a unique connex compound  to a cgraph
	"""
	winner = to_canonic_tree(graph, candidate_rule, branch_rule, allow_hashes, compact)

	output = str(winner)
	
	trace("ALGO FINISHED ! \n--------------------")
	trace("Canonical Form : " + output, 2)
	
	if compress :
		output = compress_cgraph(output)
	
	return CGraph(output)

def scott_trace(graph: Graph, delimiter = "|", candidate_rule: str = "$degree", branch_rule: str = "$depth > tree.parent_modality > $lexic", allow_hashes = True, compress = True, compact = False) -> str :
	"""
		scott_trace
		simplest way to get a canonical trace
		handle multiple connex components
	""" 
	components = graph.split_connex_compounds()
	cgraphs = []
	for component in components :
		cgraphs.append(str(to_cgraph(component, candidate_rule, branch_rule, allow_hashes, compress, compact)))
	
	return delimiter.join(sorted(cgraphs))

def compress_cgraph(cgraph: str) -> str:
	"""
	
	"""
	output = ""
	magnets = {}
	magnet = ""
	in_magnet = False
	cpt = 0
	depth = 0
	
	for symbol in cgraph :
		if not in_magnet :
			output += symbol
			#print(output)
			if symbol == "{":
				in_magnet = True
		else :
			if symbol == "{":
				depth += 1
				#print("depth += 1 => %s" % (depth)) 
			elif symbol == "}":
				
				if depth == 0:
					#print("end of magnet : %s" % (magnet))
					in_magnet = False
					if not magnet in magnets :
						cpt += 1
						magnets[magnet] = "$%s" % (cpt)
					eq = magnets[magnet]
					output += "%s}" % (eq)
					magnet = ""
				else :
					depth -= 1
					#print("depth -= 1 => %s" % (depth))
			else :
				magnet += symbol
	return output

def prune_graph(graph: Graph, candidates: List[str]) -> Graph:
	"""
		prune_graph
		-----------
		Annotates the graph with nodes allegeances to root candidates
	"""
	trace("## Substep 1 : Broadcast 'join' messages", 2)
	
	def prune_propagation(node_from: Node, node_to: Node, msg: str) -> bool:
		trace("Node #" + node_to.id + " received '" + msg + "' from #" + node_from.id, 3)
		
		if not node_to.id in candidates : # do not trust meta.isCandidate at this moment
			trace(node_to.id + " : I'm not candidate", 4)
			if "master" in node_to.meta :
				trace(node_to.id + " : ... but I already have a master...", 4)
				if node_to.meta["master"] == msg :
					trace(node_to.id + " : Oh it's you again, master. seems there is a loop. Aborting.", 4)
					return False
				else :
					trace(node_to.id + " Not my master. I'm out of this election.", 4)
					node_to.meta["master"] = None
					if msg in node_to.meta["master_attempts"]:
						trace(node_to.id + " ... and I already met this candidate before. Aborting.", 4)
						return False
					else :
						node_to.meta["master_attempts"].append(str(msg))
			else :
				trace(node_to.id + " : My master is now " + str(msg),4)
				node_to.meta["master"] = str(msg)
				node_to.meta["master_attempts"] = [ str(msg) ]
			return graph.broadcast(id_node_from = node_to.id, id_origin = node_from.id, msg = msg, callback = prune_propagation)
		else :
			trace(node_to.id + " : I'm also candidate, so I stop the propagation", 4)
			return False
	
	for id_candidate in candidates :
		graph.V[id_candidate].meta["isCandidate"] = True
		graph.broadcast(id_node_from = id_candidate, id_origin = None, msg = str(id_candidate), callback = prune_propagation)
	
	
	spreading = {}
	for id_node in graph.V :
		node = graph.V[id_node]
		if "master" in node.meta :
			master = str(node.meta["master"])
			if master in spreading :
				spreading[master].append(node.id)
			else :
				spreading[master] = [ node.id ]
	graph.meta["prune_result"] = spreading
	
	trace("## [Substep 2] : Print result :", 2)
	trace(json.dumps(spreading, indent=4), 3)
	
	return graph	
