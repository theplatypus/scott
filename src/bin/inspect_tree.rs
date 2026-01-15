use std::collections::HashSet;

use scott::dot::parse_dot_file;
use scott::tree::to_tree_string;

fn main() {
	let graph = parse_dot_file("data/bound_cases/cobound.dot").expect("failed to parse dot");
	let ids_ignore: HashSet<String> = HashSet::new();
	let dag = graph
		.to_dag_skeleton("A", &ids_ignore)
		.expect("failed to build dag skeleton");
	let tree = to_tree_string(&dag, "A", &ids_ignore).expect("failed to build tree string");
	println!("{tree}");
}
