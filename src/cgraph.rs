use std::fmt;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct CGraph {
	value: String,
}

impl CGraph {
	pub fn new(value: String) -> Self {
		Self { value }
	}

	pub fn as_str(&self) -> &str {
		&self.value
	}
}

impl fmt::Display for CGraph {
	fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
		write!(f, "{}", self.value)
	}
}
