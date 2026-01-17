use petgraph::algo::is_isomorphic_matching;

use scott::parse::from_dot;

fn main() {
    let h = from_dot("./data/isotest/cfi-rigid-t2-dot/cfi-rigid-t2-0020-01-1.dot")
        .expect("failed to parse H");
    let g = from_dot("./data/isotest/cfi-rigid-t2-dot/cfi-rigid-t2-0020-01-2.dot")
        .expect("failed to parse G");

    let g_iso = g.as_wrap().to_ungraph();
    let h_iso = h.as_wrap().to_ungraph();
    let iso = is_isomorphic_matching(&g_iso, &h_iso, |_, _| true, |_, _| true);
    assert!(iso, "expected H and G to be isomorphic");

    let e = from_dot("./data/isotest/cfi-rigid-t2-dot/cfi-rigid-t2-0020-02-1.dot")
        .expect("failed to parse E");
    let f = from_dot("./data/isotest/cfi-rigid-t2-dot/cfi-rigid-t2-0020-02-2.dot")
        .expect("failed to parse F");

    let e_iso = e.as_wrap().to_ungraph();
    let f_iso = f.as_wrap().to_ungraph();
    let iso = is_isomorphic_matching(&e_iso, &f_iso, |_, _| true, |_, _| true);
    assert!(iso, "expected E and F to be isomorphic");

    let g_iso = g.as_wrap().to_ungraph();
    let e_iso = e.as_wrap().to_ungraph();
    let g_e_iso = is_isomorphic_matching(&g_iso, &e_iso, |_, _| true, |_, _| true);

    assert!(!g_e_iso, "expected G and E not to be isomorphic");
}
