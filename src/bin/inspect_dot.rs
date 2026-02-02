use scott::parse::from_dot;

fn main() {
	let graph = from_dot("data/bound_cases/cobound.dot").expect("failed to parse dot");

	println!("nodes: {}", graph.as_wrap().graph.node_count());
	println!("edges: {}", graph.as_wrap().graph.edge_count());

	for node_index in graph.as_wrap().graph.node_indices() {
		let node = &graph.as_wrap().graph[node_index];
		println!("node {} label {}", node.id, node.label);
	}

	for edge_index in graph.as_wrap().graph.edge_indices() {
		let (a, b) = graph
			.as_wrap()
			.graph
			.edge_endpoints(edge_index)
			.expect("edge endpoints");
		let edge = &graph.as_wrap().graph[edge_index];
		let a_id = &graph.as_wrap().graph[a].id;
		let b_id = &graph.as_wrap().graph[b].id;
		println!("edge {} {} -- {} modality {}", edge.id, a_id, b_id, edge.modality);
	}
}
