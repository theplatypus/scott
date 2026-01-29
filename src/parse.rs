use crate::dot::{parse_dot_content, parse_dot_file};
use crate::error::{ScottError, ScottResult};
use crate::graph::Graph;

pub fn from_dot(path: &str) -> ScottResult<Graph> {
	let graph = parse_dot_file(path).map_err(ScottError::Parse)?;
	Ok(Graph::from_wrap(graph))
}

pub fn from_dot_str(dot_content: &str) -> ScottResult<Graph> {
	let graph = parse_dot_content(dot_content).map_err(ScottError::Parse)?;
	Ok(Graph::from_wrap(graph))
}

pub fn from_graph6(_input: &str) -> ScottResult<Graph> {
	Err(ScottError::Unsupported(
		"graph6 parsing not implemented yet".to_string(),
	))
}
