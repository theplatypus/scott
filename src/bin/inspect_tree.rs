use std::collections::HashSet;

use scott::parse::from_dot;
use scott::tree::to_tree_string;

fn main() {
	let graph = from_dot("data/bound_cases/cobound.dot").expect("failed to parse dot");
	let ids_ignore: HashSet<String> = HashSet::new();
	let dag = graph
		.to_dag_skeleton("A", &ids_ignore)
		.expect("failed to build dag skeleton");
	let tree = to_tree_string(dag.as_wrap(), "A", &ids_ignore).expect("failed to build tree string");
	println!("{tree}");
}
