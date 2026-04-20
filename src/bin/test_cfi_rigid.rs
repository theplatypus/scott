use std::collections::HashMap;
use std::env;
use std::fs::{self, File};
use std::io::{self, Write};
use std::path::Path;
use std::time::Instant;

use scott::canonize::to_cgraph;
use scott::parse::from_dot;

const DOT_DIR: &str = "data/isotest/cfi-rigid-t2-dot";

#[derive(Clone)]
struct Entry {
    size: i32,
    group: i32,
    variant: i32,
    size_str: String,
    group_str: String,
    variant_str: String,
    path: String,
}

#[derive(Clone)]
struct Variant {
    canon: String,
    path: String,
}

fn parse_filename(name: &str) -> Option<(String, String, String, i32, i32, i32)> {
    if !name.starts_with("cfi-rigid-t2-") || !name.ends_with(".dot") {
        return None;
    }
    let stem = name.strip_suffix(".dot")?;
    let parts: Vec<&str> = stem.split('-').collect();
    if parts.len() != 6 {
        return None;
    }
    let size_str = parts[3].to_string();
    let group_str = parts[4].to_string();
    let variant_str = parts[5].to_string();
    let size = size_str.parse::<i32>().ok()?;
    let group = group_str.parse::<i32>().ok()?;
    let variant = variant_str.parse::<i32>().ok()?;
    Some((size_str, group_str, variant_str, size, group, variant))
}

fn load_entries(dot_dir: &str) -> io::Result<Vec<Entry>> {
    let mut entries = Vec::new();
    for entry in fs::read_dir(dot_dir)? {
        let entry = entry?;
        let file_name = entry.file_name();
        let name = match file_name.to_str() {
            Some(value) => value,
            None => continue,
        };
        let parsed = match parse_filename(name) {
            Some(value) => value,
            None => continue,
        };
        let (size_str, group_str, variant_str, size, group, variant) = parsed;
        let path = entry.path().to_string_lossy().to_string();
        entries.push(Entry {
            size,
            group,
            variant,
            size_str,
            group_str,
            variant_str,
            path,
        });
    }
    entries.sort_by(|a, b| (a.size, a.group, a.variant).cmp(&(b.size, b.group, b.variant)));
    Ok(entries)
}

fn canon_trace(path: &str) -> Result<(usize, usize, String, f64), String> {
    let graph = from_dot(path).map_err(|err| format!("{err}"))?;
    let nodes = graph.as_wrap().graph.node_count();
    let edges = graph.as_wrap().graph.edge_count();
    let start = Instant::now();
    let canon = to_cgraph(
        &graph,
        "$degree",
        "$depth > tree.parent_modality > $lexic",
        true,
        true,
        false,
    )
    .map_err(|err| format!("{err}"))?;
    let elapsed = start.elapsed().as_secs_f64();
    Ok((nodes, edges, canon.to_string(), elapsed))
}

fn csv_escape(value: &str) -> String {
    let needs_quotes = value.contains(',') || value.contains('"') || value.contains('\n');
    if !needs_quotes {
        return value.to_string();
    }
    let escaped = value.replace('"', "\"\"");
    format!("\"{}\"", escaped)
}

fn write_csv(path: &str, rows: &[Vec<String>]) -> io::Result<()> {
    let mut file = File::create(path)?;
    writeln!(
        file,
        ",problem_size,nodes,edges,task_id,graph,time,valid,res_size,canonization"
    )?;
    for (idx, row) in rows.iter().enumerate() {
        let mut fields = Vec::with_capacity(row.len() + 1);
        fields.push(idx.to_string());
        for value in row {
            fields.push(csv_escape(value));
        }
        writeln!(file, "{}", fields.join(","))?;
    }
    Ok(())
}

fn main() -> Result<(), String> {
    let mut max_n: Option<i32> = None;
	let mut out_path = String::from("results/results_cfi-rigid-rs.csv");

    let mut args = env::args().skip(1);
    while let Some(arg) = args.next() {
        match arg.as_str() {
            "-n" => {
                let value = args.next().ok_or("missing value for -n")?;
                max_n = Some(value.parse::<i32>().map_err(|_| "invalid -n value")?);
            }
            "--out" => {
                let value = args.next().ok_or("missing value for --out")?;
                out_path = value;
            }
            _ => {
                return Err(format!("unknown argument: {arg}"));
            }
        }
    }

    if !Path::new(DOT_DIR).is_dir() {
        return Err(format!("Missing data directory: {DOT_DIR}"));
    }

    let entries = load_entries(DOT_DIR).map_err(|err| format!("{err}"))?;
    if entries.is_empty() {
        return Err(format!("No .dot files found in {DOT_DIR}"));
    }

    let mut pairs: HashMap<(String, String), HashMap<i32, Variant>> = HashMap::new();
    let mut rows: Vec<Vec<String>> = Vec::new();

    let total = entries.len();
    let mut processed = 0usize;

    for entry in entries {
        if let Some(limit) = max_n {
            if entry.size > limit {
                break;
            }
        }

        let (nodes, edges, canon, elapsed) = canon_trace(&entry.path)?;
        let task_id = format!("{}-{}", entry.size_str, entry.group_str);
        let graph_id = format!("{}.dot", entry.variant_str);

        let variants = pairs
            .entry((entry.size_str.clone(), entry.group_str.clone()))
            .or_insert_with(HashMap::new);

        let mut valid = true;
        if let Some(reference) = variants.get(&1).or_else(|| variants.get(&2)) {
            valid = reference.canon == canon;
        }

        variants.insert(
            entry.variant,
            Variant {
                canon: canon.clone(),
                path: entry.path.clone(),
            },
        );

        rows.push(vec![
            entry.size_str.clone(),
            nodes.to_string(),
            edges.to_string(),
            task_id.clone(),
            graph_id.clone(),
            elapsed.to_string(),
            valid.to_string(),
            canon.len().to_string(),
            canon.clone(),
        ]);

        processed += 1;
        println!(
            "Processed {}/{}: size={} group={} variant={} nodes={} edges={} time={:.4} valid={}",
            processed,
            total,
            entry.size_str,
            entry.group_str,
            entry.variant,
            nodes,
            edges,
            elapsed,
            if valid { "True" } else { "False" }
        );
    }

    let mut total_pairs = 0;
    let mut pair_mismatches = 0;
    let mut cross_mismatches = 0;
    let mut by_size: HashMap<String, HashMap<String, String>> = HashMap::new();

    let mut keys: Vec<(String, String)> = pairs.keys().cloned().collect();
    keys.sort_by(|a, b| a.cmp(b));

    for (size_str, group_str) in keys {
        let variants = match pairs.get(&(size_str.clone(), group_str.clone())) {
            Some(value) => value,
            None => continue,
        };
        let variant_a = match variants.get(&1) {
            Some(value) => value,
            None => {
                println!("Skipping incomplete pair for size {size_str} group {group_str}");
                continue;
            }
        };
        let variant_b = match variants.get(&2) {
            Some(value) => value,
            None => {
                println!("Skipping incomplete pair for size {size_str} group {group_str}");
                continue;
            }
        };
        total_pairs += 1;
        if variant_a.canon != variant_b.canon {
            pair_mismatches += 1;
            println!("Mismatch: size {size_str} group {group_str}");
            println!("  {}", variant_a.path);
            println!("  {}", variant_b.path);
            continue;
        }

        let groups = by_size.entry(size_str.clone()).or_insert_with(HashMap::new);
        for (other_group, other_canon) in groups.iter() {
            if &variant_a.canon == other_canon {
                cross_mismatches += 1;
                println!("Collision: size {size_str} groups {other_group} and {group_str}");
                println!("  {}", variant_a.path);
                println!("  {}", variant_b.path);
            }
        }
        groups.insert(group_str.clone(), variant_a.canon.clone());
    }

	if let Some(parent) = Path::new(&out_path).parent() {
		if !parent.as_os_str().is_empty() {
			fs::create_dir_all(parent).map_err(|err| format!("{err}"))?;
		}
	}
	write_csv(&out_path, &rows).map_err(|err| format!("{err}"))?;

    println!("Checked {total_pairs} pair(s); {pair_mismatches} mismatch(es).");
    println!("Checked cross-group uniqueness; {cross_mismatches} collision(s).");

    // Do not stop (return an error) in case of mismatches/collisions; just report them.
    if pair_mismatches > 0 || cross_mismatches > 0 {
        println!("Mismatches or collisions were detected, but not exiting with an error.");
    }

    Ok(())
}
