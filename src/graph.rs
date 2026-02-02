use std::collections::HashMap;

use petgraph::graph::{EdgeIndex, NodeIndex};
use petgraph::graph::UnGraph;
use petgraph::stable_graph::StableUnGraph;
use std::collections::{HashSet, VecDeque};

use crate::error::{ScottError, ScottResult};

#[derive(Debug, Clone, Default)]
pub struct NodeMeta {
	pub is_mirror: bool,
	pub is_virtual: bool,
	pub floor: Option<i32>,
	pub magnet: Option<String>,
	pub magnet_cache: Option<String>,
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
	pub graph: StableUnGraph<NodeData, EdgeData>,
	id_to_index: HashMap<String, NodeIndex>,
	edge_count: usize,
}

impl GraphWrap {
	pub fn new() -> Self {
		Self {
			graph: StableUnGraph::default(),
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

	pub fn add_node_with_meta(&mut self, id: &str, label: &str, meta: NodeMeta) -> NodeIndex {
		if let Some(index) = self.id_to_index.get(id) {
			return *index;
		}
		let node = NodeData {
			id: id.to_string(),
			label: label.to_string(),
			meta,
			data: HashMap::new(),
		};
		let index = self.graph.add_node(node);
		self.id_to_index.insert(id.to_string(), index);
		index
	}

	pub fn add_edge_custom(&mut self, from: NodeIndex, to: NodeIndex, mut edge: EdgeData) -> EdgeIndex {
		if edge.id.is_empty() {
			self.edge_count += 1;
			edge.id = format!("e{}", self.edge_count);
		} else {
			self.edge_count += 1;
		}
		self.graph.add_edge(from, to, edge)
	}

	pub fn remove_node(&mut self, id: &str) -> bool {
		let index = match self.id_to_index.remove(id) {
			Some(index) => index,
			None => return false,
		};
		self.graph.remove_node(index);
		true
	}

	pub fn to_ungraph(&self) -> UnGraph<(), ()> {
		let mut graph = UnGraph::default();
		let mut mapping: HashMap<NodeIndex, petgraph::graph::NodeIndex> = HashMap::new();

		for node_index in self.graph.node_indices() {
			let new_index = graph.add_node(());
			mapping.insert(node_index, new_index);
		}

		for edge_index in self.graph.edge_indices() {
			if let Some((a, b)) = self.graph.edge_endpoints(edge_index) {
				if let (Some(na), Some(nb)) = (mapping.get(&a), mapping.get(&b)) {
					graph.add_edge(*na, *nb, ());
				}
			}
		}

		graph
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

	pub fn reset_floors(&mut self) {
		let node_indices: Vec<_> = self.graph.node_indices().collect();
		for node_index in node_indices {
			if let Some(node) = self.graph.node_weight_mut(node_index) {
				node.meta.floor = None;
				node.meta.magnet_cache = None;
			}
		}
	}

	pub fn compute_floors(
		&mut self,
		root_id: &str,
		ids_ignore: &HashSet<String>,
	) -> Result<HashMap<i32, Vec<NodeIndex>>, String> {
		let root_index = self
			.node_index(root_id)
			.ok_or_else(|| format!("unknown root id '{}'", root_id))?;
		if ids_ignore.contains(root_id) {
			return Err("root id is ignored".to_string());
		}

		self.reset_floors();
		let mut floors: HashMap<i32, Vec<NodeIndex>> = HashMap::new();
		let mut queue: VecDeque<(NodeIndex, i32)> = VecDeque::new();
		queue.push_back((root_index, 0));

		let mut seen: HashSet<NodeIndex> = HashSet::new();
		seen.insert(root_index);

		while let Some((node_index, depth)) = queue.pop_front() {
			if let Some(node) = self.graph.node_weight_mut(node_index) {
				node.meta.floor = Some(depth);
			}
			floors.entry(depth).or_default().push(node_index);

			for neighbor in self.graph.neighbors(node_index) {
				if seen.contains(&neighbor) {
					continue;
				}
				let neighbor_id = match self.graph.node_weight(neighbor) {
					Some(node) => node.id.as_str(),
					None => continue,
				};
				if ids_ignore.contains(neighbor_id) {
					continue;
				}
				seen.insert(neighbor);
				queue.push_back((neighbor, depth + 1));
			}
		}

		Ok(floors)
	}

	pub fn to_dag_skeleton(
		&self,
		root_id: &str,
		ids_ignore: &HashSet<String>,
	) -> Result<GraphWrap, String> {
		let mut graph = self.clone();
		graph.compute_floors(root_id, ids_ignore)?;
		Ok(graph)
	}
}

#[derive(Debug, Clone, Default)]
pub struct Graph {
	inner: GraphWrap,
}

impl Graph {
	pub fn new() -> Self {
		Self {
			inner: GraphWrap::new(),
		}
	}

	pub fn from_wrap(inner: GraphWrap) -> Self {
		Self { inner }
	}

	pub fn as_wrap(&self) -> &GraphWrap {
		&self.inner
	}

	pub fn as_wrap_mut(&mut self) -> &mut GraphWrap {
		&mut self.inner
	}

	pub fn ensure_node(&mut self, id: &str, label: &str) -> NodeIndex {
		self.inner.ensure_node(id, label)
	}

	pub fn add_edge_with_modality(&mut self, from: &str, to: &str, modality: &str) -> EdgeIndex {
		self.inner.add_edge_with_modality(from, to, modality)
	}

	pub fn to_dag_skeleton(
		&self,
		root_id: &str,
		ids_ignore: &HashSet<String>,
	) -> ScottResult<Graph> {
		let graph = self
			.inner
			.to_dag_skeleton(root_id, ids_ignore)
			.map_err(ScottError::Parse)?;
		Ok(Graph::from_wrap(graph))
	}
}
