use std::collections::HashMap;
use std::env;
use std::fs::{self, File};
use std::io::{self, Write};
use std::path::{Path, PathBuf};
use std::time::{Instant, SystemTime, UNIX_EPOCH};

use scott::canonize::to_cgraph;
use scott::parse::from_dot;

#[derive(Clone, Debug)]
struct Entry {
	size: u32,
	group: u32,
	variant: u32,
	size_str: String,
	group_str: String,
	variant_str: String,
	path: PathBuf,
}

fn parse_entry(name: &str, path: PathBuf) -> Option<Entry> {
	if !name.starts_with("cfi-rigid-t2-") || !name.ends_with(".dot") {
		return None;
	}
	let stem = name.trim_end_matches(".dot");
	let parts: Vec<&str> = stem.split('-').collect();
	if parts.len() != 6 {
		return None;
	}
	let size_str = parts[3].to_string();
	let group_str = parts[4].to_string();
	let variant_str = parts[5].to_string();
	let size = size_str.parse().ok()?;
	let group = group_str.parse().ok()?;
	let variant = variant_str.parse().ok()?;
	Some(Entry {
		size,
		group,
		variant,
		size_str,
		group_str,
		variant_str,
		path,
	})
}

fn load_entries(dot_dir: &Path) -> io::Result<Vec<Entry>> {
	let mut entries = Vec::new();
	for entry in fs::read_dir(dot_dir)? {
		let entry = entry?;
		let path = entry.path();
		let name = match path.file_name().and_then(|n| n.to_str()) {
			Some(name) => name.to_string(),
			None => continue,
		};
		if let Some(parsed) = parse_entry(&name, path) {
			entries.push(parsed);
		}
	}
	entries.sort_by(|a, b| {
		(a.size, a.group, a.variant).cmp(&(b.size, b.group, b.variant))
	});
	Ok(entries)
}

#[cfg(unix)]
fn max_rss_bytes() -> Option<u64> {
	unsafe {
		let mut usage: libc::rusage = std::mem::zeroed();
		if libc::getrusage(libc::RUSAGE_SELF, &mut usage) != 0 {
			return None;
		}
		let factor = if cfg!(target_os = "macos") { 1_u64 } else { 1024_u64 };
		Some((usage.ru_maxrss as u64).saturating_mul(factor))
	}
}

#[cfg(not(unix))]
fn max_rss_bytes() -> Option<u64> {
	None
}

fn now_epoch_secs() -> f64 {
	SystemTime::now()
		.duration_since(UNIX_EPOCH)
		.map(|d| d.as_secs_f64())
		.unwrap_or_default()
}

fn usage() {
	eprintln!(
		"Usage: perf_baseline [--dot-dir DIR] [--max-n N] [--limit N] [--out BASE]\n\
Defaults:\n\
  --dot-dir data/isotest/cfi-rigid-t2-dot\n\
  --out results/perf_baseline\n\
Outputs: BASE.json and BASE.csv"
	);
}

fn main() -> io::Result<()> {
	let mut dot_dir = PathBuf::from("data/isotest/cfi-rigid-t2-dot");
	let mut max_n: Option<u32> = None;
	let mut limit: Option<usize> = None;
	let mut out_base = PathBuf::from("results/perf_baseline");

	let mut args = env::args().skip(1);
	while let Some(arg) = args.next() {
		match arg.as_str() {
			"--dot-dir" => {
				if let Some(value) = args.next() {
					dot_dir = PathBuf::from(value);
				}
			}
			"--max-n" => {
				if let Some(value) = args.next() {
					max_n = value.parse().ok();
				}
			}
			"--limit" => {
				if let Some(value) = args.next() {
					limit = value.parse().ok();
				}
			}
			"--out" => {
				if let Some(value) = args.next() {
					out_base = PathBuf::from(value);
				}
			}
			"--help" | "-h" => {
				usage();
				return Ok(());
			}
			unknown => {
				eprintln!("Unknown argument: {unknown}");
				usage();
				return Ok(());
			}
		}
	}

	if !dot_dir.is_dir() {
		return Err(io::Error::new(
			io::ErrorKind::NotFound,
			format!("Missing data directory: {}", dot_dir.display()),
		));
	}

	let entries = load_entries(&dot_dir)?;
	if entries.is_empty() {
		return Err(io::Error::new(
			io::ErrorKind::NotFound,
			format!("No .dot files found in {}", dot_dir.display()),
		));
	}

	if let Some(parent) = out_base.parent() {
		fs::create_dir_all(parent)?;
	}

	let started_at = now_epoch_secs();
	let mut records = Vec::new();
	let mut pairs: HashMap<(String, String), HashMap<u32, String>> = HashMap::new();
	let mut total_parse = 0.0_f64;
	let mut total_canon = 0.0_f64;
	let mut total_elapsed = 0.0_f64;
	let mut processed = 0_usize;

	let overall_start = Instant::now();
	for entry in entries {
		if let Some(max_n) = max_n {
			if entry.size > max_n {
				break;
			}
		}
		if let Some(limit) = limit {
			if processed >= limit {
				break;
			}
		}

		let parse_start = Instant::now();
		let graph = match from_dot(entry.path.to_str().unwrap_or_default()) {
			Ok(graph) => graph,
			Err(err) => {
				records.push(serde_json::json!({
					"problem_size": entry.size_str,
					"nodes": 0,
					"edges": 0,
					"task_id": format!("{}-{}", entry.size_str, entry.group_str),
					"graph": format!("{}.dot", entry.variant_str),
					"parse_time": 0.0,
					"canon_time": 0.0,
					"total_time": 0.0,
					"valid": false,
					"res_size": 0,
					"canonization": "",
					"error": format!("{err}"),
				}));
				processed += 1;
				continue;
			}
		};
		let parse_time = parse_start.elapsed().as_secs_f64();

		let canon_start = Instant::now();
		let canon = match to_cgraph(
			&graph,
			"$degree",
			"$depth > tree.parent_modality > $lexic",
			true,
			true,
			false,
		) {
			Ok(cgraph) => cgraph.to_string(),
			Err(err) => {
				records.push(serde_json::json!({
					"problem_size": entry.size_str,
					"nodes": graph.as_wrap().graph.node_count(),
					"edges": graph.as_wrap().graph.edge_count(),
					"task_id": format!("{}-{}", entry.size_str, entry.group_str),
					"graph": format!("{}.dot", entry.variant_str),
					"parse_time": parse_time,
					"canon_time": 0.0,
					"total_time": parse_time,
					"valid": false,
					"res_size": 0,
					"canonization": "",
					"error": format!("{err}"),
				}));
				processed += 1;
				continue;
			}
		};
		let canon_time = canon_start.elapsed().as_secs_f64();
		let total_time = parse_time + canon_time;

		let task_key = (entry.size_str.clone(), entry.group_str.clone());
		let entry_map = pairs.entry(task_key.clone()).or_insert_with(HashMap::new);
		let mut valid = true;
		if let Some(existing) = entry_map.get(&1).or_else(|| entry_map.get(&2)) {
			valid = *existing == canon;
		}
		entry_map.insert(entry.variant, canon.clone());

		let nodes = graph.as_wrap().graph.node_count();
		let edges = graph.as_wrap().graph.edge_count();
		records.push(serde_json::json!({
			"problem_size": entry.size_str,
			"nodes": nodes,
			"edges": edges,
			"task_id": format!("{}-{}", entry.size_str, entry.group_str),
			"graph": format!("{}.dot", entry.variant_str),
			"parse_time": parse_time,
			"canon_time": canon_time,
			"total_time": total_time,
			"valid": valid,
			"res_size": canon.len(),
			"canonization": canon,
		}));

		total_parse += parse_time;
		total_canon += canon_time;
		total_elapsed += total_time;
		processed += 1;
	}

	let wall_time = overall_start.elapsed().as_secs_f64();
	let finished_at = now_epoch_secs();

	let profile = if cfg!(debug_assertions) { "debug" } else { "release" };
	let summary = serde_json::json!({
		"started_at": started_at,
		"finished_at": finished_at,
		"profile": profile,
		"dot_dir": dot_dir.display().to_string(),
		"max_n": max_n,
		"limit": limit,
		"processed": processed,
		"totals": {
			"parse_time": total_parse,
			"canon_time": total_canon,
			"total_time": total_elapsed,
			"wall_time": wall_time,
			"max_rss_bytes": max_rss_bytes(),
		},
	});

	let json_path = out_base.with_extension("json");
	let csv_path = out_base.with_extension("csv");

	let json_payload = serde_json::json!({
		"summary": summary,
		"records": records,
	});
	fs::write(&json_path, serde_json::to_string_pretty(&json_payload).unwrap())?;

	let mut csv = String::new();
	csv.push_str(
		"problem_size,nodes,edges,task_id,graph,parse_time,canon_time,total_time,valid,res_size,canonization,profile\n",
	);
	for record in json_payload["records"].as_array().unwrap_or(&Vec::new()) {
		let problem_size = record["problem_size"].as_str().unwrap_or("");
		let nodes = record["nodes"].as_u64().unwrap_or(0);
		let edges = record["edges"].as_u64().unwrap_or(0);
		let task_id = record["task_id"].as_str().unwrap_or("");
		let graph = record["graph"].as_str().unwrap_or("");
		let parse_time = record["parse_time"].as_f64().unwrap_or(0.0);
		let canon_time = record["canon_time"].as_f64().unwrap_or(0.0);
		let total_time = record["total_time"].as_f64().unwrap_or(0.0);
		let valid = record["valid"].as_bool().unwrap_or(false);
		let res_size = record["res_size"].as_u64().unwrap_or(0);
		let canonization = record["canonization"].as_str().unwrap_or("");
		csv.push_str(&format!(
			"{},{},{},{},{},{},{},{},{},{},\"{}\",{}\n",
			problem_size,
			nodes,
			edges,
			task_id,
			graph,
			parse_time,
			canon_time,
			total_time,
			valid,
			res_size,
			canonization.replace('"', "\"\""),
			profile,
		));
	}

	let mut csv_file = File::create(&csv_path)?;
	csv_file.write_all(csv.as_bytes())?;

	println!("Wrote {}", json_path.display());
	println!("Wrote {}", csv_path.display());

	Ok(())
}
