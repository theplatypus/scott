use scott::dot::parse_dot_file;

fn main() {
	let graph = parse_dot_file("data/bound_cases/cobound.dot").expect("failed to parse dot");

	println!("nodes: {}", graph.graph.node_count());
	println!("edges: {}", graph.graph.edge_count());

	for node_index in graph.graph.node_indices() {
		let node = &graph.graph[node_index];
		println!("node {} label {}", node.id, node.label);
	}

	for edge_index in graph.graph.edge_indices() {
		let (a, b) = graph.graph.edge_endpoints(edge_index).expect("edge endpoints");
		let edge = &graph.graph[edge_index];
		let a_id = &graph.graph[a].id;
		let b_id = &graph.graph[b].id;
		println!("edge {} {} -- {} modality {}", edge.id, a_id, b_id, edge.modality);
	}
}
