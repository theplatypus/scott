use petgraph::algo::is_isomorphic_matching;
use petgraph::graph::NodeIndex;
use petgraph::graph::UnGraph;
use petgraph::graph6::from_graph6_representation;

use scott::canonize::to_cgraph;
use scott::graph::GraphWrap;

fn build_scott_graph(n: usize, edges: &[(NodeIndex, NodeIndex)]) -> GraphWrap {
    let mut graph = GraphWrap::new();
    for i in 0..n {
        let id = (i + 1).to_string();
        graph.ensure_node(&id, ".");
    }
    for (u, v) in edges {
        let u_id = (u.index() + 1).to_string();
        let v_id = (v.index() + 1).to_string();
        graph.add_edge(&u_id, &v_id);
    }
    graph
}

fn main() {
    let input = "Gr|Kto".to_string();
    let (n, edges) = from_graph6_representation::<NodeIndex>(input);
    println!("nodes: {}", n);
    println!("edges: {}", edges.len());
    for (u, v) in &edges {
        println!("{} -- {}", u.index(), v.index());
    }

    let mut graph = UnGraph::<(), ()>::default();
    for _ in 0..n {
        graph.add_node(());
    }
    for (u, v) in &edges {
        graph.add_edge(*u, *v, ());
    }

    let (n2, edges2) = from_graph6_representation::<NodeIndex>("Gr|Kto".to_string());
    let mut other = UnGraph::<(), ()>::default();
    for _ in 0..n2 {
        other.add_node(());
    }
    for (u, v) in &edges2 {
        other.add_edge(*u, *v, ());
    }

    let iso = is_isomorphic_matching(&graph, &other, |_, _| true, |_, _| true);
    println!("isomorphic (same graph6): {}", iso);

    let scott_a = build_scott_graph(n, &edges);
    let scott_b = build_scott_graph(n2, &edges2);
    let canon_a = to_cgraph(&scott_a, "$degree", "$depth > tree.parent_modality > $lexic", true, true, false);
    let canon_b = to_cgraph(&scott_b, "$degree", "$depth > tree.parent_modality > $lexic", true, true, false);
    println!("canon equal (same graph6): {}", canon_a == canon_b);

    let (n3, edges3) = from_graph6_representation::<NodeIndex>("FSOT_".to_string());
    let mut other2 = UnGraph::<(), ()>::default();
    for _ in 0..n3 {
        other2.add_node(());
    }
    for (u, v) in &edges3 {
        other2.add_edge(*u, *v, ());
    }

    let iso2 = is_isomorphic_matching(&graph, &other2, |_, _| true, |_, _| true);
    println!("isomorphic (different graph6): {}", iso2);

    let scott_c = build_scott_graph(n3, &edges3);
    let canon_c = to_cgraph(&scott_c, "$degree", "$depth > tree.parent_modality > $lexic", true, true, false);
    println!("canon equal (different graph6): {}", canon_a == canon_c);
    println!("canon: {}", canon_c);
}
