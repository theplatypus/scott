use petgraph::algo::is_isomorphic_matching;

use scott::canonize::to_cgraph;
use scott::dot::parse_dot_file;

fn main() {
    let h = parse_dot_file("./data/isotest/cfi-rigid-t2-dot/cfi-rigid-t2-0020-01-1.dot")
        .expect("failed to parse H");
    let g = parse_dot_file("./data/isotest/cfi-rigid-t2-dot/cfi-rigid-t2-0020-01-2.dot")
        .expect("failed to parse G");

    let h_c = to_cgraph(&h, "$degree", "$depth > tree.parent_modality > $lexic", true, true, false);
    let g_c = to_cgraph(&g, "$degree", "$depth > tree.parent_modality > $lexic", true, true, false);
    assert_eq!(h_c, g_c, "expected H and G canonical forms to match");

    let iso = is_isomorphic_matching(&g.graph, &h.graph, |_, _| true, |_, _| true);
    assert!(iso, "expected H and G to be isomorphic");

    let e = parse_dot_file("./data/isotest/cfi-rigid-t2-dot/cfi-rigid-t2-0020-02-1.dot")
        .expect("failed to parse E");
    let f = parse_dot_file("./data/isotest/cfi-rigid-t2-dot/cfi-rigid-t2-0020-02-2.dot")
        .expect("failed to parse F");

    let e_c = to_cgraph(&e, "$degree", "$depth > tree.parent_modality > $lexic", true, true, false);
    let f_c = to_cgraph(&f, "$degree", "$depth > tree.parent_modality > $lexic", true, true, false);
    assert_eq!(e_c, f_c, "expected E and F canonical forms to match");

    let iso = is_isomorphic_matching(&e.graph, &f.graph, |_, _| true, |_, _| true);
    assert!(iso, "expected E and F to be isomorphic");

    let g_e_equal = g_c == e_c;
    let g_e_iso = is_isomorphic_matching(&g.graph, &e.graph, |_, _| true, |_, _| true);

    assert!(!g_e_equal, "expected G and E canonical forms to differ");
    assert!(!g_e_iso, "expected G and E not to be isomorphic");
}
