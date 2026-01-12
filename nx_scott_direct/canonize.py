from typing import List

import networkx as nx

from .cgraph import CGraph
from .graph_ops import (
    normalize_graph,
    score_nodes,
    split_connex_compounds,
    to_dag,
    to_tree,
)
from .tree import def_tree_fn

import json

verbose = False
verbosity = 2


def trace(msg, indent=1, f=" "):
    if verbose and indent <= verbosity:
        print("[canonize.py]" + f + indent * "\t" + msg)


def _ensure_graph(graph):
    if not isinstance(graph, nx.Graph):
        raise TypeError("Expected networkx.Graph")
    return normalize_graph(graph)


def to_canonic_tree(graph: nx.Graph, candidate_rule: str = "$degree", branch_rule: str = "$depth > tree.parent_modality > $lexic", allow_hashes=True, compact=False):
    graph = _ensure_graph(graph)

    trace("# Step 1 : Root Candidates")
    score_nodes(graph, rule=candidate_rule, meta_attr="candidate_score")

    candidates = []
    max_score = ()
    for id_node in graph.nodes:
        node_score = graph.nodes[id_node]["meta"]["candidate_score"]
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

    unmastered = graph.graph.get("prune_result", {}).get("None", [])
    unmastered += candidates

    unmastered = unmastered if False in [graph.degree[i] == 1 for i in candidates] else []

    trees = {}
    elected = []
    max_score = ()

    done = 1
    for id_candidate in candidates:
        trace("computing candidate %s for restricted election... (%s/%s)" % (id_candidate, str(done), str(len(candidates))), 2)
        dag = to_dag(graph, id_root=id_candidate, branch_rule=branch_rule, allow_hashes=allow_hashes)
        tree = to_tree(dag, id_root=id_candidate, id_origin=None, modality_origin=None, ids_ignore=unmastered)
        tree.score_tree(tree_function)
        trace("\n", 3)
        trace("Tree-" + str(tree.depth()) + " for candidate #" + str(id_candidate) + " / " + str(len(candidates)) + " : " + str(tree), 3)

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
        to_tree(
            to_dag(graph, id_root=id_candidate, compact_form=compact, allow_hashes=allow_hashes),
            id_root=id_candidate,
            id_origin=None,
            modality_origin=None,
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


def to_cgraph(graph: nx.Graph, candidate_rule: str = "$degree", branch_rule: str = "$depth > tree.parent_modality > $lexic", allow_hashes=True, compress=True, compact=False) -> CGraph:
    graph = _ensure_graph(graph)
    winner = to_canonic_tree(graph, candidate_rule, branch_rule, allow_hashes, compact)

    output = str(winner)
    trace("ALGO FINISHED ! \n--------------------")
    trace("Canonical Form : " + output, 2)

    if compress:
        output = compress_cgraph(output)

    return CGraph(output)


def scott_trace(graph: nx.Graph, delimiter="|", candidate_rule: str = "$degree", branch_rule: str = "$depth > tree.parent_modality > $lexic", allow_hashes=True, compress=True, compact=False) -> str:
    graph = _ensure_graph(graph)
    components = split_connex_compounds(graph)
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


def prune_graph(graph: nx.Graph, candidates: List[str]) -> nx.Graph:
    trace("## Substep 1 : Broadcast 'join' messages", 2)

    def prune_propagation(node_from, node_to, msg: str) -> bool:
        trace("Node #" + str(node_to) + " received '" + msg + "' from #" + str(node_from), 3)

        node_meta = graph.nodes[node_to].setdefault("meta", {})

        if node_to not in candidates:
            if "master" in node_meta:
                if node_meta["master"] == msg:
                    return False
                node_meta["master"] = None
                node_meta.setdefault("master_attempts", [])
                if msg in node_meta["master_attempts"]:
                    return False
                node_meta["master_attempts"].append(str(msg))
            else:
                node_meta["master"] = str(msg)
                node_meta["master_attempts"] = [str(msg)]

            return broadcast(graph, node_to, node_from, msg, prune_propagation)

        return False

    for id_candidate in candidates:
        graph.nodes[id_candidate].setdefault("meta", {})["isCandidate"] = True
        broadcast(graph, id_candidate, None, str(id_candidate), prune_propagation)

    spreading = {}
    for id_node in graph.nodes:
        node_meta = graph.nodes[id_node].get("meta", {})
        if "master" in node_meta:
            master = str(node_meta["master"])
            spreading.setdefault(master, []).append(id_node)
    graph.graph["prune_result"] = spreading

    trace("## [Substep 2] : Print result :", 2)
    trace(json.dumps(spreading, indent=4), 3)

    return graph


def broadcast(graph: nx.Graph, id_node_from, id_origin, msg: str, callback) -> bool:
    acks = []
    for neighbor in graph.neighbors(id_node_from):
        if neighbor != id_origin:
            acks.append(callback(id_node_from, neighbor, msg))
    return not False in acks
