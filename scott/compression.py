"""
	Compression module
	===================
	
	Translations between fetchable and space-efficient graph representations.
"""

from .structs.graph import Graph
from .structs.cgraph import CGraph

def flatten(graph: Graph) -> CGraph:
	pass

def deflate(cgraph: CGraph) -> Graph:
	pass
