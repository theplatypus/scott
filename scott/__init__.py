"""Scott API shim with selectable backend."""

from ._backend import resolve_backend
from . import canonize
from . import parse
from . import graph

__all__ = ["canonize", "parse", "graph"]

backend_name, backend_module = resolve_backend()
if backend_name == "py":
	structs = backend_module.structs
	utils = backend_module.utils
	__all__.extend(["structs", "utils"])
