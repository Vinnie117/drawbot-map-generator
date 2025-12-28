def get_page_layout(paper_format: str, margin_mm: float):
    """
    Compute figure size (in inches) and axes rectangle for centered plotting
    with a margin around the edges.

    Args:
        paper_format (str): "a3" or "a4" (portrait).
        margin_mm (float): margin size in millimeters.

    Returns:
        (fig_width_in, fig_height_in, axes_rect)
        where axes_rect = [left, bottom, width, height]
        suitable for fig.add_axes().
    """
    # ISO 216 sizes in mm (portrait)
    sizes = {
        "a4": (210, 297),
        "a3": (297, 420)
    }

    fmt = paper_format.lower()
    if fmt not in sizes:
        raise ValueError("paper_format must be 'a3' or 'a4'")

    width_mm, height_mm = sizes[fmt]

    mm_to_inch = 1 / 25.4
    fig_width_in = width_mm * mm_to_inch
    fig_height_in = height_mm * mm_to_inch
    margin_in = margin_mm * mm_to_inch

    # margin as fraction of figure size
    left = right = margin_in / fig_width_in
    bottom = top = margin_in / fig_height_in

    axes_rect = [
        left,
        bottom,
        1 - left - right,
        1 - top - bottom
    ]

    return fig_width_in, fig_height_in, axes_rect


def get_text_height(fig, text, fontsize):
    """
    Return text height in figure coordinates (0–1).
    """
    # Ensure we have a renderer
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()

    dummy = fig.text(0, 0, text, fontsize=fontsize)
    bbox = dummy.get_window_extent(renderer=renderer)
    dummy.remove()

    return bbox.height / fig.bbox.height


def compute_block_center_delta(
    fig,
    ax,
    location,
    position="bottom",
    city_fontsize=20,
    coord_fontsize=12,
    padding_factor=0.3,
    between_factor=0.5,
    reserve_city=True,
    reserve_coords=True,
    canonical_coord_text="00.0000° N, 000.0000° E",
):
    """
    Compute ONE vertical centering delta for block_centered mode.
    Use a canonical coord string so base/overlay/combined align perfectly.
    """
    ax_pos = ax.get_position()
    city_text = str(location)

    # These must exist in your helpers
    city_h = get_text_height(fig, city_text, city_fontsize) if reserve_city else 0.0
    coord_h = get_text_height(fig, canonical_coord_text, coord_fontsize) if reserve_coords else 0.0

    base_h = city_h if city_h > 0 else (coord_h if coord_h > 0 else 0.02)
    padding = base_h * padding_factor
    between = base_h * between_factor if (reserve_city and reserve_coords) else 0.0

    if position == "bottom":
        y_city = ax_pos.y0 - padding
        y_coord = y_city - city_h - between
        block_top = ax_pos.y1
        block_bottom = (y_coord - coord_h) if reserve_coords else (y_city - city_h)
    else:
        y_city = ax_pos.y1 + padding
        y_coord = y_city + city_h + between
        block_top = (y_coord + coord_h) if reserve_coords else (y_city + city_h)
        block_bottom = ax_pos.y0

    block_center = 0.5 * (block_top + block_bottom)
    return 0.5 - block_center