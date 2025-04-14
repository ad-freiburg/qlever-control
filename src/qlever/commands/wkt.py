from __future__ import annotations

from matplotlib.font_manager import FontProperties
from matplotlib.path import Path
from matplotlib.textpath import TextPath
from shapely.geometry import Polygon
from shapely.ops import unary_union

from qlever.command import QleverCommand
from qlever.log import log


class WktCommand(QleverCommand):
    """
    Class for executing the `wkt` command.
    """

    def __init__(self):
        pass

    def description(self) -> str:
        return "Create WKT polygons from given string"

    def should_have_qleverfile(self) -> bool:
        return False

    def relevant_qleverfile_arguments(self) -> dict[str : list[str]]:
        return {}

    def additional_arguments(self, subparser) -> None:
        subparser.add_argument(
            "--string",
            type=str,
            required=True,
            help="String to convert to polygons",
        )
        subparser.add_argument(
            "--font",
            type=str,
            default="DejaVu Sans",
            help="Font familty to use for the polygons",
        )
        subparser.add_argument(
            "--size",
            type=int,
            default=100,
            help="Size of the polygons in km",
        )
        subparser.add_argument(
            "--center",
            type=str,
            default="POINT(47.9976, 7.8422)",
            help="Center of the polygons in WKT format",
        )

    def execute(self, args) -> bool:
        log.info(f"Converting string '{args.string}' to WKT polygons")

        # Parse the center point.
        center = args.center.split("(")[1].split(")")[0].split(",")

        # Get vertices from the string in the specified font.
        font_props = FontProperties(family=args.font, size=args.size)
        text_path = TextPath((0, 0), args.string, prop=font_props)
        vertices = text_path.vertices
        codes = text_path.codes

        # Turn into polygons.
        polygons = []
        current_vertices = []
        for vertex, code in zip(vertices, codes):
            # Transform the vertex to the center point.
            vertex = (
                float(center[1]) + vertex[0],
                float(center[0]) + vertex[1],
            )
            # Start a new subpath, add to the current one, or close the path.
            if code == Path.MOVETO:
                if len(current_vertices) > 2:
                    polygons.append(Polygon(current_vertices))
                current_vertices = [vertex]
            elif (
                code == Path.LINETO
                or code == Path.CURVE3
                or code == Path.CURVE4
            ):
                current_vertices.append(vertex)
            elif code == Path.CLOSEPOLY and len(current_vertices) > 2:
                current_vertices.append(current_vertices[0])  # Close the loop
                polygons.append(Polygon(current_vertices))
                current_vertices = []

        # Add the last polygon if we have unclosed points
        if len(current_vertices) > 2:
            polygons.append(Polygon(current_vertices))

        # Union overlapping parts, remove invalid polygons.
        clean = [p.buffer(0) for p in polygons if p.is_valid]
        result = unary_union(clean)

        print(result.wkt)
