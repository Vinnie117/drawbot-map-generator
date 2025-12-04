import osmnx as ox
import matplotlib.pyplot as plt
from helper_functions import get_page_layout, get_graph, get_location_coordinates

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

# --- TEXT LABELS BELOW MAP ---
ax_pos = ax.get_position()

# Get coordinates for location label
lat, lon = get_location_coordinates(location)
# Determine suffixes
lat_suffix = "N" if lat >= 0 else "S"
lon_suffix = "E" if lon >= 0 else "W"
# Build coordinate string
coord_text = f"{abs(lat):.2f}° {lat_suffix}, {abs(lon):.2f}° {lon_suffix}"

# City name label
y1 = ax_pos.y0 - 0.01
fig.text(
    0.5,
    y1,
    str(location),
    ha="center",
    va="top",
    fontsize=12
)

# Coordinates label
y2 = y1 - 0.02
fig.text(
    0.5,
    y2,
    coord_text,
    ha="center",
    va="top",
    fontsize=10,
    color="black"
)


# --- SAVE AS SVG ---
fig.savefig("test2.svg", format="svg")
plt.close(fig)

print("Saved as berlin_A4_centered.svg")
