
# Scott Rust Port & PyO3 Binding Plan

## Goals
- Reimplement the core canonization/isomorphism algorithm in Rust for speed and stack safety (non-recursive where feasible).
- Expose a Python API comparable to existing `scott` usage via PyO3 (ideally drop-in).
- Maintain behavioural parity with current Python implementations (`scott/`, `nx_scott_direct/`) verified by existing test scripts.

## Context Snapshot
- Current Rust crate exists but core logic is unimplemented; `src/bin` programs are TDD examples and expected to fail until core lands.
- Python reference implementations live in `scott/` (core) and `nx_scott_direct/` (networkx adaptation); data fixtures under `data/`.
- Test drivers of interest: `src/bin/test_graph6.rs`, `src/bin/test.rs`, and `test_isomorphism.py` (uses `scott` Python API).
- Target parity with heuristics used in Python: e.g., `to_cgraph(..., "$degree", "$depth > tree.parent_modality > $lexic", ...)`.

## Constraints & References
- Keep graph I/O compatible with current data under `data/` (graph6, DOT).
- Respect existing ordering heuristics (`$degree`, `$depth > tree.parent_modality > $lexic`, etc.).
- Validate against provided checks: `cargo run --bin test_graph6`, `cargo run --bin test`, `python3 test_isomorphism.py -n 40`.
- Avoid recursion in the Rust core; prefer explicit stacks/queues.

## Phase 0 – Setup & Baseline
- Note: current `src/bin` examples are TDD targets and may fail until core is implemented.
- Ensure Rust toolchain and Cargo build the current crate (`cargo test` smoke; binaries expected to fail until core exists).
- Run Python parity baseline: `python3 test_isomorphism.py -n 30` using existing Python impl to capture expected outputs/timings.
- Document any current failures to avoid regressions attribution confusion.
- Record environment/tool versions (Rust, Python, petgraph, PyO3) to ensure reproducibility.

## Phase 1 – Algorithm Recon
- Read core Python codepaths: `scott/` (graph structures, canonize, fragmentation), `nx_scott_direct/` for networkx adaptation.
- Trace the canonization pipeline end-to-end on a small graph: parse -> internal graph -> canonization -> serialization.
- Identify recursive sections and data dependencies; note required invariants (label ordering, tie-break rules).
- Capture reference outputs for a few fixtures (graph6 sample, two DOT pairs) to use as golden data.
- Sketch the data needed per node (id, label, modality, degree, depth) and per partition/refinement step.
- Note performance hotspots in Python (profiling optional) to target for Rust optimization.

## Phase 2 – Rust Crate Design
- Decide crate layout: core lib (`scott_core` module) plus PyO3 bindings in `src/lib.rs`; bins (`src/bin/`) remain as test drivers.
- Define Rust data structures mirroring Python graph objects (nodes with labels/modalities; edges undirected) on top of `UnGraph`.
- Choose stable ordering for node IDs (likely `String` ids mapped to indices); ensure deterministic iteration.
- Plan feature flags for Python vs pure-Rust builds if needed.
- Define public API for Rust consumers (e.g., `Graph`, `to_cgraph`, `is_isomorphic`) to mirror Python names where sensible.
- Decide error handling strategy (simple `Result<_, String>` vs custom error type) to keep PyO3 mapping straightforward.
- Decide module boundaries: e.g., `graph` (structures/builders), `canonize` (core), `parse` (I/O), `py` (bindings shims).

## Phase 3 – Parsing & I/O (Petgraph-first)
- Lean on `petgraph` for core structures: use `UnGraph` as the primary internal graph store; keep only thin wrappers for labels/modality metadata keyed by `NodeIndex`.
- Use `petgraph::graph6` helpers for graph6 parsing/serialization; avoid custom parsing where possible.
- For DOT: prefer an existing petgraph-compatible parser if feasible; otherwise parse into edge list then build `UnGraph`, keeping parsing minimal to match `parse_dot_file` (ignore attributes beyond node ids/edges unless required).
- Ensure conversions (if any) remain trivial: internal graph == `UnGraph`; provide view helpers for Python bindings and for canonical serialization.
- Add unit/integration tests for loaders using fixtures under `data/isotest/cfi-rigid-t2-dot/` to lock behaviour early.
- Confirm iteration determinism (node insertion order vs sorted ids) to keep canonical output stable.
- Provide helper constructors that mirror Python entrypoints: from graph6 string, from DOT path, from edge list.

## Phase 4 – Canonization Core (Non-Recursive)
- Translate Python canonization algorithm to Rust step-by-step:
  - Vertex partitioning, refinement, and splitting logic.
  - Tree/parent modality handling and lexicographic tie-breaks.
  - Canonical string serialization (match Python output exactly).
- Replace recursion with explicit stack/queue structures; guard against stack overflow.
- Define clear stages: initial partitioning, refinement loop, branching decisions, canonical labeling, serialization.
- Model refinement queues as `VecDeque` (BFS-like) or `Vec` (LIFO) per Python semantics; benchmark later.
- Use petgraph traversal helpers where possible; otherwise maintain adjacency lookups for speed.
- Add invariants via asserts/logging to ease debugging.
- Write focused tests on tiny graphs to confirm ordering decisions.
- Keep a debug mode (feature flag) to dump intermediate partitions/traces to compare with Python.
- Validate canonical output against golden fixtures after each major milestone to catch drift early.

## Phase 5 – Isomorphism Checks
- Implement canonical form comparison as primary iso check; optionally provide wrapper around `petgraph::is_isomorphic_matching` for debugging.
- Ensure equality semantics follow Python (`==` on canonical string).
- Add Rust tests that mirror `src/bin/test.rs` logic but within `#[test]` functions for faster iteration.
- Keep a small set of golden canonical strings (from Phase 1) to spot regressions.

## Phase 6 – Python Bindings (PyO3)
- Expose public API mirroring Python package: modules `parse`, `canonize`, `graph` as needed.
- Map Python inputs (graph6 string, DOT path) to Rust graph builder; return canonical string and graph wrappers.
- Ensure Python package metadata (`pyproject.toml`/`setup.py`) supports building extension (maturin/setuptools-rust).
- Add smoke tests in Python calling the Rust-backed module; align signatures with existing scripts to minimize rewrites.
- Provide a thin compatibility layer so existing `test_isomorphism.py` and `usage*.py` can switch to Rust backend with minimal edits (env var or module alias).
- Document any API differences (if unavoidable) and supply shims to keep current scripts functioning.
- Consider distributing both Rust-only (`cargo install`/crate) and Python wheel builds; ensure build scripts do not fight with existing `setup.py`.
- Provide type hints/docstrings in PyO3 exports for a good Python UX.

## Phase 7 – End-to-End Parity & Benchmarks
- Run provided scripts against Rust core via bins:
  - `cargo run --bin test_graph6`
  - `cargo run --bin test`
  - `python3 test_isomorphism.py -n 40` (via PyO3 bindings)
- Compare canonical strings against golden outputs captured in Phase 1.
- Add criterion or simple timing harness to compare Rust vs Python on representative graphs.
- Track any deviations; decide whether to align behaviour or document differences.
- Capture benchmark numbers in a small table for inclusion in docs/README.

## Phase 8 – Documentation & Packaging
- Update `ReadMe.md`/`docs/` with build/install instructions (Rust only and Python via PyO3).
- Document non-recursive design and any behavioural nuances.
- Add usage examples mirroring `usage.py` and `usage_advanced.py` using the Rust-backed API.
- Describe petgraph reliance and how to extend with other graph formats if needed.
- Provide release checklist (version bump, `maturin build`, wheel publish) and platform notes (manylinux, macOS).
- Note licensing and dependency versions in `LICENSE.md`/README if new crates are added.

## Deliverables & Acceptance
- Rust library implementing canonization/isomorphism core without recursion.
- PyO3 Python package providing drop-in APIs compatible with current scripts.
- Tests passing: `test_graph6.rs`, `test.rs`, `test_isomorphism.py -n 40`.
- Benchmarks demonstrating performance improvement vs Python baseline (qualitative or quantitative).

## Risks / Open Questions
- DOT parsing fidelity: do we need attributes beyond node ids? Clarify to avoid overbuilding a parser.
- Exact heuristic semantics: confirm any subtle differences between `scott` and `nx_scott` when resolving ties.
- Packaging friction: choose between maturin vs setuptools-rust; ensure existing Python packaging does not break.
- Non-recursive translation correctness: need careful parity tests; keep Python trace dumps available for cross-checking.
