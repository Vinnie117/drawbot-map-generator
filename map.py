import osmnx as ox
import matplotlib.pyplot as plt
from helper_functions import get_page_layout, get_graph

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

# --- SAVE AS SVG ---
fig.savefig("test2.svg", format="svg")
plt.close(fig)

print("Saved as berlin_A4_centered.svg")
