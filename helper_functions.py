import osmnx as ox
from pyproj import Transformer
import matplotlib.pyplot as plt

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


def add_map_labels(
    fig,
    ax,
    location,
    mode="map_centered",
    position="bottom",
    show_city=True,
    show_coords=True,
    reserve_city=None,          # NEW
    reserve_coords=None,        # NEW
    city_fontsize=20,
    coord_fontsize=12,
    padding_factor=0.3,
    between_factor=0.5,
    coords_override=None,
    coords_color="black"
):
    if position not in {"bottom", "top"}:
        raise ValueError("position must be 'bottom' or 'top'")

    # If not explicitly set, reserve what you show
    if reserve_city is None:
        reserve_city = show_city
    if reserve_coords is None:
        reserve_coords = show_coords

    ax_pos = ax.get_position()
    city_text = str(location)

    # coords text (and precision)
    if coords_override is not None:
        lat, lon = float(coords_override[0]), float(coords_override[1])
        precision = 4
    else:
        lat, lon = get_location_coordinates(location)
        precision = 2

    lat_suffix = "N" if lat >= 0 else "S"
    lon_suffix = "E" if lon >= 0 else "W"
    coord_text = f"{abs(lat):.{precision}f}° {lat_suffix}, {abs(lon):.{precision}f}° {lon_suffix}"

    # Heights used for LAYOUT (reserved), not drawing
    city_h = get_text_height(fig, city_text, city_fontsize) if reserve_city else 0.0
    coord_h = get_text_height(fig, coord_text, coord_fontsize) if reserve_coords else 0.0

    base_h = city_h if city_h > 0 else (coord_h if coord_h > 0 else 0.02)
    padding = base_h * padding_factor
    between = base_h * between_factor if (reserve_city and reserve_coords) else 0.0

    # Layout positions
    if position == "bottom":
        y_city = ax_pos.y0 - padding
        y_coord = y_city - city_h - between  # this is "reserved" position
        block_top = ax_pos.y1
        block_bottom = (y_coord - coord_h) if reserve_coords else (y_city - city_h)
    else:
        y_city = ax_pos.y1 + padding
        y_coord = y_city + city_h + between
        block_top = (y_coord + coord_h) if reserve_coords else (y_city + city_h)
        block_bottom = ax_pos.y0

    # Block centering
    if mode == "block_centered":
        delta = 0.5 - 0.5 * (block_top + block_bottom)
        ax.set_position([ax_pos.x0, ax_pos.y0 + delta, ax_pos.width, ax_pos.height])
        y_city += delta
        y_coord += delta

    # Draw only what is requested
    if show_city:
        fig.text(
            0.5, y_city, city_text,
            ha="center",
            va="top" if position == "bottom" else "bottom",
            fontsize=city_fontsize
        )

    if show_coords:
        fig.text(
            0.5, y_coord, coord_text,
            ha="center",
            va="top" if position == "bottom" else "bottom",
            fontsize=coord_fontsize,
            color=coords_color
        )





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
    page_layout,          # (fig_w, fig_h, rect) from get_page_layout
    point=None,           # (lat, lon) or None
    marker_color="red",
    marker_size=10,
    mode="block_centered",
    position="bottom",
    out_combined="combined.svg",
    out_base="layer_base.svg",
    out_overlay="layer_overlay.svg",
):
    fig_w, fig_h, rect = page_layout

    # -------------------------
    # BASE: map + city name
    # -------------------------
    fig_base = plt.figure(figsize=(fig_w, fig_h))
    ax_base = fig_base.add_axes(rect)

    ox.plot_graph(
        G, ax=ax_base,
        show=False, close=False,
        bgcolor="white",
        node_size=0,
        edge_color="black",
        edge_linewidth=0.5
    )

    # lock view for perfect alignment
    xlim = ax_base.get_xlim()
    ylim = ax_base.get_ylim()
    aspect = ax_base.get_aspect()

    # base: city only, but RESERVE coords space so centering matches combined
    add_map_labels(
        fig_base, ax_base, location,
        mode=mode, position=position,
        show_city=True,
        show_coords=False,
        reserve_city=True,
        reserve_coords=True
    )

    fig_base.patch.set_visible(False)
    ax_base.patch.set_visible(False)
    ax_base.set_axis_off()
    fig_base.savefig(out_base, format="svg", transparent=True)
    plt.close(fig_base)

    # -------------------------
    # OVERLAY: marker + coords only
    # -------------------------
    fig_ov = plt.figure(figsize=(fig_w, fig_h))
    ax_ov = fig_ov.add_axes(rect)

    ax_ov.set_xlim(xlim)
    ax_ov.set_ylim(ylim)
    ax_ov.set_aspect(aspect)
    ax_ov.set_axis_off()

    marker_latlon = None
    if point is not None:
        marker_latlon = add_marker(
            ax_ov, G, point,
            color=marker_color,
            size=marker_size
        )

    # overlay: coords only (no city), but RESERVE city space so centering matches combined
    if marker_latlon is not None:
        add_map_labels(
            fig_ov, ax_ov, location,
            mode=mode, position=position,
            show_city=False,
            show_coords=True,
            reserve_city=True,
            reserve_coords=True,
            coords_override=marker_latlon,
            coords_color=marker_color
        )

    fig_ov.patch.set_visible(False)
    ax_ov.patch.set_visible(False)
    fig_ov.savefig(out_overlay, format="svg", transparent=True)
    plt.close(fig_ov)

    # -------------------------
    # COMBINED: everything
    # -------------------------
    fig_all = plt.figure(figsize=(fig_w, fig_h))
    ax_all = fig_all.add_axes(rect)

    ax_all.set_xlim(xlim)
    ax_all.set_ylim(ylim)
    ax_all.set_aspect(aspect)
    ax_all.set_axis_off()

    ox.plot_graph(
        G, ax=ax_all,
        show=False, close=False,
        bgcolor="white",
        node_size=0,
        edge_color="black",
        edge_linewidth=0.5
    )

    marker_latlon2 = None
    if point is not None:
        marker_latlon2 = add_marker(
            ax_all, G, point,
            color=marker_color,
            size=marker_size
        )

    add_map_labels(
        fig_all, ax_all, location,
        mode=mode, position=position,
        show_city=True,
        show_coords=True,
        reserve_city=True,
        reserve_coords=True,
        coords_override=marker_latlon2,
        coords_color=marker_color if marker_latlon2 is not None else "black"
    )

    fig_all.patch.set_visible(False)
    ax_all.patch.set_visible(False)
    fig_all.savefig(out_combined, format="svg", transparent=True)
    plt.close(fig_all)