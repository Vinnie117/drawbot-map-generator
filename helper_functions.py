import osmnx as ox
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

from src.layout import compute_block_center_delta, get_text_height
from src.letters.styling import fig_hatch_filled_text
from src.letters.styling import fig_contour_filled_text
from src.letters.styling import draw_bold_text
from src.letters.vpype import vpype_add_hershey_text
from src.location import add_marker
from src.location import get_location_coordinates

def add_map_labels(
    fig,
    ax,
    location,
    mode="map_centered",
    position="bottom",
    show_city=True,
    show_coords=False,
    reserve_city=None,
    reserve_coords=None,
    city_fontsize=20,
    coord_fontsize=12,
    padding_factor=0.3,
    between_factor=0.5,
    coords_override=None,
    coords_color="black",
    color="black",
    # --- from the old version ---
    delta_override=None,           # force identical vertical centering across layers
    canonical_coord_text=None,     # force identical reserved coord height across layers
    # --- new in the current version ---
    text_backend="mpl",            # "mpl" or "vpype"
    # --- optional: keep old bold city rendering behavior when using mpl ---
    city_draw="plain",              # "bold" or "plain"
    bold_kwargs=None,              # forwarded to draw_bold_text(...)
    passes=1,     # draw same label N times at identical position

    hatch_city=False,
    hatch_coords=False,
    hatch_spacing_mm=0.6,
    hatch_angle_deg=20.0,
    hatch_outline=True,
    hatch_outline_lw=0.6,
    hatch_lw=0.35,
):
    """
    Computes layout for city / coord labels above/below the map.

    - mode="block_centered": shifts ax + labels so (map + reserved labels) are centered
    - reserve_* reserve layout height even if show_* is False
    - delta_override forces the exact same centering shift (for perfect layer alignment)
    - canonical_coord_text ensures reserved coord height is identical across layers

    If text_backend == "mpl":
        draws text on the figure.
    If text_backend == "vpype":
        does NOT draw text, returns layout info (in mm) for vpype_add_hershey_text().
    """
    if position not in {"bottom", "top"}:
        raise ValueError("position must be 'bottom' or 'top'")
    if text_backend not in {"mpl", "vpype"}:
        raise ValueError("text_backend must be 'mpl' or 'vpype'")
    if mode not in {"map_centered", "block_centered"}:
        raise ValueError("mode must be 'map_centered' or 'block_centered'")

    if reserve_city is None:
        reserve_city = show_city
    if reserve_coords is None:
        reserve_coords = show_coords

    if bold_kwargs is None:
        bold_kwargs = {}

    ax_pos = ax.get_position()
    city_text = str(location)

    # --- coordinate text (and precision) ---
    if coords_override is not None:
        lat, lon = float(coords_override[0]), float(coords_override[1])
        precision = 4
    else:
        lat, lon = get_location_coordinates(location)
        precision = 2

    lat_suffix = "N" if lat >= 0 else "S"
    lon_suffix = "E" if lon >= 0 else "W"
    coord_text = (
        f"{abs(lat):.{precision}f}° {lat_suffix}, "
        f"{abs(lon):.{precision}f}° {lon_suffix}"
    )

    # Use canonical text for layout height so multiple layers reserve identical space
    coord_text_for_layout = canonical_coord_text if canonical_coord_text else coord_text

    # --- reserved layout heights (figure fraction) ---
    city_h = get_text_height(fig, city_text, city_fontsize) if reserve_city else 0.0
    coord_h = (
        get_text_height(fig, coord_text_for_layout, coord_fontsize) if reserve_coords else 0.0
    )

    base_h = city_h if city_h > 0 else (coord_h if coord_h > 0 else 0.02)
    padding = base_h * padding_factor
    between = base_h * between_factor if (reserve_city and reserve_coords) else 0.0

    # --- layout positions (figure fraction) ---
    if position == "bottom":
        y_city = ax_pos.y0 - padding
        y_coord = y_city - city_h - between
        block_top = ax_pos.y1
        block_bottom = (y_coord - coord_h) if reserve_coords else (y_city - city_h)
        va = "top"
    else:
        y_city = ax_pos.y1 + padding
        y_coord = y_city + city_h + between
        block_top = (y_coord + coord_h) if reserve_coords else (y_city + city_h)
        block_bottom = ax_pos.y0
        va = "bottom"

    # --- block centering ---
    if mode == "block_centered":
        if delta_override is None:
            delta = 0.5 - 0.5 * (block_top + block_bottom)
        else:
            delta = float(delta_override)

        ax.set_position([ax_pos.x0, ax_pos.y0 + delta, ax_pos.width, ax_pos.height])
        y_city += delta
        y_coord += delta

 # --- MPL DRAW ---
    if text_backend == "mpl":
        if show_city:
            if city_draw == "bold" and not hatch_city:
                draw_bold_text(
                    fig, 0.5, y_city, city_text,
                    fontsize=city_fontsize,
                    ha="center", va=va,
                    color="black",
                    **{"stroke_distance": 0.0006, "paths": 5, **bold_kwargs},
                )

            else:
                # hatch or plain multipass normal text
                if hatch_city:
                    for _ in range(int(passes)):
                        fig_contour_filled_text(
                            fig,
                            0.5, y_city,
                            city_text,
                            fontsize_pt=city_fontsize,
                            fontfamily="Times New Roman",
                            ha="center",
                            va=va,
                            step_mm=0.05,     # smaller = denser contours
                            lw=0.30,
                            outline=True,
                            outline_lw=0.50,
                            color=color,
                        )

                    # fig_hatch_filled_text(
                    #     fig,
                    #     0.5, y_city,
                    #     city_text,
                    #     fontsize_pt=city_fontsize,
                    #     fontfamily="Times New Roman",
                    #     ha="center",
                    #     va=va,
                    #     angle_deg=hatch_angle_deg,
                    #     spacing_mm=hatch_spacing_mm,
                    #     outline=hatch_outline,
                    #     outline_lw=hatch_outline_lw,
                    #     hatch_lw=hatch_lw,
                    #     color="black",
                    #     zorder=1000,
                    # )

                else:
                    for _ in range(int(passes)):
                        fig.text(
                            0.5, y_city, city_text,
                            ha="center", va=va,
                            fontsize=city_fontsize,
                            fontfamily="Times New Roman",
                            color="black",
                        )

        if show_coords:
            if hatch_coords:
                fig_hatch_filled_text(
                    fig,
                    0.5, y_coord,
                    coord_text,
                    fontsize_pt=coord_fontsize,
                    fontfamily="Times New Roman",
                    ha="center",
                    va=va,
                    angle_deg=hatch_angle_deg,
                    spacing_mm=max(0.35, hatch_spacing_mm * 0.85),
                    outline=False,                 # coords usually cleaner without outline
                    outline_lw=hatch_outline_lw,
                    hatch_lw=max(0.25, hatch_lw * 0.9),
                    color=coords_color,
                    zorder=1000,
                )
            else:
                fig.text(
                    0.5, y_coord, coord_text,
                    ha="center", va=va,
                    fontsize=coord_fontsize,
                    color=coords_color,
                    fontfamily="Times New Roman",
                )

        return None

    # --- VPYPE RETURN ---
    # (return positions in mm; vpype will do the actual text rendering)
    fig_w_in, fig_h_in = fig.get_size_inches()
    mm_per_in = 25.4
    fig_w_mm = fig_w_in * mm_per_in
    fig_h_mm = fig_h_in * mm_per_in

    def pt_to_mm(pt: float) -> float:
        return pt * 0.3527777778  # exact

    # Matplotlib y is from bottom; SVG/vpype y is from top => flip it.
    def mpl_yfrac_to_vpype_mm(y_frac: float) -> float:
        y_mm_from_bottom = y_frac * fig_h_mm
        return fig_h_mm - y_mm_from_bottom

    # vpype places text at a baseline; Matplotlib with va="top" uses top edge.
    # This heuristic shifts baseline down by ~0.85 of font height.
    def baseline_shift_mm(fontsize_mm: float, va: str) -> float:
        if va == "top":
            return 0.85 * fontsize_mm
        elif va == "bottom":
            return 0.15 * fontsize_mm
        return 0.0

    va_city = "top" if position == "bottom" else "bottom"
    va_coord = va_city

    city_size_mm = pt_to_mm(city_fontsize)
    coord_size_mm = pt_to_mm(coord_fontsize)

    x_center_mm = 0.5 * fig_w_mm

    y_city_mm = mpl_yfrac_to_vpype_mm(y_city) + baseline_shift_mm(city_size_mm, va_city)
    y_coord_mm = mpl_yfrac_to_vpype_mm(y_coord) + baseline_shift_mm(coord_size_mm, va_coord)

    return {
        "city": {
            "text": city_text,
            "x_mm": x_center_mm,
            "y_mm": y_city_mm,
            "fontsize_mm": city_size_mm,
            "visible": show_city,
        },
        "coords": {
            "text": coord_text,
            "x_mm": x_center_mm,
            "y_mm": y_coord_mm,
            "fontsize_mm": coord_size_mm,
            "visible": show_coords,
            "color": coords_color,
        }
    }



def export_svg_with_layers(
    G,
    location,
    page_layout,  # (fig_w, fig_h, rect) from get_page_layout
    point=None,  # (lat, lon) or None
    marker_color="red",
    marker_size=10,
    mode="block_centered",
    position="bottom",
    out_combined="combined.svg",
    out_combined_preview=None,
    out_base="layer_base.svg",
    out_overlay="layer_overlay.svg",
    city_fontsize=20,
    coord_fontsize=12,
    padding_factor=0.3,
    between_factor=0.5,
    text_backend = None,
    multipass=1
):
    """
    Export three SVGs that overlay perfectly (puzzle-piece alignment):
      - base:     map + city only (coords reserved for consistent centering)
      - overlay:  marker + coords only (city reserved for consistent centering)
      - combined: everything
      - combined preview: everything plus a red margin guide, if requested

    Key: compute ONE delta using canonical coord string, reuse it for all 3.
    """
    fig_w, fig_h, rect = page_layout
    canonical_coord_text = "00.0000° N, 000.0000° E"

    # -------------------------
    # BASE
    # -------------------------
    fig_base = plt.figure(figsize=(fig_w, fig_h))
    ax_base = fig_base.add_axes(rect)

    ox.plot_graph(
        G,
        ax=ax_base,
        show=False,
        close=False,
        bgcolor="white",
        node_size=0,
        edge_color="black",
        edge_linewidth=0.5,
    )

    # lock view for perfect alignment
    xlim = ax_base.get_xlim()
    ylim = ax_base.get_ylim()
    aspect = ax_base.get_aspect()

    # compute ONE centering delta based on canonical reserved strings
    delta = compute_block_center_delta(
        fig_base,
        ax_base,
        location,
        position=position,
        city_fontsize=city_fontsize,
        coord_fontsize=coord_fontsize,
        padding_factor=padding_factor,
        between_factor=between_factor,
        reserve_city=True,
        reserve_coords=True,
        canonical_coord_text=canonical_coord_text,
    )

    # base: city only (coords reserved)
    add_map_labels(
        fig_base,
        ax_base,
        location,
        mode=mode,
        position=position,
        show_city=False,
        show_coords=False,
        reserve_city=True,
        reserve_coords=True,
        city_fontsize=city_fontsize,
        coord_fontsize=coord_fontsize,
        padding_factor=padding_factor,
        between_factor=between_factor,
        delta_override=delta,
        canonical_coord_text=canonical_coord_text
    )

    fig_base.patch.set_visible(False)
    ax_base.patch.set_visible(False)
    ax_base.set_axis_off()
    fig_base.savefig(out_base, format="svg", transparent=True)
    plt.close(fig_base)

    # -------------------------
    # OVERLAY
    # -------------------------
    fig_ov = plt.figure(figsize=(fig_w, fig_h))
    ax_ov = fig_ov.add_axes(rect)

    ax_ov.set_xlim(xlim)
    ax_ov.set_ylim(ylim)
    ax_ov.set_aspect(aspect)
    ax_ov.set_axis_off()

    marker_latlon = None
    if point is not None:
        marker_latlon = add_marker(ax_ov, G, point, color=marker_color, size=marker_size)

    # overlay: coords only (city reserved)
    if marker_latlon is not None:

        #### VPYPE
        if text_backend == "vpype":
            label_layout = add_map_labels(
                fig_ov,
                ax_ov,
                location,
                mode="block_centered",
                position="bottom",
                show_city=True,
                show_coords=False,
                coords_override=marker_latlon,  # show marker coords if present
                coords_color=marker_color,      # same color as dot
                city_fontsize=city_fontsize,
                coord_fontsize=coord_fontsize,
                padding_factor=padding_factor,
                between_factor=between_factor,
                text_backend="vpype",           # IMPORTANT
            )

        if text_backend == "mpl":

            ### Matplotlib
            add_map_labels(
                fig_ov, ax_ov, location,
                mode=mode,
                position=position,
                text_backend="mpl",
                delta_override=delta,
                reserve_city=True,
                reserve_coords=True,
                canonical_coord_text=canonical_coord_text,
                city_fontsize=city_fontsize,
                coord_fontsize=coord_fontsize,
                padding_factor=padding_factor,
                between_factor=between_factor,

                show_city=True,
                show_coords=False,
                color="green",

                hatch_city=True,
                hatch_coords=False,
                hatch_spacing_mm=0.3,
                hatch_angle_deg=25,
                hatch_outline=True,
                hatch_outline_lw=0.5,
                hatch_lw=0.30,

                passes=multipass
            )


    else:
        # no marker: still reserve layout so overlay aligns if you later combine

        if text_backend == "vpype":
            #### VPYPE
            label_layout = add_map_labels(
                fig_ov,
                ax_ov,
                location,
                mode="block_centered",
                position="bottom",
                show_city=True,
                show_coords=False,
                coords_override=marker_latlon,  # show marker coords if present
                coords_color=marker_color,      # same color as dot
                city_fontsize=city_fontsize,
                coord_fontsize=coord_fontsize,
                padding_factor=padding_factor,
                between_factor=between_factor,
                text_backend="vpype",           # IMPORTANT
            )

        if text_backend == "mpl":
            ### Matplotlib
            add_map_labels(
                fig_ov, ax_ov, location,
                mode=mode,
                position=position,
                text_backend="mpl",
                delta_override=delta,
                reserve_city=True,
                reserve_coords=True,
                canonical_coord_text=canonical_coord_text,
                city_fontsize=city_fontsize,
                coord_fontsize=coord_fontsize,
                padding_factor=padding_factor,
                between_factor=between_factor,

                show_city=True,
                show_coords=False,
                color="red",

                hatch_city=True,
                hatch_coords=False,
                hatch_spacing_mm=0.3,
                hatch_angle_deg=25,
                hatch_outline=True,
                hatch_outline_lw=0.5,
                hatch_lw=0.30,

                passes=multipass
            )


    fig_ov.patch.set_visible(False)
    ax_ov.patch.set_visible(False)
    fig_ov.savefig(out_overlay, format="svg", transparent=True)

    if text_backend == "vpype":

        vpype_add_hershey_text(
            out_overlay,
            "maps/test_vpype_layer.svg",
            label_layout,
            font="timesr",
            stroke_distance_mm=0.3,
            offset_paths=4,                  # number of directions away from the center
            offset_rings=(0.0, 0.33, 0.66, 1.0),    # how many layer to draw in what distance (multiplied with distance)
            passes=1,
        )



    plt.close(fig_ov)

    # -------------------------
    # COMBINED
    # -------------------------
    fig_all = plt.figure(figsize=(fig_w, fig_h))
    ax_all = fig_all.add_axes(rect)

    ax_all.set_xlim(xlim)
    ax_all.set_ylim(ylim)
    ax_all.set_aspect(aspect)
    ax_all.set_axis_off()

    ox.plot_graph(
        G,
        ax=ax_all,
        show=False,
        close=False,
        bgcolor="white",
        node_size=0,
        edge_color="black",
        edge_linewidth=0.5,
    )

    marker_latlon2 = None
    if point is not None:
        marker_latlon2 = add_marker(ax_all, G, point, color=marker_color, size=marker_size)

    add_map_labels(
        fig_all,
        ax_all,
        location,
        mode=mode,
        position=position,
        show_city=True,
        show_coords=False,
        reserve_city=True,
        reserve_coords=True,
        coords_override=marker_latlon2,
        coords_color=marker_color if marker_latlon2 is not None else "black",
        city_fontsize=city_fontsize,
        coord_fontsize=coord_fontsize,
        padding_factor=padding_factor,
        between_factor=between_factor,
        delta_override=delta,
        canonical_coord_text=canonical_coord_text,
        hatch_city=True,
        hatch_coords=False,
        hatch_spacing_mm=0.3,
        hatch_angle_deg=25,
        hatch_outline=True,
        hatch_outline_lw=0.5,
        hatch_lw=0.30,
        passes=multipass
    )

    fig_all.patch.set_visible(False)
    ax_all.patch.set_visible(False)
    fig_all.savefig(out_combined, format="svg", transparent=True)

    if out_combined_preview is not None:
        margin_x, margin_y, margin_w, margin_h = rect
        margin_guide = Rectangle(
            (margin_x, margin_y),
            margin_w,
            margin_h,
            transform=fig_all.transFigure,
            fill=False,
            edgecolor="red",
            linewidth=1.0,
            zorder=10000,
            clip_on=False,
            joinstyle="miter",
        )
        fig_all.add_artist(margin_guide)
        fig_all.patch.set_visible(True)
        fig_all.patch.set_facecolor("white")
        fig_all.savefig(out_combined_preview, format="svg", transparent=False)

    plt.close(fig_all)
