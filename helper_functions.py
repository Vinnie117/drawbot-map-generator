import osmnx as ox
from pyproj import Transformer
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.patches import Rectangle
import math

import numpy as np
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties
from matplotlib.path import Path
from matplotlib.patches import PathPatch
from matplotlib.transforms import Affine2D

from shapely.geometry import Polygon, LineString, MultiLineString, GeometryCollection
from shapely.ops import unary_union

def get_page_layout(paper_format: str, margin_mm: float):
    """
    Compute figure size (in inches) and axes rectangle for centered plotting
    with a margin around the edges.

    Args:
        paper_format (str): "a3" or "a4" (portrait).
        margin_mm (float): margin size in millimeters.

    Returns:
        (fig_width_in, fig_height_in, axes_rect)
        where axes_rect = [left, bottom, width, height]
        suitable for fig.add_axes().
    """
    # ISO 216 sizes in mm (portrait)
    sizes = {
        "a4": (210, 297),
        "a3": (297, 420)
    }

    fmt = paper_format.lower()
    if fmt not in sizes:
        raise ValueError("paper_format must be 'a3' or 'a4'")

    width_mm, height_mm = sizes[fmt]

    mm_to_inch = 1 / 25.4
    fig_width_in = width_mm * mm_to_inch
    fig_height_in = height_mm * mm_to_inch
    margin_in = margin_mm * mm_to_inch

    # margin as fraction of figure size
    left = right = margin_in / fig_width_in
    bottom = top = margin_in / fig_height_in

    axes_rect = [
        left,
        bottom,
        1 - left - right,
        1 - top - bottom
    ]

    return fig_width_in, fig_height_in, axes_rect



def get_graph(location, network_type="drive", dist=2000):
    """
    Create an OSMnx graph either from:
      - a place name (string), or
      - coordinates (tuple -> (lat, lon))

    Args:
        location: str OR (lat, lon)
        network_type: "drive", "walk", "bike", etc.
        dist: radius in meters around the coordinate point (ignored for place names)

    Returns:
        OSMnx MultiDiGraph
    """
    # Case 1 → place name
    if isinstance(location, str):
        return ox.graph_from_place(location, network_type=network_type)

    # Case 2 → coordinate pair
    if (
        isinstance(location, (tuple, list)) 
        and len(location) == 2
        and all(isinstance(v, (float, int)) for v in location)
    ):
        lat, lon = location
        return ox.graph_from_point((lat, lon), dist=dist, network_type=network_type)

    raise ValueError("location must be a place name (str) or a (lat, lon) tuple")


def get_location_coordinates(location):
    """
    Returns (lat, lon) for a location.
    - If location is already a tuple/list -> return it unchanged.
    - If it's a place name string -> geocode it using OSMnx.
    """
    if isinstance(location, (tuple, list)) and len(location) == 2:
        return float(location[0]), float(location[1])

    pt = ox.geocode(location)
    return float(pt[0]), float(pt[1])


def get_text_height(fig, text, fontsize):
    """
    Return text height in figure coordinates (0–1).
    """
    # Ensure we have a renderer
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()

    dummy = fig.text(0, 0, text, fontsize=fontsize)
    bbox = dummy.get_window_extent(renderer=renderer)
    dummy.remove()

    return bbox.height / fig.bbox.height

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




def compute_block_center_delta(
    fig,
    ax,
    location,
    position="bottom",
    city_fontsize=20,
    coord_fontsize=12,
    padding_factor=0.3,
    between_factor=0.5,
    reserve_city=True,
    reserve_coords=True,
    canonical_coord_text="00.0000° N, 000.0000° E",
):
    """
    Compute ONE vertical centering delta for block_centered mode.
    Use a canonical coord string so base/overlay/combined align perfectly.
    """
    ax_pos = ax.get_position()
    city_text = str(location)

    # These must exist in your helpers
    city_h = get_text_height(fig, city_text, city_fontsize) if reserve_city else 0.0
    coord_h = get_text_height(fig, canonical_coord_text, coord_fontsize) if reserve_coords else 0.0

    base_h = city_h if city_h > 0 else (coord_h if coord_h > 0 else 0.02)
    padding = base_h * padding_factor
    between = base_h * between_factor if (reserve_city and reserve_coords) else 0.0

    if position == "bottom":
        y_city = ax_pos.y0 - padding
        y_coord = y_city - city_h - between
        block_top = ax_pos.y1
        block_bottom = (y_coord - coord_h) if reserve_coords else (y_city - city_h)
    else:
        y_city = ax_pos.y1 + padding
        y_coord = y_city + city_h + between
        block_top = (y_coord + coord_h) if reserve_coords else (y_city + city_h)
        block_bottom = ax_pos.y0

    block_center = 0.5 * (block_top + block_bottom)
    return 0.5 - block_center


def add_map_labels(
    fig,
    ax,
    location,
    mode="map_centered",
    position="bottom",
    show_city=True,
    show_coords=True,
    reserve_city=None,
    reserve_coords=None,
    city_fontsize=20,
    coord_fontsize=12,
    padding_factor=0.3,
    between_factor=0.5,
    coords_override=None,
    coords_color="black",
    # --- from the old version ---
    delta_override=None,           # force identical vertical centering across layers
    canonical_coord_text=None,     # force identical reserved coord height across layers
    # --- new in the current version ---
    text_backend="mpl",            # "mpl" or "vpype"
    # --- optional: keep old bold city rendering behavior when using mpl ---
    city_draw="plain",              # "bold" or "plain"
    bold_kwargs=None,              # forwarded to draw_bold_text(...)
    multipass=5,     # draw same label N times at identical position

    hatch_city=False,
    hatch_coords=False,
    hatch_spacing_mm=0.6,
    hatch_angle_deg=20.0,
    hatch_outline=True,
    hatch_outline_lw=0.6,
    hatch_lw=0.35,
):
    """
    Computes layout for city / coord labels above/below the map.

    - mode="block_centered": shifts ax + labels so (map + reserved labels) are centered
    - reserve_* reserve layout height even if show_* is False
    - delta_override forces the exact same centering shift (for perfect layer alignment)
    - canonical_coord_text ensures reserved coord height is identical across layers

    If text_backend == "mpl":
        draws text on the figure.
    If text_backend == "vpype":
        does NOT draw text, returns layout info (in mm) for vpype_add_hershey_text().
    """
    if position not in {"bottom", "top"}:
        raise ValueError("position must be 'bottom' or 'top'")
    if text_backend not in {"mpl", "vpype"}:
        raise ValueError("text_backend must be 'mpl' or 'vpype'")
    if mode not in {"map_centered", "block_centered"}:
        raise ValueError("mode must be 'map_centered' or 'block_centered'")

    if reserve_city is None:
        reserve_city = show_city
    if reserve_coords is None:
        reserve_coords = show_coords

    if bold_kwargs is None:
        bold_kwargs = {}

    ax_pos = ax.get_position()
    city_text = str(location)

    # --- coordinate text (and precision) ---
    if coords_override is not None:
        lat, lon = float(coords_override[0]), float(coords_override[1])
        precision = 4
    else:
        lat, lon = get_location_coordinates(location)
        precision = 2

    lat_suffix = "N" if lat >= 0 else "S"
    lon_suffix = "E" if lon >= 0 else "W"
    coord_text = (
        f"{abs(lat):.{precision}f}° {lat_suffix}, "
        f"{abs(lon):.{precision}f}° {lon_suffix}"
    )

    # Use canonical text for layout height so multiple layers reserve identical space
    coord_text_for_layout = canonical_coord_text if canonical_coord_text else coord_text

    # --- reserved layout heights (figure fraction) ---
    city_h = get_text_height(fig, city_text, city_fontsize) if reserve_city else 0.0
    coord_h = (
        get_text_height(fig, coord_text_for_layout, coord_fontsize) if reserve_coords else 0.0
    )

    base_h = city_h if city_h > 0 else (coord_h if coord_h > 0 else 0.02)
    padding = base_h * padding_factor
    between = base_h * between_factor if (reserve_city and reserve_coords) else 0.0

    # --- layout positions (figure fraction) ---
    if position == "bottom":
        y_city = ax_pos.y0 - padding
        y_coord = y_city - city_h - between
        block_top = ax_pos.y1
        block_bottom = (y_coord - coord_h) if reserve_coords else (y_city - city_h)
        va = "top"
    else:
        y_city = ax_pos.y1 + padding
        y_coord = y_city + city_h + between
        block_top = (y_coord + coord_h) if reserve_coords else (y_city + city_h)
        block_bottom = ax_pos.y0
        va = "bottom"

    # --- block centering ---
    if mode == "block_centered":
        if delta_override is None:
            delta = 0.5 - 0.5 * (block_top + block_bottom)
        else:
            delta = float(delta_override)

        ax.set_position([ax_pos.x0, ax_pos.y0 + delta, ax_pos.width, ax_pos.height])
        y_city += delta
        y_coord += delta

 # --- MPL DRAW ---
    if text_backend == "mpl":
        if show_city:
            if city_draw == "bold" and not hatch_city:
                draw_bold_text(
                    fig, 0.5, y_city, city_text,
                    fontsize=city_fontsize,
                    ha="center", va=va,
                    color="black",
                    **{"stroke_distance": 0.0006, "paths": 5, **bold_kwargs},
                )

            else:
                # hatch or plain multipass normal text
                if hatch_city:
                    fig_hatch_filled_text(
                        fig,
                        0.5, y_city,
                        city_text,
                        fontsize_pt=city_fontsize,
                        fontfamily="Times New Roman",
                        ha="center",
                        va=va,
                        angle_deg=hatch_angle_deg,
                        spacing_mm=hatch_spacing_mm,
                        outline=hatch_outline,
                        outline_lw=hatch_outline_lw,
                        hatch_lw=hatch_lw,
                        color="black",
                        zorder=1000,
                    )
                else:
                    for _ in range(int(multipass)):
                        fig.text(
                            0.5, y_city, city_text,
                            ha="center", va=va,
                            fontsize=city_fontsize,
                            fontfamily="Times New Roman",
                            color="black",
                        )

        if show_coords:
            if hatch_coords:
                fig_hatch_filled_text(
                    fig,
                    0.5, y_coord,
                    coord_text,
                    fontsize_pt=coord_fontsize,
                    fontfamily="Times New Roman",
                    ha="center",
                    va=va,
                    angle_deg=hatch_angle_deg,
                    spacing_mm=max(0.35, hatch_spacing_mm * 0.85),
                    outline=False,                 # coords usually cleaner without outline
                    outline_lw=hatch_outline_lw,
                    hatch_lw=max(0.25, hatch_lw * 0.9),
                    color=coords_color,
                    zorder=1000,
                )
            else:
                fig.text(
                    0.5, y_coord, coord_text,
                    ha="center", va=va,
                    fontsize=coord_fontsize,
                    color=coords_color,
                    fontfamily="Times New Roman",
                )

        return None

    # --- VPYPE RETURN ---
    # (return positions in mm; vpype will do the actual text rendering)
    fig_w_in, fig_h_in = fig.get_size_inches()
    mm_per_in = 25.4
    fig_w_mm = fig_w_in * mm_per_in
    fig_h_mm = fig_h_in * mm_per_in

    def pt_to_mm(pt: float) -> float:
        return pt * 0.3527777778  # exact

    # Matplotlib y is from bottom; SVG/vpype y is from top => flip it.
    def mpl_yfrac_to_vpype_mm(y_frac: float) -> float:
        y_mm_from_bottom = y_frac * fig_h_mm
        return fig_h_mm - y_mm_from_bottom

    # vpype places text at a baseline; Matplotlib with va="top" uses top edge.
    # This heuristic shifts baseline down by ~0.85 of font height.
    def baseline_shift_mm(fontsize_mm: float, va: str) -> float:
        if va == "top":
            return 0.85 * fontsize_mm
        elif va == "bottom":
            return 0.15 * fontsize_mm
        return 0.0

    va_city = "top" if position == "bottom" else "bottom"
    va_coord = va_city

    city_size_mm = pt_to_mm(city_fontsize)
    coord_size_mm = pt_to_mm(coord_fontsize)

    x_center_mm = 0.5 * fig_w_mm

    y_city_mm = mpl_yfrac_to_vpype_mm(y_city) + baseline_shift_mm(city_size_mm, va_city)
    y_coord_mm = mpl_yfrac_to_vpype_mm(y_coord) + baseline_shift_mm(coord_size_mm, va_coord)

    return {
        "city": {
            "text": city_text,
            "x_mm": x_center_mm,
            "y_mm": y_city_mm,
            "fontsize_mm": city_size_mm,
            "visible": show_city,
        },
        "coords": {
            "text": coord_text,
            "x_mm": x_center_mm,
            "y_mm": y_coord_mm,
            "fontsize_mm": coord_size_mm,
            "visible": show_coords,
            "color": coords_color,
        }
    }






def add_marker(ax, G, lat_lon, color="red", size=40, zorder=10, edgecolor=None, linewidth=0):
    """
    Draw a marker on the OSMnx map at (lat, lon) (WGS84) and return (lat, lon).
    """
    lat, lon = float(lat_lon[0]), float(lat_lon[1])
    graph_crs = G.graph.get("crs", None)

    if graph_crs is None or str(graph_crs).lower() in {"epsg:4326", "4326"}:
        x, y = lon, lat
    else:
        transformer = Transformer.from_crs("EPSG:4326", graph_crs, always_xy=True)
        x, y = transformer.transform(lon, lat)

    ax.scatter([x], [y], s=size, c=color, zorder=zorder,
               edgecolors=edgecolor if edgecolor is not None else "none",
               linewidths=linewidth)
    return (lat, lon)


def export_svg_with_layers(
    G,
    location,
    page_layout,  # (fig_w, fig_h, rect) from get_page_layout
    point=None,  # (lat, lon) or None
    marker_color="red",
    marker_size=10,
    mode="block_centered",
    position="bottom",
    out_combined="combined.svg",
    out_base="layer_base.svg",
    out_overlay="layer_overlay.svg",
    city_fontsize=20,
    coord_fontsize=12,
    padding_factor=0.3,
    between_factor=0.5,
    text_backend = None,
    multipass=1
):
    """
    Export three SVGs that overlay perfectly (puzzle-piece alignment):
      - base:     map + city only (coords reserved for consistent centering)
      - overlay:  marker + coords only (city reserved for consistent centering)
      - combined: everything

    Key: compute ONE delta using canonical coord string, reuse it for all 3.
    """
    fig_w, fig_h, rect = page_layout
    canonical_coord_text = "00.0000° N, 000.0000° E"

    # -------------------------
    # BASE
    # -------------------------
    fig_base = plt.figure(figsize=(fig_w, fig_h))
    ax_base = fig_base.add_axes(rect)

    ox.plot_graph(
        G,
        ax=ax_base,
        show=False,
        close=False,
        bgcolor="white",
        node_size=0,
        edge_color="black",
        edge_linewidth=0.5,
    )

    # lock view for perfect alignment
    xlim = ax_base.get_xlim()
    ylim = ax_base.get_ylim()
    aspect = ax_base.get_aspect()

    # compute ONE centering delta based on canonical reserved strings
    delta = compute_block_center_delta(
        fig_base,
        ax_base,
        location,
        position=position,
        city_fontsize=city_fontsize,
        coord_fontsize=coord_fontsize,
        padding_factor=padding_factor,
        between_factor=between_factor,
        reserve_city=True,
        reserve_coords=True,
        canonical_coord_text=canonical_coord_text,
    )

    # base: city only (coords reserved)
    add_map_labels(
        fig_base,
        ax_base,
        location,
        mode=mode,
        position=position,
        show_city=False,
        show_coords=False,
        reserve_city=True,
        reserve_coords=True,
        city_fontsize=city_fontsize,
        coord_fontsize=coord_fontsize,
        padding_factor=padding_factor,
        between_factor=between_factor,
        delta_override=delta,
        canonical_coord_text=canonical_coord_text
    )

    fig_base.patch.set_visible(False)
    ax_base.patch.set_visible(False)
    ax_base.set_axis_off()
    fig_base.savefig(out_base, format="svg", transparent=True)
    plt.close(fig_base)

    # -------------------------
    # OVERLAY
    # -------------------------
    fig_ov = plt.figure(figsize=(fig_w, fig_h))
    ax_ov = fig_ov.add_axes(rect)

    ax_ov.set_xlim(xlim)
    ax_ov.set_ylim(ylim)
    ax_ov.set_aspect(aspect)
    ax_ov.set_axis_off()

    marker_latlon = None
    if point is not None:
        marker_latlon = add_marker(ax_ov, G, point, color=marker_color, size=marker_size)

    # overlay: coords only (city reserved)
    if marker_latlon is not None:

        #### VPYPE
        if text_backend == "vpype":
            label_layout = add_map_labels(
                fig_ov,
                ax_ov,
                location,
                mode="block_centered",
                position="bottom",
                show_city=True,
                show_coords=False,
                coords_override=marker_latlon,  # show marker coords if present
                coords_color=marker_color,      # same color as dot
                text_backend="vpype",           # IMPORTANT
            )

        if text_backend == "mpl":

            ### Matplotlib
            for _ in range(int(multipass)):
                add_map_labels(
                    fig_ov, ax_ov, "Berlin",
                    text_backend="mpl",
                    city_draw="plain",
                    show_coords=False,
                    hatch_city=True,
                    hatch_coords=False,        # I'd keep coords normal unless you really need “filled”
                    hatch_spacing_mm=0.3,
                    hatch_angle_deg=25,
                    hatch_outline=True,
                    hatch_outline_lw=0.5,
                    hatch_lw=0.30,
                )

    else:
        # no marker: still reserve layout so overlay aligns if you later combine

        if text_backend == "vpype":
            #### VPYPE
            label_layout = add_map_labels(
                fig_ov,
                ax_ov,
                location,
                mode="block_centered",
                position="bottom",
                show_city=True,
                show_coords=False,
                coords_override=marker_latlon,  # show marker coords if present
                coords_color=marker_color,      # same color as dot
                text_backend="vpype",           # IMPORTANT
            )

        if text_backend == "mpl":
            ### Matplotlib
            add_map_labels(
                fig_ov, ax_ov, "Berlin Bla Blubb",
                text_backend="mpl",
                city_draw="plain",
                hatch_city=True,
                hatch_coords=False,        # I'd keep coords normal unless you really need “filled”
                hatch_spacing_mm=0.55,
                hatch_angle_deg=25,
                hatch_outline=True,
                hatch_outline_lw=0.5,
                hatch_lw=0.30,
            )

    fig_ov.patch.set_visible(False)
    ax_ov.patch.set_visible(False)
    fig_ov.savefig(out_overlay, format="svg", transparent=True)

    if text_backend == "vpype":

        vpype_add_hershey_text(
            out_overlay,
            "maps/test_vpype_layer.svg",
            label_layout,
            font="timesr",
            stroke_distance_mm=0.3,
            offset_paths=4,                  # number of directions away from the center
            offset_rings=(0.0, 0.33, 0.66, 1.0),    # how many layer to draw in what distance (multiplied with distance)
            passes=1,
        )



    plt.close(fig_ov)

    # -------------------------
    # COMBINED
    # -------------------------
    fig_all = plt.figure(figsize=(fig_w, fig_h))
    ax_all = fig_all.add_axes(rect)

    ax_all.set_xlim(xlim)
    ax_all.set_ylim(ylim)
    ax_all.set_aspect(aspect)
    ax_all.set_axis_off()

    ox.plot_graph(
        G,
        ax=ax_all,
        show=False,
        close=False,
        bgcolor="white",
        node_size=0,
        edge_color="black",
        edge_linewidth=0.5,
    )

    marker_latlon2 = None
    if point is not None:
        marker_latlon2 = add_marker(ax_all, G, point, color=marker_color, size=marker_size)

    add_map_labels(
        fig_all,
        ax_all,
        location,
        mode=mode,
        position=position,
        show_city=True,
        show_coords=True,
        reserve_city=True,
        reserve_coords=True,
        coords_override=marker_latlon2,
        coords_color=marker_color if marker_latlon2 is not None else "black",
        city_fontsize=city_fontsize,
        coord_fontsize=coord_fontsize,
        padding_factor=padding_factor,
        between_factor=between_factor,
        delta_override=delta,
        canonical_coord_text=canonical_coord_text
    )

    fig_all.patch.set_visible(False)
    ax_all.patch.set_visible(False)
    fig_all.savefig(out_combined, format="svg", transparent=True)
    plt.close(fig_all)


def set_map_frame(fig, ax, enabled=True, linewidth=1.0, color="black", pad=0.0, zorder=50):
    """
    Draw (or hide) a rectangle frame around the map axes area.

    Args:
        fig, ax: Matplotlib figure/axes.
        enabled (bool): show/hide frame.
        linewidth (float): stroke width in points.
        color (str): stroke color.
        pad (float): padding around the axes box in figure coordinates (0..1).
                     Example: 0.005 adds a small gap outward.
        zorder (int): draw order.
    Returns:
        The Rectangle artist (or None if disabled).
    """
    # store reference so repeated calls replace the old one
    old = getattr(ax, "_map_frame_artist", None)
    if old is not None:
        old.remove()
        ax._map_frame_artist = None

    if not enabled:
        return None

    pos = ax.get_position()  # in figure coords
    x0 = pos.x0 - pad
    y0 = pos.y0 - pad
    w = pos.width + 2 * pad
    h = pos.height + 2 * pad

    frame = Rectangle(
        (x0, y0), w, h,
        transform=fig.transFigure,
        fill=False,
        edgecolor=color,
        linewidth=linewidth,
        zorder=zorder,
        joinstyle="miter"
    )
    fig.add_artist(frame)
    ax._map_frame_artist = frame
    return frame

def filter_short_edges(G, min_length_m=20):
    """
    Remove edges shorter than min_length_m from an OSMnx graph.

    Args:
        G: OSMnx graph
        min_length_m: minimum edge length to keep (meters)

    Returns:
        Filtered graph
    """
    # Ensure projected CRS so lengths are meters
    if str(G.graph.get("crs", "")).lower() in {"epsg:4326", "4326"}:
        G = ox.project_graph(G)

    gdf_nodes, gdf_edges = ox.graph_to_gdfs(G, nodes=True, edges=True, fill_edge_geometry=True)

    # Compute length (in graph CRS units; projected -> meters)
    gdf_edges = gdf_edges[gdf_edges.geometry.length >= float(min_length_m)]

    # Keep only nodes that still appear in remaining edges
    used_nodes = set(gdf_edges.index.get_level_values("u")) | set(gdf_edges.index.get_level_values("v"))
    gdf_nodes = gdf_nodes.loc[gdf_nodes.index.intersection(used_nodes)]

    # Rebuild graph
    G_filt = ox.graph_from_gdfs(gdf_nodes, gdf_edges)
    return G_filt


def crop_view_to_frame(
    fig,
    ax,
    G,
    center_latlon=None,          # (lat, lon)
    bbox_latlon=None,            # (north, south, east, west)
    height_m=5000,               # used with center_latlon
    width_m=None,                # optional; if None derived from axis aspect and height
):
    """
    Crop the axes view so the map fills the axes rectangle (crop mode),
    and choose which area is shown using either a center point or a bbox.

    Exactly one of center_latlon or bbox_latlon should be provided.

    Args:
        fig, ax: Matplotlib figure/axes.
        G: OSMnx graph (used for CRS transform).
        center_latlon: (lat, lon) center of view in WGS84.
        bbox_latlon: (north, south, east, west) in WGS84.
        height_m: desired height of view in meters (if using center_latlon).
        width_m: desired width in meters (if using center_latlon). If None, computed
                 to match axes aspect ratio.
    """
    if (center_latlon is None) == (bbox_latlon is None):
        raise ValueError("Provide exactly one of center_latlon or bbox_latlon")

    graph_crs = G.graph.get("crs", None)
    if graph_crs is None:
        raise ValueError("Graph CRS missing: G.graph['crs'] is required")

    # transformer from WGS84 -> graph CRS (meters in UTM usually)
    transformer = Transformer.from_crs("EPSG:4326", graph_crs, always_xy=True)

    # axes aspect ratio (width/height in pixels)
    fig.canvas.draw()
    bbox = ax.get_window_extent()
    ax_aspect = bbox.width / bbox.height  # width/height

    if center_latlon is not None:
        lat, lon = float(center_latlon[0]), float(center_latlon[1])
        cx, cy = transformer.transform(lon, lat)

        h = float(height_m)
        w = float(width_m) if width_m is not None else ax_aspect * h

        ax.set_xlim(cx - w / 2, cx + w / 2)
        ax.set_ylim(cy - h / 2, cy + h / 2)

    else:
        north, south, east, west = bbox_latlon
        # transform bbox corners
        x_w, y_s = transformer.transform(float(west), float(south))
        x_e, y_n = transformer.transform(float(east), float(north))

        xmin, xmax = sorted([x_w, x_e])
        ymin, ymax = sorted([y_s, y_n])

        xspan = xmax - xmin
        yspan = ymax - ymin
        xmid = (xmin + xmax) / 2
        ymid = (ymin + ymax) / 2

        # CROP to fill axes (reduce the longer dimension)
        data_aspect = xspan / yspan if yspan != 0 else ax_aspect

        if data_aspect > ax_aspect:
            # too wide -> crop x
            new_xspan = ax_aspect * yspan
            ax.set_xlim(xmid - new_xspan / 2, xmid + new_xspan / 2)
            ax.set_ylim(ymin, ymax)
        else:
            # too tall -> crop y
            new_yspan = xspan / ax_aspect
            ax.set_xlim(xmin, xmax)
            ax.set_ylim(ymid - new_yspan / 2, ymid + new_yspan / 2)

    ax.margins(0)

    
import shutil
import subprocess



def _circle_offsets_mm(radius_mm: float, paths: int):
    """Generate (dx, dy) offsets evenly spaced on a circle."""
    if radius_mm <= 0:
        return [(0.0, 0.0)]
    return [
        (
            radius_mm * math.cos(2 * math.pi * i / paths),
            radius_mm * math.sin(2 * math.pi * i / paths),
        )
        for i in range(paths)
    ]

def _make_offsets_mm(
    stroke_distance_mm: float,
    paths: int,
    rings=(0.0, 0.5, 1.0, 1.5),
    include_center=True,
):
    """
    Create offsets in mm.

    stroke_distance_mm: base radial step in mm
    paths: number of offsets per ring (angular resolution)
    rings: multiples of stroke_distance_mm used as radii
    include_center: ensure (0,0) is included
    """
    offsets = []
    for f in rings:
        r = f * stroke_distance_mm
        offsets.extend(_circle_offsets_mm(r, paths))

    if include_center and (0.0, 0.0) not in offsets:
        offsets.append((0.0, 0.0))

    # De-duplicate (floating tolerance)
    uniq = []
    seen = set()
    for dx, dy in offsets:
        key = (round(dx, 4), round(dy, 4))  # 0.0001mm tolerance
        if key not in seen:
            seen.add(key)
            uniq.append((dx, dy))
    return uniq



def vpype_add_hershey_text(
    in_svg,
    out_svg,
    label_layout,
    font="futural",

    # NEW: thickness / boldness controls
    passes=1,                      # multipass count per offset position (darkens)
    stroke_distance_mm=0.0,         # >0 enables offset boldness (thickens)
    offset_paths=12,               # number of offsets around each ring
    offset_rings=(0.0, 1.0),       # radii in multiples of stroke_distance_mm (0.0 means center)
    layer="new",                   # put text on new layer by default
):
    """
    Add single-stroke (Hershey) text to an SVG using vpype, optionally thickened.

    Two mechanisms:
      - passes: repeats the exact same geometry N times (darker, not thicker)
      - offsets: draws the text multiple times with small XY shifts (thicker)

    Recommended starting point for a 0.7mm pen:
      stroke_distance_mm=0.25 to 0.35
      offset_paths=12 to 20
      offset_rings=(0.0, 1.0)  or (0.0, 0.7, 1.0)
      passes=1 or 2
    """
    vpype_cmd = shutil.which("vpype")
    if vpype_cmd is None:
        raise RuntimeError("vpype executable not found in PATH")

    cmd = [vpype_cmd, "read", in_svg]

    # Build offsets
    if stroke_distance_mm and stroke_distance_mm > 0:
        offsets = _make_offsets_mm(
            stroke_distance_mm=float(stroke_distance_mm),
            paths=int(offset_paths),
            rings=tuple(offset_rings),
            include_center=True,
        )
    else:
        offsets = [(0.0, 0.0)]  # no thickening, just one placement

    for key in ("city", "coords"):
        item = label_layout.get(key)
        if not item or not item.get("visible", False):
            continue

        text = item["text"]
        size_mm = float(item["fontsize_mm"])
        x0 = float(item["x_mm"])
        y0 = float(item["y_mm"])

        # Draw at each offset
        for dx, dy in offsets:
            cmd += [
                "text",
                "--layer", layer,
                "--font", font,
                "--size", f"{size_mm:.3f}mm",
                "--align", "center",
                "--position", f"{(x0 + dx):.3f}mm", f"{(y0 + dy):.3f}mm",
                text,
            ]

            # Optional: repeat the same geometry (darker)
            if passes and int(passes) > 1:
                cmd += ["multipass", str(int(passes))]

    cmd += ["write", out_svg]
    subprocess.run(cmd, check=True)




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