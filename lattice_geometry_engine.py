"""
Lattice geometry engine — dynamic working area, tool, and pore sizes.

Tool tip may be a circle or a regular polygon (3–10 sides). User size is the
circumdiameter (vertex-to-vertex for polygons; ordinary diameter for circles).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

TOOL_DIAMETER_OPTIONS = list(range(400, 1600, 100))  # 400–1500 µm
TOOL_SHAPE_OPTIONS = [
    {"value": "circle", "label": "Circle", "sides": None},
    {"value": "3", "label": "Triangle (3 sides)", "sides": 3},
    {"value": "4", "label": "Square (4 sides)", "sides": 4},
    {"value": "5", "label": "Pentagon (5 sides)", "sides": 5},
    {"value": "6", "label": "Hexagon (6 sides)", "sides": 6},
    {"value": "7", "label": "Heptagon (7 sides)", "sides": 7},
    {"value": "8", "label": "Octagon (8 sides)", "sides": 8},
    {"value": "9", "label": "Nonagon (9 sides)", "sides": 9},
    {"value": "10", "label": "Decagon (10 sides)", "sides": 10},
]
# Physical node size from lab lattice geometry (fixed; does not change with user pore input)
DEFAULT_NODE_DIAMETER_UM = 235.6

POLYGON_NAME = {
    3: "triangle",
    4: "square",
    5: "pentagon",
    6: "hexagon",
    7: "heptagon",
    8: "octagon",
    9: "nonagon",
    10: "decagon",
}


@dataclass
class LatticeConfig:
    working_area_um: float = 1500.0
    tool_diameter_um: float = 900.0  # circumdiameter for polygons
    pore_diameter_um: float = 235.6
    unit_cell_um: float | None = None  # auto = working_area / 3
    tool_sides: int | None = None  # None / 0 = circle; 3–10 = regular polygon
    tool_rotation_deg: float = 0.0

    def __post_init__(self):
        if self.unit_cell_um is None:
            self.unit_cell_um = self.working_area_um / 3.0
        if self.tool_sides is not None:
            sides = int(self.tool_sides)
            if sides < 3:
                self.tool_sides = None
            elif sides > 10:
                raise ValueError("tool_sides must be between 3 and 10")
            else:
                self.tool_sides = sides
        self.tool_radius = self.tool_diameter_um / 2.0  # circumradius
        self.pore_radius = self.pore_diameter_um / 2.0
        # Nodes are fixed physical strut junctions; only pore (white) scales with user input
        self.node_radius = DEFAULT_NODE_DIAMETER_UM / 2.0
        self.n_cells = max(1, int(round(self.working_area_um / self.unit_cell_um)))

    @property
    def is_circle(self) -> bool:
        return self.tool_sides is None

    @property
    def tool_shape_label(self) -> str:
        if self.is_circle:
            return "circle"
        return POLYGON_NAME.get(self.tool_sides, f"{self.tool_sides}-gon")

    @property
    def tool_pore_ratio(self) -> float:
        """Ratio using circumdiameter (same field for circle and polygons)."""
        return self.tool_diameter_um / max(self.pore_diameter_um, 1e-6)

    @property
    def equivalent_area_diameter_um(self) -> float:
        """
        Diameter of a circle with the same area as the tool footprint.
        For a circle this equals tool_diameter_um.
        For a regular n-gon with circumdiameter D:
          A = (n/2) R² sin(2π/n), R = D/2
          D_eq = 2 sqrt(A/π) = D * sqrt(n sin(2π/n) / (2π))
        """
        if self.is_circle:
            return self.tool_diameter_um
        n = self.tool_sides
        return self.tool_diameter_um * math.sqrt(n * math.sin(2 * math.pi / n) / (2 * math.pi))

    @property
    def inradius_um(self) -> float:
        """Apothem / inscribed radius (circle: same as circumradius)."""
        if self.is_circle:
            return self.tool_radius
        return self.tool_radius * math.cos(math.pi / self.tool_sides)

    @property
    def inscribed_diameter_um(self) -> float:
        return 2.0 * self.inradius_um

    def position_bounds(self) -> tuple[float, float]:
        """Valid tool center range so full tool footprint stays inside working area."""
        m = self.tool_radius
        return m, self.working_area_um - m

    def tool_size_summary(self) -> dict:
        return {
            "tool_shape": self.tool_shape_label,
            "tool_sides": self.tool_sides,
            "circumdiameter_um": round(self.tool_diameter_um, 2),
            "circumradius_um": round(self.tool_radius, 2),
            "equivalent_area_diameter_um": round(self.equivalent_area_diameter_um, 2),
            "inscribed_diameter_um": round(self.inscribed_diameter_um, 2),
            "inradius_um": round(self.inradius_um, 2),
        }


@dataclass
class GeometryFeatures:
    tool_x: float
    tool_y: float
    min_dist_to_strut: float
    min_dist_to_node_center: float
    nodes_inside_tool: int
    pores_center_inside_tool: int
    strut_intersection_length: float
    pore_overlap_fraction: float
    node_overlap_fraction: float
    geometry_risk: float
    tool_pore_ratio: float


def _node_grid_size(cfg: LatticeConfig) -> int:
    return cfg.n_cells + 1


def node_centers(cfg: LatticeConfig) -> list[tuple[float, float]]:
    n = _node_grid_size(cfg)
    uc = cfg.unit_cell_um
    return [(i * uc, j * uc) for i in range(n) for j in range(n)]


def pore_centers(cfg: LatticeConfig) -> list[tuple[float, float]]:
    uc = cfg.unit_cell_um
    pts = []
    for i in range(cfg.n_cells):
        for j in range(cfg.n_cells):
            pts.append((i * uc + uc / 2, j * uc + uc / 2))
    return pts


def strut_segments(cfg: LatticeConfig) -> list[tuple[float, float, float, float]]:
    segs = []
    n = _node_grid_size(cfg)
    w = cfg.working_area_um
    uc = cfg.unit_cell_um
    for k in range(n):
        y = k * uc
        if y <= w:
            segs.append((0, y, w, y))
        x = k * uc
        if x <= w:
            segs.append((x, 0, x, w))
    return segs


def _dist_point_to_segment(px, py, x1, y1, x2, y2) -> float:
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
    proj_x = x1 + t * dx
    proj_y = y1 + t * dy
    return math.hypot(px - proj_x, py - proj_y)


def regular_polygon_vertices(
    cx: float, cy: float, radius: float, n: int, rotation_deg: float = 0.0,
) -> list[tuple[float, float]]:
    """Vertices of a regular n-gon with circumradius `radius`, flat-top adjusted by rotation."""
    rot = math.radians(rotation_deg) - math.pi / 2  # first vertex "up" at 0°
    return [
        (cx + radius * math.cos(rot + 2 * math.pi * i / n),
         cy + radius * math.sin(rot + 2 * math.pi * i / n))
        for i in range(n)
    ]


def point_in_polygon(px: float, py: float, vertices: list[tuple[float, float]]) -> bool:
    """Ray-casting point-in-polygon test."""
    inside = False
    n = len(vertices)
    j = n - 1
    for i in range(n):
        xi, yi = vertices[i]
        xj, yj = vertices[j]
        if ((yi > py) != (yj > py)) and (
            px < (xj - xi) * (py - yi) / (yj - yi + 1e-15) + xi
        ):
            inside = not inside
        j = i
    return inside


def _dist_point_to_polygon(px: float, py: float, vertices: list[tuple[float, float]]) -> float:
    """Signed distance: negative if inside, positive if outside (approx via edges)."""
    n = len(vertices)
    min_d = float("inf")
    for i in range(n):
        x1, y1 = vertices[i]
        x2, y2 = vertices[(i + 1) % n]
        min_d = min(min_d, _dist_point_to_segment(px, py, x1, y1, x2, y2))
    if point_in_polygon(px, py, vertices):
        return -min_d
    return min_d


def circle_segment_intersection_length(cx, cy, r, x1, y1, x2, y2, n=20) -> float:
    length = 0.0
    prev_inside = False
    prev_pt = None
    for i in range(n):
        t = i / (n - 1)
        px = x1 + t * (x2 - x1)
        py = y1 + t * (y2 - y1)
        inside = (px - cx) * (px - cx) + (py - cy) * (py - cy) <= r * r
        if prev_inside and inside and prev_pt is not None:
            length += math.hypot(px - prev_pt[0], py - prev_pt[1])
        prev_inside = inside
        prev_pt = (px, py)
    return length


def polygon_segment_intersection_length(
    vertices: list[tuple[float, float]], x1, y1, x2, y2, n=20,
) -> float:
    length = 0.0
    prev_inside = False
    prev_pt = None
    for i in range(n):
        t = i / (n - 1)
        px = x1 + t * (x2 - x1)
        py = y1 + t * (y2 - y1)
        inside = point_in_polygon(px, py, vertices)
        if prev_inside and inside and prev_pt is not None:
            length += math.hypot(px - prev_pt[0], py - prev_pt[1])
        prev_inside = inside
        prev_pt = (px, py)
    return length


def pore_circle_overlap(cx, cy, tool_r, pore_x, pore_y, pore_r) -> float:
    d = math.hypot(cx - pore_x, cy - pore_y)
    if d >= tool_r + pore_r:
        return 0.0
    if d <= abs(tool_r - pore_r):
        return min(1.0, (tool_r / max(pore_r, 1e-6)) ** 2 * 0.5)
    r1, r2 = tool_r, pore_r
    if d < 1e-9:
        return 1.0
    part1 = r1 * r1 * math.acos(min(1, max(-1, (d * d + r1 * r1 - r2 * r2) / (2 * d * r1))))
    part2 = r2 * r2 * math.acos(min(1, max(-1, (d * d + r2 * r2 - r1 * r1) / (2 * d * r2))))
    part3 = 0.5 * math.sqrt(max(0, (-d + r1 + r2) * (d + r1 - r2) * (d - r1 + r2) * (d + r1 + r2)))
    return min(1.0, (part1 + part2 - part3) / (math.pi * pore_r * pore_r))


def polygon_circle_overlap(
    vertices: list[tuple[float, float]],
    cx: float, cy: float,
    circle_x: float, circle_y: float, circle_r: float,
    samples: int = 24,
) -> float:
    """Fraction of the circle area that lies inside the polygon (sampled rings)."""
    d_center = math.hypot(cx - circle_x, cy - circle_y)
    poly_r = max(math.hypot(vx - cx, vy - cy) for vx, vy in vertices)
    if d_center >= poly_r + circle_r:
        return 0.0
    if point_in_polygon(circle_x, circle_y, vertices) and (
        -_dist_point_to_polygon(circle_x, circle_y, vertices) >= circle_r
    ):
        return 1.0

    hits = 1 if point_in_polygon(circle_x, circle_y, vertices) else 0
    total = 1
    n_ang = max(6, samples // 2)
    for k in (0.5, 1.0):
        rr = circle_r * k
        for i in range(n_ang):
            ang = 2 * math.pi * i / n_ang
            px = circle_x + rr * math.cos(ang)
            py = circle_y + rr * math.sin(ang)
            total += 1
            if point_in_polygon(px, py, vertices):
                hits += 1
    return min(1.0, hits / total)


# Cache lattice topology per config key (reused heavily during grid scans)
_LATTICE_CACHE: dict[tuple, tuple] = {}


def _lattice_topology(cfg: LatticeConfig):
    key = (
        round(cfg.working_area_um, 3),
        round(cfg.unit_cell_um, 3),
        cfg.n_cells,
        round(cfg.pore_diameter_um, 3),
    )
    cached = _LATTICE_CACHE.get(key)
    if cached is not None:
        return cached
    nodes = node_centers(cfg)
    pores = pore_centers(cfg)
    segs = strut_segments(cfg)
    _LATTICE_CACHE[key] = (nodes, pores, segs)
    if len(_LATTICE_CACHE) > 32:
        _LATTICE_CACHE.pop(next(iter(_LATTICE_CACHE)))
    return nodes, pores, segs


def analyze_position(cfg: LatticeConfig, tool_x: float, tool_y: float) -> GeometryFeatures:
    cx, cy, r = tool_x, tool_y, cfg.tool_radius
    nodes, pores, segs = _lattice_topology(cfg)

    min_node = min(math.hypot(cx - nx, cy - ny) for nx, ny in nodes)
    min_strut = min(_dist_point_to_segment(cx, cy, *s) for s in segs) if segs else 0

    if cfg.is_circle:
        nodes_in = sum(1 for nx, ny in nodes if math.hypot(cx - nx, cy - ny) <= r + cfg.node_radius)
        pores_in = sum(1 for px, py in pores if math.hypot(cx - px, cy - py) <= r)
        strut_len = sum(circle_segment_intersection_length(cx, cy, r, *s) for s in segs)
        pore_frac = max(
            (pore_circle_overlap(cx, cy, r, px, py, cfg.pore_radius) for px, py in pores),
            default=0,
        )
        node_frac = sum(
            pore_circle_overlap(cx, cy, r, nx, ny, cfg.node_radius) for nx, ny in nodes
        ) / max(len(nodes), 1)
    else:
        verts = regular_polygon_vertices(cx, cy, r, cfg.tool_sides, cfg.tool_rotation_deg)
        nodes_in = sum(
            1 for nx, ny in nodes
            if _dist_point_to_polygon(nx, ny, verts) <= cfg.node_radius
        )
        pores_in = sum(1 for px, py in pores if point_in_polygon(px, py, verts))
        strut_len = sum(polygon_segment_intersection_length(verts, *s) for s in segs)
        pore_frac = max(
            (
                polygon_circle_overlap(verts, cx, cy, px, py, cfg.pore_radius)
                for px, py in pores
                if math.hypot(cx - px, cy - py) <= r + cfg.pore_radius
            ),
            default=0,
        )
        node_frac = sum(
            polygon_circle_overlap(verts, cx, cy, nx, ny, cfg.node_radius)
            for nx, ny in nodes
            if math.hypot(cx - nx, cy - ny) <= r + cfg.node_radius
        ) / max(len(nodes), 1)

    scale = cfg.unit_cell_um / 500.0
    strut_risk = max(0, 1 - min_strut / (200.0 * scale))
    intersect_risk = min(1.0, strut_len / (800.0 * scale))
    ratio_factor = min(1.0, max(0, (cfg.tool_pore_ratio - 2.0) / 4.0))
    geometry_risk = min(1.0, 0.5 * strut_risk + 0.3 * intersect_risk + 0.2 * ratio_factor)

    return GeometryFeatures(
        tool_x=tool_x, tool_y=tool_y,
        min_dist_to_strut=min_strut, min_dist_to_node_center=min_node,
        nodes_inside_tool=nodes_in, pores_center_inside_tool=pores_in,
        strut_intersection_length=strut_len,
        pore_overlap_fraction=pore_frac, node_overlap_fraction=node_frac,
        geometry_risk=geometry_risk, tool_pore_ratio=cfg.tool_pore_ratio,
    )


def feature_vector(cfg: LatticeConfig, tool_x: float, tool_y: float) -> np.ndarray:
    g = analyze_position(cfg, tool_x, tool_y)
    return np.array([
        tool_x / cfg.working_area_um, tool_y / cfg.working_area_um,
        g.min_dist_to_strut, g.min_dist_to_node_center,
        g.nodes_inside_tool, g.pores_center_inside_tool,
        g.strut_intersection_length, g.pore_overlap_fraction,
        g.node_overlap_fraction, g.geometry_risk,
        cfg.tool_pore_ratio, cfg.working_area_um, cfg.tool_diameter_um,
    ])


def grid_positions(cfg: LatticeConfig, step_um: float = 75.0) -> np.ndarray:
    lo, hi = cfg.position_bounds()
    if hi <= lo:
        return np.array([[cfg.working_area_um / 2, cfg.working_area_um / 2]])
    xs = np.arange(lo, hi + 1, step_um)
    ys = np.arange(lo, hi + 1, step_um)
    return np.array([[x, y] for x in xs for y in ys])
