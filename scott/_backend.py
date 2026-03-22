"""Backend resolution: Rust (default) or legacy pure-Python."""

import os


def resolve_backend():
	name = os.getenv("SCOTT_BACKEND", "").strip().lower()

	if name in ("legacy", "py", "scott-legacy", "scott_legacy"):
		import scott_legacy as legacy
		return "py", legacy

	if name in ("rs", "rust", "", "auto"):
		try:
			from . import _scott
			return "rs", _scott
		except ImportError:
			if name in ("rs", "rust"):
				raise
			raise ImportError(
				"The scott Rust extension (_scott) is not available. "
				"Build it with: maturin develop --release\n"
				"Or use the pure-Python fallback: SCOTT_BACKEND=legacy"
			)

	raise ImportError("unknown backend '%s'" % name)
