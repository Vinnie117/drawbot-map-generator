import osmnx as ox
from pyproj import Transformer

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
    position="bottom",        # NEW: "bottom" or "top"
    show_coords=True,
    city_fontsize=20,
    coord_fontsize=12,
    padding_factor=0.3,
    between_factor=0.5,
):
    """
    Add city name (+ optional coordinates) above or below the map.

    Args:
        fig, ax: Matplotlib figure and axes.
        location: place name string or (lat, lon) tuple.
        mode:
            - "map_centered": map is centered; labels appended above/below.
            - "block_centered": map + labels are treated as one block and
                                vertically centered on the figure.
        position:
            - "bottom": labels below the map
            - "top": labels above the map
        show_coords (bool): toggle coordinate line on/off.
        city_fontsize, coord_fontsize: font sizes.
        padding_factor: spacing between map and city label (relative to city height).
        between_factor: spacing between city label and coordinates (relative to city height).
    """
    if position not in {"bottom", "top"}:
        raise ValueError("position must be 'bottom' or 'top'")

    ax_pos = ax.get_position()

    # --- Text contents ---
    city_text = str(location)

    lat, lon = get_location_coordinates(location)
    lat_suffix = "N" if lat >= 0 else "S"
    lon_suffix = "E" if lon >= 0 else "W"
    coord_text = f"{abs(lat):.2f}° {lat_suffix}, {abs(lon):.2f}° {lon_suffix}"

    # --- Text heights ---
    city_h = get_text_height(fig, city_text, city_fontsize)
    coord_h = get_text_height(fig, coord_text, coord_fontsize) if show_coords else 0.0

    padding = city_h * padding_factor
    between = city_h * between_factor if show_coords else 0.0

    # --- Initial positions (relative to map) ---
    if position == "bottom":
        y_city = ax_pos.y0 - padding
        y_coord = y_city - city_h - between if show_coords else None
        block_top = ax_pos.y1
        block_bottom = (y_coord - coord_h) if show_coords else (y_city - city_h)

    else:  # position == "top"
        y_city = ax_pos.y1 + padding
        y_coord = y_city + city_h + between if show_coords else None
        block_top = (y_coord + coord_h) if show_coords else (y_city + city_h)
        block_bottom = ax_pos.y0

    # --- Block centering logic ---
    if mode == "block_centered":
        block_center = 0.5 * (block_top + block_bottom)
        delta = 0.5 - block_center

        # Shift map
        ax.set_position([
            ax_pos.x0,
            ax_pos.y0 + delta,
            ax_pos.width,
            ax_pos.height,
        ])

        # Shift labels
        y_city += delta
        if show_coords:
            y_coord += delta

    # --- Draw city label ---
    fig.text(
        0.5,
        y_city,
        city_text,
        ha="center",
        va="top" if position == "bottom" else "bottom",
        fontsize=city_fontsize,
    )

    # --- Draw coordinates ---
    if show_coords:
        fig.text(
            0.5,
            y_coord,
            coord_text,
            ha="center",
            va="top" if position == "bottom" else "bottom",
            fontsize=coord_fontsize,
            color="black",
        )




def add_marker(ax, G, lat_lon, color="red", size=40, zorder=10):
    """
    Draw a marker (dot) on an OSMnx map at the given (lat, lon).

    Args:
        ax: Matplotlib axes that the graph was drawn onto.
        G: OSMnx graph.
        lat_lon: tuple (lat, lon) in WGS84.
        color: dot color.
        size: scatter size (points^2).
        zorder: draw order (higher draws on top).
    """
    lat, lon = lat_lon

    graph_crs = G.graph.get("crs", None)

    # If graph is unprojected (EPSG:4326), nodes use lon/lat directly as x/y
    if graph_crs is None or str(graph_crs).lower() in {"epsg:4326", "4326"}:
        x, y = lon, lat
    else:
        # Transform WGS84 lon/lat -> graph CRS
        transformer = Transformer.from_crs("EPSG:4326", graph_crs, always_xy=True)
        x, y = transformer.transform(lon, lat)

    ax.scatter([x], [y], s=size, c=color, zorder=zorder)
