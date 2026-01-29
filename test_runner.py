#!/usr/bin/env python3
"""Unified test entrypoint for Scott variants."""

import argparse
import sys

from test_harness import (
	EngineError,
	compare_traces,
	run_cfi_rigid_py,
	run_cfi_rigid_rs,
	run_validity_py,
	run_validity_rs,
)


def build_parser():
	parser = argparse.ArgumentParser(description="Run Scott test suites.")
	parser.add_argument(
		"--interactive",
		action="store_true",
		help="Run in interactive mode.",
	)

	subparsers = parser.add_subparsers(dest="command")

	validity = subparsers.add_parser("validity", help="Run validity checks.")
	validity.add_argument(
		"--engine",
		default="py",
		help="Engine: py (legacy), nx, rs (default: py).",
	)
	validity.add_argument(
		"--release",
		action="store_true",
		help="Use a release build for Rust.",
	)

	cfi = subparsers.add_parser("cfi-rigid", help="Run cfi-rigid benchmark.")
	cfi.add_argument(
		"--engine",
		default="py",
		help="Engine: py (legacy), nx, rs (default: py).",
	)
	cfi.add_argument(
		"-n",
		type=int,
		default=None,
		help="Stop after processing graphs with |V| greater than n.",
	)
	cfi.add_argument(
		"--out",
		default=None,
		help="Output CSV path (default: results/results_cfi-rigid-<engine>.csv).",
	)
	cfi.add_argument(
		"--release",
		action="store_true",
		help="Use a release build for Rust.",
	)

	traces = subparsers.add_parser("compare-traces", help="Compare trace output.")
	traces.add_argument("--left", required=True, help="Left engine: py, nx, rs.")
	traces.add_argument("--right", required=True, help="Right engine: py, nx, rs.")
	traces.add_argument("--dot", required=True, help="DOT file path to compare.")
	traces.add_argument(
		"--raw",
		action="store_true",
		help="Show raw diff (no normalization).",
	)
	traces.add_argument(
		"--release",
		action="store_true",
		help="Use a release build for Rust.",
	)

	return parser


def run_interactive():
	print("Select a test action:")
	print("  1) validity")
	print("  2) cfi-rigid")
	print("  3) compare-traces")
	print("  4) quit")
	choice = input("Choice: ").strip()
	if choice == "1":
		engine = input("Engine [py|nx|rs] (default: py): ").strip() or "py"
		release = input("Use release build for Rust? [y/N]: ").strip().lower() == "y"
		return run_validity(engine, release)
	if choice == "2":
		engine = input("Engine [py|nx|rs] (default: py): ").strip() or "py"
		limit = input("Max |V| (blank for all): ").strip()
		max_n = int(limit) if limit else None
		out_path = input("Output CSV (blank for default): ").strip() or None
		release = input("Use release build for Rust? [y/N]: ").strip().lower() == "y"
		return run_cfi_rigid(engine, max_n, out_path, release)
	if choice == "3":
		left = input("Left engine [py|nx|rs]: ").strip()
		right = input("Right engine [py|nx|rs]: ").strip()
		dot_path = input("DOT file path: ").strip()
		normalized = input("Normalize diff? [Y/n]: ").strip().lower() != "n"
		release = input("Use release build for Rust? [y/N]: ").strip().lower() == "y"
		return run_compare_traces(left, right, dot_path, release, normalized)
	return 0


def run_validity(engine, release):
	try:
		if engine in ("rs", "rust"):
			ok = run_validity_rs(release=release)
		else:
			ok = run_validity_py(engine)
		return 0 if ok else 1
	except EngineError as exc:
		print("Error: %s" % exc, file=sys.stderr)
		return 2


def run_cfi_rigid(engine, max_n, out_path, release):
	try:
		if engine in ("rs", "rust"):
			ok = run_cfi_rigid_rs(max_n=max_n, out_path=out_path, release=release)
		else:
			ok = run_cfi_rigid_py(engine, max_n=max_n, out_path=out_path)
		return 0 if ok else 1
	except EngineError as exc:
		print("Error: %s" % exc, file=sys.stderr)
		return 2


def run_compare_traces(left, right, dot_path, release, normalized):
	try:
		ok = compare_traces(left, right, dot_path, release=release, normalized=normalized)
		return 0 if ok else 1
	except EngineError as exc:
		print("Error: %s" % exc, file=sys.stderr)
		return 2


def main(argv=None):
	parser = build_parser()
	args = parser.parse_args(argv)

	if args.interactive or args.command is None:
		return run_interactive()

	if args.command == "validity":
		return run_validity(args.engine, args.release)
	if args.command == "cfi-rigid":
		return run_cfi_rigid(args.engine, args.n, args.out, args.release)
	if args.command == "compare-traces":
		normalized = not args.raw
		return run_compare_traces(args.left, args.right, args.dot, args.release, normalized)

	return 0


if __name__ == "__main__":
	raise SystemExit(main())
