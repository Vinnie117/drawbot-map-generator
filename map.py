import osmnx as ox
import matplotlib.pyplot as plt
from src.frame import crop_view_to_frame, set_map_frame
from helper_functions import add_map_labels, export_svg_with_layers
from src.letters.vpype import vpype_add_hershey_text
from src.layout import get_page_layout
from src.location import get_graph, add_marker, filter_short_edges


# --- SETTINGS ---
ox.settings.use_cache = True
ox.settings.log_console = True

FORMAT = "a5"
MARGIN_BY_FORMAT_MM = {
    "a5": 10,
    "a4": 20,
    "a3": 30,
}

location = "Köln"  # "Berlin, Germany"  # or (52.52, 13.405)
fig_w, fig_h, rect = get_page_layout(FORMAT, MARGIN_BY_FORMAT_MM[FORMAT.lower()])

# Example point (Brandenburger Tor)
point = (52.516275, 13.377704)
marker_color = "red"

# --- DOWNLOAD GRAPH ---
G_raw = get_graph(location, network_type="drive", dist=5000)
G = filter_short_edges(G_raw, min_length_m=30)

#### suburb
# location = "Eppendorf, Hamburg, Germany"
# gdf = ox.geocode_to_gdf(location)
# poly = gdf.geometry.iloc[0]

# G = ox.graph_from_polygon(
#     poly,
#     network_type="drive",   # or "walk", "bike"
#     simplify=True
# )
# G = filter_short_edges(G, min_length_m=0)


# --- CREATE FIGURE ---
fig = plt.figure(figsize=(fig_w, fig_h))

# Add axes with margins applied
ax = fig.add_axes(rect)

# --- DRAW GRAPH ---
ox.plot_graph(
    G,
    ax=ax,
    show=False,
    close=False,
    bgcolor="white",
    node_size=0,
    edge_color="black",
    edge_linewidth=0.5
)

city_fontsize = 24 if FORMAT == "a3" else 20

export_svg_with_layers(
    G=G,
    location=location,
    page_layout=(fig_w, fig_h, rect),
    point=None,                     # set to None if no marker
    marker_color=marker_color,
    marker_size=20,
    mode="block_centered",
    position="bottom",

    out_base="maps/koeln_base.svg",
    out_overlay="maps/koeln_overlay.svg",
    out_combined=f"maps/koeln_combined_{FORMAT}.svg",
    out_combined_preview=f"maps/koeln_combined_{FORMAT}_preview.svg",
    metadata=f"maps/koeln_combined_{FORMAT}_metadata.yaml",

    city_fontsize=city_fontsize,
    coord_fontsize=12,
    padding_factor=0.3,
    between_factor=0.5,
    multipass = 2,
    text_backend="mpl"  # "vpype" or "mpl"
)

print("END")
