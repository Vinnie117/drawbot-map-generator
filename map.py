import osmnx as ox

ox.settings.use_cache = True
ox.settings.log_console = True

place_name = "Berlin, Germany"

# Download the street network
G = ox.graph_from_place(place_name, network_type="drive")

# Plot and save as SVG
fig, ax = ox.plot_graph(
    G,
    bgcolor="white",
    node_size=0,
    edge_color="black",
    edge_linewidth=0.5,
    save=True,
    filepath="berlin.svg",   # extension determines format
    dpi=300
)

print("Saved as berlin.svg")
