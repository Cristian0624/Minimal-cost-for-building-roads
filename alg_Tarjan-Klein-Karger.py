import random

# ─── Union-Find (same as your example) ──────────────────────────────────────
def find(parent, x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x

def union(parent, rank, x, y):
    rx, ry = find(parent, x), find(parent, y)
    if rx == ry:
        return False
    if rank[rx] < rank[ry]:
        rx, ry = ry, rx
    parent[ry] = rx
    if rank[rx] == rank[ry]:
        rank[rx] += 1
    return True

# ─── Step 1: Borůvka pass ────────────────────────────────────────────────────
# Each component finds its cheapest outgoing edge and contracts.
# One pass reduces the number of components by at least half.
def boruvka_pass(points, edges, parent, rank):
    cheapest = {}  # component root → cheapest edge leaving it

    for edge in edges:
        ru = find(parent, edge["from"])
        rv = find(parent, edge["to"])
        if ru == rv:
            continue  # same component, skip
        for root in (ru, rv):
            if root not in cheapest or edge["weight"] < cheapest[root]["weight"]:
                cheapest[root] = edge

    mst_edges = []
    for edge in cheapest.values():
        if union(parent, rank, edge["from"], edge["to"]):
            mst_edges.append(edge)

    return mst_edges

# ─── Step 2: MST verification (linear-time, Tarjan / Dixon-Rauch-Tarjan) ─────
# Given a spanning forest F and a set of edges, mark every edge e as
# "F-heavy" if e's weight is strictly greater than the maximum edge weight
# on the unique F-path between e's endpoints.  F-heavy edges can never
# belong to any MST and are discarded.
#
# Implementation: for each tree edge we store its weight; for each
# non-tree edge (u,v,w) we walk up both endpoints to their LCA and
# record the maximum tree-edge weight seen.  If w > that maximum the
# edge is F-heavy.
def _build_tree(points, tree_edges):
    """Return adjacency list {node: [(neighbour, weight)]} for the forest."""
    adj = {p["id"]: [] for p in points}
    for e in tree_edges:
        adj[e["from"]].append((e["to"],   e["weight"]))
        adj[e["to"]].append  ((e["from"], e["weight"]))
    return adj

def _lca_max_weight(adj, all_ids):
    """
    For every node compute depth, parent, and the weight of the edge to its
    parent using a simple iterative DFS from each unvisited node.
    Returns (depth, par, par_weight).
    """
    depth      = {}
    par        = {}
    par_weight = {}

    for root in all_ids:
        if root in depth:
            continue
        stack = [(root, -1, 0, 0)]
        while stack:
            node, parent_node, d, pw = stack.pop()
            if node in depth:
                continue
            depth[node]      = d
            par[node]        = parent_node
            par_weight[node] = pw
            for (nb, w) in adj.get(node, []):
                if nb not in depth:
                    stack.append((nb, node, d + 1, w))

    return depth, par, par_weight

def remove_f_heavy_edges(points, tree_edges, candidate_edges):
    """
    Return only those candidate_edges that are NOT F-heavy w.r.t. tree_edges.
    An edge (u,v,w) is F-heavy if w > max tree-edge weight on the F-path u→v.
    """
    adj = _build_tree(points, tree_edges)
    all_ids = [p["id"] for p in points]
    depth, par, par_weight = _lca_max_weight(adj, all_ids)

    def max_weight_on_path(u, v):
        """Walk u and v up to their LCA, tracking maximum edge weight."""
        max_w = 0
        while depth.get(u, 0) > depth.get(v, 0):
            max_w = max(max_w, par_weight.get(u, 0))
            u = par.get(u, u)
        while depth.get(v, 0) > depth.get(u, 0):
            max_w = max(max_w, par_weight.get(v, 0))
            v = par.get(v, v)
        while u != v:
            max_w = max(max_w, par_weight.get(u, 0), par_weight.get(v, 0))
            u = par.get(u, u)
            v = par.get(v, v)
        return max_w

    light_edges = []
    for edge in candidate_edges:
        u, v, w = edge["from"], edge["to"], edge["weight"]
        # If either endpoint is absent from the forest, the edge is trivially light
        if u not in depth or v not in depth:
            light_edges.append(edge)
            continue
        max_w = max_weight_on_path(u, v)
        # keep the edge if it is NOT heavier than the bottleneck on its F-path
        if w <= max_w or max_w == 0:
            light_edges.append(edge)

    return light_edges

# ─── Step 3: Karger random sampling ─────────────────────────────────────────
# Sample each edge independently with probability p = 0.5.
# The MST of the sample acts as the verification forest F.
def random_sample(edges, p=0.5):
    return [e for e in edges if random.random() < p]

# ─── KKT: Karger-Klein-Tarjan MST ───────────────────────────────────────────
# Randomised expected O(m) MST algorithm.
#
# Recursion outline:
#   1. Two Borůvka passes  → at most n/4 super-nodes remain.
#   2. Sample each surviving edge with p = 0.5.
#   3. Recursively find MST  F  of the sample.
#   4. Remove all F-heavy edges from the surviving edge set.
#   5. Recursively find MST  of the reduced (F-light) graph.
#   6. Return Borůvka edges ∪ sub-MST edges.
def kkt(points, edges):
    n = len(points)

    # ── base cases ───────────────────────────────────────────────────────────
    if n <= 1 or not edges:
        return [], 0

    if n == 2:
        best = min(edges, key=lambda e: e["weight"])
        return [best], best["weight"]

    # ── initialise union-find over current node set ──────────────────────────
    parent = {p["id"]: p["id"] for p in points}
    rank   = {p["id"]: 0        for p in points}

    mst_edges    = []
    total_weight = 0

    # ── Step 1: two Borůvka passes ───────────────────────────────────────────
    for _ in range(2):
        batch        = boruvka_pass(points, edges, parent, rank)
        mst_edges   += batch
        total_weight += sum(e["weight"] for e in batch)
        # drop edges whose endpoints are now in the same component
        edges = [e for e in edges
                 if find(parent, e["from"]) != find(parent, e["to"])]

    if not edges:
        return mst_edges, total_weight

    # ── rebuild compressed super-node graph ──────────────────────────────────
    seen_roots = {}
    for p in points:
        r = find(parent, p["id"])
        if r not in seen_roots:
            seen_roots[r] = {"id": r, "x": p["x"], "y": p["y"]}
    compressed_points = list(seen_roots.values())

    # keep only cheapest edge between each pair of super-nodes
    best_edge = {}
    for e in edges:
        ru  = find(parent, e["from"])
        rv  = find(parent, e["to"])
        key = (min(ru, rv), max(ru, rv))
        if key not in best_edge or e["weight"] < best_edge[key]["weight"]:
            best_edge[key] = {"from": ru, "to": rv, "weight": e["weight"]}
    compressed_edges = list(best_edge.values())

    # ── Step 2: random sample ────────────────────────────────────────────────
    sampled = random_sample(compressed_edges, p=0.5)

    # ── Step 3: recursive MST of sample → forest F ───────────────────────────
    if sampled:
        sample_ids = {e["from"] for e in sampled} | {e["to"] for e in sampled}
        sample_pts = [p for p in compressed_points if p["id"] in sample_ids]
        forest_edges, _ = kkt(sample_pts, sampled)
    else:
        forest_edges = []

    # ── Step 4: remove F-heavy edges ─────────────────────────────────────────
    if forest_edges:
        light = remove_f_heavy_edges(compressed_points, forest_edges, compressed_edges)
    else:
        light = compressed_edges   # no forest → nothing to prune

    # ── Step 5: recursive MST of F-light edges ───────────────────────────────
    light_ids = {e["from"] for e in light} | {e["to"] for e in light}
    light_pts = [p for p in compressed_points if p["id"] in light_ids]

    if light:
        sub_mst, sub_w = kkt(light_pts, light)
        mst_edges    += sub_mst
        total_weight += sub_w

    return mst_edges, total_weight


# ── Example ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    points = [
        {"id": 0, "x": 0, "y": 0},
        {"id": 1, "x": 2, "y": 0},
        {"id": 2, "x": 1, "y": 2},
        {"id": 3, "x": 3, "y": 2},
        {"id": 4, "x": 4, "y": 0},
    ]
    edges = [
        {"from": 0, "to": 1, "weight": 10},
        {"from": 0, "to": 2, "weight":  6},
        {"from": 0, "to": 3, "weight":  5},
        {"from": 1, "to": 4, "weight": 15},
        {"from": 2, "to": 3, "weight":  4},
        {"from": 3, "to": 4, "weight":  8},
        {"from": 1, "to": 2, "weight": 11},
    ]

    random.seed(42)
    mst, total = kkt(points, edges)

    print(f"Total weight: {total}")
    for e in mst:
        print(f"  {e['from']} → {e['to']}  (weight: {e['weight']})")