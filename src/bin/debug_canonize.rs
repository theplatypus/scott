use std::collections::{HashSet, VecDeque};

use scott::dag::{to_dag_with_mode, InboundMode};
use scott::parse::from_dot;
use scott::tree::to_tree_string;

fn main() {
	let args: Vec<String> = std::env::args().collect();
	if args.len() < 2 {
		eprintln!("usage: debug_canonize <dot-path>");
		std::process::exit(1);
	}
	let path = &args[1];
	let graph = from_dot(path).expect("failed to parse dot");
	let mut graph_wrap = graph.as_wrap().clone();

	let scores = score_candidates(&graph_wrap);
	println!("candidates:");
	for (id, score) in &scores {
		println!("  {id}: {:?}", score);
	}
	let candidates = select_candidates(&scores);
	println!("selected candidates: {:?}", candidates);

	let unmastered = prune_graph(&mut graph_wrap, &candidates);
	println!("unmastered: {:?}", unmastered);

	let ids_ignore = if candidates.iter().all(|id| is_leaf(&graph_wrap, id)) {
		HashSet::new()
	} else {
		unmastered
	};
	println!("ids_ignore: {:?}", ids_ignore);

	let mode = InboundMode::Duplicate;
	let allow_hashes = true;

	println!("candidate trees (restricted):");
	for id_candidate in &candidates {
		let dag = to_dag_with_mode(&graph_wrap, id_candidate, &ids_ignore, mode, allow_hashes)
			.expect("failed to build dag");
		let tree = to_tree_string(&dag, id_candidate, &ids_ignore)
			.expect("failed to build tree");
		let tree_compact = compress_cgraph(&tree);
		let (virtuals, mirrors) = count_special_nodes(&dag);
		println!("  {id_candidate} -> {}", tree_compact);
		println!("    dag nodes: {} edges: {} virtuals: {} mirrors: {}", dag.graph.node_count(), dag.graph.edge_count(), virtuals, mirrors);
	}

	let mut elected = Vec::new();
	let mut max_score: Option<String> = None;
	for id_candidate in &candidates {
		let dag = to_dag_with_mode(&graph_wrap, id_candidate, &ids_ignore, mode, allow_hashes)
			.expect("failed to build dag");
		let tree = to_tree_string(&dag, id_candidate, &ids_ignore)
			.expect("failed to build tree");
		match max_score {
			Some(ref score) if tree == *score => {
				elected.push(id_candidate.clone());
			}
			Some(ref score) if tree > *score => {
				max_score = Some(tree);
				elected.clear();
				elected.push(id_candidate.clone());
			}
			None => {
				max_score = Some(tree);
				elected.push(id_candidate.clone());
			}
			_ => {}
		}
	}
	println!("elected: {:?}", elected);

	let empty_ignore = HashSet::new();
	let mut best_tree: Option<String> = None;
	let mut best_root: Option<String> = None;
	for id_candidate in &elected {
		let dag = to_dag_with_mode(&graph_wrap, id_candidate, &empty_ignore, mode, allow_hashes)
			.expect("failed to build dag");
		let tree = to_tree_string(&dag, id_candidate, &empty_ignore)
			.expect("failed to build tree");
		match best_tree {
			Some(ref current) if tree < *current => {
				best_tree = Some(tree);
				best_root = Some(id_candidate.clone());
			}
			None => {
				best_tree = Some(tree);
				best_root = Some(id_candidate.clone());
			}
			_ => {}
		}
	}
	let final_tree = best_tree.unwrap_or_default();
	let final_tree_compact = compress_cgraph(&final_tree);
	println!("final root: {:?}", best_root);
	println!("final tree: {}", final_tree_compact);
}

fn score_candidates(graph: &scott::graph::GraphWrap) -> Vec<(String, Vec<i32>)> {
	let mut scores = Vec::new();
	for node_index in graph.graph.node_indices() {
		let id = graph.graph[node_index].id.clone();
		let degree = graph.graph.neighbors(node_index).count() as i32;
		scores.push((id, vec![degree]));
	}
	scores
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

fn prune_graph(graph: &mut scott::graph::GraphWrap, candidates: &[String]) -> HashSet<String> {
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
							meta.master = Some(msg.clone());
							meta.master_attempts.push(msg.clone());
							should_broadcast = true;
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
		if node.meta.master.is_none() {
			unmastered.insert(node.id.clone());
		}
	}
	for id in candidates {
		unmastered.insert(id.clone());
	}
	unmastered
}

fn is_leaf(graph: &scott::graph::GraphWrap, id: &str) -> bool {
	let index = match graph.node_index(id) {
		Some(index) => index,
		None => return false,
	};
	graph.graph.neighbors(index).count() == 1
}

fn count_special_nodes(graph: &scott::graph::GraphWrap) -> (usize, usize) {
	let mut virtuals = 0usize;
	let mut mirrors = 0usize;
	for node_index in graph.graph.node_indices() {
		let meta = &graph.graph[node_index].meta;
		if meta.is_virtual {
			virtuals += 1;
		}
		if meta.is_mirror {
			mirrors += 1;
		}
	}
	(virtuals, mirrors)
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
