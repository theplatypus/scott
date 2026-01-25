import hashlib
import re
from typing import Callable, List, Tuple

TreeScoring = Callable[["Tree"], Tuple]

verbose = False


def trace(msg, indent=1, f=" "):
    if verbose:
        print("[tree.py]" + f + indent * "\t" + msg)


def def_tree_fn(rule: str = "$depth > $lexic") -> TreeScoring:
    args = [arg.strip() for arg in rule.split(">")]
    return lambda tree: tuple([tree.__eval__(str(arg)) for arg in args])


attributes_definitions = {
    "$depth": "tree.depth()",
    "$size": "len(tree.enumerate_nodes())",
    "$lexic": "str(tree)",
    "$root": "tree.root",
}


def hashex(string):
    return hashlib.sha224(string.encode()).hexdigest()


class Tree:
    def __init__(self, graph, root_id, children: List["Tree"], parent_modality: str):
        self.graph = graph
        self.root = root_id
        self.children = children
        self.parent_modality = parent_modality
        self.meta = {}

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        if "trace" in self.meta:
            return self.meta["trace"]

        lbl = self._get_label()
        if self.is_leaf():
            self.meta["trace"] = lbl
            return lbl
        if not self.is_scored():
            raise Exception("Tree is not scored")
        trace = "(" + ", ".join(
            [str(branch) + ":" + str(modality) for (branch, modality) in sorted(self.children, key=lambda child: child[0].meta["score"])]
        ) + ")" + lbl
        self.meta["trace"] = trace
        return trace

    def __eval__(self, arg: str):
        tree = self
        arg = arg.replace("$root.label", "tree.graph.nodes[tree.root].get('label')")
        defs = re.findall(r"\$\w*", arg)
        for definition in defs:
            definition = str(definition)
            if definition in attributes_definitions:
                formal_def = attributes_definitions[definition]
                arg = arg.replace(definition, formal_def)
            else:
                raise AttributeError("Unknown Attribute definition : " + definition)

        return eval(arg)

    def _get_label(self):
        data = self.graph.nodes[self.root]
        meta = data.get("meta", {})
        label = data.get("label", str(self.root))
        if meta.get("is_mirror"):
            return label + "#" + str(data.get("arity")) + "{" + str(data.get("magnet")) + "}"
        if meta.get("is_virtual"):
            return label + "*{" + str(data.get("magnet")) + "}"
        return label

    def hashtree(self):
        return hashlib.sha224(str(self).encode()).hexdigest()

    def get_order_sequence(self, prop=None):
        self.score_tree()
        lbl = self.root if prop is None else self.graph.nodes[self.root].get("meta", {}).get(prop)
        if self.is_leaf():
            return lbl
        seq = [
            lbl,
            [branch.get_order_sequence(prop) for (branch, modality) in sorted(self.children, key=lambda child: child[0].meta["score"])],
        ]
        return seq

    def map_node(self, node_fn=hashex):
        def filt(i):
            if "@" in i:
                l = i[: i.index("@")] 
                return l if ("#" not in l and "*" not in l) else None
            if "#" not in i and "*" not in i:
                return i
            return None

        def flatten(l):
            return flatten(l[0]) + (flatten(l[1:]) if len(l) > 1 else []) if type(l) is list else [l]

        mapping = {self.root: node_fn(self)}

        if not self.is_leaf():
            submaps = [branch.map_node(node_fn) for (branch, modality) in self.children]
            for submap in submaps:
                for id_node in submap:
                    id_node_sanitized = filt(str(id_node))
                    if id_node_sanitized:
                        if id_node_sanitized in mapping:
                            mapping[id_node_sanitized] = sorted(flatten([mapping[id_node_sanitized]] + [submap[id_node]]))
                        else:
                            mapping[id_node_sanitized] = submap[id_node]

        for k in mapping:
            mapping[k] = str(mapping[k])

        return mapping

    def is_scored(self) -> bool:
        return not False in ["score" in child.meta for (child, modality) in self.children]

    def is_leaf(self) -> bool:
        return self.children is None

    def depth(self) -> int:
        if self.is_leaf():
            return 1
        return 1 + max([0] + [child.depth() for (child, modality) in self.children])

    def enumerate_nodes(self, depth_max: int = -1, current_depth: int = 0):
        enum = [(self.root, current_depth)]
        if not self.is_leaf() and depth_max != 0:
            depth_max -= 1
            for (child, modality) in self.children:
                enum += child.enumerate_nodes(depth_max, current_depth + 1)
        return enum

    def score_tree(self, fn: TreeScoring = def_tree_fn()) -> bool:
        if self.is_leaf():
            self.meta["score"] = fn(self)
            trace("score[ " + str(self) + " ] = " + str(fn(self)), 3)
            return True
        statuses = []
        for (child, modality) in self.children:
            statuses.append(child.score_tree(fn))
        self.meta["score"] = fn(self)
        trace("score[ " + str(self) + " ] = " + str(fn(self)), 3)
        return not False in statuses
