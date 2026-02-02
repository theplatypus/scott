pub mod canonize;
pub mod cgraph;
pub mod dag;
pub mod dot;
pub mod error;
pub mod graph;
pub mod parse;
pub mod tree;

#[cfg(feature = "python")]
mod py;

#[cfg(feature = "python")]
use pyo3::prelude::*;

#[cfg(feature = "python")]
#[pymodule]
fn _scott(py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
	py::init_module(py, m)
}
