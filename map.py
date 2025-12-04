import osmnx as ox
import matplotlib.pyplot as plt
from helper_functions import get_page_layout 

# --- SETTINGS ---
ox.settings.use_cache = True
ox.settings.log_console = True

place_name = "Berlin, Germany"
fig_w, fig_h, rect = get_page_layout("a4", 20)

# --- DOWNLOAD GRAPH ---
G = ox.graph_from_place(place_name, network_type="drive")

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

# --- SAVE AS SVG ---
fig.savefig("berlin_A4_centered.svg", format="svg")
plt.close(fig)

print("Saved as berlin_A4_centered.svg")
