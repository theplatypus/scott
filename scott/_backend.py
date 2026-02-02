import importlib.util
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_scott_nx():
	module_name = "scott_nx"
	if module_name in sys.modules:
		return sys.modules[module_name]
	module_path = os.path.join(REPO_ROOT, "scott-nx", "__init__.py")
	if not os.path.isfile(module_path):
		raise ImportError("missing scott-nx package at %s" % module_path)
	module_dir = os.path.dirname(module_path)
	spec = importlib.util.spec_from_file_location(
		module_name,
		module_path,
		submodule_search_locations=[module_dir],
	)
	if spec is None or spec.loader is None:
		raise ImportError("failed to load scott-nx module")
	module = importlib.util.module_from_spec(spec)
	sys.modules[module_name] = module
	spec.loader.exec_module(module)
	return module


def resolve_backend():
	name = os.getenv("SCOTT_BACKEND", "legacy").strip().lower()
	if name in ("legacy", "py", "scott-legacy", "scott_legacy"):
		import scott_legacy as legacy
		return "py", legacy
	if name in ("nx", "scott-nx", "scott_nx"):
		module = _load_scott_nx()
		return "nx", module
	if name in ("rs", "rust"):
		from . import _scott
		return "rs", _scott
	raise ImportError("unknown backend '%s'" % name)
