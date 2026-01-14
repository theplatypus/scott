use petgraph::algo::is_isomorphic_matching;

use scott::dot::parse_dot_file;

fn main() {
    let h = parse_dot_file("./data/isotest/cfi-rigid-t2-dot/cfi-rigid-t2-0020-01-1.dot")
        .expect("failed to parse H");
    let g = parse_dot_file("./data/isotest/cfi-rigid-t2-dot/cfi-rigid-t2-0020-01-2.dot")
        .expect("failed to parse G");

    let iso = is_isomorphic_matching(&g.graph, &h.graph, |_, _| true, |_, _| true);
    assert!(iso, "expected H and G to be isomorphic");

    let e = parse_dot_file("./data/isotest/cfi-rigid-t2-dot/cfi-rigid-t2-0020-02-1.dot")
        .expect("failed to parse E");
    let f = parse_dot_file("./data/isotest/cfi-rigid-t2-dot/cfi-rigid-t2-0020-02-2.dot")
        .expect("failed to parse F");

    let iso = is_isomorphic_matching(&e.graph, &f.graph, |_, _| true, |_, _| true);
    assert!(iso, "expected E and F to be isomorphic");

    let g_e_iso = is_isomorphic_matching(&g.graph, &e.graph, |_, _| true, |_, _| true);

    assert!(!g_e_iso, "expected G and E not to be isomorphic");
}
