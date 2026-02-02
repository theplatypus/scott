#!/usr/bin/env python3
"""Run isomorphism checks on cfi-rigid-t2-dot graphs."""

import argparse
import os
import re
import sys

import scott as st

DOT_DIR = os.path.join("data", "isotest", "cfi-rigid-t2-dot")
DOT_RE = re.compile(r"cfi-rigid-t2-(\d+)-(\d+)-(\d+)\.dot$")


def load_entries(dot_dir):
    entries = []
    for name in os.listdir(dot_dir):
        match = DOT_RE.match(name)
        if not match:
            continue
        size = int(match.group(1))
        group = int(match.group(2))
        variant = int(match.group(3))
        entries.append((size, group, variant, os.path.join(dot_dir, name)))
    entries.sort()
    return entries


def canon_trace(path):
    graph = st.parse.from_dot(file_path=path)[0]
    return str(st.canonize.to_cgraph(graph))


def main():
    parser = argparse.ArgumentParser(
        description="Check isomorphism pairs in cfi-rigid-t2-dot datasets."
    )
    parser.add_argument(
        "-n",
        type=int,
        default=None,
        help="Stop after processing graphs with |V| greater than n.",
    )
    args = parser.parse_args()

    if not os.path.isdir(DOT_DIR):
        print("Missing data directory: %s" % DOT_DIR, file=sys.stderr)
        return 2

    entries = load_entries(DOT_DIR)
    if not entries:
        print("No .dot files found in %s" % DOT_DIR, file=sys.stderr)
        return 2

    pairs = {}
    for size, group, variant, path in entries:
        if args.n is not None and size > args.n:
            break
        key = (size, group)
        pairs.setdefault(key, {})[variant] = path

    total = 0
    mismatches = 0

    for (size, group), variants in sorted(pairs.items()):
        if 1 not in variants or 2 not in variants:
            print("Skipping incomplete pair for size %d group %02d" % (size, group))
            continue
        total += 1
        path_a = variants[1]
        path_b = variants[2]
        trace_a = canon_trace(path_a)
        trace_b = canon_trace(path_b)
        if trace_a != trace_b:
            mismatches += 1
            print("Mismatch: size %d group %02d" % (size, group))
            print("  %s" % path_a)
            print("  %s" % path_b)

    print("Checked %d pair(s); %d mismatch(es)." % (total, mismatches))
    return 1 if mismatches else 0


if __name__ == "__main__":
    raise SystemExit(main())
