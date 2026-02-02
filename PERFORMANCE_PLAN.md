# Rust Engine Performance Plan

Goals:
- Speed up canonization and isomorphism checks.
- Reduce peak memory and allocation pressure.
- Preserve deterministic output and trace compatibility.

Scope:
- Rust core modules: `src/dag.rs`, `src/tree.rs`, `src/canonize.rs`, `src/graph.rs`, `src/parse.rs`.
- Rust bins and test harness are used for profiling and validation, but not the primary focus.

## 0) Baseline + measurement

1) Add a repeatable benchmark driver (no randomness):
   - Run a fixed subset of `data/isotest/cfi-rigid-t2-dot/`.
   - Capture runtime (wall), allocations (if possible), and peak RSS.
   - Emit JSON/CSV with per-graph timings and totals.

2) Capture current metrics before changes:
   - Debug + release timings.
   - Peak RSS.
   - Trace counts for DAG rewrites and tree sizes to ensure parity.

3) Tooling:
   - macOS: `time`, `leaks`, `vmmap`, Instruments (Time Profiler).

Deliverable: `results/perf_baseline.json` and a short summary in `docs/Testing.md`.

## 1) Low-risk wins (allocations + reuse)

1) Pre-allocate and reuse buffers:
   - Reuse `Vec`, `VecDeque`, and `HashMap` across iterations (clear instead of drop).
   - Replace temporary `Vec` allocations in tight loops with scratch buffers.

2) Avoid repeated `String` creation:
   - Use integer node indices throughout DAG and tree logic.
   - Delay string formatting until the final tree serialization step.
   - Store magnet IDs as `u64` or `[u8; 16]` (md5) instead of hex strings.

3) Compact identifiers:
   - Use `u32` for node IDs and internal indices wherever possible.
   - Use `SmallVec` or `Vec<[u32; 2]>` for edge endpoints to reduce heap churn.

4) Reduce cloning:
   - Audit `clone()` in DAG and tree builders.
   - Replace with references or indices.
   - Use `mem::take` for swap-based ownership moves.

Deliverable: 10-30% allocation drop; measurable wall-time improvement on cfi-rigid.

## 2) Sorting and tie-breaking cost

1) Stable, deterministic ordering without heavy `String` comparison:
   - Define a compact `EdgeKey`/`NodeKey` (tuple of ints).
   - For magnet ordering and tie-breaks, compare compact keys then fallback to lexicographic only at final string step.

2) Sorting micro-optimizations:
   - Use `sort_unstable_by` with custom comparator where stability is not required.
   - Avoid sorting the full list when only top-k is needed (use selection).

3) Cache ordering for repeated sets:
   - Cobound and inbound candidate sets often repeat across steps.
   - Use a small LRU cache keyed by `Vec<u32>` signature to reuse sorted order.

Deliverable: reduce time in `dag_cobound_scores` and `dag_inbound_scores`.

## 3) DAG rewrite algorithm efficiency

1) Reduce graph mutations:
   - Batch edge insertions/removals instead of mutating `petgraph` per step.
   - Maintain adjacency lists in a separate structure to compute rewrites faster.

2) Replace `petgraph` in the inner loop:
   - Keep `petgraph::Graph` for I/O and final conversion.
   - Use a custom adjacency (Vec<Vec<u32>>) for rewrites to avoid `petgraph` overhead.

3) Optimize "cobound" and "inbound" selection:
   - Precompute per-floor candidate lists once.
   - Track remaining candidates by floor with a queue and an active bitmap.

Deliverable: reduce DAG rewrite runtime by 2x on cfi-rigid sizes.

## 4) Magnet computation and caching

1) Replace magnet string concatenation:
   - Use a compact hash of a structured magnet key (ints and small slices).
   - Implement a small, fast hasher (`ahash` or `fxhash`) for in-memory comparison.

2) Magnet cache:
   - Keep per-node/per-edge magnet results for reuse in repeated inbound/cobound checks.
   - Invalidate only when necessary (after a rewrite, invalidate affected region).

3) Memory-efficient magnet maps:
   - Use `Vec<Option<Magnet>>` indexed by node/edge ID.
   - Avoid `HashMap<String, ...>` for magnets where possible.

Deliverable: reduced time in magnet generation, fewer allocations.

## 5) Tree serialization

1) Build the tree string with a single `String` buffer:
   - Pre-estimate capacity to avoid re-allocations.
   - Use `push_str` + `push` with small, fixed tokens.

2) Avoid repeated sub-tree stringification:
   - Memoize string fragments for repeated subtrees in the DAG (if safe for canonical output).
   - Use a DAG-to-tree node map with cached serialization.

Deliverable: faster `to_tree_string` and smaller peak memory for large trees.

## 6) Memory footprint reduction

1) Replace `HashMap` with `FxHashMap` / `AHashMap` where hash DOS is not a concern.
2) Compact node/edge structs:
   - Pack booleans in bitflags.
   - Use `u32` where sizes are bounded.
3) Use `Vec<u32>` adjacency with deduped neighbors.
4) Remove large debug state unless `debug` feature enabled.

Deliverable: lower RSS and smaller serialized `cgraph` intermediates.

## 7) Parallelism (optional, guarded)

1) Only for candidate-independent work:
   - Per-candidate DAG/tree computation can be parallelized when determinism is preserved.
2) Use `rayon` under a feature flag and stable reduction:
   - Sort results by key to enforce deterministic selection.

Deliverable: speedup on multi-core machines with optional feature.

## 8) Validation and regression control

1) For each phase:
   - Compare canonical outputs on a fixed fixture set.
   - Check traces with the existing Python comparison tooling.
2) Add a small regression suite:
   - 5-10 graphs with expected canonical output.
   - Ensure rust outputs are stable under reordering of input nodes.

Deliverable: performance gains without output drift.

## Milestones

1) Baseline + low-risk improvements (sections 0-1).
2) Sorting and magnet caching (sections 2-4).
3) DAG inner loop overhaul (section 3).
4) Tree serialization + memory compaction (sections 5-6).
5) Optional parallelism (section 7).

Target outcomes:
- 2-5x speedup on cfi-rigid sizes 20-30.
- 30-50% reduction in peak RSS and allocations.
