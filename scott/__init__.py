"""Scott — graph canonization with selectable backend."""

from . import canonize
from . import parse
from . import graph
from . import structs

try:
	from importlib.metadata import version, PackageNotFoundError
	try:
		__version__ = version("scott")
	except PackageNotFoundError:
		import re as _re, pathlib as _pathlib
		_cargo = _pathlib.Path(__file__).parent.parent / "Cargo.toml"
		_m = _re.search(r'^version\s*=\s*"([^"]+)"', _cargo.read_text(), _re.MULTILINE)
		__version__ = _m.group(1) if _m else "unknown"
except Exception:
	__version__ = "unknown"

__all__ = ["canonize", "parse", "graph", "structs", "__version__"]
