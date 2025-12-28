from matplotlib.patches import Rectangle
from pyproj import Transformer


def set_map_frame(fig, ax, enabled=True, linewidth=1.0, color="black", pad=0.0, zorder=50):
    """
    Draw (or hide) a rectangle frame around the map axes area.

    Args:
        fig, ax: Matplotlib figure/axes.
        enabled (bool): show/hide frame.
        linewidth (float): stroke width in points.
        color (str): stroke color.
        pad (float): padding around the axes box in figure coordinates (0..1).
                     Example: 0.005 adds a small gap outward.
        zorder (int): draw order.
    Returns:
        The Rectangle artist (or None if disabled).
    """
    # store reference so repeated calls replace the old one
    old = getattr(ax, "_map_frame_artist", None)
    if old is not None:
        old.remove()
        ax._map_frame_artist = None

    if not enabled:
        return None

    pos = ax.get_position()  # in figure coords
    x0 = pos.x0 - pad
    y0 = pos.y0 - pad
    w = pos.width + 2 * pad
    h = pos.height + 2 * pad

    frame = Rectangle(
        (x0, y0), w, h,
        transform=fig.transFigure,
        fill=False,
        edgecolor=color,
        linewidth=linewidth,
        zorder=zorder,
        joinstyle="miter"
    )
    fig.add_artist(frame)
    ax._map_frame_artist = frame
    return frame


def crop_view_to_frame(
    fig,
    ax,
    G,
    center_latlon=None,          # (lat, lon)
    bbox_latlon=None,            # (north, south, east, west)
    height_m=5000,               # used with center_latlon
    width_m=None,                # optional; if None derived from axis aspect and height
):
    """
    Crop the axes view so the map fills the axes rectangle (crop mode),
    and choose which area is shown using either a center point or a bbox.

    Exactly one of center_latlon or bbox_latlon should be provided.

    Args:
        fig, ax: Matplotlib figure/axes.
        G: OSMnx graph (used for CRS transform).
        center_latlon: (lat, lon) center of view in WGS84.
        bbox_latlon: (north, south, east, west) in WGS84.
        height_m: desired height of view in meters (if using center_latlon).
        width_m: desired width in meters (if using center_latlon). If None, computed
                 to match axes aspect ratio.
    """
    if (center_latlon is None) == (bbox_latlon is None):
        raise ValueError("Provide exactly one of center_latlon or bbox_latlon")

    graph_crs = G.graph.get("crs", None)
    if graph_crs is None:
        raise ValueError("Graph CRS missing: G.graph['crs'] is required")

    # transformer from WGS84 -> graph CRS (meters in UTM usually)
    transformer = Transformer.from_crs("EPSG:4326", graph_crs, always_xy=True)

    # axes aspect ratio (width/height in pixels)
    fig.canvas.draw()
    bbox = ax.get_window_extent()
    ax_aspect = bbox.width / bbox.height  # width/height

    if center_latlon is not None:
        lat, lon = float(center_latlon[0]), float(center_latlon[1])
        cx, cy = transformer.transform(lon, lat)

        h = float(height_m)
        w = float(width_m) if width_m is not None else ax_aspect * h

        ax.set_xlim(cx - w / 2, cx + w / 2)
        ax.set_ylim(cy - h / 2, cy + h / 2)

    else:
        north, south, east, west = bbox_latlon
        # transform bbox corners
        x_w, y_s = transformer.transform(float(west), float(south))
        x_e, y_n = transformer.transform(float(east), float(north))

        xmin, xmax = sorted([x_w, x_e])
        ymin, ymax = sorted([y_s, y_n])

        xspan = xmax - xmin
        yspan = ymax - ymin
        xmid = (xmin + xmax) / 2
        ymid = (ymin + ymax) / 2

        # CROP to fill axes (reduce the longer dimension)
        data_aspect = xspan / yspan if yspan != 0 else ax_aspect

        if data_aspect > ax_aspect:
            # too wide -> crop x
            new_xspan = ax_aspect * yspan
            ax.set_xlim(xmid - new_xspan / 2, xmid + new_xspan / 2)
            ax.set_ylim(ymin, ymax)
        else:
            # too tall -> crop y
            new_yspan = xspan / ax_aspect
            ax.set_xlim(xmin, xmax)
            ax.set_ylim(ymid - new_yspan / 2, ymid + new_yspan / 2)

    ax.margins(0)