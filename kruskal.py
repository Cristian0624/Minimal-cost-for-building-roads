import math
import os
import random
from PIL import Image, ImageDraw, ImageFont


# ── Colours ───────────────────────────────────────────────────
BG_COLOR        = (15,  20,  35)
GRID_COLOR      = (30,  38,  60)
SKIPPED_COLOR   = (60,  70,  100)
MST_COLOR       = (0,   210, 130)
MST_NODE_FILL   = (0,   170, 100)   # distinct fill for MST-only nodes
CITY_FILL       = (30,  140, 255)
CITY_OUTLINE    = (180, 220, 255)
MST_NODE_OUTLINE= (180, 255, 220)
TITLE_COLOR     = (0,   210, 130)
LEGEND_BG       = (25,  32,  52)

# ── Scale thresholds ──────────────────────────────────────────
# <= SMALL  : ellipse, full detail (labels on all nodes, costs, glow)
# <= MEDIUM : scatter, labels on all nodes, no costs
# > MEDIUM  : scatter, MST edges only, labels only on MST nodes
SMALL  = 15
MEDIUM = 50


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


# ── Adaptive layout parameters ────────────────────────────────

def _layout_params(num_cities):
    if num_cities <= SMALL:
        return dict(
            img_w=900, img_h=620, margin=80,
            city_r=22, edge_w_skip=1, edge_w_mst=4,
            show_labels="all",     # "all" | "mst" | "none"
            show_costs=True,
            show_glow=True,
            draw_skipped=True,
            font_title=22, font_label=16, font_cost=13,
            grid_step=40, layout="ellipse",
        )
    elif num_cities <= MEDIUM:
        return dict(
            img_w=1400, img_h=1000, margin=60,
            city_r=10, edge_w_skip=1, edge_w_mst=2,
            show_labels="all",
            show_costs=False,
            show_glow=False,
            draw_skipped=True,
            font_title=24, font_label=9, font_cost=0,
            grid_step=70, layout="scatter",
        )
    else:
        # > MEDIUM: scatter, MST-only edges, labels only on MST nodes
        side = max(2400, int(math.ceil(math.sqrt(num_cities))) * 55 + 300)
        # Scale node radius down gracefully
        city_r = max(3, min(8, int(30 / math.log10(num_cities + 1))))
        font_lbl = max(7, min(11, int(40 / math.log10(num_cities + 1))))
        return dict(
            img_w=side, img_h=side, margin=100,
            city_r=city_r, edge_w_skip=1, edge_w_mst=max(1, city_r // 3),
            show_labels="mst",     # only MST nodes get labelled
            show_costs=False,
            show_glow=False,
            draw_skipped=False,    # clean: MST edges only
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

    # Scatter with minimum-distance guarantee
    rng = random.Random(seed_positions)
    min_dist = p["city_r"] * 4
    pos = []
    attempts = 0
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

    # Glow halo (small graphs only)
    if p["show_glow"]:
        for gr in range(r + 12, r - 1, -3):
            alpha = max(0, 40 - (gr - r) * 5)
            draw.ellipse([x-gr, y-gr, x+gr, y+gr], fill=(0, 80, 200, alpha))

    # Node colour: MST nodes get a distinct green tint when labels are mst-only
    if p["show_labels"] == "mst" and is_mst_node:
        fill, outline = MST_NODE_FILL, MST_NODE_OUTLINE
    else:
        fill, outline = CITY_FILL, CITY_OUTLINE

    draw.ellipse([x-r, y-r, x+r, y+r],
                 fill=fill, outline=outline, width=max(1, r // 10))

    # Label visibility rules
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
    box_h = 70 if not mst_only else 46
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


# ── Main visualizer ───────────────────────────────────────────

def visualize(num_cities, all_roads, mst_edges, total_cost, title, filename,
              position_seed=0):
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

    # Nodes that appear in any MST edge
    mst_nodes = set()
    for _, a, b in mst_edges:
        mst_nodes.add(a)
        mst_nodes.add(b)

    # Candidate (skipped) edges — only drawn when draw_skipped is True
    if p["draw_skipped"]:
        for cost, a, b in all_roads:
            if (min(a, b), max(a, b)) not in mst_set:
                _draw_edge(draw, pos[a], pos[b],
                           SKIPPED_COLOR, p["edge_w_skip"],
                           cost, font_cost, p["show_costs"])

    # MST edges — always drawn
    for cost, a, b in mst_edges:
        _draw_edge(draw, pos[a], pos[b],
                   MST_COLOR, p["edge_w_mst"],
                   cost, font_cost, p["show_costs"])

    # City nodes — all drawn, but appearance & label depend on MST membership
    for i, pt in enumerate(pos):
        is_mst = i in mst_nodes
        label = str(i)
        _draw_city(draw, pt, label, p, font_label, is_mst_node=is_mst)

    # Title
    try:
        bbox = draw.textbbox((0, 0), title, font=font_title)
        tw = bbox[2] - bbox[0]
    except Exception:
        tw = len(title) * p["font_title"] // 2
    draw.text(((p["img_w"] - tw) // 2, 16), title, fill=TITLE_COLOR, font=font_title)

    # Legend
    if total_cost is not None:
        _draw_legend(draw, p, font_legend, total_cost, mst_only=not p["draw_skipped"])
    else:
        draw.text((14, p["img_h"] - 40),
                  "⚠ Disconnected graph — no spanning tree",
                  fill=(255, 100, 80), font=font_legend)

    img.save(filename)


# ── Union-Find ────────────────────────────────────────────────

class UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))
        self.rank   = [0] * n

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, x, y):
        rx, ry = self.find(x), self.find(y)
        if rx == ry:
            return False
        if self.rank[rx] < self.rank[ry]:
            rx, ry = ry, rx
        self.parent[ry] = rx
        if self.rank[rx] == self.rank[ry]:
            self.rank[rx] += 1
        return True


# ── Random graph generator ────────────────────────────────────

def generate_random_graph(
    min_cities=4,
    max_cities=10,
    min_cost=1,
    max_cost=20,
    edge_density=0.5,
    seed=None,
):
    """
    Generate a random connected graph for use with kruskal().

    Parameters:
        min_cities   (int)   : minimum number of city nodes (>= 2)
        max_cities   (int)   : maximum number of city nodes
        min_cost     (int)   : minimum road cost
        max_cost     (int)   : maximum road cost
        edge_density (float) : 0.0–1.0 — fraction of extra candidate edges
                               added on top of the guaranteed spanning tree.
                               0.0 = bare minimum (n-1 edges, always connected)
                               1.0 = complete graph
                               Keep low (e.g. 0.02–0.05) for 100+ cities.
        seed         (int)   : optional random seed for reproducibility

    Returns:
        (num_cities, roads)  where roads is [(cost, a, b), ...]
    """
    rng = random.Random(seed)  # isolated instance — never touches global state

    num_cities = rng.randint(min_cities, max_cities)

    # 1. Random spanning tree — guarantees connectivity.
    nodes = list(range(num_cities))
    rng.shuffle(nodes)
    edges = set()
    roads = []
    for i in range(1, num_cities):
        a = nodes[rng.randint(0, i - 1)]
        b = nodes[i]
        key = (min(a, b), max(a, b))
        edges.add(key)
        roads.append((rng.randint(min_cost, max_cost), a, b))

    # 2. Extra candidate edges.
    max_possible_extra = num_cities * (num_cities - 1) // 2 - len(edges)
    num_extra = int(max_possible_extra * edge_density)

    if num_extra > 0:
        if num_cities <= 500:
            all_pairs = [
                (a, b)
                for a in range(num_cities)
                for b in range(a + 1, num_cities)
                if (a, b) not in edges
            ]
            rng.shuffle(all_pairs)
            for a, b in all_pairs[:num_extra]:
                roads.append((rng.randint(min_cost, max_cost), a, b))
        else:
            # Random sampling for very large graphs
            added, attempts = 0, 0
            max_attempts = num_extra * 10
            while added < num_extra and attempts < max_attempts:
                a = rng.randint(0, num_cities - 1)
                b = rng.randint(0, num_cities - 1)
                if a != b:
                    key = (min(a, b), max(a, b))
                    if key not in edges:
                        edges.add(key)
                        roads.append((rng.randint(min_cost, max_cost), a, b))
                        added += 1
                attempts += 1

    return num_cities, roads


# ── Kruskal ───────────────────────────────────────────────────

def kruskal(num_cities, roads, visualize_to=None,graph_title="MST – Road Construction", position_seed=0):
    roads_sorted = sorted(roads, key=lambda r: r[0])
    uf = UnionFind(num_cities)
    mst_edges  = []
    total_cost = 0

    for cost, a, b in roads_sorted:
        if uf.union(a, b):
            mst_edges.append((cost, a, b))
            total_cost += cost
            if len(mst_edges) == num_cities - 1:
                break

    connected = len({uf.find(i) for i in range(num_cities)}) == 1
    if not connected:
        total_cost = None

    if visualize_to:
        visualize(num_cities, roads, mst_edges, total_cost,
                  graph_title, visualize_to, position_seed=position_seed)

    return mst_edges, total_cost


# ── Examples ──────────────────────────────────────────────────

if __name__ == "__main__":

    # Small — ellipse, full detail: all labels, cost tags, glow
    num_cities, roads = generate_random_graph(
        min_cities=5, max_cities=15, edge_density=0.5)
    kruskal(num_cities=num_cities, roads=roads,
            visualize_to="small.png",
            graph_title=f"MST – {num_cities} Cities (small)")

    # Medium — scatter, all labels, no costs, candidate edges shown
    num_cities, roads = generate_random_graph(
        min_cities=16, max_cities=50, edge_density=0.1)
    kruskal(num_cities=num_cities, roads=roads,
            visualize_to="medium.png",
            graph_title=f"MST – {num_cities} Cities (medium)")

    # Large — scatter, MST edges only, labels on MST nodes only
    num_cities, roads = generate_random_graph(
        min_cities=51, max_cities=100, edge_density=0.03)
    kruskal(num_cities=num_cities, roads=roads,
            visualize_to="large.png",
            graph_title=f"MST – {num_cities} Cities (large)")
