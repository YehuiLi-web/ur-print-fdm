from __future__ import annotations

from ur_print_fdm.plugins.contracts import GCodeConverter
from ur_print_fdm.processes.gcode_planar import gcode_to_urscript, parse_gcode


class PlanarGCodeConverter:
    id = "gcode_planar_v1"
    title = "G-code → URScript (planar)"

    def parse(self, gcode_path: str) -> list[dict]:
        return parse_gcode(gcode_path)

    def convert(self, gcode_path: str, out_path: str, params: dict) -> bool:
        return gcode_to_urscript(gcode_path, out_path, params)

