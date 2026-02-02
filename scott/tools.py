"""Developer command entrypoints."""

import subprocess


def _run(cmd):
	result = subprocess.run(cmd)
	return result.returncode


def test():
	return _run(["pytest", "-v"])


def unit():
	return _run(["pytest", "-v", "-m", "unit"])


def canonization():
	return _run(["pytest", "-v", "-m", "canonization"])


def lint():
	return _run(["ruff", "check", "."])


def format():
	return _run(["ruff", "format", "."])
