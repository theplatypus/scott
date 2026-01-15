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
	let root_index = graph
		.node_index(root_id)
		.ok_or_else(|| format!("unknown root id '{}'", root_id))?;
	if ids_ignore.contains(root_id) {
		return Err("root id is ignored".to_string());
	}

	let mut visited: HashSet<NodeIndex> = HashSet::new();
	let mut out: HashMap<NodeIndex, String> = HashMap::new();
	let mut stack: Vec<(NodeIndex, Option<NodeIndex>, bool, Vec<(NodeIndex, String)>)> = Vec::new();

	stack.push((root_index, None, false, Vec::new()));

	while let Some((node_index, parent, expanded, mut children)) = stack.pop() {
		if expanded {
			let label = format_label(graph, node_index);
			let node_str = if children.is_empty() {
				label
			} else {
				let parts = children
					.iter()
					.map(|(child_index, modality)| {
						let child_str = out
							.get(child_index)
							.cloned()
							.unwrap_or_else(|| "?".to_string());
						format!("{child_str}:{modality}")
					})
					.collect::<Vec<_>>()
					.join(", ");
				format!("({parts}){label}")
			};
			out.insert(node_index, node_str);
			continue;
		}

		if visited.contains(&node_index) {
			continue;
		}
		visited.insert(node_index);

		for neighbor in graph.graph.neighbors(node_index) {
			if Some(neighbor) == parent {
				continue;
			}
			let neighbor_id = match graph.graph.node_weight(neighbor) {
				Some(node) => node.id.as_str(),
				None => continue,
			};
			if ids_ignore.contains(neighbor_id) {
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
			children.push((neighbor, modality));
		}

		children.sort_by(|(a_index, _), (b_index, _)| {
			let a_id = graph.graph[*a_index].id.as_str();
			let b_id = graph.graph[*b_index].id.as_str();
			a_id.cmp(b_id)
		});

		stack.push((node_index, parent, true, children.clone()));
		for (child, _) in children.into_iter().rev() {
			stack.push((child, Some(node_index), false, Vec::new()));
		}
	}

	out.get(&root_index)
		.cloned()
		.ok_or_else(|| "failed to build tree string".to_string())
}
