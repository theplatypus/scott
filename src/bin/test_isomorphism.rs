use petgraph::algo::is_isomorphic_matching;

use scott::canonize::to_cgraph;
use scott::parse::from_dot;

fn main() {
    let h = from_dot("./data/isotest/cfi-rigid-t2-dot/cfi-rigid-t2-0020-01-1.dot")
        .expect("failed to parse H");
    let g = from_dot("./data/isotest/cfi-rigid-t2-dot/cfi-rigid-t2-0020-01-2.dot")
        .expect("failed to parse G");

    let h_c = to_cgraph(&h, "$degree", "$depth > tree.parent_modality > $lexic", true, true, false)
        .expect("failed to canonize H");
    let g_c = to_cgraph(&g, "$degree", "$depth > tree.parent_modality > $lexic", true, true, false)
        .expect("failed to canonize G");
    assert_eq!(h_c, g_c, "expected H and G canonical forms to match");
    println!("Success: H and G canonical forms match");

    let g_iso = g.as_wrap().to_ungraph();
    let h_iso = h.as_wrap().to_ungraph();
    let iso = is_isomorphic_matching(&g_iso, &h_iso, |_, _| true, |_, _| true);
    assert!(iso, "expected H and G to be isomorphic");
    println!("Success: H and G are isomorphic");

    let e = from_dot("./data/isotest/cfi-rigid-t2-dot/cfi-rigid-t2-0020-02-1.dot")
        .expect("failed to parse E");
    let f = from_dot("./data/isotest/cfi-rigid-t2-dot/cfi-rigid-t2-0020-02-2.dot")
        .expect("failed to parse F");

    let e_c = to_cgraph(&e, "$degree", "$depth > tree.parent_modality > $lexic", true, true, false)
        .expect("failed to canonize E");
    let f_c = to_cgraph(&f, "$degree", "$depth > tree.parent_modality > $lexic", true, true, false)
        .expect("failed to canonize F");
    assert_eq!(e_c, f_c, "expected E and F canonical forms to match");
    println!("Success: E and F canonical forms match");

    let e_iso = e.as_wrap().to_ungraph();
    let f_iso = f.as_wrap().to_ungraph();
    let iso = is_isomorphic_matching(&e_iso, &f_iso, |_, _| true, |_, _| true);
    assert!(iso, "expected E and F to be isomorphic");
    println!("Success: E and F are isomorphic");

    let g_e_equal = g_c == e_c;
    let g_iso = g.as_wrap().to_ungraph();
    let e_iso = e.as_wrap().to_ungraph();
    let g_e_iso = is_isomorphic_matching(&g_iso, &e_iso, |_, _| true, |_, _| true);

    assert!(!g_e_equal, "expected G and E canonical forms to differ");
    println!("Success: G and E canonical forms differ");

    assert!(!g_e_iso, "expected G and E not to be isomorphic");
    println!("Success: G and E are not isomorphic");
}
