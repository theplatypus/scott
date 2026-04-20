use std::collections::{HashSet, VecDeque};

use crate::cgraph::CGraph;
use crate::dag::{to_dag_with_mode, InboundMode};
use crate::error::{ScottError, ScottResult};
use crate::graph::{Graph, GraphWrap};
use crate::tree::{to_tree_node_order, to_tree_string, to_tree_string_with_depth};

#[cfg(feature = "parallel")]
use rayon::prelude::*;

pub fn to_cgraph(
	_graph: &Graph,
	_candidate_rule: &str,
	_branch_rule: &str,
	_allow_hashes: bool,
	_compress: bool,
	_compact: bool,
) -> ScottResult<CGraph> {
	let mut graph = _graph.as_wrap().clone();
	if graph.graph.node_count() == 0 {
		return Ok(CGraph::new(String::new()));
	}

	let candidate_scores = score_candidates(&graph, _candidate_rule)?;
	let candidates = select_candidates(&candidate_scores);
	let unmastered = prune_graph(&mut graph, &candidates);

	let ids_ignore = if candidates.iter().all(|id| is_leaf(&graph, id)) {
		HashSet::new()
	} else {
		unmastered
	};

	let mode = if _compact {
		InboundMode::Elect
	} else {
		InboundMode::Duplicate
	};

	let candidate_results = collect_candidate_scores(
		&graph,
		&candidates,
		&ids_ignore,
		mode,
		_allow_hashes,
	)?;
	let mut elected = Vec::new();
	let mut max_score: Option<(i32, String)> = None;
	for (id_candidate, depth, tree) in candidate_results {
		let score = (depth, tree.clone());
		match max_score {
			Some(ref best) if score == *best => {
				elected.push(id_candidate);
			}
			Some(ref best) if score > *best => {
				max_score = Some(score);
				elected.clear();
				elected.push(id_candidate);
			}
			None => {
				max_score = Some(score);
				elected.push(id_candidate);
			}
			_ => {}
		}
	}

	let best_tree = collect_best_tree(&graph, &elected, mode, _allow_hashes)?;

	let output = best_tree.unwrap_or_default();
	if _compress {
		Ok(CGraph::new(compress_cgraph(&output)))
	} else {
		Ok(CGraph::new(output))
	}
}


fn score_candidates(graph: &GraphWrap, rule: &str) -> ScottResult<Vec<(String, Vec<i32>)>> {
	let mut scores = Vec::with_capacity(graph.graph.node_count());
	for node_index in graph.graph.node_indices() {
		let id = graph.graph[node_index].id.clone();
		let degree = graph.graph.neighbors(node_index).count() as i32;
		let score = match rule {
			"$degree" => vec![degree],
			_ => {
				return Err(ScottError::Unsupported(format!(
					"candidate rule '{}' not implemented",
					rule
				)))
			}
		};
		scores.push((id, score));
	}
	Ok(scores)
}

fn select_candidates(scores: &[(String, Vec<i32>)]) -> Vec<String> {
	let mut candidates = Vec::with_capacity(scores.len());
	let mut max_score: Option<Vec<i32>> = None;
	for (id, score) in scores {
		match max_score {
			Some(ref max) if score == max => {
				candidates.push(id.clone());
			}
			Some(ref max) if score > max => {
				max_score = Some(score.clone());
				candidates.clear();
				candidates.push(id.clone());
			}
			None => {
				max_score = Some(score.clone());
				candidates.push(id.clone());
			}
			_ => {}
		}
	}
	candidates
}

fn collect_candidate_scores(
	graph: &GraphWrap,
	candidates: &[String],
	ids_ignore: &HashSet<String>,
	mode: InboundMode,
	allow_hashes: bool,
) -> ScottResult<Vec<(String, i32, String)>> {
	#[cfg(feature = "parallel")]
	{
		let empty_ignore = HashSet::new();
		let results: Vec<ScottResult<(String, i32, String)>> = candidates
			.par_iter()
			.map(|id_candidate| {
				let dag = to_dag_with_mode(graph, id_candidate, &empty_ignore, mode, allow_hashes)?;
				let (tree, depth) =
					to_tree_string_with_depth(&dag, id_candidate, ids_ignore)
						.map_err(ScottError::Parse)?;
				Ok((id_candidate.clone(), depth, tree))
			})
			.collect();
		let mut output = Vec::with_capacity(results.len());
		for item in results {
			output.push(item?);
		}
		return Ok(output);
	}
	#[cfg(not(feature = "parallel"))]
	{
		let empty_ignore = HashSet::new();
		let mut output = Vec::with_capacity(candidates.len());
		for id_candidate in candidates {
			let dag = to_dag_with_mode(graph, id_candidate, &empty_ignore, mode, allow_hashes)?;
			let (tree, depth) =
				to_tree_string_with_depth(&dag, id_candidate, ids_ignore)
					.map_err(ScottError::Parse)?;
			output.push((id_candidate.clone(), depth, tree));
		}
		Ok(output)
	}
}

fn collect_best_tree(
	graph: &GraphWrap,
	elected: &[String],
	mode: InboundMode,
	allow_hashes: bool,
) -> ScottResult<Option<String>> {
	#[cfg(feature = "parallel")]
	{
		let empty_ignore = HashSet::new();
		let results: Vec<ScottResult<String>> = elected
			.par_iter()
			.map(|id_candidate| {
				let dag = to_dag_with_mode(graph, id_candidate, &empty_ignore, mode, allow_hashes)?;
				let tree = to_tree_string(&dag, id_candidate, &empty_ignore)
					.map_err(ScottError::Parse)?;
				Ok(tree)
			})
			.collect();
		let mut best_tree: Option<String> = None;
		for item in results {
			let tree = item?;
			match best_tree {
				Some(ref current) if tree < *current => best_tree = Some(tree),
				None => best_tree = Some(tree),
				_ => {}
			}
		}
		return Ok(best_tree);
	}
	#[cfg(not(feature = "parallel"))]
	{
		let empty_ignore = HashSet::new();
		let mut best_tree: Option<String> = None;
		for id_candidate in elected {
			let dag = to_dag_with_mode(graph, id_candidate, &empty_ignore, mode, allow_hashes)?;
			let tree = to_tree_string(&dag, id_candidate, &empty_ignore)
				.map_err(ScottError::Parse)?;
			match best_tree {
				Some(ref current) if tree < *current => best_tree = Some(tree),
				None => best_tree = Some(tree),
				_ => {}
			}
		}
		Ok(best_tree)
	}
}

fn prune_graph(graph: &mut GraphWrap, candidates: &[String]) -> HashSet<String> {
	let mut candidates_set = HashSet::with_capacity(candidates.len());
	for id in candidates {
		candidates_set.insert(id.clone());
	}

	let node_indices: Vec<_> = graph.graph.node_indices().collect();
	for node_index in node_indices {
		if let Some(node) = graph.graph.node_weight_mut(node_index) {
			node.meta.master = None;
			node.meta.master_attempts.clear();
		}
	}

	for id_candidate in candidates {
		let start_index = match graph.node_index(id_candidate) {
			Some(index) => index,
			None => continue,
		};
		let mut queue = VecDeque::with_capacity(graph.graph.node_count());
		queue.push_back((start_index, None, id_candidate.clone()));
		while let Some((from, origin, msg)) = queue.pop_front() {
			let neighbors: Vec<_> = graph.graph.neighbors(from).collect();
			for neighbor in neighbors {
				if Some(neighbor) == origin {
					continue;
				}
				let neighbor_id = graph.graph[neighbor].id.clone();
				if candidates_set.contains(&neighbor_id) {
					continue;
				}

				let should_broadcast;
				{
					let meta = &mut graph.graph[neighbor].meta;
					match &meta.master {
						Some(master) => {
							if master == &msg {
								continue;
							}
							meta.master = None;
							if meta.master_attempts.iter().any(|m| m == &msg) {
								continue;
							}
							meta.master_attempts.push(msg.clone());
							should_broadcast = true;
						}
						None => {
							if !meta.master_attempts.is_empty() {
								if meta.master_attempts.iter().any(|m| m == &msg) {
									continue;
								}
								meta.master_attempts.push(msg.clone());
								should_broadcast = true;
							} else {
								meta.master = Some(msg.clone());
								meta.master_attempts.push(msg.clone());
								should_broadcast = true;
							}
						}
					}
				}

				if should_broadcast {
					queue.push_back((neighbor, Some(from), msg.clone()));
				}
			}
		}
	}

	let mut unmastered = HashSet::with_capacity(graph.graph.node_count());
	for node_index in graph.graph.node_indices() {
		let node = &graph.graph[node_index];
		if node.meta.master.is_none() && !node.meta.master_attempts.is_empty() {
			unmastered.insert(node.id.clone());
		}
	}
	unmastered
}

fn is_leaf(graph: &GraphWrap, id: &str) -> bool {
	let index = match graph.node_index(id) {
		Some(index) => index,
		None => return false,
	};
	graph.graph.neighbors(index).count() == 1
}

fn compress_cgraph(cgraph: &str) -> String {
	let mut output = String::new();
	let mut magnets: std::collections::HashMap<String, String> = std::collections::HashMap::new();
	let mut magnet = String::new();
	let mut in_magnet = false;
	let mut cpt = 0usize;
	let mut depth = 0usize;

	for ch in cgraph.chars() {
		if !in_magnet {
			output.push(ch);
			if ch == '{' {
				in_magnet = true;
			}
			continue;
		}

		if ch == '{' {
			depth += 1;
			magnet.push(ch);
		} else if ch == '}' {
			if depth == 0 {
				in_magnet = false;
				let entry = magnets.entry(magnet.clone()).or_insert_with(|| {
					cpt += 1;
					format!("${}", cpt)
				});
				output.push_str(entry);
				output.push('}');
				magnet.clear();
			} else {
				depth -= 1;
				magnet.push(ch);
			}
		} else {
			magnet.push(ch);
		}
	}

	output
}

pub fn canonical_node_order(
	_graph: &Graph,
	_candidate_rule: &str,
	_branch_rule: &str,
	_allow_hashes: bool,
	_compact: bool,
) -> ScottResult<Vec<String>> {
	let mut graph = _graph.as_wrap().clone();
	if graph.graph.node_count() == 0 {
		return Ok(Vec::new());
	}

	let candidate_scores = score_candidates(&graph, _candidate_rule)?;
	let candidates = select_candidates(&candidate_scores);
	let unmastered = prune_graph(&mut graph, &candidates);

	let ids_ignore = if candidates.iter().all(|id| is_leaf(&graph, id)) {
		HashSet::new()
	} else {
		unmastered
	};

	let mode = if _compact {
		InboundMode::Elect
	} else {
		InboundMode::Duplicate
	};

	let candidate_results = collect_candidate_scores(
		&graph,
		&candidates,
		&ids_ignore,
		mode,
		_allow_hashes,
	)?;
	let mut elected = Vec::new();
	let mut max_score: Option<(i32, String)> = None;
	for (id_candidate, depth, tree) in candidate_results {
		let score = (depth, tree.clone());
		match max_score {
			Some(ref best) if score == *best => {
				elected.push(id_candidate);
			}
			Some(ref best) if score > *best => {
				max_score = Some(score);
				elected.clear();
				elected.push(id_candidate);
			}
			None => {
				max_score = Some(score);
				elected.push(id_candidate);
			}
			_ => {}
		}
	}

	// Pick the best elected candidate (same logic as collect_best_tree)
	let empty_ignore = HashSet::new();
	let mut best: Option<(String, Vec<String>)> = None;
	for id_candidate in &elected {
		let dag = to_dag_with_mode(&graph, id_candidate, &empty_ignore, mode, _allow_hashes)?;
		let tree = to_tree_string(&dag, id_candidate, &empty_ignore)
			.map_err(ScottError::Parse)?;
		let order = to_tree_node_order(&dag, id_candidate, &empty_ignore)
			.map_err(ScottError::Parse)?;
		match best {
			Some((ref current_tree, _)) if tree < *current_tree => {
				best = Some((tree, order));
			}
			None => {
				best = Some((tree, order));
			}
			_ => {}
		}
	}

	Ok(best.map(|(_, order)| order).unwrap_or_default())
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
