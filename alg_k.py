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


def kruskal(points, edges):

    n = len(points)
    parent = {p["id"]: p["id"] for p in points}
    rank   = {p["id"]: 0        for p in points}

    mst_edges    = []
    total_weight = 0

    for edge in sorted(edges, key=lambda e: e["weight"]):
        if union(parent, rank, edge["from"], edge["to"]):
            mst_edges.append(edge)
            total_weight += edge["weight"]
            if len(mst_edges) == n - 1:
                break

    return mst_edges, total_weight


# ── Example ───────────────────────────────────────────────────

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
        {"from": 0, "to": 2, "weight": 6},
        {"from": 0, "to": 3, "weight": 5},
        {"from": 1, "to": 4, "weight": 15},
        {"from": 2, "to": 3, "weight": 4},
        {"from": 3, "to": 4, "weight": 8},
        {"from": 1, "to": 2, "weight": 11},
    ]

    mst, total = kruskal(points, edges)

    print(f"Total weight: {total}")
    for e in mst:
        print(f"  {e['from']} → {e['to']}  (weight: {e['weight']})")