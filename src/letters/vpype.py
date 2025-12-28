import math
import shutil
import subprocess


def _circle_offsets_mm(radius_mm: float, paths: int):
    """Generate (dx, dy) offsets evenly spaced on a circle."""
    if radius_mm <= 0:
        return [(0.0, 0.0)]
    return [
        (
            radius_mm * math.cos(2 * math.pi * i / paths),
            radius_mm * math.sin(2 * math.pi * i / paths),
        )
        for i in range(paths)
    ]


def _make_offsets_mm(
    stroke_distance_mm: float,
    paths: int,
    rings=(0.0, 0.5, 1.0, 1.5),
    include_center=True,
):
    """
    Create offsets in mm.

    stroke_distance_mm: base radial step in mm
    paths: number of offsets per ring (angular resolution)
    rings: multiples of stroke_distance_mm used as radii
    include_center: ensure (0,0) is included
    """
    offsets = []
    for f in rings:
        r = f * stroke_distance_mm
        offsets.extend(_circle_offsets_mm(r, paths))

    if include_center and (0.0, 0.0) not in offsets:
        offsets.append((0.0, 0.0))

    # De-duplicate (floating tolerance)
    uniq = []
    seen = set()
    for dx, dy in offsets:
        key = (round(dx, 4), round(dy, 4))  # 0.0001mm tolerance
        if key not in seen:
            seen.add(key)
            uniq.append((dx, dy))
    return uniq


def vpype_add_hershey_text(
    in_svg,
    out_svg,
    label_layout,
    font="futural",

    # NEW: thickness / boldness controls
    passes=1,                      # multipass count per offset position (darkens)
    stroke_distance_mm=0.0,         # >0 enables offset boldness (thickens)
    offset_paths=12,               # number of offsets around each ring
    offset_rings=(0.0, 1.0),       # radii in multiples of stroke_distance_mm (0.0 means center)
    layer="new",                   # put text on new layer by default
):
    """
    Add single-stroke (Hershey) text to an SVG using vpype, optionally thickened.

    Two mechanisms:
      - passes: repeats the exact same geometry N times (darker, not thicker)
      - offsets: draws the text multiple times with small XY shifts (thicker)

    Recommended starting point for a 0.7mm pen:
      stroke_distance_mm=0.25 to 0.35
      offset_paths=12 to 20
      offset_rings=(0.0, 1.0)  or (0.0, 0.7, 1.0)
      passes=1 or 2
    """
    vpype_cmd = shutil.which("vpype")
    if vpype_cmd is None:
        raise RuntimeError("vpype executable not found in PATH")

    cmd = [vpype_cmd, "read", in_svg]

    # Build offsets
    if stroke_distance_mm and stroke_distance_mm > 0:
        offsets = _make_offsets_mm(
            stroke_distance_mm=float(stroke_distance_mm),
            paths=int(offset_paths),
            rings=tuple(offset_rings),
            include_center=True,
        )
    else:
        offsets = [(0.0, 0.0)]  # no thickening, just one placement

    for key in ("city", "coords"):
        item = label_layout.get(key)
        if not item or not item.get("visible", False):
            continue

        text = item["text"]
        size_mm = float(item["fontsize_mm"])
        x0 = float(item["x_mm"])
        y0 = float(item["y_mm"])

        # Draw at each offset
        for dx, dy in offsets:
            cmd += [
                "text",
                "--layer", layer,
                "--font", font,
                "--size", f"{size_mm:.3f}mm",
                "--align", "center",
                "--position", f"{(x0 + dx):.3f}mm", f"{(y0 + dy):.3f}mm",
                text,
            ]

            # Optional: repeat the same geometry (darker)
            if passes and int(passes) > 1:
                cmd += ["multipass", str(int(passes))]

    cmd += ["write", out_svg]
    subprocess.run(cmd, check=True)