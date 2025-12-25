import osmnx as ox

suburb_name = "Eppendorf, Hamburg, Germany"

gdf = ox.geocode_to_gdf(suburb_name)
print(gdf[["display_name", "osm_type", "geometry"]])