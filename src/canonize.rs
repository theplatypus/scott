use std::collections::{HashSet, VecDeque};

use crate::cgraph::CGraph;
use crate::dag::{to_dag_with_mode, InboundMode};
use crate::error::{ScottError, ScottResult};
use crate::graph::{Graph, GraphWrap};
use crate::tree::{to_tree_string, to_tree_string_with_depth};

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

	let mut elected = Vec::new();
	let mut max_score: Option<(i32, String, String)> = None;
	for id_candidate in &candidates {
		let dag = to_dag_with_mode(&graph, id_candidate, &ids_ignore, mode, _allow_hashes)?;
		let (tree, depth) = to_tree_string_with_depth(&dag, id_candidate, &ids_ignore)
			.map_err(ScottError::Parse)?;
		let score = (depth, String::new(), tree.clone());
		match max_score {
			Some(ref best) if score == *best => {
				elected.push(id_candidate.clone());
			}
			Some(ref best) if score > *best => {
				max_score = Some(score);
				elected.clear();
				elected.push(id_candidate.clone());
			}
			None => {
				max_score = Some(score);
				elected.push(id_candidate.clone());
			}
			_ => {}
		}
	}

	let mut best_tree: Option<String> = None;
	let empty_ignore = HashSet::new();
	for id_candidate in &elected {
		let dag = to_dag_with_mode(&graph, id_candidate, &empty_ignore, mode, _allow_hashes)?;
		let tree = to_tree_string(&dag, id_candidate, &empty_ignore)
			.map_err(ScottError::Parse)?;
		match best_tree {
			Some(ref current) if tree < *current => best_tree = Some(tree),
			None => best_tree = Some(tree),
			_ => {}
		}
	}

	let output = best_tree.unwrap_or_default();
	if _compress {
		Ok(CGraph::new(compress_cgraph(&output)))
	} else {
		Ok(CGraph::new(output))
	}
}


fn score_candidates(graph: &GraphWrap, rule: &str) -> ScottResult<Vec<(String, Vec<i32>)>> {
	let mut scores = Vec::new();
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
	let mut candidates = Vec::new();
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

fn prune_graph(graph: &mut GraphWrap, candidates: &[String]) -> HashSet<String> {
	let mut candidates_set = HashSet::new();
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
		let mut queue = VecDeque::new();
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

	let mut unmastered = HashSet::new();
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
