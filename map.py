import osmnx as ox
import matplotlib.pyplot as plt

# --- SETTINGS ---
ox.settings.use_cache = True
ox.settings.log_console = True

place_name = "Berlin, Germany"
margin_mm = 20                             # margin around the map
a4_width_mm = 210
a4_height_mm = 297

# Convert mm → inches for Matplotlib
mm_to_inch = 1 / 25.4
fig_width_in = a4_width_mm * mm_to_inch
fig_height_in = a4_height_mm * mm_to_inch
margin_in = margin_mm * mm_to_inch

# Compute normalized figure margins
left = right = margin_in / fig_width_in
bottom = top = margin_in / fig_height_in

# --- DOWNLOAD GRAPH ---
G = ox.graph_from_place(place_name, network_type="drive")

# --- CREATE FIGURE ---
fig = plt.figure(figsize=(fig_width_in, fig_height_in))

# Add axes with margins applied
ax = fig.add_axes([left, bottom, 1 - left - right, 1 - top - bottom])

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
