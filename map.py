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

location = "Berlin, Germany"  # "Berlin, Germany"  # or (52.52, 13.405)
fig_w, fig_h, rect = get_page_layout("a4", 20)

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

# # show a 5km-tall window centered on Brandenburger Tor
# crop_view_to_frame(
#     fig, ax, G,
#     center_latlon=(52.516275, 13.377704),
#     height_m=5000
# )

# Add marker point
#marker_latlon = add_marker(ax, G, point, color=marker_color, size=20)

# --- LABELS (choose layout mode here) ---
# Map + labels centered, with coordinates
add_map_labels(
    fig,
    ax,
    location,
    mode="block_centered",
    position="bottom",
    show_city=True,
    show_coords=False,
    coords_override=None,  # show marker coords if present
    #coords_color=marker_color,      # same color as dot
    text_backend="mpl",           # IMPORTANT
    passes=5,
    city_draw="plain"
)

# or: Map + only city name centered, no coordinates
# add_map_labels(fig, ax, location, mode="block_centered", position="top", show_coords=False, padding_factor=0.5)

# or: keep only the map centered, text just appended below
#add_map_labels(fig, ax, location, mode="map_centered", position="bottom", show_coords=True)

# turn frame on / off by setting 'enabled' arg
set_map_frame(fig, ax, enabled=False, linewidth=1.2, color="black", pad=0.0)

# --- SAVE AS SVG ---

fig.patch.set_visible(False)   # removes patch_1
ax.patch.set_visible(False)    # removes patch_2
fig.savefig("maps/koeln_a4_filtered_30m.svg", format="svg", transparent=True)

#### this command needs a return object (label_layout) from add_map_labels()
# vpype_add_hershey_text(
#     "maps/koeln_a4_filtered_30m.svg",
#     "maps/koeln.svg",
#     label_layout,
#     font="timesr",
#     stroke_distance_mm=0.3,
#     offset_paths=6,
#     offset_rings=(0.0, 0.33, 0.66, 1.0),
#     passes=1,
# )


plt.close(fig)

print("#### #### ####")

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
    out_combined="maps/koeln_combined.svg",

    city_fontsize=20,
    coord_fontsize=12,
    padding_factor=0.3,
    between_factor=0.5,
    multipass = 2,
    text_backend="mpl"  # "vpype" or "mpl"
)

print("END")