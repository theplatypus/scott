#!/usr/bin/env python3
"""Compatibility wrapper for the unified test runner."""

import os
import sys

TEST_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(TEST_DIR)
for path in (TEST_DIR, REPO_ROOT):
	if path not in sys.path:
		sys.path.insert(0, path)

from cli import test_runner


if __name__ == "__main__":
	backend = os.getenv("SCOTT_BACKEND", "py").strip().lower()
	engine = "py"
	if backend in ("nx", "scott-nx", "scott_nx"):
		engine = "nx"
	elif backend in ("rs", "rust"):
		engine = "rs"
	args = ["validity", "--engine", engine] + sys.argv[1:]
	raise SystemExit(test_runner.main(args))
