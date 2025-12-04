import osmnx as ox
import matplotlib.pyplot as plt
from helper_functions import get_page_layout, get_graph, get_location_coordinates, get_text_height

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
city_fontsize = 20
coord_fontsize = 12

city_text = str(location)
coord_text = coord_text  # from earlier

# Measure heights
city_h = get_text_height(fig, city_text, city_fontsize)
coord_h = get_text_height(fig, coord_text, coord_fontsize)

padding = city_h * 0.3  # XX% of city text height as extra spacing

# Position city name
y1 = ax_pos.y0 - padding
fig.text(
    0.5,
    y1,
    city_text,
    ha="center",
    va="top",
    fontsize=city_fontsize
)

# Position coordinates directly below city name
y2 = y1 - city_h - padding
fig.text(
    0.5,
    y2,
    coord_text,
    ha="center",
    va="top",
    fontsize=coord_fontsize
)


# --- SAVE AS SVG ---
fig.savefig("test2.svg", format="svg")
plt.close(fig)

print("Saved as berlin_A4_centered.svg")
