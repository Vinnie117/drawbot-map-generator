from matplotlib.font_manager import FontProperties
from matplotlib.patches import PathPatch
from matplotlib.path import Path
from matplotlib.transforms import Affine2D
import numpy as np
from matplotlib.textpath import TextPath
from shapely.geometry import GeometryCollection, LineString, MultiLineString, Polygon
from shapely.ops import unary_union
import math


def draw_bold_text(fig, x, y, text, *, fontsize, ha, va, color, stroke_distance, paths):

    offsets = []
    for r in (0.5 * stroke_distance, stroke_distance, 1.5 * stroke_distance):
        offsets += [
            (
                r * math.cos(2 * math.pi * i / paths),
                r * math.sin(2 * math.pi * i / paths),
            )
            for i in range(paths)
        ]

    # draw bold strokes
    for dx, dy in offsets:
        fig.text(
            x + dx, y + dy, text,
            fontsize=fontsize,
            ha=ha, va=va,
            color=color,
        )

    # draw main pass last (sharpens center)
    fig.text(
        x, y, text,
        fontsize=fontsize,
        ha=ha, va=va,
        color=color,
    )

def _compound_textpath_to_shapely(tp: TextPath):

    """
    Robust conversion preserving holes:
    Uses tp.to_polygons() rings and assigns them as shells/holes by containment depth.
    """
    rings = tp.to_polygons(closed_only=True)
    clean = []
    for r in rings:
        if r.shape[0] < 4:
            continue
        if not np.allclose(r[0], r[-1]):
            r = np.vstack([r, r[0]])
        clean.append(r)

    if not clean:
        return None

    ring_polys = [Polygon(r[:-1]) for r in clean]
    reps = [p.representative_point() for p in ring_polys]

    # containment depth per ring
    depth = []
    for i, p in enumerate(ring_polys):
        d = 0
        for j, q in enumerate(ring_polys):
            if i != j and q.contains(reps[i]):
                d += 1
        depth.append(d)

    outers = [i for i, d in enumerate(depth) if d % 2 == 0]
    built = []

    for oi in outers:
        shell = clean[oi][:-1]
        holes = []
        for hi, d in enumerate(depth):
            if hi == oi:
                continue
            if d % 2 == 1 and ring_polys[oi].contains(reps[hi]):
                holes.append(clean[hi][:-1])
        poly = Polygon(shell, holes=holes)
        if not poly.is_empty and poly.area > 0:
            built.append(poly)

    if not built:
        return None

    return unary_union(built)


def fig_hatch_filled_text(
    fig,
    x_fig, y_fig,
    text,
    *,
    fontsize_pt=28,
    fontfamily="Times New Roman",
    ha="center",
    va="top",
    angle_deg=20.0,
    spacing_mm=0.6,
    outline=True,
    outline_lw=0.6,
    hatch_lw=0.35,
    color="black",
    zorder=1000,
):
    """
    Draw hatch-filled text at figure-fraction coordinates (like fig.text),
    using stroke lines clipped to glyph polygons.
    """
    fp = FontProperties(family=fontfamily)
    tp = TextPath((0, 0), text, size=fontsize_pt, prop=fp)

    # Anchor alignment in *point* space
    bb = tp.get_extents()
    w, h = bb.width, bb.height

    if ha == "center":
        shift_x = -(bb.x0 + w / 2.0)
    elif ha == "right":
        shift_x = -(bb.x0 + w)
    else:
        shift_x = -bb.x0

    if va == "center":
        shift_y = -(bb.y0 + h / 2.0)
    elif va == "top":
        shift_y = -(bb.y0 + h)
    elif va == "bottom":
        shift_y = -bb.y0
    else:
        shift_y = 0.0

    tp_aligned = Affine2D().translate(shift_x, shift_y).transform_path(tp)

    poly = _compound_textpath_to_shapely(tp_aligned)
    if poly is None or poly.is_empty:
        return

    # Hatch spacing in points
    spacing_pt = spacing_mm * 72.0 / 25.4

    # Build hatch lines in point coords
    ang = np.deg2rad(angle_deg)
    ca, sa = np.cos(ang), np.sin(ang)
    rot = np.array([[ca, -sa], [sa, ca]])
    invrot = np.array([[ca, sa], [-sa, ca]])  # inverse

    minx, miny, maxx, maxy = poly.bounds
    size = max(maxx - minx, maxy - miny)
    pad = 0.75 * size
    minx2, miny2, maxx2, maxy2 = minx - pad, miny - pad, maxx + pad, maxy + pad

    corners = np.array([[minx2, miny2], [minx2, maxy2], [maxx2, miny2], [maxx2, maxy2]])
    corners_r = corners @ rot.T
    ymin_r, ymax_r = corners_r[:, 1].min(), corners_r[:, 1].max()
    xmin_r, xmax_r = corners_r[:, 0].min(), corners_r[:, 0].max()

    ys = np.arange(ymin_r - spacing_pt, ymax_r + spacing_pt, spacing_pt)

    segments = []
    for y in ys:
        p1 = np.array([xmin_r - pad, y]) @ invrot.T
        p2 = np.array([xmax_r + pad, y]) @ invrot.T
        line = LineString([tuple(p1), tuple(p2)])
        inter = poly.intersection(line)

        if inter.is_empty:
            continue
        if isinstance(inter, LineString):
            segments.append(inter)
        elif isinstance(inter, MultiLineString):
            segments.extend(list(inter.geoms))
        elif isinstance(inter, GeometryCollection):
            for g in inter.geoms:
                if isinstance(g, LineString) and not g.is_empty:
                    segments.append(g)

    # Convert segments -> Matplotlib Path in point coords
    verts, codes = [], []
    for seg in segments:
        coords = np.asarray(seg.coords)
        if coords.shape[0] < 2:
            continue
        verts.append((coords[0, 0], coords[0, 1]))
        codes.append(Path.MOVETO)
        for k in range(1, coords.shape[0]):
            verts.append((coords[k, 0], coords[k, 1]))
            codes.append(Path.LINETO)

    if not verts:
        return

    hatch_path = Path(verts, codes)

    # points -> figure fraction + placement
    fig_w_in, fig_h_in = fig.get_size_inches()
    sx = 1.0 / (72.0 * fig_w_in)
    sy = 1.0 / (72.0 * fig_h_in)

    tr = Affine2D().scale(sx, sy).translate(x_fig, y_fig) + fig.transFigure

    hatch_patch = PathPatch(
        hatch_path,
        transform=tr,
        facecolor="none",
        edgecolor=color,
        lw=hatch_lw,
        capstyle="round",
        joinstyle="round",
        zorder=zorder,
    )
    hatch_patch.set_clip_on(False)
    hatch_patch.set_in_layout(True)
    fig.add_artist(hatch_patch)

    if outline:
        outline_patch = PathPatch(
            tp_aligned,
            transform=tr,
            facecolor="none",
            edgecolor=color,
            lw=outline_lw,
            capstyle="round",
            joinstyle="round",
            zorder=zorder + 1,
        )
        outline_patch.set_clip_on(False)
        outline_patch.set_in_layout(True)
        fig.add_artist(outline_patch)


def _textpath_to_shapely_evenodd(tp_path):
    """
    Convert a Matplotlib Path (aligned TextPath) to Shapely geometry using
    an even-odd fill rule (XOR / symmetric_difference). This preserves holes
    reliably for tricky glyphs like 'a', 'e', 'g', etc.
    """
    rings = tp_path.to_polygons(closed_only=True)

    geom = None
    for r in rings:
        if r.shape[0] < 4:
            continue
        if not np.allclose(r[0], r[-1]):
            r = np.vstack([r, r[0]])

        poly = Polygon(r[:-1])
        if poly.is_empty:
            continue

        # Fix occasional invalid rings from font outlines
        if not poly.is_valid:
            poly = poly.buffer(0)

        if poly.is_empty:
            continue

        geom = poly if geom is None else geom.symmetric_difference(poly)

    if geom is None or geom.is_empty:
        return None

    # Optional cleanup
    if not geom.is_valid:
        geom = geom.buffer(0)

    return geom


def _shapely_lines_to_mpl_path(geom):
    """Convert Shapely LineString/MultiLineString into a single Matplotlib Path."""
    verts, codes = [], []

    def add_line(ls: LineString):
        coords = np.asarray(ls.coords)
        if coords.shape[0] < 2:
            return
        verts.append((coords[0, 0], coords[0, 1]))
        codes.append(Path.MOVETO)
        for k in range(1, coords.shape[0]):
            verts.append((coords[k, 0], coords[k, 1]))
            codes.append(Path.LINETO)

    if isinstance(geom, LineString):
        add_line(geom)
    elif isinstance(geom, MultiLineString):
        for g in geom.geoms:
            add_line(g)
    elif isinstance(geom, GeometryCollection):
        for g in geom.geoms:
            if isinstance(g, LineString):
                add_line(g)
            elif isinstance(g, MultiLineString):
                for h in g.geoms:
                    add_line(h)

    if not verts:
        return None
    return Path(verts, codes)


def fig_contour_filled_text(
    fig,
    x_fig, y_fig,
    text,
    *,
    fontsize_pt=28,
    fontfamily="Times New Roman",
    ha="center",
    va="top",
    step_mm=0.7,          # spacing between contour lines (smaller = denser)
    max_levels=200,       # safety cap
    outline=True,
    lw=0.35,              # stroke width for contours (visual)
    outline_lw=0.6,
    color="black",
    zorder=1000,
):
    """
    Draw topographic contour-style fill for text:
    repeated inward offsets (buffers) of glyph polygons, rendered as lines.
    """

    # 1) TextPath in points
    fp = FontProperties(family=fontfamily)
    tp = TextPath((0, 0), text, size=fontsize_pt, prop=fp)

    # 2) Align anchor in point space
    bb = tp.get_extents()
    w, h = bb.width, bb.height

    if ha == "center":
        shift_x = -(bb.x0 + w / 2.0)
    elif ha == "right":
        shift_x = -(bb.x0 + w)
    else:
        shift_x = -bb.x0

    if va == "center":
        shift_y = -(bb.y0 + h / 2.0)
    elif va == "top":
        shift_y = -(bb.y0 + h)
    elif va == "bottom":
        shift_y = -bb.y0
    else:
        shift_y = 0.0

    tp_aligned = Affine2D().translate(shift_x, shift_y).transform_path(tp)

    # 3) Convert to shapely polygon(s)
    poly = _textpath_to_shapely_evenodd(tp_aligned)
    if poly is None or poly.is_empty:
        return

    # 4) Generate inward contours by negative buffering
    step_pt = step_mm * 72.0 / 25.4  # mm -> points
    current = poly

    contour_lines = []
    for _ in range(max_levels):
        # boundary of current shape
        contour_lines.append(current.boundary)
        # move inward
        next_shape = current.buffer(-step_pt, join_style=2, cap_style=2)
        if next_shape.is_empty:
            break
        current = next_shape

    # Union all lines for simpler drawing
    all_lines = unary_union(contour_lines)
    path = _shapely_lines_to_mpl_path(all_lines)
    if path is None:
        return

    # 5) Transform points -> figure fraction -> display
    fig_w_in, fig_h_in = fig.get_size_inches()
    sx = 1.0 / (72.0 * fig_w_in)
    sy = 1.0 / (72.0 * fig_h_in)
    tr = Affine2D().scale(sx, sy).translate(x_fig, y_fig) + fig.transFigure

    # Draw contours
    contour_patch = PathPatch(
        path,
        transform=tr,
        facecolor="none",
        edgecolor=color,
        lw=lw,
        capstyle="round",
        joinstyle="round",
        zorder=zorder,
    )
    contour_patch.set_clip_on(False)
    contour_patch.set_in_layout(True)
    fig.add_artist(contour_patch)

    # Optional crisp outline on top
    if outline:
        outline_patch = PathPatch(
            tp_aligned,
            transform=tr,
            facecolor="none",
            edgecolor=color,
            lw=outline_lw,
            capstyle="round",
            joinstyle="round",
            zorder=zorder + 1,
        )
        outline_patch.set_clip_on(False)
        outline_patch.set_in_layout(True)
        fig.add_artist(outline_patch)
