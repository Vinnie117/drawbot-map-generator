import osmnx as ox
from pyproj import Transformer


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