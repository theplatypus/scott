#!/usr/bin/env python3
"""Compatibility wrapper for the unified test runner."""

import os
import sys

import test_runner


if __name__ == "__main__":
	backend = os.getenv("SCOTT_BACKEND", "py").strip().lower()
	engine = "py"
	if backend in ("nx", "scott-nx", "scott_nx"):
		engine = "nx"
	elif backend in ("rs", "rust"):
		engine = "rs"
	args = ["cfi-rigid", "--engine", engine] + sys.argv[1:]
	raise SystemExit(test_runner.main(args))
