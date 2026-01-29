use std::fs;

use crate::graph::GraphWrap;

fn strip_quotes(input: &str) -> &str {
	let trimmed = input.trim();
	if trimmed.len() >= 2 {
		let bytes = trimmed.as_bytes();
		if (bytes[0] == b'"' && bytes[trimmed.len() - 1] == b'"')
			|| (bytes[0] == b'\'' && bytes[trimmed.len() - 1] == b'\'')
		{
			return &trimmed[1..trimmed.len() - 1];
		}
	}
	trimmed
}

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

fn parse_attrs(line: &str) -> std::collections::HashMap<String, String> {
	let mut attrs = std::collections::HashMap::new();
	let open = match line.find('[') {
		Some(pos) => pos,
		None => return attrs,
	};
	let close = match line[open + 1..].find(']') {
		Some(pos) => open + 1 + pos,
		None => return attrs,
	};
	let body = &line[open + 1..close];
	for entry in body.split(',') {
		let mut parts = entry.splitn(2, '=');
		let key = parts.next().unwrap_or("").trim();
		let value = parts.next().unwrap_or("").trim();
		if !key.is_empty() {
			attrs.insert(key.to_string(), strip_quotes(value).to_string());
		}
	}
	attrs
}

pub fn parse_dot_content(content: &str) -> Result<GraphWrap, String> {
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

		let attrs = parse_attrs(line);

		if line.contains("--") {
			let mut parts = line.splitn(2, "--");
			let left = parts.next().unwrap_or("");
			let right = parts.next().unwrap_or("");
			let left_id = parse_node_id(left)
				.map_err(|err| format!("line {}: {}", line_no + 1, err))?;
			let right_clean = strip_trailing_semicolon(right);
			let right_id = parse_node_id(right_clean)
				.map_err(|err| format!("line {}: {}", line_no + 1, err))?;
			let weight = attrs.get("weight").map(|val| val.as_str()).unwrap_or("1");
			graph.add_edge_with_modality(&left_id, &right_id, weight);
			continue;
		}

		if line.contains('[') {
			let id = parse_node_id(line)
				.map_err(|err| format!("line {}: {}", line_no + 1, err))?;
			let label = attrs.get("label").map(|val| val.as_str()).unwrap_or(".");
			graph.ensure_node(&id, label);
		}
	}

	Ok(graph)
}

pub fn parse_dot_file(path: &str) -> Result<GraphWrap, String> {
	let content = fs::read_to_string(path).map_err(|err| err.to_string())?;
	parse_dot_content(&content)
}
