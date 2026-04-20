# Scott Changelog


---
## [1.1.1] - 2026-04-20

### ⚙️  Miscellaneous Tasks

- [chore] bump version

---
## [1.1.0] - 2026-04-20

### ✨ Enhancements

- [enh] provides __version__ attr

### 📚 Documentation

- [doc] enhance Readme
- [doc] update usage.py

### ⚙️  Miscellaneous Tasks

- [chore] init git cliff
- [chore] Changelog

### 💼 Other

- [clean] rm plan files

---
## [1.1.0-rc4] - 2026-04-19

### 🚀 Features

- [feat] include adjacency_matrix in rust engine
- [feat] parse from networkx format

### 🐛 Bug Fixes

- [fix] structs: ensure compatibility with v1.0
- [fix] backward compat with graph object
- [fix] auto test running from source instead of the wheel

### ✨ Enhancements

- [enh] install: installation process with pip/uv

### 📚 Documentation

- [doc] about parallelism
- [doc] claude /init
- [doc] update Readme

### ⚡ Performance

- [perf] plan for better performance
- [perf] baseline
- [perf] fewer clones, better prealloc
- [perf] dag.rs: sorting/tie-breaking optimizations
- [perf] dag.rs: precompute buckets + reduce scans
- [perf] magnet optimization
- [perf] tree.rs: Tree serialization
- [perf] optional parallelism

### 🧪 Testing

- [test] remove nx engine from test_runner
- [test] add default .dot file for test_runner

### ⚙️  Miscellaneous Tasks

- [chore] remove mentions of PySpark
- [chore] update uv.lock
- [ci] publish to pypi
- [ci] rename pypi pkg to `scott-trace`
- [ci] test on Test Pypi
- [ci] upload to Pypi main instance
- [ci] publish pre-releases to Test Pypi
- [ci] skip existing tags on Test Pypi

### 💼 Other

- [misc] sample results
- [misc] update version
- [arch] Rust core + Python I/O + optional legacy backend
- [build] rm conda Dockerfile
- [build] update Dockerfiles
- [build] add jupyter Dockerfile
- [build] auto build wheels
- [build] use abi3-py38 for wheel

---
## [1.1.0-rc3] - 2026-02-02

### 💼 Other

- [misc] improve tooling (#9)

---
## [1.1.0-rc2] - 2026-02-02

### 💼 Other

- Add test_cfi_rigid.rs
- Update gitignore
- Init AGENTS.md
- Rename nx_scott_direct -> scott-nx
- Rename scott -> scott_legacy
- Create PyO3 module
- Enabled PyO3 extension build
- Unified test CLI + harness + docs
- Refactored DOT parsing to support content strings
- Ignore .so files
- Init CI.yml
- First results

---
## [1.1.0-rc1] - 2026-02-02

### 🧪 Testing

- [test] add .dot sample
- [test] add isomorphisn testing script

### 💼 Other

- Interface with networkx
- Implementation over nx struct
- Init rust project
- Init pyo3
- [misc] add tag on pypy Dockerfile
- Phase0: dot parser
- Phase0: lib scaffolding
- Codex plan
- Define GraphWrap struct
- Enhance dot parser
- Enh: add helpers
- Add struct tree
- Convert graph to dag
- Test case
- Scaffold core lib
- Adapt tests
- Add modue dag
- Enhance tests
- Init + traces comparisons
- Match python's pruning
- Sorted trace output in Python
- Root leaf formatting
- Build DAGs with no-ignore  in restricted election
- Traces match!
- Rename test.rs -> test_isomorphism.rs
- `dag_cobound_scores` using same order than Python
- Make cobounds ordering independent of parsing
- Test: assert successes
- Enhance determinism
- Reduce noise in traces comparison

---
## [1.0.1] - 2024-09-11

### 💼 Other

- Check len(permut) before flattening

---
## [1.0.0] - 2020-05-10

### 💼 Other

- Initial commit
- Set theme jekyll-theme-cayman
- Delete .DS_Store
- Update ReadMe.md
- Add files via upload
- Update index.md
- Update _config.yml
- Create analytics.html
- Create head.html
- Update analytics.html
- Rename analytics.html to google-analytics.html
- Delete head.html
- Update smiles2mol.py
- Fix #1 
- ADD split_connex_compounds
- Connex Compounds
- FIX ngrams_generation
- Radial N-Grams


