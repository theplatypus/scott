import io

from ._backend import resolve_backend
from .graph import Graph


def from_dot(dot_content=None, file_path=None):
	backend, module = resolve_backend()
	if backend == "py":
		return module.parse.from_dot(dot_content=dot_content, file_path=file_path)
	if backend == "nx":
		if file_path is None and dot_content is None:
			raise ValueError("dot_content or file_path is required")
		try:
			import networkx as nx
		except Exception as exc:
			raise ImportError("networkx is required for scott-nx: %s" % exc)
		if file_path is not None:
			graph = nx.Graph(nx.nx_pydot.read_dot(file_path))
		else:
			buffer = io.StringIO(dot_content)
			graph = nx.Graph(nx.nx_pydot.read_dot(buffer))
		return [graph]
	if backend == "rs":
		if file_path is not None:
			graph = module.parse_dot(file_path)
		elif dot_content is not None:
			graph = module.parse_dot_string(dot_content)
		else:
			raise ValueError("dot_content or file_path is required")
		return [Graph(graph)]
	
	raise ImportError("unknown backend '%s'" % backend)


def from_graph6(graph6_content=None, file_path=None):
	raise NotImplementedError("graph6 parsing not implemented in Rust yet")
