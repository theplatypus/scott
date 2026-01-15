use std::collections::{HashMap, HashSet};

use petgraph::graph::{EdgeIndex, NodeIndex};
use petgraph::visit::EdgeRef;

use crate::error::{ScottError, ScottResult};
use crate::graph::{EdgeData, GraphWrap, NodeMeta};

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
	let mut dag = graph.clone();
	let floors = dag
		.compute_floors(root_id, ids_ignore)
		.map_err(ScottError::Parse)?;
	remove_unfloored_nodes(&mut dag);
	rewrite_bounds(&mut dag, &floors)?;
	Ok(dag)
}

fn remove_unfloored_nodes(graph: &mut GraphWrap) {
	let mut to_remove = Vec::new();
	for node_index in graph.graph.node_indices() {
		if graph.graph[node_index].meta.floor.is_none() {
			to_remove.push(graph.graph[node_index].id.clone());
		}
	}
	for id in to_remove {
		graph.remove_node(&id);
	}
}

fn rewrite_bounds(graph: &mut GraphWrap, floors: &HashMap<i32, Vec<NodeIndex>>) -> ScottResult<()> {
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
		if let Some(cobound) = select_cobound(&cobounds, floor) {
			fix_cobound(graph, cobound, &mut virtual_counter)?;
			continue;
		}

		if let Some(inbound) = select_inbound(&inbounds, floor) {
			fix_inbound(graph, inbound, &mut mirror_counter)?;
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

fn select_cobound(cobounds: &[Cobound], floor: i32) -> Option<Cobound> {
	let mut scoped: Vec<Cobound> = cobounds.iter().filter(|c| c.floor == floor).cloned().collect();
	scoped.sort_by_key(|c| c.edge.index());
	scoped.into_iter().next()
}

fn select_inbound(inbounds: &[Inbound], floor: i32) -> Option<Inbound> {
	let mut scoped: Vec<Inbound> = inbounds.iter().filter(|i| i.floor == floor).cloned().collect();
	scoped.sort_by_key(|i| i.node.index());
	scoped.into_iter().next()
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

	let a_id = graph.graph[a].id.clone();
	let b_id = graph.graph[b].id.clone();
	let magnet = cobound_magnet(&a_id, &b_id, &edge.modality);

	graph.graph.remove_edge(cobound.edge);

	let virtual_a_id = format!("*v{}", *virtual_counter);
	*virtual_counter += 1;
	let virtual_b_id = format!("*v{}", *virtual_counter);
	*virtual_counter += 1;

	let mut vmeta = NodeMeta::default();
	vmeta.is_virtual = true;
	vmeta.magnet = Some(magnet.clone());
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

fn cobound_magnet(a_id: &str, b_id: &str, modality: &str) -> String {
	let mut ends = [a_id, b_id];
	ends.sort();
	format!("_{}-{}-{}_", ends[0], modality, ends[1])
}

fn fix_inbound(
	graph: &mut GraphWrap,
	inbound: Inbound,
	mirror_counter: &mut usize,
) -> ScottResult<()> {
	let arity = inbound.edges.len();
	let magnet = format!("_m{}_{}", inbound.node.index(), arity);
	let label = ".".to_string();
	let floor = inbound.floor;
	let node_id = graph.graph[inbound.node].id.clone();

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

		let mut edge_to_node = EdgeData::default();
		edge_to_node.id = format!("{}_link_{}", node_id, i);
		edge_to_node.modality = "1".to_string();
		graph.add_edge_custom(mirror, inbound.node, edge_to_node);
	}

	*mirror_counter += 1;
	Ok(())
}
