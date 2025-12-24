from xml.etree import ElementTree as ET

def clean_svg(in_path: str, out_path: str) -> None:
    tree = ET.parse(in_path)
    root = tree.getroot()

    # SVG namespace handling
    # tags may look like "{http://www.w3.org/2000/svg}path"
    def is_path(elem):
        return elem.tag.endswith("path")

    removed = 0

    # Walk parents so we can remove children
    for parent in root.iter():
        # list() because we may modify children while iterating
        for child in list(parent):
            if is_path(child):
                d = child.attrib.get("d")
                if d is None or d.strip() == "":
                    parent.remove(child)
                    removed += 1

    tree.write(out_path, encoding="utf-8", xml_declaration=True)
    print(f"Removed {removed} empty <path> elements -> {out_path}")

if __name__ == "__main__":
    clean_svg("hamburg_a4.svg", "hamburg_a4_clean.svg")

# vpype read hamburg_a4_clean.svg linemerge linesimplify linesort write hamburg_a4_plot.svg
# vpype read hamburg_a4_clean.svg linesimplify -t 0.2 linesort write hamburg_a4_plot2.svg