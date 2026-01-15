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

	pub fn node_index(&self, id: &str) -> Option<NodeIndex> {
		self.id_to_index.get(id).copied()
	}

	pub fn node_data(&self, id: &str) -> Option<&NodeData> {
		self.node_index(id).and_then(|index| self.graph.node_weight(index))
	}

	pub fn node_data_mut(&mut self, id: &str) -> Option<&mut NodeData> {
		self.node_index(id).and_then(|index| self.graph.node_weight_mut(index))
	}

	pub fn node_meta(&self, id: &str) -> Option<&NodeMeta> {
		self.node_data(id).map(|node| &node.meta)
	}

	pub fn node_meta_mut(&mut self, id: &str) -> Option<&mut NodeMeta> {
		self.node_data_mut(id).map(|node| &mut node.meta)
	}

	pub fn edge_data(&self, index: EdgeIndex) -> Option<&EdgeData> {
		self.graph.edge_weight(index)
	}

	pub fn edge_data_mut(&mut self, index: EdgeIndex) -> Option<&mut EdgeData> {
		self.graph.edge_weight_mut(index)
	}

	pub fn set_node_floor(&mut self, id: &str, floor: i32) -> bool {
		match self.node_meta_mut(id) {
			Some(meta) => {
				meta.floor = Some(floor);
				true
			}
			None => false,
		}
	}

	pub fn set_node_magnet(&mut self, id: &str, magnet: &str) -> bool {
		match self.node_meta_mut(id) {
			Some(meta) => {
				meta.magnet = Some(magnet.to_string());
				true
			}
			None => false,
		}
	}

	pub fn set_node_candidate_score(&mut self, id: &str, score: Vec<String>) -> bool {
		match self.node_meta_mut(id) {
			Some(meta) => {
				meta.candidate_score = Some(score);
				true
			}
			None => false,
		}
	}

	pub fn set_node_master(&mut self, id: &str, master: &str) -> bool {
		match self.node_meta_mut(id) {
			Some(meta) => {
				meta.master = Some(master.to_string());
				true
			}
			None => false,
		}
	}

	pub fn clear_node_master(&mut self, id: &str) -> bool {
		match self.node_meta_mut(id) {
			Some(meta) => {
				meta.master = None;
				true
			}
			None => false,
		}
	}

	pub fn add_node_master_attempt(&mut self, id: &str, master: &str) -> bool {
		match self.node_meta_mut(id) {
			Some(meta) => {
				meta.master_attempts.push(master.to_string());
				true
			}
			None => false,
		}
	}

	pub fn set_node_virtual(&mut self, id: &str, is_virtual: bool) -> bool {
		match self.node_meta_mut(id) {
			Some(meta) => {
				meta.is_virtual = is_virtual;
				true
			}
			None => false,
		}
	}

	pub fn set_node_mirror(&mut self, id: &str, is_mirror: bool) -> bool {
		match self.node_meta_mut(id) {
			Some(meta) => {
				meta.is_mirror = is_mirror;
				true
			}
			None => false,
		}
	}
}
