use scott::canonize::to_cgraph;
use scott::parse::from_dot;

fn main() {
	let cobound = from_dot("data/bound_cases/cobound.dot").expect("failed to parse cobound");
	let cobound_c = to_cgraph(
		&cobound,
		"$degree",
		"$depth > tree.parent_modality > $lexic",
		true,
		true,
		false,
	)
	.expect("failed to canonize cobound");
	println!("cobound canonical: {}", cobound_c.as_str());
	assert_eq!(
		cobound_c.as_str(),
		"(A:1, (*{$1}:1)C:1, (*{$1}:1)D:1)B",
		"unexpected cobound canonical form"
	);

	let inbound = from_dot("data/bound_cases/simple_inbound.dot").expect("failed to parse inbound");
	let inbound_c = to_cgraph(
		&inbound,
		"$degree",
		"$depth > tree.parent_modality > $lexic",
		true,
		true,
		false,
	)
	.expect("failed to canonize inbound");
	println!("inbound canonical: {}", inbound_c.as_str());
	assert_eq!(
		inbound_c.as_str(),
		"(E:1, ((A:1).#2{$1}:1)B:1, ((A:1).#2{$1}:1)C:1)D",
		"unexpected inbound canonical form"
	);
}
