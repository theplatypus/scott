use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::wrap_pyfunction;

use crate::canonize::{canonical_node_order, to_cgraph};
use crate::graph::Graph;
use crate::parse::{from_dot, from_dot_str};

#[pyclass]
pub struct PyGraph {
	inner: Graph,
}

#[pymethods]
impl PyGraph {
	#[getter]
	fn node_count(&self) -> usize {
		self.inner.as_wrap().graph.node_count()
	}

	#[getter]
	fn edge_count(&self) -> usize {
		self.inner.as_wrap().graph.edge_count()
	}

	fn node_labels(&self) -> Vec<(String, String)> {
		let wrap = self.inner.as_wrap();
		let mut nodes = Vec::new();
		for index in wrap.graph.node_indices() {
			let node = &wrap.graph[index];
			nodes.push((node.id.clone(), node.label.clone()));
		}
		nodes
	}

	fn edges(&self) -> Vec<(String, String, String, String)> {
		let wrap = self.inner.as_wrap();
		let mut edges = Vec::new();
		for edge_index in wrap.graph.edge_indices() {
			let (a, b) = match wrap.graph.edge_endpoints(edge_index) {
				Some(endpoints) => endpoints,
				None => continue,
			};
			let edge = &wrap.graph[edge_index];
			let id_a = wrap.graph[a].id.clone();
			let id_b = wrap.graph[b].id.clone();
			edges.push((edge.id.clone(), id_a, id_b, edge.modality.clone()));
		}
		edges
	}
}

#[pyclass]
pub struct PyCGraph {
	value: String,
}

#[pymethods]
impl PyCGraph {
	fn as_str(&self) -> &str {
		&self.value
	}

	fn __str__(&self) -> String {
		self.value.clone()
	}

	fn __repr__(&self) -> String {
		self.value.clone()
	}
}

fn map_err(err: impl ToString) -> PyErr {
	PyValueError::new_err(err.to_string())
}

#[pyfunction]
fn parse_dot(path: &str) -> PyResult<PyGraph> {
	let graph = from_dot(path).map_err(map_err)?;
	Ok(PyGraph { inner: graph })
}

#[pyfunction]
fn parse_dot_string(content: &str) -> PyResult<PyGraph> {
	let graph = from_dot_str(content).map_err(map_err)?;
	Ok(PyGraph { inner: graph })
}

#[pyfunction]
fn graph_from_edges(nodes: Vec<(String, String)>, edges: Vec<(String, String, String)>) -> PyResult<PyGraph> {
	let mut graph = Graph::new();
	for (node_id, label) in nodes {
		graph.ensure_node(&node_id, &label);
	}
	for (id_a, id_b, modality) in edges {
		graph.add_edge_with_modality(&id_a, &id_b, &modality);
	}
	Ok(PyGraph { inner: graph })
}

#[pyfunction]
fn to_cgraph_py(
	graph: &PyGraph,
	candidate_rule: Option<&str>,
	branch_rule: Option<&str>,
	allow_hashes: Option<bool>,
	compress: Option<bool>,
	compact: Option<bool>,
) -> PyResult<PyCGraph> {
	let candidate_rule = candidate_rule.unwrap_or("$degree");
	let branch_rule = branch_rule.unwrap_or("$depth > tree.parent_modality > $lexic");
	let allow_hashes = allow_hashes.unwrap_or(true);
	let compress = compress.unwrap_or(true);
	let compact = compact.unwrap_or(false);

	let cgraph = to_cgraph(
		&graph.inner,
		candidate_rule,
		branch_rule,
		allow_hashes,
		compress,
		compact,
	)
	.map_err(map_err)?;

	Ok(PyCGraph {
		value: cgraph.to_string(),
	})
}

#[pyfunction]
#[pyo3(signature = (graph, candidate_rule=None, branch_rule=None, allow_hashes=None, compact=None))]
fn canonical_node_order_py(
	graph: &PyGraph,
	candidate_rule: Option<&str>,
	branch_rule: Option<&str>,
	allow_hashes: Option<bool>,
	compact: Option<bool>,
) -> PyResult<Vec<String>> {
	let candidate_rule = candidate_rule.unwrap_or("$degree");
	let branch_rule = branch_rule.unwrap_or("$depth > tree.parent_modality > $lexic");
	let allow_hashes = allow_hashes.unwrap_or(true);
	let compact = compact.unwrap_or(false);

	let order = canonical_node_order(
		&graph.inner,
		candidate_rule,
		branch_rule,
		allow_hashes,
		compact,
	)
	.map_err(map_err)?;

	Ok(order)
}

pub fn init_module(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
	m.add_class::<PyGraph>()?;
	m.add_class::<PyCGraph>()?;
	m.add_function(wrap_pyfunction!(parse_dot, m)?)?;
	m.add_function(wrap_pyfunction!(parse_dot_string, m)?)?;
	m.add_function(wrap_pyfunction!(graph_from_edges, m)?)?;
	m.add_function(wrap_pyfunction!(to_cgraph_py, m)?)?;
	m.add_function(wrap_pyfunction!(canonical_node_order_py, m)?)?;
	Ok(())
}
