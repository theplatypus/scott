pub mod canonize;
pub mod cgraph;
pub mod dag;
pub mod dot;
pub mod error;
pub mod graph;
pub mod parse;
pub mod tree;
mod py;

use pyo3::prelude::*;

#[pymodule]
fn _scott(py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
	py::init_module(py, m)
}
