use std::collections::HashMap;

use petgraph::graph::NodeIndex;
use petgraph::graph::UnGraph;

#[derive(Debug, Default, Clone)]
pub struct GraphWrap {
	pub graph: UnGraph<(), ()>,
	id_to_index: HashMap<String, NodeIndex>,
}

impl GraphWrap {
	pub fn new() -> Self {
		Self {
			graph: UnGraph::default(),
			id_to_index: HashMap::new(),
		}
	}

	pub fn ensure_node(&mut self, id: &str, _label: &str) -> NodeIndex {
		if let Some(index) = self.id_to_index.get(id) {
			return *index;
		}
		let index = self.graph.add_node(());
		self.id_to_index.insert(id.to_string(), index);
		index
	}

	pub fn add_edge(&mut self, from: &str, to: &str) {
		let from_index = self.ensure_node(from, ".");
		let to_index = self.ensure_node(to, ".");
		self.graph.add_edge(from_index, to_index, ());
	}
}
