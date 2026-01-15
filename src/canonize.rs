use crate::cgraph::CGraph;
use crate::error::ScottResult;
use crate::graph::Graph;

pub fn to_cgraph(
	_graph: &Graph,
	_candidate_rule: &str,
	_branch_rule: &str,
	_allow_hashes: bool,
	_compress: bool,
	_compact: bool,
) -> ScottResult<CGraph> {
	Ok(CGraph::new("scott-rs-placeholder".to_string()))
}

pub fn is_isomorphic(
	left: &Graph,
	right: &Graph,
	candidate_rule: &str,
	branch_rule: &str,
	allow_hashes: bool,
	compress: bool,
	compact: bool,
) -> ScottResult<bool> {
	let left_c = to_cgraph(left, candidate_rule, branch_rule, allow_hashes, compress, compact)?;
	let right_c = to_cgraph(right, candidate_rule, branch_rule, allow_hashes, compress, compact)?;
	Ok(left_c == right_c)
}
