import osmnx as ox
import matplotlib.pyplot as plt
from helper_functions import get_page_layout, get_graph, get_location_coordinates, get_text_height, add_map_labels

# --- SETTINGS ---
ox.settings.use_cache = True
ox.settings.log_console = True

location = "Berlin, Germany"  # "Berlin, Germany"  # or (52.52, 13.405)
fig_w, fig_h, rect = get_page_layout("a4", 20)

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

# --- LABELS (choose layout mode here) ---
# Map + labels centered, with coordinates
add_map_labels(fig, ax, location, mode="block_centered", show_coords=True)

# or: Map + only city name centered, no coordinates
# add_map_labels(fig, ax, location, mode="block_centered", show_coords=False)

# or: keep only the map centered, text just appended below
#add_map_labels(fig, ax, location, mode="map_centered", show_coords=True)

# --- SAVE AS SVG ---
fig.savefig("test3.svg", format="svg")
plt.close(fig)

print("Saved as berlin_A4_centered.svg")
