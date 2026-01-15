use std::fmt;

#[derive(Debug, Clone)]
pub enum ScottError {
	Io(String),
	Parse(String),
	MissingNode(String),
	InvalidRule(String),
	Unsupported(String),
}

impl fmt::Display for ScottError {
	fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
		match self {
			Self::Io(msg) => write!(f, "io error: {msg}"),
			Self::Parse(msg) => write!(f, "parse error: {msg}"),
			Self::MissingNode(msg) => write!(f, "missing node: {msg}"),
			Self::InvalidRule(msg) => write!(f, "invalid rule: {msg}"),
			Self::Unsupported(msg) => write!(f, "unsupported: {msg}"),
		}
	}
}

impl std::error::Error for ScottError {}

pub type ScottResult<T> = Result<T, ScottError>;
