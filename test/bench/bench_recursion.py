import time
from scott.structs.graph import Graph
from scott.structs.node import Node
from scott.structs.edge import Edge


def build_chain(size: int) -> Graph:
    g = Graph()
    for i in range(size):
        g.add_node(Node(str(i), 'N'))
    for i in range(size - 1):
        g.add_edge(Edge(str(i), g.V[str(i)], g.V[str(i + 1)]))
    return g


def benchmark(size: int = 300):
    g = build_chain(size)
    start = time.perf_counter()
    t_rec = g.to_tree_recursive('0')
    rec_time = time.perf_counter() - start

    start = time.perf_counter()
    t_iter = g.to_tree('0')
    iter_time = time.perf_counter() - start

    start = time.perf_counter()
    t_rec.enumerate_nodes_recursive()
    enum_rec_time = time.perf_counter() - start

    start = time.perf_counter()
    t_iter.enumerate_nodes()
    enum_iter_time = time.perf_counter() - start

    start = time.perf_counter()
    t_rec.score_tree_recursive()
    score_rec_time = time.perf_counter() - start

    start = time.perf_counter()
    t_iter.score_tree()
    score_iter_time = time.perf_counter() - start

    print("to_tree recursive:", rec_time)
    print("to_tree iterative:", iter_time)
    print("enumerate_nodes recursive:", enum_rec_time)
    print("enumerate_nodes iterative:", enum_iter_time)
    print("score_tree recursive:", score_rec_time)
    print("score_tree iterative:", score_iter_time)


if __name__ == '__main__':
    benchmark()
