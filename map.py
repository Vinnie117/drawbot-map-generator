import osmnx as ox
import matplotlib.pyplot as plt
from helper_functions import get_page_layout, get_graph, set_map_frame, add_map_labels, add_marker, export_svg_with_layers


# --- SETTINGS ---
ox.settings.use_cache = True
ox.settings.log_console = True

location = "Berlin, Germany"  # "Berlin, Germany"  # or (52.52, 13.405)
fig_w, fig_h, rect = get_page_layout("a4", 20)

# Example point (Brandenburger Tor)
point = (52.516275, 13.377704)
marker_color = "red"

# --- DOWNLOAD GRAPH ---
G = get_graph(location, network_type="drive", dist=5000)


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

# Add marker point
marker_latlon = add_marker(ax, G, point, color=marker_color, size=20)

# --- LABELS (choose layout mode here) ---
# Map + labels centered, with coordinates
add_map_labels(
    fig, ax, location,
    mode="block_centered",
    position="bottom",
    show_city=True,
    show_coords=True,
    coords_override=marker_latlon,   # show marker coords if present
    coords_color=marker_color        # same color as dot
)

# or: Map + only city name centered, no coordinates
# add_map_labels(fig, ax, location, mode="block_centered", position="top", show_coords=False, padding_factor=0.5)

# or: keep only the map centered, text just appended below
#add_map_labels(fig, ax, location, mode="map_centered", position="bottom", show_coords=True)

# turn frame on / off by setting 'enabled' arg
set_map_frame(fig, ax, enabled=True, linewidth=1.2, color="black", pad=0.0)

# --- SAVE AS SVG ---

fig.patch.set_visible(False)   # removes patch_1
ax.patch.set_visible(False)    # removes patch_2
fig.savefig("test5.svg", format="svg", transparent=True)
plt.close(fig)

print("#### #### ####")

export_svg_with_layers(
    G,
    location,
    page_layout=(fig_w, fig_h, rect),
    point=point,
    marker_color="red",
    marker_size=10,
    mode="block_centered",
    position="bottom",
    out_combined="all_in_one.svg",
    out_base="base_map.svg",
    out_overlay="marker_overlay.svg"
)

print("END")