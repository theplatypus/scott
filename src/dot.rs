use std::fs;

use crate::graph::GraphWrap;

fn strip_trailing_semicolon(input: &str) -> &str {
	let trimmed = input.trim();
	trimmed.strip_suffix(';').unwrap_or(trimmed).trim()
}

fn parse_node_id(input: &str) -> Result<String, String> {
	let trimmed = input.trim();
	if trimmed.is_empty() {
		return Err("empty node id".to_string());
	}
	let id = trimmed
		.split(|ch: char| ch.is_whitespace() || ch == '[')
		.next()
		.unwrap_or("")
		.trim();
	if id.is_empty() {
		return Err(format!("invalid node id in '{}'", input));
	}
	Ok(id.to_string())
}

pub fn parse_dot_file(path: &str) -> Result<GraphWrap, String> {
	let content = fs::read_to_string(path).map_err(|err| err.to_string())?;
	let mut graph = GraphWrap::new();

	for (line_no, raw_line) in content.lines().enumerate() {
		let line = raw_line.trim();
		if line.is_empty()
			|| line.starts_with("graph")
			|| line.starts_with("strict graph")
			|| line.starts_with('}')
		{
			continue;
		}

		if line.contains("--") {
			let mut parts = line.splitn(2, "--");
			let left = parts.next().unwrap_or("");
			let right = parts.next().unwrap_or("");
			let left_id = parse_node_id(left)
				.map_err(|err| format!("line {}: {}", line_no + 1, err))?;
			let right_clean = strip_trailing_semicolon(right);
			let right_id = parse_node_id(right_clean)
				.map_err(|err| format!("line {}: {}", line_no + 1, err))?;
			graph.add_edge(&left_id, &right_id);
			continue;
		}

		if line.contains('[') {
			let id = parse_node_id(line)
				.map_err(|err| format!("line {}: {}", line_no + 1, err))?;
			graph.ensure_node(&id, ".");
		}
	}

	Ok(graph)
}
