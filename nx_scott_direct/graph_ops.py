import copy
import hashlib
import math
import random
import re
from typing import Callable, List, Tuple

import networkx as nx

from .tree import Tree, def_tree_fn
from .trace import emit

Node_Callback = Callable[[str, str, str], bool]
Comparator = Callable[[Tuple, Tuple], int]
Scoring = Callable[[str, nx.Graph], Tuple]

verbose = False
verbosity = 4


def trace(msg, indent=1, f=" ", override=False):
    if (verbose and indent <= verbosity) or override:
        print("[graph_ops.py]" + f + indent * "\t" + msg)


def _ensure_node_meta(graph, node_id):
    data = graph.nodes[node_id]
    meta = data.setdefault("meta", {})
    meta.setdefault("is_mirror", False)
    meta.setdefault("is_virtual", False)
    data.setdefault("label", str(node_id))
    return meta


def _ensure_edge_meta(graph, edge):
    u, v, k = edge
    data = _edge_data(graph, u, v, k)
    data.setdefault("meta", {})
    data.setdefault("modality", "1")
    data.setdefault("edge_id", _edge_id(edge))
    return data


def _edge_id(edge):
    u, v, k = edge
    return f"{u}-{v}" if k is None else f"{u}-{v}-{k}"


def _edge_data(graph, u, v, k):
    if graph.is_multigraph():
        return graph.edges[u, v, k]
    return graph.edges[u, v]


def _iter_edges(graph):
    if graph.is_multigraph():
        for u, v, k, data in graph.edges(keys=True, data=True):
            yield u, v, k, data
    else:
        for u, v, data in graph.edges(data=True):
            yield u, v, None, data


def _remove_edge(graph, edge):
    u, v, k = edge
    if graph.is_multigraph():
        graph.remove_edge(u, v, key=k)
    else:
        graph.remove_edge(u, v)


def _add_edge(graph, u, v, data):
    attrs = dict(data)
    if graph.is_multigraph():
        graph.add_edge(u, v, **attrs)
    else:
        graph.add_edge(u, v, **attrs)


def normalize_graph(graph: nx.Graph) -> nx.Graph:
    graph = copy.deepcopy(graph)
    for node_id in graph.nodes:
        _ensure_node_meta(graph, node_id)

    for idx, (u, v, k, data) in enumerate(_iter_edges(graph), start=1):
        data.setdefault("modality", data.get("modality", "1"))
        data.setdefault("edge_id", data.get("edge_id", f"e{idx}"))
        data.setdefault("meta", {})
    return graph


def str_to_int(val):
    try:
        val = int(val)
    except Exception:
        total = 0
        for c in str(val):
            total += ord(c)
        val = total
    return val


def def_node_fn(rule: str) -> Scoring:
    args = [arg.strip() for arg in rule.split(">")]
    return lambda id_node, graph: tuple([_eval_node(graph, str(arg), id_node) for arg in args])


attributes_definitions = {
    "$degree": "graph.degree[id_node]",
    "$label": "graph.nodes[id_node].get('label')",
    "$bounds": "tuple([ -i for i in evaluate_bounds(graph, id_node)])",
}


def _eval_node(graph, arg: str, id_node):
    defs = re.findall(r"\$\w*", arg)
    for definition in defs:
        definition = str(definition)
        if definition in attributes_definitions:
            formal_def = attributes_definitions[definition]
            arg = arg.replace(definition, formal_def)
        else:
            raise AttributeError("Unknown Attribute definition : " + definition)
    return eval(arg)


def score_nodes(graph: nx.Graph, rule: str = "$degree", meta_attr: str = "score") -> bool:
    score = def_node_fn(rule)
    trace("`" + rule + "`" + " => " + str(score), 3)
    for id_node in graph.nodes:
        _ensure_node_meta(graph, id_node)
        score_res = score(id_node, graph)
        graph.nodes[id_node]["meta"][meta_attr] = score_res
        trace("Node #" + str(id_node) + " :\t" + str(score_res), 3)
    return True


def reset_floor(graph: nx.Graph):
    for node_id in graph.nodes:
        graph.nodes[node_id].get("meta", {}).pop("floor", None)


def group_by_floor(graph: nx.Graph, id_root):
    floors = {}
    lengths = nx.single_source_shortest_path_length(graph, id_root)
    items = lengths.items() if hasattr(lengths, "items") else lengths
    for node_id, dist in items:
        _ensure_node_meta(graph, node_id)
        graph.nodes[node_id]["meta"]["floor"] = dist
        floors.setdefault(dist, []).append(node_id)
    graph.graph["floored_by"] = id_root
    graph.graph["floors"] = floors
    return floors


def find_cobounds(graph: nx.Graph):
    cobounds = []
    for u, v, k, data in _iter_edges(graph):
        floor_u = graph.nodes[u]["meta"].get("floor")
        floor_v = graph.nodes[v]["meta"].get("floor")
        if floor_u is not None and floor_u == floor_v:
            cobounds.append((u, v, k))
    trace(str(len(cobounds)) + " cobounds found", 4)
    return cobounds


def find_inbounds(graph: nx.Graph) -> List:
    inbounds = []
    for id_node in graph.nodes:
        routes = list(graph.edges(id_node, keys=True, data=True)) if graph.is_multigraph() else list(graph.edges(id_node, data=True))
        upstairs = []
        for route in routes:
            if graph.is_multigraph():
                u, v, k, data = route
            else:
                u, v, data = route
                k = None
            other = v if u == id_node else u
            if int(graph.nodes[other]["meta"].get("floor")) < int(graph.nodes[id_node]["meta"].get("floor")):
                upstairs.append((u, v, k))
        if len(upstairs) > 1:
            inbounds.append((int(graph.nodes[id_node]["meta"].get("floor")), id_node, upstairs))
    trace(str(len(inbounds)) + " inbounds found", 4)
    return inbounds


def cobounds_by_floor(graph: nx.Graph):
    trace("Substep 2.1 : Co--bound detection", 2)
    cobounds = find_cobounds(graph)
    trace(str(len(cobounds)) + " cobounds found : ", 3)

    trace("Substep 2.2 : Co--bound flooring", 2)
    cobounds_by_floor = {}
    cobound_floors = []
    for edge in cobounds:
        u, v, k = edge
        floor = graph.nodes[u]["meta"]["floor"]
        if floor in cobounds_by_floor:
            cobounds_by_floor[floor].append(edge)
        else:
            cobounds_by_floor[floor] = [edge]
            cobound_floors.append(floor)
    cobound_floors = sorted(cobound_floors, reverse=True)
    trace("cobounds_by_floor : %s" % (str(cobounds_by_floor)), 3)
    return cobounds_by_floor, cobound_floors


def inbounds_by_floor(graph: nx.Graph):
    trace("Substep 3 : In--bound detection", 2)
    inbounds = find_inbounds(graph)
    inbounds.sort(reverse=True)
    trace(str(len(inbounds)) + " inbounds found : ", 3)

    trace("Substep 3.1 : In--bound flooring", 2)
    inbounds_by_floor = {}
    inbound_floors = []
    for floor, id_node, upstairs in inbounds:
        if floor in inbounds_by_floor:
            inbounds_by_floor[floor].append((floor, id_node, upstairs))
        else:
            inbounds_by_floor[floor] = [(floor, id_node, upstairs)]
            inbound_floors.append(floor)
    inbound_floors = sorted(inbound_floors, reverse=True)
    trace("inbounds_by_floor : %s" % (str(inbounds_by_floor)), 3)
    return inbounds_by_floor, inbound_floors


def get_magnet(graph: nx.Graph, id_node: str, ignore_virtuals: bool = False, allow_hashes: bool = True) -> str:
    trace("getting magnet for node #%s" % (id_node), 3)
    floored_by = graph.graph.get("floored_by")
    if floored_by is None:
        raise Exception("Cannot compute magnet in unfloored graph")

    meta = graph.nodes[id_node].setdefault("meta", {})
    if "magnet" in meta and str(floored_by) in meta["magnet"]:
        return meta["magnet"][str(floored_by)]

    ignore = [
        id_remote
        for id_remote in graph.nodes
        if graph.nodes[id_remote]["meta"].get("floor") <= graph.nodes[id_node]["meta"].get("floor")
    ]
    tree = to_tree(graph, id_root=id_node, ids_ignore=ignore)
    tree.score_tree()

    magnet = "_" + str(tree) + "_"
    if allow_hashes:
        magnet = "_" + str(hashlib.md5(magnet.encode("utf-8")).hexdigest()) + "_"

    meta.setdefault("magnet", {})[str(floored_by)] = magnet
    return magnet


def score_cobounds(graph: nx.Graph, cobounds, allow_hashes: bool = True) -> List:
    ret = []
    for edge in cobounds:
        u, v, k = edge
        data = _edge_data(graph, u, v, k)
        sep = "-%s-" % (data.get("modality"))
        magnet = sep.join(sorted([
            get_magnet(graph, u, allow_hashes=allow_hashes),
            get_magnet(graph, v, allow_hashes=allow_hashes),
        ]))
        ret.append((magnet, edge))
        data.setdefault("meta", {})["magnet"] = magnet
    return sorted(ret)


def score_inbounds(graph: nx.Graph, inbounds) -> List:
    scored = []
    for inbound in inbounds:
        floor, id_node, id_edges = inbound
        arity = len(id_edges)
        main_magnet = get_magnet(graph, id_node)

        roots_ids = []
        for edge in id_edges:
            u, v, k = edge
            other = v if u == id_node else u
            roots_ids.append(other)

        root_magnets = [hashlib.md5(get_magnet(graph, id_root).encode("utf-8")).hexdigest() for id_root in roots_ids]
        score = (arity, main_magnet, " ".join(sorted(root_magnets)))
        scored.append((score, inbound))
    return scored


def fix_cobound(graph: nx.Graph, cobound_edge, id_virtual_a: str, id_virtual_b: str) -> bool:
    u, v, k = cobound_edge
    data = dict(_edge_data(graph, u, v, k))
    fingerprint = data.get("meta", {}).get("magnet")
    floor_virtual = int(graph.nodes[u]["meta"].get("floor")) + 1

    _remove_edge(graph, cobound_edge)

    graph.add_node(id_virtual_a, label="", magnet=fingerprint, meta={"is_mirror": False, "is_virtual": True, "floor": floor_virtual})
    graph.add_node(id_virtual_b, label="", magnet=fingerprint, meta={"is_mirror": False, "is_virtual": True, "floor": floor_virtual})

    graph.graph.setdefault("floors", {}).setdefault(floor_virtual, []).extend([id_virtual_a, id_virtual_b])

    edge_a = dict(data)
    edge_a["edge_id"] = f"*{data.get('edge_id')}_a"
    edge_b = dict(data)
    edge_b["edge_id"] = f"*{data.get('edge_id')}_b"

    _add_edge(graph, u, id_virtual_a, edge_a)
    _add_edge(graph, id_virtual_b, v, edge_b)
    return True


def include_graph(graph: nx.Graph, subgraph: nx.Graph, suffix: str):
    new_to_old = {}
    old_to_new = {}

    for id_node, data in subgraph.nodes(data=True):
        new_id = f"{id_node}@{suffix}"
        while new_id in graph.nodes:
            random_id = new_id + str(random.random())
            new_id = f"{id_node}@{suffix}-{hashlib.md5(random_id.encode('utf-8')).hexdigest()}"
        new_to_old[new_id] = id_node
        old_to_new[id_node] = new_id
        graph.add_node(new_id, **copy.deepcopy(data))

    for u, v, k, data in _iter_edges(subgraph):
        new_u = old_to_new[u]
        new_v = old_to_new[v]
        new_data = copy.deepcopy(data)
        new_data["edge_id"] = f"{new_data.get('edge_id')}@{suffix}"
        _add_edge(graph, new_u, new_v, new_data)

    return old_to_new


def switch_edge(graph: nx.Graph, edge, id_node_old, id_node_new) -> bool:
    u, v, k = edge
    data = dict(_edge_data(graph, u, v, k))
    if u == id_node_old:
        new_u, new_v = id_node_new, v
    elif v == id_node_old:
        new_u, new_v = u, id_node_new
    else:
        return False
    _remove_edge(graph, edge)
    _add_edge(graph, new_u, new_v, data)
    return True


def fix_inbound(graph: nx.Graph, inbound, id_mirror: str, scoring=def_tree_fn("$lexic"), mode: str = "duplicate") -> bool:
    floor, id_node, id_edges = inbound
    arity = len(id_edges)
    node_data = graph.nodes[id_node]
    floor_mirror = floor
    floor_sub = floor_mirror + 1
    floor_roots = floor_mirror - 1

    outgoing_edges = []
    for edge in list(graph.edges(id_node, keys=True, data=True)) if graph.is_multigraph() else list(graph.edges(id_node, data=True)):
        if graph.is_multigraph():
            u, v, k, data = edge
        else:
            u, v, data = edge
            k = None
        other = v if u == id_node else u
        if int(graph.nodes[other]["meta"].get("floor")) > int(graph.nodes[id_node]["meta"].get("floor")):
            outgoing_edges.append((u, v, k))

    roots_nodes = [node_id for node_id in graph.nodes if graph.nodes[node_id]["meta"].get("floor") <= floor_roots]
    magnet = get_magnet(graph, id_node)

    if mode == "duplicate":
        subtree = to_tree(copy.deepcopy(graph), id_root=id_node, ids_ignore=roots_nodes)
        ids_children = [child_id for (child_id, _) in subtree.enumerate_nodes()]
        ids_to_ignore = [node_id for node_id in graph.nodes if node_id not in ids_children]
        subdag = to_dag(copy.deepcopy(graph), id_root=id_node, ids_ignore=ids_to_ignore)

        for id_descendant in ids_children:
            subdag.nodes[id_descendant]["meta"]["floor"] = subdag.nodes[id_descendant]["meta"]["floor"] + floor_sub

        for i, edge in enumerate(id_edges):
            u, v, k = edge
            other = v if u == id_node else u
            id_n_mirror = f"{id_mirror}_{i}"
            graph.add_node(
                id_n_mirror,
                label=".",
                arity=arity,
                magnet=magnet,
                meta={"is_mirror": True, "is_virtual": False, "floor": floor_mirror},
            )
            switch_edge(graph, edge, id_node, id_n_mirror)
            translating = include_graph(graph, copy.deepcopy(subdag), id_n_mirror)
            root_id = translating[subtree.root]
            _add_edge(graph, id_n_mirror, root_id, {"edge_id": f"e{id_n_mirror}", "modality": "1", "meta": {}})
    else:
        roots_candidates = []
        for i, edge in enumerate(id_edges):
            u, v, k = edge
            other = v if u == id_node else u
            id_n_mirror = f"{id_mirror}_{i}"
            graph.add_node(
                id_n_mirror,
                label=node_data.get("label", str(id_node)),
                arity=arity,
                magnet=magnet,
                meta={"is_mirror": True, "is_virtual": False, "floor": floor_mirror},
            )
            switch_edge(graph, edge, id_node, id_n_mirror)
            associated_candidate = to_tree(copy.deepcopy(graph), other, ids_ignore=roots_nodes)
            associated_candidate.score_tree(scoring)
            roots_candidates.append((associated_candidate.meta.get("score"), other, id_n_mirror))

        roots_candidates.sort()
        for outgoing_edge in outgoing_edges:
            main_root = roots_candidates[0]
            switch_edge(graph, outgoing_edge, id_node, main_root[2])

        graph.remove_node(id_node)

    return True


def _edge_repr(edge):
    u, v, k = edge
    if str(u) > str(v):
        u, v = v, u
    if k is None:
        return [u, v]
    return [u, v, k]


def _inbound_repr(inbound):
    floor, id_node, id_edges = inbound
    edge_reprs = [_edge_repr(edge) for edge in id_edges]
    edge_reprs.sort()
    return [floor, id_node, edge_reprs]


def _count_special_nodes(graph: nx.Graph) -> tuple:
    virtuals = 0
    mirrors = 0
    for node in graph.nodes:
        meta = graph.nodes[node].get("meta", {})
        if meta.get("is_virtual"):
            virtuals += 1
        if meta.get("is_mirror"):
            mirrors += 1
    return virtuals, mirrors


def to_dag(graph: nx.Graph, id_root: str, branch_rule: str = "$root.label > $depth > $lexic", ids_ignore: List = None, compact_form=False, allow_hashes=True) -> nx.Graph:
    graph = normalize_graph(graph)
    if ids_ignore is None:
        ids_ignore = []

    for id_node in list(graph.nodes):
        if id_node in ids_ignore:
            graph.remove_node(id_node)

    reset_floor(graph)
    floors = group_by_floor(graph, id_root)
    graph.graph["floors"] = floors

    for id_node in list(graph.nodes):
        if "floor" not in graph.nodes[id_node].get("meta", {}):
            graph.remove_node(id_node)

    cobounds_nb = len(find_cobounds(graph))
    inbounds_nb = len(find_inbounds(graph))
    edit_nb = cobounds_nb + inbounds_nb

    id_virtual = 0
    id_mirror = 1
    ordering_fn = def_tree_fn(branch_rule)
    mode = "elect" if compact_form else "duplicate"

    for _ in range(0, edit_nb):
        cobounds_by, cobound_floors = cobounds_by_floor(graph)
        inbounds_by, inbound_floors = inbounds_by_floor(graph)
        floors = sorted(set(inbound_floors).union(cobound_floors), reverse=True)
        if not floors:
            break
        floor = floors[0]

        if floor in cobounds_by:
            scored_cobounds = score_cobounds(graph, cobounds_by[floor], allow_hashes=allow_hashes)
            scored_cobounds = sorted(scored_cobounds, key=lambda entry: _edge_repr(entry[1]))
            scored_cobounds = sorted(scored_cobounds, key=lambda entry: entry[0], reverse=True)
            emit(
                "dag_cobound_scores",
                floor=floor,
                scores=[(score, _edge_repr(edge)) for score, edge in scored_cobounds[:5]],
            )
            score, cobound = scored_cobounds[0]
            emit("dag_choice", floor=floor, type="cobound", score=score, choice=_edge_repr(cobound))
            fix_cobound(graph, cobound, f"*{id_virtual}", f"*{id_virtual + 1}")
            id_virtual += 2
        else:
            scored_inbounds = score_inbounds(graph, inbounds_by[floor])
            scored_inbounds = sorted(scored_inbounds, key=lambda entry: _inbound_repr(entry[1]))
            scored_inbounds = sorted(scored_inbounds, key=lambda entry: entry[0], reverse=True)
            emit(
                "dag_inbound_scores",
                floor=floor,
                scores=[(score, _inbound_repr(inbound)) for score, inbound in scored_inbounds[:5]],
            )
            score, inbound = scored_inbounds[0]
            emit("dag_choice", floor=floor, type="inbound", score=score, choice=_inbound_repr(inbound))
            fix_inbound(graph, inbound, f"#{id_mirror}", scoring=ordering_fn, mode=mode)
            id_mirror += 1

        virtuals, mirrors = _count_special_nodes(graph)
        emit(
            "dag_counts",
            nodes=graph.number_of_nodes(),
            edges=graph.number_of_edges(),
            virtuals=virtuals,
            mirrors=mirrors,
        )

    return graph


def to_tree(graph: nx.Graph, id_root: str, id_origin: str = None, modality_origin: str = None, ids_ignore: List[str] = None) -> Tree:
    if ids_ignore is None:
        ids_ignore = []
    trace(
        "building a tree rooted on %s (lvl %s), initiated by %s" % (
            id_root,
            str(graph.nodes[id_root]["meta"].get("floor")),
            id_origin,
        ),
        3,
    )

    if graph.degree[id_root] == 1 and id_origin is not None:
        return Tree(graph, id_root, None, modality_origin)

    ids_ignore = list(set(ids_ignore + [id_origin] if id_origin is not None else ids_ignore))
    children = []
    for edge in list(graph.edges(id_root, keys=True, data=True)) if graph.is_multigraph() else list(graph.edges(id_root, data=True)):
        if graph.is_multigraph():
            u, v, k, data = edge
        else:
            u, v, data = edge
            k = None
        other = v if u == id_root else u
        if other == id_origin or other in ids_ignore:
            continue
        child = to_tree(graph, id_root=other, id_origin=id_root, modality_origin=data.get("modality"), ids_ignore=ids_ignore)
        children.append((child, data.get("modality")))

    return Tree(graph, id_root, children, modality_origin)


def split_connex_compounds(graph: nx.Graph):
    components = list(nx.connected_components(graph))
    if len(components) <= 1:
        return [graph]
    sub_graphs = []
    for comp in components:
        sub_graphs.append(graph.subgraph(comp).copy())
    return sub_graphs


def evaluate_bounds(graph: nx.Graph, id_node):
    graph_copy = normalize_graph(graph)
    reset_floor(graph_copy)
    group_by_floor(graph_copy, id_node)
    return (len(find_inbounds(graph_copy)), len(find_cobounds(graph_copy)))
