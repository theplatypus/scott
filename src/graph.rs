use std::collections::HashMap;

use petgraph::graph::{EdgeIndex, NodeIndex, UnGraph};

#[derive(Debug, Clone, Default)]
pub struct NodeMeta {
	pub is_mirror: bool,
	pub is_virtual: bool,
	pub floor: Option<i32>,
	pub magnet: Option<String>,
	pub arity: Option<usize>,
	pub master: Option<String>,
	pub master_attempts: Vec<String>,
	pub candidate_score: Option<Vec<String>>,
}

#[derive(Debug, Clone, Default)]
pub struct NodeData {
	pub id: String,
	pub label: String,
	pub meta: NodeMeta,
	pub data: HashMap<String, String>,
}

#[derive(Debug, Clone, Default)]
pub struct EdgeData {
	pub id: String,
	pub modality: String,
	pub directed: bool,
	pub meta: HashMap<String, String>,
	pub data: HashMap<String, String>,
}

#[derive(Debug, Default, Clone)]
pub struct GraphWrap {
	pub graph: UnGraph<NodeData, EdgeData>,
	id_to_index: HashMap<String, NodeIndex>,
	edge_count: usize,
}

impl GraphWrap {
	pub fn new() -> Self {
		Self {
			graph: UnGraph::default(),
			id_to_index: HashMap::new(),
			edge_count: 0,
		}
	}

	pub fn ensure_node(&mut self, id: &str, label: &str) -> NodeIndex {
		if let Some(index) = self.id_to_index.get(id) {
			if !label.is_empty() {
				if let Some(node) = self.graph.node_weight_mut(*index) {
					if node.label.is_empty() {
						node.label = label.to_string();
					}
				}
			}
			return *index;
		}
		let node = NodeData {
			id: id.to_string(),
			label: label.to_string(),
			meta: NodeMeta::default(),
			data: HashMap::new(),
		};
		let index = self.graph.add_node(node);
		self.id_to_index.insert(id.to_string(), index);
		index
	}

	pub fn add_edge(&mut self, from: &str, to: &str) -> EdgeIndex {
		self.add_edge_with_modality(from, to, "1")
	}

	pub fn add_edge_with_modality(&mut self, from: &str, to: &str, modality: &str) -> EdgeIndex {
		let from_index = self.ensure_node(from, ".");
		let to_index = self.ensure_node(to, ".");
		self.edge_count += 1;
		let edge = EdgeData {
			id: format!("e{}", self.edge_count),
			modality: modality.to_string(),
			directed: false,
			meta: HashMap::new(),
			data: HashMap::new(),
		};
		self.graph.add_edge(from_index, to_index, edge)
	}
}
