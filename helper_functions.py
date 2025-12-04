import osmnx as ox

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
    - If location is already a tuple → return it unchanged.
    - If it's a place name → geocode it using OSMnx.
    """
    if isinstance(location, (tuple, list)) and len(location) == 2:
        return location
    
    # Otherwise: geocode place name
    pt = ox.geocode(location)
    return (pt[0], pt[1])   # lat, lon