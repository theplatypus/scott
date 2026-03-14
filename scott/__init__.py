"""Scott API shim with selectable backend."""

from ._backend import resolve_backend
from . import canonize
from . import parse
from . import graph
from . import structs

__all__ = ["canonize", "parse", "graph", "structs"]

backend_name, backend_module = resolve_backend()
if backend_name == "py":
	utils = backend_module.utils
	__all__.append("utils")
