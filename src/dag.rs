use std::cmp::Ordering;
use std::collections::{HashMap, HashSet, VecDeque};

use petgraph::graph::{EdgeIndex, NodeIndex};
use petgraph::visit::EdgeRef;

use crate::error::{ScottError, ScottResult};
use crate::graph::{EdgeData, GraphWrap, NodeMeta};
use crate::tree::{to_tree_string, to_tree_string_for_magnet};
use serde_json::Value;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum InboundMode {
	Duplicate,
	Elect,
}

#[derive(Debug, Clone)]
pub struct Cobound {
	pub edge: EdgeIndex,
	pub floor: i32,
}

#[derive(Debug, Clone)]
pub struct Inbound {
	pub floor: i32,
	pub node: NodeIndex,
	pub edges: Vec<EdgeIndex>,
}

pub fn to_dag(
	graph: &GraphWrap,
	root_id: &str,
	ids_ignore: &HashSet<String>,
) -> ScottResult<GraphWrap> {
	to_dag_with_mode(graph, root_id, ids_ignore, InboundMode::Duplicate, true)
}

pub fn to_dag_with_mode(
	graph: &GraphWrap,
	root_id: &str,
	ids_ignore: &HashSet<String>,
	mode: InboundMode,
	allow_hashes: bool,
) -> ScottResult<GraphWrap> {
	let mut dag = graph.clone();
	let floors = dag
		.compute_floors(root_id, ids_ignore)
		.map_err(ScottError::Parse)?;
	remove_unfloored_nodes(&mut dag);
	rewrite_bounds(&mut dag, &floors, mode, allow_hashes)?;
	Ok(dag)
}

fn remove_unfloored_nodes(graph: &mut GraphWrap) {
	let mut to_remove = Vec::with_capacity(graph.graph.node_count());
	for node_index in graph.graph.node_indices() {
		if graph.graph[node_index].meta.floor.is_none() {
			to_remove.push(graph.graph[node_index].id.clone());
		}
	}
	for id in to_remove {
		graph.remove_node(&id);
	}
}

fn rewrite_bounds(
	graph: &mut GraphWrap,
	floors: &HashMap<i32, Vec<NodeIndex>>,
	mode: InboundMode,
	allow_hashes: bool,
) -> ScottResult<()> {
	let mut virtual_counter = 0usize;
	let mut mirror_counter = 0usize;

	let mut work_guard = 0usize;
	loop {
		if work_guard > 10_000 {
			return Err(ScottError::Unsupported(
				"dag rewrite loop exceeded guard limit".to_string(),
			));
		}
		work_guard += 1;

		let cobounds = find_cobounds(graph);
		let inbounds = find_inbounds(graph);
		if cobounds.is_empty() && inbounds.is_empty() {
			break;
		}

		let floor = highest_floor(&cobounds, &inbounds);
		if let Some(cobound) = select_cobound(graph, &cobounds, floor, allow_hashes)? {
			fix_cobound(graph, cobound, &mut virtual_counter, allow_hashes)?;
			emit_counts(graph);
			continue;
		}

		if let Some(inbound) = select_inbound(graph, &inbounds, floor, allow_hashes)? {
			fix_inbound(graph, inbound, &mut mirror_counter, mode, allow_hashes)?;
			emit_counts(graph);
			continue;
		}
	}

	for (floor, nodes) in floors {
		for node_index in nodes {
			if let Some(node) = graph.graph.node_weight_mut(*node_index) {
				node.meta.floor = Some(*floor);
			}
		}
	}

	Ok(())
}

fn highest_floor(cobounds: &[Cobound], inbounds: &[Inbound]) -> i32 {
	let max_cobound = cobounds.iter().map(|c| c.floor).max().unwrap_or(0);
	let max_inbound = inbounds.iter().map(|i| i.floor).max().unwrap_or(0);
	std::cmp::max(max_cobound, max_inbound)
}

fn select_cobound(
	graph: &mut GraphWrap,
	cobounds: &[Cobound],
	floor: i32,
	allow_hashes: bool,
) -> ScottResult<Option<Cobound>> {
	let scoped: Vec<Cobound> = cobounds.iter().filter(|c| c.floor == floor).cloned().collect();
	if scoped.is_empty() {
		return Ok(None);
	}
	let mut scored: Vec<(String, (String, String), Cobound)> = Vec::new();
	for cobound in scoped {
		let (a, b) = graph
			.graph
			.edge_endpoints(cobound.edge)
			.ok_or_else(|| ScottError::Parse("cobound endpoints missing".to_string()))?;
		let modality = graph
			.graph
			.edge_weight(cobound.edge)
			.ok_or_else(|| ScottError::Parse("cobound edge missing".to_string()))?
			.modality
			.clone();
		let (a_id, b_id) = edge_key(graph, a, b);
		let magnet_a = get_magnet(graph, a, allow_hashes)?;
		let magnet_b = get_magnet(graph, b, allow_hashes)?;
		let sep = format!("-{}-", modality);
		let mut magnets = [magnet_a, magnet_b];
		magnets.sort();
		let magnet = format!("{}{}{}", magnets[0], sep, magnets[1]);
		scored.push((magnet, (a_id, b_id), cobound));
	}
	scored.sort_by(|a, b| {
		let score_cmp = b.0.cmp(&a.0);
		if score_cmp != Ordering::Equal {
			return score_cmp;
		}
		let edge_cmp = a.1.0.cmp(&b.1.0);
		if edge_cmp != Ordering::Equal {
			return edge_cmp;
		}
		a.1.1.cmp(&b.1.1)
	});
	emit(
		"dag_cobound_scores",
		vec![
			("floor", Value::Number(floor.into())),
			("scores", Value::Array(top_scores(&scored, graph, 5))),
		],
	);
	if let Some((score, _edge_ids, cobound)) = scored.first().cloned() {
		emit(
			"dag_choice",
			vec![
				("floor", Value::Number(floor.into())),
				("type", Value::String("cobound".to_string())),
				("score", Value::String(score)),
				("choice", edge_repr(graph, cobound.edge)),
			],
		);
		Ok(Some(cobound))
	} else {
		Ok(None)
	}
}

fn select_inbound(
	graph: &mut GraphWrap,
	inbounds: &[Inbound],
	floor: i32,
	allow_hashes: bool,
) -> ScottResult<Option<Inbound>> {
	let scoped: Vec<Inbound> = inbounds.iter().filter(|i| i.floor == floor).cloned().collect();
	let mut scored: Vec<((usize, String, String), String, Inbound)> = Vec::new();
	for inbound in scoped {
		let arity = inbound.edges.len();
		let main_magnet = get_magnet(graph, inbound.node, allow_hashes)?;
		let mut root_magnets = Vec::new();
		for edge_index in &inbound.edges {
			let (a, b) = graph
				.graph
				.edge_endpoints(*edge_index)
				.ok_or_else(|| ScottError::Parse("inbound endpoints missing".to_string()))?;
			let other = if a == inbound.node { b } else { a };
			let magnet = get_magnet(graph, other, allow_hashes)?;
			let digest = md5::compute(magnet.as_bytes());
			root_magnets.push(format!("{:x}", digest));
		}
		root_magnets.sort();
		let roots_joined = root_magnets.join(" ");
		let score = (arity, main_magnet, roots_joined);
		let repr = inbound_repr(graph, &inbound);
		scored.push((score, to_json(repr), inbound));
	}
	scored.sort_by(|a, b| {
		let arity_cmp = b.0.0.cmp(&a.0.0);
		if arity_cmp != Ordering::Equal {
			return arity_cmp;
		}
		let magnet_cmp = b.0.1.cmp(&a.0.1);
		if magnet_cmp != Ordering::Equal {
			return magnet_cmp;
		}
		let roots_cmp = b.0.2.cmp(&a.0.2);
		if roots_cmp != Ordering::Equal {
			return roots_cmp;
		}
		a.1.cmp(&b.1)
	});
	emit(
		"dag_inbound_scores",
		vec![
			("floor", Value::Number(floor.into())),
			("scores", Value::Array(top_inbound_scores(&scored, graph, 5))),
		],
	);
	if let Some((score, _repr, inbound)) = scored.first().cloned() {
		emit(
			"dag_choice",
			vec![
				("floor", Value::Number(floor.into())),
				("type", Value::String("inbound".to_string())),
				("score", inbound_score_value(&score)),
				("choice", inbound_repr(graph, &inbound)),
			],
		);
		Ok(Some(inbound))
	} else {
		Ok(None)
	}
}

fn find_cobounds(graph: &GraphWrap) -> Vec<Cobound> {
	let mut cobounds = Vec::new();
	for edge_index in graph.graph.edge_indices() {
		if let Some((a, b)) = graph.graph.edge_endpoints(edge_index) {
			let floor_a = graph.graph[a].meta.floor;
			let floor_b = graph.graph[b].meta.floor;
			if let (Some(floor_a), Some(floor_b)) = (floor_a, floor_b) {
				if floor_a == floor_b {
					cobounds.push(Cobound {
						edge: edge_index,
						floor: floor_a,
					});
				}
			}
		}
	}
	cobounds
}

fn find_inbounds(graph: &GraphWrap) -> Vec<Inbound> {
	let mut inbounds = Vec::new();
	for node_index in graph.graph.node_indices() {
		let floor = match graph.graph[node_index].meta.floor {
			Some(floor) => floor,
			None => continue,
		};
		let mut upstairs = Vec::new();
		for edge_index in graph.graph.edges(node_index).map(|edge| edge.id()) {
			let (a, b) = graph.graph.edge_endpoints(edge_index).unwrap();
			let other = if a == node_index { b } else { a };
			if let Some(other_floor) = graph.graph[other].meta.floor {
				if other_floor < floor {
					upstairs.push(edge_index);
				}
			}
		}
		if upstairs.len() > 1 {
			inbounds.push(Inbound {
				floor,
				node: node_index,
				edges: upstairs,
			});
		}
	}
	inbounds
}

fn fix_cobound(
	graph: &mut GraphWrap,
	cobound: Cobound,
	virtual_counter: &mut usize,
	allow_hashes: bool,
) -> ScottResult<()> {
	let (a, b) = graph
		.graph
		.edge_endpoints(cobound.edge)
		.ok_or_else(|| ScottError::Parse("cobound endpoints missing".to_string()))?;
	let edge = graph
		.graph
		.edge_weight(cobound.edge)
		.ok_or_else(|| ScottError::Parse("cobound edge missing".to_string()))?
		.clone();

	let magnet_a = get_magnet(graph, a, allow_hashes)?;
	let magnet_b = get_magnet(graph, b, allow_hashes)?;
	let sep = format!("-{}-", edge.modality);
	let mut magnets = [magnet_a, magnet_b];
	magnets.sort();
	let magnet = format!("{}{}{}", magnets[0], sep, magnets[1]);

	graph.graph.remove_edge(cobound.edge);

	let virtual_a_id = format!("*v{}", *virtual_counter);
	*virtual_counter += 1;
	let virtual_b_id = format!("*v{}", *virtual_counter);
	*virtual_counter += 1;

	let mut vmeta = NodeMeta::default();
	vmeta.is_virtual = true;
	vmeta.magnet = Some(magnet.clone());
	vmeta.floor = Some(cobound.floor + 1);
	let va = graph.add_node_with_meta(&virtual_a_id, "", vmeta.clone());
	let vb = graph.add_node_with_meta(&virtual_b_id, "", vmeta);

	let mut edge_a = edge.clone();
	edge_a.id = format!("*{}_a", edge.id);
	graph.add_edge_custom(a, va, edge_a);

	let mut edge_b = edge.clone();
	edge_b.id = format!("*{}_b", edge.id);
	graph.add_edge_custom(b, vb, edge_b);

	Ok(())
}

fn fix_inbound(
	graph: &mut GraphWrap,
	inbound: Inbound,
	mirror_counter: &mut usize,
	mode: InboundMode,
	allow_hashes: bool,
) -> ScottResult<()> {
	match mode {
		InboundMode::Duplicate => fix_inbound_duplicate(graph, inbound, mirror_counter, allow_hashes),
		InboundMode::Elect => fix_inbound_elect(graph, inbound, mirror_counter, allow_hashes),
	}
}

fn fix_inbound_duplicate(
	graph: &mut GraphWrap,
	inbound: Inbound,
	mirror_counter: &mut usize,
	allow_hashes: bool,
) -> ScottResult<()> {
	let arity = inbound.edges.len();
	let magnet = get_magnet(graph, inbound.node, allow_hashes)?;
	let floor = inbound.floor;
	let floor_sub = floor + 1;
	let node_id = graph.graph[inbound.node].id.clone();

	let roots_nodes = collect_roots_by_floor(graph, floor - 1);
	let ids_ignore = nodes_not_in_subtree(graph, inbound.node, &roots_nodes);
	let subdag = to_dag_with_mode(graph, &node_id, &ids_ignore, InboundMode::Duplicate, allow_hashes)?;

	for (i, edge_index) in inbound.edges.iter().enumerate() {
		let edge = graph
			.graph
			.edge_weight(*edge_index)
			.ok_or_else(|| ScottError::Parse("inbound edge missing".to_string()))?
			.clone();
		let (a, b) = graph
			.graph
			.edge_endpoints(*edge_index)
			.ok_or_else(|| ScottError::Parse("inbound endpoints missing".to_string()))?;
		let other = if a == inbound.node { b } else { a };

		let mirror_id = format!("#m{}_{}", *mirror_counter, i);
		let mut meta = NodeMeta::default();
		meta.is_mirror = true;
		meta.arity = Some(arity);
		meta.magnet = Some(magnet.clone());
		meta.floor = Some(floor);
		let mirror = graph.add_node_with_meta(&mirror_id, ".", meta);

		graph.graph.remove_edge(*edge_index);
		let mut edge_to_mirror = edge.clone();
		edge_to_mirror.id = format!("#{}_{}", edge.id, i);
		graph.add_edge_custom(other, mirror, edge_to_mirror);

		let suffix = format!("@{}", mirror_id);
		let root_copy = include_subgraph(graph, &subdag, &suffix, floor_sub)?;
		let mut edge_to_root = EdgeData::default();
		edge_to_root.id = format!("{}_link_{}", node_id, i);
		edge_to_root.modality = "1".to_string();
		graph.add_edge_custom(mirror, root_copy, edge_to_root);
	}

	*mirror_counter += 1;
	Ok(())
}

fn fix_inbound_elect(
	graph: &mut GraphWrap,
	inbound: Inbound,
	mirror_counter: &mut usize,
	allow_hashes: bool,
) -> ScottResult<()> {
	let arity = inbound.edges.len();
	let magnet = get_magnet(graph, inbound.node, allow_hashes)?;
	let floor = inbound.floor;
	let node_id = graph.graph[inbound.node].id.clone();
	let label = graph.graph[inbound.node].label.clone();

	let roots_nodes = collect_roots_by_floor(graph, floor - 1);
	let mut candidates = Vec::new();

	for (i, edge_index) in inbound.edges.iter().enumerate() {
		let edge = graph
			.graph
			.edge_weight(*edge_index)
			.ok_or_else(|| ScottError::Parse("inbound edge missing".to_string()))?
			.clone();
		let (a, b) = graph
			.graph
			.edge_endpoints(*edge_index)
			.ok_or_else(|| ScottError::Parse("inbound endpoints missing".to_string()))?;
		let other = if a == inbound.node { b } else { a };

		let mirror_id = format!("#m{}_{}", *mirror_counter, i);
		let mut meta = NodeMeta::default();
		meta.is_mirror = true;
		meta.arity = Some(arity);
		meta.magnet = Some(magnet.clone());
		meta.floor = Some(floor);

		let mirror = graph.add_node_with_meta(&mirror_id, &label, meta);

		graph.graph.remove_edge(*edge_index);
		let mut edge_to_mirror = edge.clone();
		edge_to_mirror.id = format!("#{}_{}", edge.id, i);
		graph.add_edge_custom(other, mirror, edge_to_mirror);

		let other_id = graph.graph[other].id.clone();
		let tree = to_tree_string(graph, &other_id, &roots_nodes).unwrap_or_default();
		candidates.push((tree, mirror));
	}

	candidates.sort_by(|a, b| a.0.cmp(&b.0));
	let main_mirror = candidates
		.first()
		.map(|(_, mirror)| *mirror)
		.ok_or_else(|| ScottError::Parse("no inbound candidates".to_string()))?;

	let mut outgoing_edges = Vec::new();
	for edge_index in graph.graph.edges(inbound.node).map(|edge| edge.id()) {
		let (a, b) = graph.graph.edge_endpoints(edge_index).unwrap();
		let other = if a == inbound.node { b } else { a };
		if let Some(other_floor) = graph.graph[other].meta.floor {
			if other_floor > floor {
				outgoing_edges.push(edge_index);
			}
		}
	}

	for edge_index in outgoing_edges {
		let edge = graph
			.graph
			.edge_weight(edge_index)
			.ok_or_else(|| ScottError::Parse("outgoing edge missing".to_string()))?
			.clone();
		let (a, b) = graph
			.graph
			.edge_endpoints(edge_index)
			.ok_or_else(|| ScottError::Parse("outgoing endpoints missing".to_string()))?;
		let other = if a == inbound.node { b } else { a };
		graph.graph.remove_edge(edge_index);
		let mut edge_to_mirror = edge.clone();
		edge_to_mirror.id = format!("{}_main", edge.id);
		graph.add_edge_custom(other, main_mirror, edge_to_mirror);
	}

	graph.remove_node(&node_id);
	*mirror_counter += 1;
	Ok(())
}

fn collect_roots_by_floor(graph: &GraphWrap, max_floor: i32) -> HashSet<String> {
	let mut roots = HashSet::new();
	for node_index in graph.graph.node_indices() {
		if let Some(floor) = graph.graph[node_index].meta.floor {
			if floor <= max_floor {
				roots.insert(graph.graph[node_index].id.clone());
			}
		}
	}
	roots
}

fn nodes_not_in_subtree(
	graph: &GraphWrap,
	root: NodeIndex,
	roots_nodes: &HashSet<String>,
) -> HashSet<String> {
	let mut keep: HashSet<NodeIndex> = HashSet::new();
	let mut queue: VecDeque<NodeIndex> = VecDeque::new();
	queue.push_back(root);
	keep.insert(root);

	while let Some(current) = queue.pop_front() {
		for neighbor in graph.graph.neighbors(current) {
			let neighbor_id = graph.graph[neighbor].id.as_str();
			if roots_nodes.contains(neighbor_id) {
				continue;
			}
			if keep.insert(neighbor) {
				queue.push_back(neighbor);
			}
		}
	}

	let mut ignore = HashSet::new();
	for node_index in graph.graph.node_indices() {
		if !keep.contains(&node_index) {
			ignore.insert(graph.graph[node_index].id.clone());
		}
	}
	ignore
}

fn include_subgraph(
	target: &mut GraphWrap,
	source: &GraphWrap,
	suffix: &str,
	floor_offset: i32,
) -> ScottResult<NodeIndex> {
	let mut mapping: HashMap<NodeIndex, NodeIndex> = HashMap::new();
	let root_index = source
		.graph
		.node_indices()
		.min_by_key(|index| source.graph[*index].meta.floor.unwrap_or(0))
		.ok_or_else(|| ScottError::Parse("empty subgraph".to_string()))?;

	for node_index in source.graph.node_indices() {
		let node = &source.graph[node_index];
		let mut meta = node.meta.clone();
		meta.floor = meta.floor.map(|floor| floor + floor_offset);
		let new_id = format!("{}{}", node.id, suffix);
		let new_index = target.add_node_with_meta(&new_id, &node.label, meta);
		mapping.insert(node_index, new_index);
	}

	for edge_index in source.graph.edge_indices() {
		let edge = source.graph.edge_weight(edge_index).unwrap().clone();
		let (a, b) = source.graph.edge_endpoints(edge_index).unwrap();
		let na = *mapping.get(&a).unwrap();
		let nb = *mapping.get(&b).unwrap();
		target.add_edge_custom(na, nb, edge);
	}

	mapping
		.get(&root_index)
		.copied()
		.ok_or_else(|| ScottError::Parse("missing root mapping".to_string()))
}

fn get_magnet(graph: &mut GraphWrap, node_index: NodeIndex, allow_hashes: bool) -> ScottResult<String> {
	if let Some(magnet) = graph.graph[node_index].meta.magnet_cache.clone() {
		return Ok(magnet);
	}
	let floor = graph.graph[node_index]
		.meta
		.floor
		.ok_or_else(|| ScottError::Parse("magnet requires floored graph".to_string()))?;
	let mut ids_ignore = HashSet::new();
	for other_index in graph.graph.node_indices() {
		if let Some(other_floor) = graph.graph[other_index].meta.floor {
			if other_floor <= floor {
				ids_ignore.insert(graph.graph[other_index].id.clone());
			}
		}
	}
	let node_id = graph.graph[node_index].id.clone();
	ids_ignore.remove(&node_id);
	let tree = to_tree_string_for_magnet(graph, &node_id, &ids_ignore)
		.map_err(ScottError::Parse)?;
	let magnet = format!("_{}_", tree);
	let value = if allow_hashes {
		let digest = md5::compute(magnet.as_bytes());
		format!("_{:x}_", digest)
	} else {
		magnet
	};

	if std::env::var("SCOTT_TRACE_MAGNET").ok().as_deref() == Some("1") {
		emit(
			"magnet",
			vec![
				("node", Value::String(node_id)),
				("magnet", Value::String(value.clone())),
			],
		);
	}
	if let Some(node) = graph.graph.node_weight_mut(node_index) {
		node.meta.magnet_cache = Some(value.clone());
	}
	Ok(value)
}

fn emit_counts(graph: &GraphWrap) {
	let (virtuals, mirrors) = count_special_nodes(graph);
	emit(
		"dag_counts",
		vec![
			("nodes", Value::Number(graph.graph.node_count().into())),
			("edges", Value::Number(graph.graph.edge_count().into())),
			("virtuals", Value::Number(virtuals.into())),
			("mirrors", Value::Number(mirrors.into())),
		],
	);
}

fn count_special_nodes(graph: &GraphWrap) -> (usize, usize) {
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

fn emit(event: &str, fields: Vec<(&str, Value)>) {
	if std::env::var("SCOTT_TRACE").ok().as_deref() != Some("1") {
		return;
	}
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

fn edge_repr(graph: &GraphWrap, edge: EdgeIndex) -> Value {
	if let Some((a, b)) = graph.graph.edge_endpoints(edge) {
		let (a_id, b_id) = edge_key(graph, a, b);
		Value::Array(vec![Value::String(a_id), Value::String(b_id)])
	} else {
		Value::Array(vec![])
	}
}

fn edge_key(graph: &GraphWrap, a: NodeIndex, b: NodeIndex) -> (String, String) {
	let a_id = graph.graph[a].id.clone();
	let b_id = graph.graph[b].id.clone();
	if a_id <= b_id {
		(a_id, b_id)
	} else {
		(b_id, a_id)
	}
}

fn inbound_repr(graph: &GraphWrap, inbound: &Inbound) -> Value {
	let node_id = graph.graph[inbound.node].id.clone();
	let mut edges = inbound
		.edges
		.iter()
		.map(|edge| edge_repr(graph, *edge))
		.collect::<Vec<_>>();
	edges.sort_by(|a, b| {
		let a_key = to_json(a.clone());
		let b_key = to_json(b.clone());
		a_key.cmp(&b_key)
	});
	Value::Array(vec![
		Value::Number(inbound.floor.into()),
		Value::String(node_id),
		Value::Array(edges),
	])
}

fn top_scores(
	scored: &[(String, (String, String), Cobound)],
	graph: &GraphWrap,
	limit: usize,
) -> Vec<Value> {
	scored
		.iter()
		.take(limit)
		.map(|(score, _edge_ids, cobound)| {
			Value::Array(vec![Value::String(score.clone()), edge_repr(graph, cobound.edge)])
		})
		.collect()
}

fn inbound_score_value(score: &(usize, String, String)) -> Value {
	Value::Array(vec![
		Value::Number(score.0.into()),
		Value::String(score.1.clone()),
		Value::String(score.2.clone()),
	])
}

fn top_inbound_scores(
	scored: &[((usize, String, String), String, Inbound)],
	graph: &GraphWrap,
	limit: usize,
) -> Vec<Value> {
	scored
		.iter()
		.take(limit)
		.map(|(score, _repr, inbound)| {
			Value::Array(vec![inbound_score_value(score), inbound_repr(graph, inbound)])
		})
		.collect()
}
