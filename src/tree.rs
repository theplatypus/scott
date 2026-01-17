use std::collections::HashMap;
use std::collections::HashSet;

use petgraph::graph::NodeIndex;

use crate::graph::GraphWrap;

fn format_label(graph: &GraphWrap, node_index: NodeIndex) -> String {
	let node = &graph.graph[node_index];
	let label = node.label.as_str();
	let magnet = node.meta.magnet.as_deref().unwrap_or("");
	if node.meta.is_mirror {
		let arity = node.meta.arity.unwrap_or(0);
		format!("{label}#{arity}{{{magnet}}}")
	} else if node.meta.is_virtual {
		format!("{label}*{{{magnet}}}")
	} else {
		label.to_string()
	}
}

pub fn to_tree_string(
	graph: &GraphWrap,
	root_id: &str,
	ids_ignore: &HashSet<String>,
) -> Result<String, String> {
	let (tree, _depth) = to_tree_string_with_depth(graph, root_id, ids_ignore)?;
	Ok(tree)
}

pub fn to_tree_string_with_depth(
	graph: &GraphWrap,
	root_id: &str,
	ids_ignore: &HashSet<String>,
) -> Result<(String, i32), String> {
	let root_index = graph
		.node_index(root_id)
		.ok_or_else(|| format!("unknown root id '{}'", root_id))?;
	let mut effective_ignore = ids_ignore.clone();
	effective_ignore.remove(root_id);

	let mut visited: HashSet<NodeIndex> = HashSet::new();
	let mut out: HashMap<NodeIndex, (String, i32)> = HashMap::new();
	let mut stack: Vec<(NodeIndex, Option<NodeIndex>, bool, Vec<(usize, NodeIndex, String)>)> = Vec::new();

	stack.push((root_index, None, false, Vec::new()));

	while let Some((node_index, parent, expanded, mut children)) = stack.pop() {
		if expanded {
			let label = format_label(graph, node_index);
			let mut child_outputs: Vec<(usize, NodeIndex, String, i32, String)> = children
				.iter()
				.map(|(position, child_index, modality)| {
					let (child_str, child_depth) = out
						.get(child_index)
						.cloned()
						.unwrap_or_else(|| ("?".to_string(), 1));
					(*position, *child_index, modality.clone(), child_depth, child_str)
				})
				.collect();
			child_outputs.sort_by(|(a_pos, _a_idx, a_mod, a_depth, a_str), (b_pos, _b_idx, b_mod, b_depth, b_str)| {
				let key_a = (*a_depth, a_mod, a_str);
				let key_b = (*b_depth, b_mod, b_str);
				key_a.cmp(&key_b).then_with(|| a_pos.cmp(b_pos))
			});

			let node_str = if child_outputs.is_empty() {
				label
			} else {
				let parts = child_outputs
					.iter()
					.map(|(_, _, modality, _, child_str)| format!("{child_str}:{modality}"))
					.collect::<Vec<_>>()
					.join(", ");
				format!("({parts}){label}")
			};
			let depth = if child_outputs.is_empty() {
				1
			} else {
				1 + child_outputs
					.iter()
					.map(|(_, _, _, depth, _)| *depth)
					.max()
					.unwrap_or(0)
			};
			out.insert(node_index, (node_str, depth));
			continue;
		}

		if visited.contains(&node_index) {
			continue;
		}
		visited.insert(node_index);

		for (position, neighbor) in graph.graph.neighbors(node_index).enumerate() {
			if Some(neighbor) == parent {
				continue;
			}
			let neighbor_id = match graph.graph.node_weight(neighbor) {
				Some(node) => node.id.as_str(),
				None => continue,
			};
			if effective_ignore.contains(neighbor_id) {
				continue;
			}
			if visited.contains(&neighbor) {
				continue;
			}
			let modality = graph
				.graph
				.find_edge(node_index, neighbor)
				.and_then(|edge_index| graph.graph.edge_weight(edge_index))
				.map(|edge| edge.modality.as_str())
				.unwrap_or("1")
				.to_string();
			children.push((position, neighbor, modality));
		}

		stack.push((node_index, parent, true, children.clone()));
		for (_, child, _) in children.into_iter().rev() {
			stack.push((child, Some(node_index), false, Vec::new()));
		}
	}

	out.get(&root_index)
		.map(|(tree, depth)| (tree.clone(), *depth))
		.ok_or_else(|| "failed to build tree string".to_string())
}
