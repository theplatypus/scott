#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
	echo "usage: ./compare_traces.sh <dot-path>"
	exit 1
fi

dot_path="$1"
py_trace="$(mktemp)"
rs_trace="$(mktemp)"
py_norm="$(mktemp)"
rs_norm="$(mktemp)"

echo "== python =="
SCOTT_TRACE=1 python3 - "$dot_path" >"$py_trace" <<'PY'
import sys
import json
import networkx as nx
from nx_scott_direct import to_cgraph

dot_path = sys.argv[1]
graph = nx.Graph(nx.nx_pydot.read_dot(dot_path))
print(f"TRACE input dot={json.dumps(dot_path, separators=(',', ':'))}")
print(f"TRACE result cgraph={json.dumps(str(to_cgraph(graph)), separators=(',', ':'))}")
PY

# cat "$py_trace"

echo "== rust =="
cargo run --bin debug_canonize -- "$dot_path" >"$rs_trace"

python3 - "$py_trace" "$py_norm" <<'PY'
import json
import sys

src = sys.argv[1]
dst = sys.argv[2]

def normalize_line(line: str) -> str:
	line = line.rstrip("\n")
	if not line.startswith("TRACE "):
		return line
	parts = line.split(" ")
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
		out += f" {key}={value}"
	return out

with open(src, "r", encoding="utf-8") as handle:
	lines = handle.readlines()

with open(dst, "w", encoding="utf-8") as handle:
	for line in lines:
		handle.write(normalize_line(line) + "\n")
PY

python3 - "$rs_trace" "$rs_norm" <<'PY'
import json
import sys

src = sys.argv[1]
dst = sys.argv[2]

def normalize_line(line: str) -> str:
	line = line.rstrip("\n")
	if not line.startswith("TRACE "):
		return line
	parts = line.split(" ")
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
		out += f" {key}={value}"
	return out

with open(src, "r", encoding="utf-8") as handle:
	lines = handle.readlines()

with open(dst, "w", encoding="utf-8") as handle:
	for line in lines:
		handle.write(normalize_line(line) + "\n")
PY

# cat "$rs_trace"

echo "== diff (normalized) =="
set +e
diff -u "$py_norm" "$rs_norm"
diff_status=$?
set -e

if [[ $diff_status -eq 0 ]]; then
	echo "traces match"
fi

echo "== diff (raw) =="
set +e
diff -u "$py_trace" "$rs_trace"
set -e

echo "== result diff =="
py_result="$(rg '^TRACE result ' "$py_trace" || true)"
rs_result="$(rg '^TRACE result ' "$rs_trace" || true)"
if [[ -n "$py_result" || -n "$rs_result" ]]; then
	printf "%s\n" "$py_result" >"$py_trace.result"
	printf "%s\n" "$rs_result" >"$rs_trace.result"
	set +e
	diff -u "$py_trace.result" "$rs_trace.result"
	set -e
	rm -f "$py_trace.result" "$rs_trace.result"
else
	echo "no TRACE result lines found"
fi

rm -f "$py_trace" "$rs_trace"
rm -f "$py_norm" "$rs_norm"
