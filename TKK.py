import random
import math
import os
from PIL import Image, ImageDraw, ImageFont


# ══════════════════════════════════════════════════════════════════════════════
#  COLOURS  (identical palette to kruskal.py)
# ══════════════════════════════════════════════════════════════════════════════
BG_COLOR         = (15,  20,  35)
GRID_COLOR       = (30,  38,  60)
SKIPPED_COLOR    = (60,  70,  100)
MST_COLOR        = (0,   210, 130)
MST_NODE_FILL    = (0,   170, 100)
CITY_FILL        = (30,  140, 255)
CITY_OUTLINE     = (180, 220, 255)
MST_NODE_OUTLINE = (180, 255, 220)
TITLE_COLOR      = (0,   210, 130)
LEGEND_BG        = (25,  32,  52)

SMALL  = 15
MEDIUM = 50


# ══════════════════════════════════════════════════════════════════════════════
#  VISUALISATION  (copied verbatim from kruskal.py — zero changes)
# ══════════════════════════════════════════════════════════════════════════════

def _font(size):
    for path in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "C:/Windows/Fonts/arial.ttf",
    ]:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _layout_params(num_cities):
    if num_cities <= SMALL:
        return dict(
            img_w=900, img_h=620, margin=80,
            city_r=22, edge_w_skip=1, edge_w_mst=4,
            show_labels="all", show_costs=True, show_glow=True,
            draw_skipped=True,
            font_title=22, font_label=16, font_cost=13,
            grid_step=40, layout="ellipse",
        )
    elif num_cities <= MEDIUM:
        return dict(
            img_w=1400, img_h=1000, margin=60,
            city_r=10, edge_w_skip=1, edge_w_mst=2,
            show_labels="all", show_costs=False, show_glow=False,
            draw_skipped=True,
            font_title=24, font_label=9, font_cost=0,
            grid_step=70, layout="scatter",
        )
    else:
        side   = max(2400, int(math.ceil(math.sqrt(num_cities))) * 55 + 300)
        city_r = max(3, min(8, int(30 / math.log10(num_cities + 1))))
        font_lbl = max(7, min(11, int(40 / math.log10(num_cities + 1))))
        return dict(
            img_w=side, img_h=side, margin=100,
            city_r=city_r, edge_w_skip=1, edge_w_mst=max(1, city_r // 3),
            show_labels="mst", show_costs=False, show_glow=False,
            draw_skipped=False,
            font_title=36, font_label=font_lbl, font_cost=0,
            grid_step=150, layout="scatter",
        )


def _city_positions(num_cities, p, seed_positions=0):
    w, h, m = p["img_w"], p["img_h"], p["margin"]
    if p["layout"] == "ellipse":
        cx, cy = w // 2, h // 2 - 20
        rx = (w - 2 * m) // 2 - 10
        ry = (h - 2 * m) // 2 - 30
        return [
            (int(cx + rx * math.cos(2 * math.pi * i / num_cities - math.pi / 2)),
             int(cy + ry * math.sin(2 * math.pi * i / num_cities - math.pi / 2)))
            for i in range(num_cities)
        ]
    rng = random.Random(seed_positions)
    min_dist = p["city_r"] * 4
    pos, attempts = [], 0
    while len(pos) < num_cities:
        x = rng.randint(m, w - m)
        y = rng.randint(m, h - m)
        if all(math.hypot(x - px, y - py) >= min_dist for px, py in pos):
            pos.append((x, y))
            attempts = 0
        else:
            attempts += 1
            if attempts > 600:
                min_dist = max(p["city_r"] * 2, min_dist - 1)
                attempts = 0
    return pos


def _draw_grid(draw, p):
    w, h, step = p["img_w"], p["img_h"], p["grid_step"]
    for x in range(0, w, step):
        draw.line([(x, 0), (x, h)], fill=GRID_COLOR, width=1)
    for y in range(0, h, step):
        draw.line([(0, y), (w, y)], fill=GRID_COLOR, width=1)


def _draw_edge(draw, p1, p2, color, width, cost, font, show_cost):
    draw.line([p1, p2], fill=color, width=width)
    if show_cost and font is not None and cost is not None:
        mx, my = (p1[0] + p2[0]) // 2, (p1[1] + p2[1]) // 2
        text = str(cost)
        try:
            bbox = draw.textbbox((0, 0), text, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        except Exception:
            tw, th = 20, 12
        pad = 3
        draw.rounded_rectangle(
            [mx - tw//2 - pad, my - th//2 - pad,
             mx + tw//2 + pad, my + th//2 + pad],
            radius=3, fill=(20, 26, 46))
        draw.text((mx - tw//2, my - th//2), text, fill=color, font=font)


def _draw_city(draw, pt, label, p, font_label, is_mst_node):
    x, y = pt
    r = p["city_r"]
    if p["show_glow"]:
        for gr in range(r + 12, r - 1, -3):
            alpha = max(0, 40 - (gr - r) * 5)
            draw.ellipse([x-gr, y-gr, x+gr, y+gr], fill=(0, 80, 200, alpha))
    if p["show_labels"] == "mst" and is_mst_node:
        fill, outline = MST_NODE_FILL, MST_NODE_OUTLINE
    else:
        fill, outline = CITY_FILL, CITY_OUTLINE
    draw.ellipse([x-r, y-r, x+r, y+r],
                 fill=fill, outline=outline, width=max(1, r // 10))
    show = (
        (p["show_labels"] == "all") or
        (p["show_labels"] == "mst" and is_mst_node)
    )
    if show and font_label and label:
        try:
            bbox = draw.textbbox((0, 0), label, font=font_label)
            tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
            draw.text((x - tw//2, y - th//2), label,
                      fill=(255, 255, 255), font=font_label)
        except Exception:
            pass


def _draw_legend(draw, p, font_sm, total_cost, mst_only):
    h = p["img_h"]
    box_w = 380 if not mst_only else 300
    box_h = 70  if not mst_only else 46
    x0, y0 = 14, h - box_h - 14
    x1, y1 = x0 + box_w, h - 14
    draw.rounded_rectangle([x0, y0, x1, y1], radius=8, fill=LEGEND_BG)
    if not mst_only:
        draw.line([(x0+14, y0+22), (x0+44, y0+22)], fill=SKIPPED_COLOR, width=2)
        draw.text((x0+54, y0+14), "Candidate road (skipped)", fill=SKIPPED_COLOR, font=font_sm)
        draw.line([(x0+14, y0+46), (x0+44, y0+46)], fill=MST_COLOR, width=3)
        draw.text((x0+54, y0+38), f"MST road  |  Total cost: {total_cost}", fill=MST_COLOR, font=font_sm)
    else:
        draw.line([(x0+14, y0+22), (x0+44, y0+22)], fill=MST_COLOR, width=3)
        draw.text((x0+54, y0+14), f"MST road  |  Total cost: {total_cost}", fill=MST_COLOR, font=font_sm)


def visualize(num_cities, all_roads, mst_edges, total_cost, title, filename,
              position_seed=0):
    """
    all_roads  : [(cost, a, b), ...]
    mst_edges  : [(cost, a, b), ...]  ← same format
    """
    p = _layout_params(num_cities)
    img  = Image.new("RGB", (p["img_w"], p["img_h"]), BG_COLOR)
    draw = ImageDraw.Draw(img, "RGBA")

    font_title  = _font(p["font_title"])
    font_label  = _font(p["font_label"]) if p["font_label"] else None
    font_cost   = _font(p["font_cost"])  if p["font_cost"]  else None
    font_legend = _font(15)

    _draw_grid(draw, p)

    pos     = _city_positions(num_cities, p, seed_positions=position_seed)
    mst_set = {(min(a, b), max(a, b)) for _, a, b in mst_edges}

    mst_nodes = set()
    for _, a, b in mst_edges:
        mst_nodes.add(a)
        mst_nodes.add(b)

    if p["draw_skipped"]:
        for cost, a, b in all_roads:
            if (min(a, b), max(a, b)) not in mst_set:
                _draw_edge(draw, pos[a], pos[b],
                           SKIPPED_COLOR, p["edge_w_skip"],
                           cost, font_cost, p["show_costs"])

    for cost, a, b in mst_edges:
        _draw_edge(draw, pos[a], pos[b],
                   MST_COLOR, p["edge_w_mst"],
                   cost, font_cost, p["show_costs"])

    for i, pt in enumerate(pos):
        _draw_city(draw, pt, str(i), p, font_label, is_mst_node=(i in mst_nodes))

    try:
        bbox = draw.textbbox((0, 0), title, font=font_title)
        tw = bbox[2] - bbox[0]
    except Exception:
        tw = len(title) * p["font_title"] // 2
    draw.text(((p["img_w"] - tw) // 2, 16), title, fill=TITLE_COLOR, font=font_title)

    if total_cost is not None:
        _draw_legend(draw, p, font_legend, total_cost, mst_only=not p["draw_skipped"])
    else:
        draw.text((14, p["img_h"] - 40),
                  "⚠ Disconnected graph — no spanning tree",
                  fill=(255, 100, 80), font=font_legend)

    img.save(filename)
    print(f"  Saved → {filename}")


# ══════════════════════════════════════════════════════════════════════════════
#  RANDOM GRAPH GENERATOR  (identical to kruskal.py)
# ══════════════════════════════════════════════════════════════════════════════

def generate_random_graph(
    min_cities=4, max_cities=10,
    min_cost=1,   max_cost=20,
    edge_density=0.5,
    seed=None,
):
    rng = random.Random(seed)
    num_cities = rng.randint(min_cities, max_cities)

    nodes = list(range(num_cities))
    rng.shuffle(nodes)
    edges_set = set()
    roads = []
    for i in range(1, num_cities):
        a = nodes[rng.randint(0, i - 1)]
        b = nodes[i]
        key = (min(a, b), max(a, b))
        edges_set.add(key)
        roads.append((rng.randint(min_cost, max_cost), a, b))

    max_possible_extra = num_cities * (num_cities - 1) // 2 - len(edges_set)
    num_extra = int(max_possible_extra * edge_density)

    if num_extra > 0:
        if num_cities <= 500:
            all_pairs = [
                (a, b)
                for a in range(num_cities)
                for b in range(a + 1, num_cities)
                if (a, b) not in edges_set
            ]
            rng.shuffle(all_pairs)
            for a, b in all_pairs[:num_extra]:
                roads.append((rng.randint(min_cost, max_cost), a, b))
        else:
            added, attempts = 0, 0
            max_attempts = num_extra * 10
            while added < num_extra and attempts < max_attempts:
                a = rng.randint(0, num_cities - 1)
                b = rng.randint(0, num_cities - 1)
                if a != b:
                    key = (min(a, b), max(a, b))
                    if key not in edges_set:
                        edges_set.add(key)
                        roads.append((rng.randint(min_cost, max_cost), a, b))
                        added += 1
                attempts += 1

    return num_cities, roads


# ══════════════════════════════════════════════════════════════════════════════
#  KKT  –  UNION-FIND
# ══════════════════════════════════════════════════════════════════════════════

def _find(parent, x):
    while parent[x] != x:
        parent[x] = parent[parent[x]]
        x = parent[x]
    return x


def _union(parent, rank, x, y):
    rx, ry = _find(parent, x), _find(parent, y)
    if rx == ry:
        return False
    if rank[rx] < rank[ry]:
        rx, ry = ry, rx
    parent[ry] = rx
    if rank[rx] == rank[ry]:
        rank[rx] += 1
    return True


# ══════════════════════════════════════════════════════════════════════════════
#  KKT  –  BORŮVKA PASS
# ══════════════════════════════════════════════════════════════════════════════

def _boruvka_pass(points, edges, parent, rank):
    cheapest = {}
    for edge in edges:
        ru = _find(parent, edge["from"])
        rv = _find(parent, edge["to"])
        if ru == rv:
            continue
        for root in (ru, rv):
            if root not in cheapest or edge["weight"] < cheapest[root]["weight"]:
                cheapest[root] = edge

    mst_edges = []
    for edge in cheapest.values():
        if _union(parent, rank, edge["from"], edge["to"]):
            mst_edges.append(edge)
    return mst_edges


# ══════════════════════════════════════════════════════════════════════════════
#  KKT  –  F-HEAVY EDGE REMOVAL  (Tarjan / Dixon-Rauch-Tarjan)
# ══════════════════════════════════════════════════════════════════════════════

def _build_tree(points, tree_edges):
    adj = {p["id"]: [] for p in points}
    for e in tree_edges:
        adj[e["from"]].append((e["to"],   e["weight"]))
        adj[e["to"]].append  ((e["from"], e["weight"]))
    return adj


def _lca_max_weight(adj, all_ids):
    depth, par, par_weight = {}, {}, {}
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
            for nb, w in adj.get(node, []):
                if nb not in depth:
                    stack.append((nb, node, d + 1, w))
    return depth, par, par_weight


def _remove_f_heavy_edges(points, tree_edges, candidate_edges):
    adj = _build_tree(points, tree_edges)
    all_ids = [p["id"] for p in points]
    depth, par, par_weight = _lca_max_weight(adj, all_ids)

    def max_weight_on_path(u, v):
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

    light = []
    for edge in candidate_edges:
        u, v, w = edge["from"], edge["to"], edge["weight"]
        if u not in depth or v not in depth:
            light.append(edge)
            continue
        max_w = max_weight_on_path(u, v)
        if w <= max_w or max_w == 0:
            light.append(edge)
    return light


# ══════════════════════════════════════════════════════════════════════════════
#  KKT  –  CORE RECURSIVE ALGORITHM
# ══════════════════════════════════════════════════════════════════════════════

def _kkt(points, edges):
    """
    Internal recursive KKT.  Works with dicts:
      points : [{"id": int, ...}, ...]
      edges  : [{"from": int, "to": int, "weight": int}, ...]
    Returns (mst_edge_dicts, total_weight).
    """
    n = len(points)
    if n <= 1 or not edges:
        return [], 0
    if n == 2:
        best = min(edges, key=lambda e: e["weight"])
        return [best], best["weight"]

    parent = {p["id"]: p["id"] for p in points}
    rank   = {p["id"]: 0        for p in points}

    mst_edges    = []
    total_weight = 0

    # Two Borůvka passes — reduces to ≤ n/4 super-nodes
    for _ in range(2):
        batch        = _boruvka_pass(points, edges, parent, rank)
        mst_edges   += batch
        total_weight += sum(e["weight"] for e in batch)
        edges = [e for e in edges
                 if _find(parent, e["from"]) != _find(parent, e["to"])]

    if not edges:
        return mst_edges, total_weight

    # Compress to super-node graph
    seen_roots = {}
    for p in points:
        r = _find(parent, p["id"])
        if r not in seen_roots:
            seen_roots[r] = {"id": r, "x": p.get("x", 0), "y": p.get("y", 0)}
    compressed_points = list(seen_roots.values())

    best_edge = {}
    for e in edges:
        ru  = _find(parent, e["from"])
        rv  = _find(parent, e["to"])
        key = (min(ru, rv), max(ru, rv))
        if key not in best_edge or e["weight"] < best_edge[key]["weight"]:
            best_edge[key] = {"from": ru, "to": rv, "weight": e["weight"]}
    compressed_edges = list(best_edge.values())

    # Random sample → recursive MST of sample → forest F
    sampled = [e for e in compressed_edges if random.random() < 0.5]

    if sampled:
        sample_ids = {e["from"] for e in sampled} | {e["to"] for e in sampled}
        sample_pts = [p for p in compressed_points if p["id"] in sample_ids]
        forest_edges, _ = _kkt(sample_pts, sampled)
    else:
        forest_edges = []

    # Remove F-heavy edges
    light = (_remove_f_heavy_edges(compressed_points, forest_edges, compressed_edges)
             if forest_edges else compressed_edges)

    # Recursive MST of F-light graph
    light_ids = {e["from"] for e in light} | {e["to"] for e in light}
    light_pts = [p for p in compressed_points if p["id"] in light_ids]

    if light:
        sub_mst, sub_w = _kkt(light_pts, light)
        mst_edges    += sub_mst
        total_weight += sub_w

    return mst_edges, total_weight


# ══════════════════════════════════════════════════════════════════════════════
#  KKT  –  PUBLIC ENTRY POINT  (mirrors kruskal() signature)
# ══════════════════════════════════════════════════════════════════════════════

def kkt(num_cities, roads, visualize_to=None,
        graph_title="MST – KKT (Karger-Klein-Tarjan)",
        position_seed=0):
    """
    Parameters
    ----------
    num_cities   : int
    roads        : [(cost, a, b), ...]          ← same format as kruskal.py
    visualize_to : str | None  — output PNG path
    graph_title  : str
    position_seed: int

    Returns
    -------
    (mst_edges, total_cost)
    where mst_edges is [(cost, a, b), ...] and total_cost is int | None.
    """
    # Convert flat (cost, a, b) tuples → dict format expected by _kkt
    points = [{"id": i, "x": 0, "y": 0} for i in range(num_cities)]
    edges  = [{"from": a, "to": b, "weight": cost} for cost, a, b in roads]

    mst_dicts, total_weight = _kkt(points, edges)

    # Deduplicate MST edges (KKT may add equivalent super-node edges twice)
    seen = set()
    unique_mst = []
    for e in mst_dicts:
        key = (min(e["from"], e["to"]), max(e["from"], e["to"]))
        if key not in seen:
            seen.add(key)
            unique_mst.append(e)

    # Convert back to (cost, a, b) tuples
    mst_edges = [(e["weight"], e["from"], e["to"]) for e in unique_mst]

    # Recompute total from deduplicated list (more reliable)
    total_cost = sum(c for c, _, _ in mst_edges) if mst_edges else None

    # Connectivity check
    parent = list(range(num_cities))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for _, a, b in mst_edges:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    connected = len({find(i) for i in range(num_cities)}) == 1
    if not connected:
        total_cost = None

    if visualize_to:
        visualize(num_cities, roads, mst_edges, total_cost,
                  graph_title, visualize_to, position_seed=position_seed)

    return mst_edges, total_cost


# ══════════════════════════════════════════════════════════════════════════════
#  EXAMPLES  (mirrors kruskal.py __main__ block)
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    random.seed(42)

    # ── Small: ellipse, full detail ──────────────────────────────────────────
    num_cities, roads = generate_random_graph(
        min_cities=15, max_cities=25, edge_density=0.5, seed=1)
    mst, cost = kkt(num_cities=num_cities, roads=roads,
                    visualize_to="kkt_small.png",
                    graph_title=f"KKT MST – {num_cities} Cities (small)")
    print(f"Small  | cities={num_cities}  MST edges={len(mst)}  total cost={cost}")

    # ── Medium: scatter, all labels, no cost tags ────────────────────────────
    num_cities, roads = generate_random_graph(
        min_cities=30, max_cities=50, edge_density=0.1, seed=2)
    mst, cost = kkt(num_cities=num_cities, roads=roads,
                    visualize_to="kkt_medium.png",
                    graph_title=f"KKT MST – {num_cities} Cities (medium)")
    print(f"Medium | cities={num_cities}  MST edges={len(mst)}  total cost={cost}")

    # ── Large: scatter, MST edges only, MST-node labels only ────────────────
    num_cities, roads = generate_random_graph(
        min_cities=100, max_cities=250, edge_density=0.03, seed=3)
    mst, cost = kkt(num_cities=num_cities, roads=roads,
                    visualize_to="kkt_large.png",
                    graph_title=f"KKT MST – {num_cities} Cities (large)")
    print(f"Large  | cities={num_cities}  MST edges={len(mst)}  total cost={cost}")