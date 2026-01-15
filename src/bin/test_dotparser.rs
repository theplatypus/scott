use petgraph::algo::is_isomorphic_matching;

use scott::parse::from_dot;

fn main() {
    let h = from_dot("./data/isotest/cfi-rigid-t2-dot/cfi-rigid-t2-0020-01-1.dot")
        .expect("failed to parse H");
    let g = from_dot("./data/isotest/cfi-rigid-t2-dot/cfi-rigid-t2-0020-01-2.dot")
        .expect("failed to parse G");

    let iso = is_isomorphic_matching(&g.as_wrap().graph, &h.as_wrap().graph, |_, _| true, |_, _| true);
    assert!(iso, "expected H and G to be isomorphic");

    let e = from_dot("./data/isotest/cfi-rigid-t2-dot/cfi-rigid-t2-0020-02-1.dot")
        .expect("failed to parse E");
    let f = from_dot("./data/isotest/cfi-rigid-t2-dot/cfi-rigid-t2-0020-02-2.dot")
        .expect("failed to parse F");

    let iso = is_isomorphic_matching(&e.as_wrap().graph, &f.as_wrap().graph, |_, _| true, |_, _| true);
    assert!(iso, "expected E and F to be isomorphic");

    let g_e_iso = is_isomorphic_matching(&g.as_wrap().graph, &e.as_wrap().graph, |_, _| true, |_, _| true);

    assert!(!g_e_iso, "expected G and E not to be isomorphic");
}
