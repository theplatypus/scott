from typing import List

import networkx as nx

from .graph import Graph, from_networkx
from .cgraph import CGraph
from .tree import def_tree_fn

import json

verbose = False
verbosity = 2


def trace(msg, indent=1, f=" "):
    if verbose and indent <= verbosity:
        print("[canonize.py]" + f + indent * "\t" + msg)


def _ensure_graph(graph) -> Graph:
    if isinstance(graph, Graph):
        return graph
    if isinstance(graph, nx.Graph):
        return from_networkx(graph)
    raise TypeError("Expected networkx.Graph or nx_scott.graph.Graph")


def to_canonic_tree(graph, candidate_rule: str = "$degree", branch_rule: str = "$depth > tree.parent_modality > $lexic", allow_hashes=True, compact=False):
    graph = _ensure_graph(graph)

    trace("# Step 1 : Root Candidates")
    graph.score_nodes(rule=candidate_rule, meta_attr="candidate_score")

    candidates = []
    max_score = ()
    for id_node, node in graph.V.items():
        node_score = node.meta["candidate_score"]
        if node_score == max_score:
            candidates.append(id_node)
        elif node_score > max_score:
            max_score = node_score
            candidates = [id_node]

    trace("Candidates : " + str(candidates) + "\n", 2)

    trace("# Step 2 : Pruning")
    prune_graph(graph, candidates)
    trace("\n")

    trace("# Step 3 : Election")
    trace("## Substep 1 : Define a Tree ordering function", 2)

    tree_function = def_tree_fn(branch_rule)
    trace("`" + branch_rule + "` => " + str(tree_function), 3)

    trace("## Substep 2 : Get and score candidates rooted-Tree", 2)

    unmastered = graph.meta["prune_result"].get("None", []) if "prune_result" in graph.meta else []
    unmastered += candidates

    unmastered = unmastered if False in [graph.is_leaf(i) for i in candidates] else []

    trees = {}
    elected = []
    max_score = ()

    done = 1
    for id_candidate in candidates:
        trace("computing candidate %s for restricted election... (%s/%s)" % (id_candidate, str(done), str(len(candidates))), 2)
        dag = graph.to_dag(id_root=id_candidate, branch_rule=branch_rule, allow_hashes=allow_hashes)
        tree = dag.to_tree(id_root=id_candidate, id_origin=None, modality_origin=None, ids_ignore=unmastered)
        tree.score_tree(tree_function)
        trace("\n", 3)
        trace("Tree-" + str(tree.depth()) + " for candidate #" + id_candidate + " / " + str(len(candidates)) + " : " + str(tree), 3)
        trace("Ordered tree : " + str(tree) + " ; score : " + str(tree.meta["score"]), 3)
        trees[id_candidate] = tree

        done += 1
        if tree.meta["score"] == max_score:
            elected.append(id_candidate)
        elif tree.meta["score"] > max_score:
            elected = [id_candidate]
            max_score = tree.meta["score"]

    trace("\n")
    trace(" --- Election winner(s) : " + str(elected) + " with score " + str(max_score), 3)

    candidate_trees = [
        graph.to_dag(id_root=id_candidate, compact_form=compact, allow_hashes=allow_hashes).to_tree(
            id_root=id_candidate, id_origin=None, modality_origin=None
        )
        for id_candidate in elected
    ]

    res = []
    for tree in candidate_trees:
        tree.score_tree(tree_function)
        res.append((str(tree), tree))
        tree.get_order_sequence()

    winner = sorted(res, key=lambda i: i[0])[0][1]
    winner.get_order_sequence()

    return winner


def to_cgraph(graph, candidate_rule: str = "$degree", branch_rule: str = "$depth > tree.parent_modality > $lexic", allow_hashes=True, compress=True, compact=False) -> CGraph:
    graph = _ensure_graph(graph)
    winner = to_canonic_tree(graph, candidate_rule, branch_rule, allow_hashes, compact)
    output = str(winner)

    trace("ALGO FINISHED ! \n--------------------")
    trace("Canonical Form : " + output, 2)

    if compress:
        output = compress_cgraph(output)

    return CGraph(output)


def scott_trace(graph, delimiter="|", candidate_rule: str = "$degree", branch_rule: str = "$depth > tree.parent_modality > $lexic", allow_hashes=True, compress=True, compact=False) -> str:
    graph = _ensure_graph(graph)
    components = graph.split_connex_compounds()
    cgraphs = []
    for component in components:
        cgraphs.append(str(to_cgraph(component, candidate_rule, branch_rule, allow_hashes, compress, compact)))

    return delimiter.join(sorted(cgraphs))


def compress_cgraph(cgraph: str) -> str:
    output = ""
    magnets = {}
    magnet = ""
    in_magnet = False
    cpt = 0
    depth = 0

    for symbol in cgraph:
        if not in_magnet:
            output += symbol
            if symbol == "{":
                in_magnet = True
        else:
            if symbol == "{":
                depth += 1
            elif symbol == "}":
                if depth == 0:
                    in_magnet = False
                    if magnet not in magnets:
                        cpt += 1
                        magnets[magnet] = "$%s" % (cpt)
                    eq = magnets[magnet]
                    output += "%s}" % (eq)
                    magnet = ""
                else:
                    depth -= 1
            else:
                magnet += symbol

    return output


def prune_graph(graph: Graph, candidates: List[str]) -> Graph:
    trace("## Substep 1 : Broadcast 'join' messages", 2)

    def prune_propagation(node_from, node_to, msg: str) -> bool:
        trace("Node #" + node_to.id + " received '" + msg + "' from #" + node_from.id, 3)

        if node_to.id not in candidates:
            trace(node_to.id + " : I'm not candidate", 4)
            if "master" in node_to.meta:
                trace(node_to.id + " : ... but I already have a master...", 4)
                if node_to.meta["master"] == msg:
                    trace(node_to.id + " : Oh it's you again, master. seems there is a loop. Aborting.", 4)
                    return False
                trace(node_to.id + " Not my master. I'm out of this election.", 4)
                node_to.meta["master"] = None
                if msg in node_to.meta["master_attempts"]:
                    trace(node_to.id + " ... and I already met this candidate before. Aborting.", 4)
                    return False
                node_to.meta["master_attempts"].append(str(msg))
            else:
                trace(node_to.id + " : My master is now " + str(msg), 4)
                node_to.meta["master"] = str(msg)
                node_to.meta["master_attempts"] = [str(msg)]
            return graph.broadcast(id_node_from=node_to.id, id_origin=node_from.id, msg=msg, callback=prune_propagation)

        trace(node_to.id + " : I'm also candidate, so I stop the propagation", 4)
        return False

    for id_candidate in candidates:
        graph.V[id_candidate].meta["isCandidate"] = True
        graph.broadcast(id_node_from=id_candidate, id_origin=None, msg=str(id_candidate), callback=prune_propagation)

    spreading = {}
    for id_node in graph.V:
        node = graph.V[id_node]
        if "master" in node.meta:
            master = str(node.meta["master"])
            if master in spreading:
                spreading[master].append(node.id)
            else:
                spreading[master] = [node.id]
    graph.meta["prune_result"] = spreading

    trace("## [Substep 2] : Print result :", 2)
    trace(json.dumps(spreading, indent=4), 3)

    return graph
