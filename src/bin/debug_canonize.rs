use std::collections::{BTreeMap, HashSet, VecDeque};

use scott::dag::{to_dag_with_mode, InboundMode};
use scott::parse::from_dot;
use scott::tree::{to_tree_string, to_tree_string_with_depth};
use serde_json::Value;

fn main() {
	let args: Vec<String> = std::env::args().collect();
	if args.len() < 2 {
		eprintln!("usage: debug_canonize <dot-path>");
		std::process::exit(1);
	}
	let path = &args[1];
	emit("input", vec![("dot", Value::String(path.clone()))]);
	let graph = from_dot(path).expect("failed to parse dot");
	let mut graph_wrap = graph.as_wrap().clone();

	let scores = score_candidates(&graph_wrap);
	emit("candidates", vec![("scores", scores_to_json(&scores))]);
	let candidates = select_candidates(&scores);
	emit("selected_candidates", vec![("candidates", vec_string(&candidates))]);

	let unmastered = prune_graph(&mut graph_wrap, &candidates);
	let prune_result = build_prune_result(&graph_wrap);
	emit("prune_result", vec![("spreading", map_string(&prune_result))]);
	let mut ids_ignore = unmastered.clone();
	for id in &candidates {
		ids_ignore.insert(id.clone());
	}
	emit("unmastered", vec![("nodes", set_string(&ids_ignore))]);
	emit("ids_ignore", vec![("nodes", set_string(&ids_ignore))]);

	let ids_ignore = if candidates.iter().all(|id| is_leaf(&graph_wrap, id)) {
		HashSet::new()
	} else {
		ids_ignore
	};

	let mode = InboundMode::Duplicate;
	let allow_hashes = true;

	for id_candidate in &candidates {
		let empty_ignore = HashSet::new();
		let dag = to_dag_with_mode(&graph_wrap, id_candidate, &empty_ignore, mode, allow_hashes)
			.expect("failed to build dag");
		let tree = to_tree_string(&dag, id_candidate, &ids_ignore)
			.expect("failed to build tree");
		let tree_compact = compress_cgraph(&tree);
		let (virtuals, mirrors) = count_special_nodes(&dag);
		emit(
			"candidate_tree_restricted",
			vec![
				("candidate", Value::String(id_candidate.clone())),
				("tree", Value::String(tree_compact)),
				("dag_nodes", Value::Number(dag.graph.node_count().into())),
				("dag_edges", Value::Number(dag.graph.edge_count().into())),
				("dag_virtuals", Value::Number(virtuals.into())),
				("dag_mirrors", Value::Number(mirrors.into())),
			],
		);
	}

	let mut elected = Vec::new();
	let mut max_score: Option<(i32, String)> = None;
	for id_candidate in &candidates {
		let empty_ignore = HashSet::new();
		let dag = to_dag_with_mode(&graph_wrap, id_candidate, &empty_ignore, mode, allow_hashes)
			.expect("failed to build dag");
		let (tree, depth) = to_tree_string_with_depth(&dag, id_candidate, &ids_ignore)
			.expect("failed to build tree");
		let score = (depth, tree.clone());
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
	let score_json = match max_score {
		Some((depth, tree)) => Value::Array(vec![
			Value::Number(depth.into()),
			Value::Null,
			Value::String(tree),
		]),
		None => Value::Null,
	};
	emit(
		"elected",
		vec![
			("candidates", vec_string(&elected)),
			("score", score_json),
		],
	);

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
	emit(
		"final",
		vec![
			("root", Value::String(best_root.unwrap_or_default())),
			("tree", Value::String(final_tree_compact.clone())),
		],
	);
	emit("result", vec![("cgraph", Value::String(final_tree_compact))]);
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

fn emit(event: &str, fields: Vec<(&str, Value)>) {
	let mut entries: Vec<(String, String)> = fields
		.into_iter()
		.map(|(key, value)| (key.to_string(), to_json(value)))
		.collect();
	entries.sort_by(|a, b| a.0.cmp(&b.0));
	let mut out = String::new();
	out.push_str("TRACE ");
	out.push_str(event);
	for (key, value) in entries {
		out.push(' ');
		out.push_str(&key);
		out.push('=');
		out.push_str(&value);
	}
	println!("{out}");
}

fn to_json(value: Value) -> String {
	match value {
		Value::Object(map) => {
			let mut entries: Vec<(String, String)> = map
				.into_iter()
				.map(|(key, value)| (key, to_json(value)))
				.collect();
			entries.sort_by(|a, b| a.0.cmp(&b.0));
			let mut out = String::from("{");
			for (idx, (key, value)) in entries.iter().enumerate() {
				if idx > 0 {
					out.push(',');
				}
				out.push_str(&format!("\"{}\":{}", escape_json(key), value));
			}
			out.push('}');
			out
		}
		Value::Array(items) => {
			let mut out = String::from("[");
			for (idx, item) in items.into_iter().enumerate() {
				if idx > 0 {
					out.push(',');
				}
				out.push_str(&to_json(item));
			}
			out.push(']');
			out
		}
		Value::String(s) => format!("\"{}\"", escape_json(&s)),
		Value::Number(n) => n.to_string(),
		Value::Bool(b) => {
			if b { "true".to_string() } else { "false".to_string() }
		}
		Value::Null => "null".to_string(),
	}
}

fn escape_json(input: &str) -> String {
	input
		.replace('\\', "\\\\")
		.replace('"', "\\\"")
		.replace('\n', "\\n")
		.replace('\r', "\\r")
		.replace('\t', "\\t")
}

fn scores_to_json(scores: &[(String, Vec<i32>)]) -> Value {
	let mut entries = Vec::new();
	for (id, score) in scores {
		let score_value = Value::Array(score.iter().map(|v| Value::Number((*v).into())).collect());
		entries.push(Value::Array(vec![Value::String(id.clone()), score_value]));
	}
	Value::Array(entries)
}

fn vec_string(items: &[String]) -> Value {
	Value::Array(items.iter().map(|item| Value::String(item.clone())).collect())
}

fn set_string(items: &HashSet<String>) -> Value {
	let mut values: Vec<String> = items.iter().cloned().collect();
	values.sort();
	vec_string(&values)
}

fn map_string(map: &BTreeMap<String, Vec<String>>) -> Value {
	let mut obj = serde_json::Map::new();
	for (key, value) in map {
		let mut values = value.clone();
		values.sort();
		obj.insert(key.clone(), vec_string(&values));
	}
	Value::Object(obj)
}

fn build_prune_result(graph: &scott::graph::GraphWrap) -> BTreeMap<String, Vec<String>> {
	let mut spreading: BTreeMap<String, Vec<String>> = BTreeMap::new();
	for node_index in graph.graph.node_indices() {
		let node = &graph.graph[node_index];
		if let Some(master) = node.meta.master.as_ref() {
			spreading.entry(master.clone()).or_default().push(node.id.clone());
		} else if !node.meta.master_attempts.is_empty() {
			spreading.entry("None".to_string()).or_default().push(node.id.clone());
		}
	}
	spreading
}
