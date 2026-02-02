#!/usr/bin/env python3
"""Shared test helpers for Scott variants."""

import contextlib
import csv
import difflib
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import time

DOT_DIR = os.path.join("data", "isotest", "cfi-rigid-t2-dot")
DOT_RE = re.compile(r"cfi-rigid-t2-(\d+)-(\d+)-(\d+)\.dot$")
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(REPO_ROOT, "results")


class EngineError(Exception):
	pass


def ensure_results_dir():
	os.makedirs(RESULTS_DIR, exist_ok=True)


def resolve_engine(engine):
	engine = (engine or "").strip().lower()
	if engine in ("py", "legacy", "scott-legacy", "scott_legacy"):
		return "py"
	if engine in ("nx", "scott-nx", "scott_nx"):
		return "nx"
	if engine in ("rs", "rust"):
		return "rs"
	raise EngineError("unknown engine: %s" % engine)


def load_scott_nx():
	module_name = "scott_nx"
	if module_name in sys.modules:
		return sys.modules[module_name]
	module_path = os.path.join(REPO_ROOT, "scott-nx", "__init__.py")
	if not os.path.isfile(module_path):
		raise EngineError("missing scott-nx package at %s" % module_path)
	module_dir = os.path.dirname(module_path)
	spec = importlib.util.spec_from_file_location(
		module_name,
		module_path,
		submodule_search_locations=[module_dir],
	)
	if spec is None or spec.loader is None:
		raise EngineError("failed to load scott-nx module")
	module = importlib.util.module_from_spec(spec)
	sys.modules[module_name] = module
	spec.loader.exec_module(module)
	return module


def load_engine(engine):
	engine = resolve_engine(engine)
	if engine == "py":
		import scott_legacy as st

		def parse_graph(path):
			return st.parse.from_dot(file_path=path)[0]

		def to_cgraph(graph):
			return str(st.canonize.to_cgraph(graph))

		def count_nodes_edges(graph):
			return len(graph.V), len(graph.E)

		return {
			"name": "py",
			"parse_graph": parse_graph,
			"to_cgraph": to_cgraph,
			"count_nodes_edges": count_nodes_edges,
		}

	if engine == "nx":
		try:
			import networkx as nx
		except Exception as exc:
			raise EngineError("networkx is required for scott-nx: %s" % exc)
		module = load_scott_nx()

		def parse_graph(path):
			return nx.Graph(nx.nx_pydot.read_dot(path))

		def to_cgraph(graph):
			return str(module.to_cgraph(graph))

		def count_nodes_edges(graph):
			return graph.number_of_nodes(), graph.number_of_edges()

		return {
			"name": "nx",
			"parse_graph": parse_graph,
			"to_cgraph": to_cgraph,
			"count_nodes_edges": count_nodes_edges,
		}

	raise EngineError("unsupported engine: %s" % engine)


def load_entries(dot_dir):
	entries = []
	for name in os.listdir(dot_dir):
		match = DOT_RE.match(name)
		if not match:
			continue
		size_str, group_str, variant_str = match.groups()
		entries.append(
			(
				int(size_str),
				int(group_str),
				int(variant_str),
				size_str,
				group_str,
				variant_str,
				os.path.join(dot_dir, name),
			)
		)
	entries.sort(key=lambda row: (row[0], row[1], row[2]))
	return entries


def run_validity_py(engine):
	engine = load_engine(engine)
	pairs = [
		(
			os.path.join(DOT_DIR, "cfi-rigid-t2-0020-01-1.dot"),
			os.path.join(DOT_DIR, "cfi-rigid-t2-0020-01-2.dot"),
			True,
		),
		(
			os.path.join(DOT_DIR, "cfi-rigid-t2-0020-02-1.dot"),
			os.path.join(DOT_DIR, "cfi-rigid-t2-0020-02-2.dot"),
			True,
		),
		(
			os.path.join(DOT_DIR, "cfi-rigid-t2-0020-01-2.dot"),
			os.path.join(DOT_DIR, "cfi-rigid-t2-0020-02-1.dot"),
			False,
		),
	]
	failed = 0
	for left, right, expected in pairs:
		g_left = engine["parse_graph"](left)
		g_right = engine["parse_graph"](right)
		c_left = engine["to_cgraph"](g_left)
		c_right = engine["to_cgraph"](g_right)
		matched = c_left == c_right
		status = "OK" if matched == expected else "FAIL"
		print("%s: %s vs %s" % (status, left, right))
		if matched != expected:
			failed += 1
	print("Validity checks: %d failure(s)." % failed)
	return failed == 0


def run_validity_rs(release=False):
	cmd = ["cargo", "run", "--quiet", "--bin", "test_isomorphism", "--"]
	if release:
		cmd.insert(2, "--release")
	result = subprocess.run(cmd)
	return result.returncode == 0


def run_cfi_rigid_py(engine, max_n=None, out_path=None):
	engine = load_engine(engine)
	ensure_results_dir()
	if out_path is None:
		out_path = os.path.join(RESULTS_DIR, "results_cfi-rigid-%s.csv" % engine["name"])

	if not os.path.isdir(DOT_DIR):
		raise EngineError("Missing data directory: %s" % DOT_DIR)

	entries = load_entries(DOT_DIR)
	if not entries:
		raise EngineError("No .dot files found in %s" % DOT_DIR)

	pairs = {}
	rows = []
	processed = 0
	for size_int, group_int, variant_int, size_str, group_str, variant_str, path in entries:
		if max_n is not None and size_int > max_n:
			break

		graph = engine["parse_graph"](path)
		start = time.perf_counter()
		canon = engine["to_cgraph"](graph)
		elapsed = time.perf_counter() - start

		nodes, edges = engine["count_nodes_edges"](graph)
		task_id = "%s-%s" % (size_str, group_str)
		graph_id = "%s.dot" % variant_str

		variants = pairs.setdefault((size_str, group_str), {})
		valid = True
		if variants:
			ref = variants.get(1, {}).get("canon") or variants.get(2, {}).get("canon")
			if ref is not None:
				valid = bool(ref == canon)
		variants[variant_int] = {"canon": canon, "path": path}

		rows.append([
			size_str,
			str(nodes),
			str(edges),
			task_id,
			graph_id,
			str(elapsed),
			str(valid),
			str(len(canon)),
			canon,
		])

		processed += 1
		print(
			"Processed %d: size=%s group=%s variant=%s nodes=%d edges=%d time=%.4f valid=%s"
			% (processed, size_str, group_str, variant_str, nodes, edges, elapsed, valid),
			flush=True,
		)

	total_pairs = 0
	pair_mismatches = 0
	cross_mismatches = 0
	by_size = {}

	for (size_str, group_str), variants in sorted(pairs.items()):
		if 1 not in variants or 2 not in variants:
			print("Skipping incomplete pair for size %s group %s" % (size_str, group_str))
			continue
		total_pairs += 1
		canon_a = variants[1]["canon"]
		canon_b = variants[2]["canon"]
		if canon_a != canon_b:
			pair_mismatches += 1
			print("Mismatch: size %s group %s" % (size_str, group_str))
			print("  %s" % variants[1]["path"])
			print("  %s" % variants[2]["path"])
			continue

		groups = by_size.setdefault(size_str, {})
		for other_group, other_canon in groups.items():
			if canon_a == other_canon:
				cross_mismatches += 1
				print("Collision: size %s groups %s and %s" % (size_str, other_group, group_str))
				print("  %s" % variants[1]["path"])
				print("  %s" % variants[2]["path"])
		groups[group_str] = canon_a

	write_csv(out_path, rows)

	print("Checked %d pair(s); %d mismatch(es)." % (total_pairs, pair_mismatches))
	print("Checked cross-group uniqueness; %d collision(s)." % cross_mismatches)

	return pair_mismatches == 0 and cross_mismatches == 0


def run_cfi_rigid_rs(max_n=None, out_path=None, release=False):
	ensure_results_dir()
	if out_path is None:
		out_path = os.path.join(RESULTS_DIR, "results_cfi-rigid-rs.csv")

	cmd = ["cargo", "run", "--quiet", "--bin", "test_cfi_rigid", "--", "--out", out_path]
	if release:
		cmd.insert(2, "--release")
	if max_n is not None:
		cmd.extend(["-n", str(max_n)])
	result = subprocess.run(cmd)
	return result.returncode == 0


def write_csv(path, rows):
	with open(path, "w", newline="") as handle:
		writer = csv.writer(handle)
		writer.writerow([
			"",
			"problem_size",
			"nodes",
			"edges",
			"task_id",
			"graph",
			"time",
			"valid",
			"res_size",
			"canonization",
		])
		for idx, row in enumerate(rows):
			writer.writerow([idx] + row)


def capture_trace_py(engine, dot_path):
	engine = load_engine(engine)
	previous = os.environ.get("SCOTT_TRACE")
	os.environ["SCOTT_TRACE"] = "1"
	buffer = io.StringIO()
	with contextlib.redirect_stdout(buffer):
		graph = engine["parse_graph"](dot_path)
		canon = engine["to_cgraph"](graph)
	if previous is None:
		os.environ.pop("SCOTT_TRACE", None)
	else:
		os.environ["SCOTT_TRACE"] = previous
	lines = []
	lines.append("TRACE input dot=%s" % json.dumps(dot_path, separators=(",", ":")))
	for line in buffer.getvalue().splitlines():
		if line.startswith("TRACE "):
			lines.append(line)
	lines.append("TRACE result cgraph=%s" % json.dumps(str(canon), separators=(",", ":")))
	return lines


def capture_trace_rs(dot_path, release=False):
	cmd = ["cargo", "run", "--quiet", "--bin", "debug_canonize", "--", dot_path]
	if release:
		cmd.insert(2, "--release")
	result = subprocess.run(cmd, capture_output=True, text=True)
	if result.returncode != 0:
		raise EngineError(result.stderr.strip() or "rust trace failed")
	lines = []
	for line in result.stdout.splitlines():
		if line.startswith("TRACE "):
			lines.append(line)
	return lines


def normalize_trace_line(line):
	line = line.rstrip("\n")
	if not line.startswith("TRACE "):
		return line
	parts = line.split(" ")
	if len(parts) < 2:
		return line
	event = parts[1]
	items = []
	for part in parts[2:]:
		if "=" not in part:
			continue
		key, value = part.split("=", 1)
		try:
			parsed = json.loads(value)
			value = json.dumps(parsed, sort_keys=True, separators=(",", ":"))
		except Exception:
			pass
		items.append((key, value))
	items.sort(key=lambda item: item[0])
	out = "TRACE " + event
	for key, value in items:
		out += " %s=%s" % (key, value)
	return out


def normalize_trace(lines):
	return [normalize_trace_line(line) for line in lines]


def diff_traces(left_lines, right_lines, normalized=True):
	if normalized:
		left_lines = normalize_trace(left_lines)
		right_lines = normalize_trace(right_lines)
	return list(difflib.unified_diff(left_lines, right_lines, lineterm=""))


def compare_traces(left_engine, right_engine, dot_path, release=False, normalized=True):
	left_engine = resolve_engine(left_engine)
	right_engine = resolve_engine(right_engine)

	if left_engine == "rs":
		left_lines = capture_trace_rs(dot_path, release=release)
	else:
		left_lines = capture_trace_py(left_engine, dot_path)

	if right_engine == "rs":
		right_lines = capture_trace_rs(dot_path, release=release)
	else:
		right_lines = capture_trace_py(right_engine, dot_path)

	diff = diff_traces(left_lines, right_lines, normalized=normalized)
	for line in diff:
		print(line)
	return len(diff) == 0
