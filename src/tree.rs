use std::collections::HashMap;
use std::collections::HashSet;
use std::sync::Arc;

use petgraph::graph::NodeIndex;

use crate::graph::GraphWrap;

fn format_label(graph: &GraphWrap, node_index: NodeIndex) -> String {
	let node = &graph.graph[node_index];
	let label = node.label.as_str();
	let magnet = node.meta.magnet.as_deref().unwrap_or("");
	if node.meta.is_mirror {
		let arity = node.meta.arity.unwrap_or(0);
		let mut out = String::with_capacity(label.len() + magnet.len() + 8);
		out.push_str(label);
		out.push('#');
		out.push_str(&arity.to_string());
		out.push('{');
		out.push_str(magnet);
		out.push('}');
		out
	} else if node.meta.is_virtual {
		let mut out = String::with_capacity(label.len() + magnet.len() + 4);
		out.push_str(label);
		out.push('*');
		out.push('{');
		out.push_str(magnet);
		out.push('}');
		out
	} else {
		label.to_string()
	}
}

pub fn to_tree_string(
	graph: &GraphWrap,
	root_id: &str,
	ids_ignore: &HashSet<String>,
) -> Result<String, String> {
	let (tree, _depth) = to_tree_string_with_depth_order(graph, root_id, ids_ignore, true)?;
	Ok(tree)
}

pub fn to_tree_string_for_magnet(
	graph: &GraphWrap,
	root_id: &str,
	ids_ignore: &HashSet<String>,
) -> Result<String, String> {
	let (tree, _depth) = to_tree_string_with_depth_order(graph, root_id, ids_ignore, false)?;
	Ok(tree)
}

pub fn to_tree_string_with_depth(
	graph: &GraphWrap,
	root_id: &str,
	ids_ignore: &HashSet<String>,
) -> Result<(String, i32), String> {
	to_tree_string_with_depth_order(graph, root_id, ids_ignore, true)
}

fn to_tree_string_with_depth_order(
	graph: &GraphWrap,
	root_id: &str,
	ids_ignore: &HashSet<String>,
	include_modality: bool,
) -> Result<(String, i32), String> {
	let root_index = graph
		.node_index(root_id)
		.ok_or_else(|| format!("unknown root id '{}'", root_id))?;

	let node_count = graph.graph.node_count();
	let mut visited: HashSet<NodeIndex> = HashSet::with_capacity(node_count);
	let mut out: HashMap<NodeIndex, (Arc<str>, i32)> = HashMap::with_capacity(node_count);
	let mut intern: HashMap<Arc<str>, Arc<str>> = HashMap::with_capacity(node_count);
	let mut stack: Vec<(NodeIndex, Option<NodeIndex>, bool, Vec<(usize, NodeIndex, String)>)> =
		Vec::with_capacity(node_count);

	stack.push((root_index, None, false, Vec::new()));

	while let Some((node_index, parent, expanded, mut children)) = stack.pop() {
		if expanded {
			let label = format_label(graph, node_index);
			let is_leaf = parent.is_some() && graph.graph.neighbors(node_index).count() == 1;
			if is_leaf {
				let arc = interned_arc(&mut intern, label);
				out.insert(node_index, (arc, 1));
				continue;
			}

			let mut child_outputs: Vec<(usize, NodeIndex, String, i32, Arc<str>)> =
				Vec::with_capacity(children.len());
			for (position, child_index, modality) in &children {
				let (child_str, child_depth) = match out.get(child_index) {
					Some((value, depth)) => (value.clone(), *depth),
					None => (Arc::<str>::from("?"), 1),
				};
				child_outputs.push((*position, *child_index, modality.clone(), child_depth, child_str));
			}
			if include_modality {
				child_outputs.sort_by(
					|(a_pos, _a_idx, a_mod, a_depth, a_str),
					  (b_pos, _b_idx, b_mod, b_depth, b_str)| {
						let key_a = (*a_depth, a_mod, a_str);
						let key_b = (*b_depth, b_mod, b_str);
						key_a.cmp(&key_b).then_with(|| a_pos.cmp(b_pos))
					},
				);
			} else {
				child_outputs.sort_by(
					|(a_pos, _a_idx, _a_mod, a_depth, a_str),
					  (b_pos, _b_idx, _b_mod, b_depth, b_str)| {
						let key_a = (*a_depth, a_str);
						let key_b = (*b_depth, b_str);
						key_a.cmp(&key_b).then_with(|| a_pos.cmp(b_pos))
					},
				);
			}

			let node_str = build_node_string(&label, &child_outputs);
			let depth = if child_outputs.is_empty() {
				1
			} else {
				1 + child_outputs
					.iter()
					.map(|(_, _, _, depth, _)| *depth)
					.max()
					.unwrap_or(0)
			};
			let arc = interned_arc(&mut intern, node_str);
			out.insert(node_index, (arc, depth));
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
			if neighbor_id != root_id && ids_ignore.contains(neighbor_id) {
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

		let mut child_nodes: Vec<NodeIndex> = Vec::with_capacity(children.len());
		for (_, child, _) in &children {
			child_nodes.push(*child);
		}
		stack.push((node_index, parent, true, children));
		for child in child_nodes.into_iter().rev() {
			stack.push((child, Some(node_index), false, Vec::new()));
		}
	}

	out.get(&root_index)
		.map(|(tree, depth)| (tree.to_string(), *depth))
		.ok_or_else(|| "failed to build tree string".to_string())
}

fn interned_arc(intern: &mut HashMap<Arc<str>, Arc<str>>, value: String) -> Arc<str> {
	if let Some(existing) = intern.get(value.as_str()) {
		return existing.clone();
	}
	let arc: Arc<str> = Arc::from(value);
	intern.insert(arc.clone(), arc.clone());
	arc
}

fn build_node_string(
	label: &str,
	children: &[(usize, NodeIndex, String, i32, Arc<str>)],
) -> String {
	let mut capacity = label.len() + 2;
	if !children.is_empty() {
		for (idx, (_, _, modality, _, child_str)) in children.iter().enumerate() {
			if idx > 0 {
				capacity += 2;
			}
			capacity += child_str.len() + 1 + modality.len();
		}
	}
	let mut out = String::with_capacity(capacity);
	out.push('(');
	for (idx, (_, _, modality, _, child_str)) in children.iter().enumerate() {
		if idx > 0 {
			out.push_str(", ");
		}
		out.push_str(child_str.as_ref());
		out.push(':');
		out.push_str(modality);
	}
	out.push(')');
	out.push_str(label);
	out
}
