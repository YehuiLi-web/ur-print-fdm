from __future__ import annotations

import math
import re
from pathlib import Path


def parse_gcode(gcode_path: str, e_eps: float = 1e-8) -> list[dict]:
    """解析 Gcode 提取路径点"""
    layer_re = re.compile(r";\s*(?:LAYER\s*[:=]?\s*|layer\s+)(-?\d+)", re.I)
    mode_abs_e = True
    X = Y = Z = E = F = 0.0
    ops: list[dict] = []
    current_layer = None
    support_mode = False

    with open(gcode_path, "r", encoding="utf-8", errors="ignore") as f:
        for raw in f:
            raw_stripped = raw.strip()
            if not raw_stripped:
                continue

            # 层号嗅探
            m_layer = layer_re.search(raw_stripped)
            if m_layer:
                try:
                    current_layer = int(m_layer.group(1))
                except Exception:
                    pass

            # 支撑嗅探
            raw_upper = raw_stripped.upper()
            if ";TYPE:" in raw_upper:
                support_mode = "SUPPORT" in raw_upper

            s = raw_stripped.split(";", 1)[0].strip()
            if not s:
                continue

            parts = s.split()
            if not parts:
                continue

            cmd = parts[0].upper()

            if cmd == "M82":
                mode_abs_e = True
                continue
            if cmd == "M83":
                mode_abs_e = False
                continue

            if cmd not in {"G0", "G1"}:
                continue

            Xn, Yn, Zn = X, Y, Z
            En = None
            for tok in parts[1:]:
                if len(tok) < 2:
                    continue
                key = tok[0].upper()
                if key not in {"X", "Y", "Z", "E", "F"}:
                    continue
                try:
                    val = float(tok[1:])
                except ValueError:
                    continue

                if key == "X":
                    Xn = val
                elif key == "Y":
                    Yn = val
                elif key == "Z":
                    Zn = val
                elif key == "E":
                    En = val
                else:
                    F = val

            dE = 0.0
            if En is not None:
                if mode_abs_e:
                    dE = En - E
                    E = En
                else:
                    dE = En
                    E = E + En

            L = math.hypot(math.hypot(Xn - X, Yn - Y), Zn - Z)
            if L > 0.0:
                ops.append(
                    {
                        "type": "move",
                        "x0": X,
                        "y0": Y,
                        "z0": Z,
                        "x": Xn,
                        "y": Yn,
                        "z": Zn,
                        "f": F,
                        "de": dE,
                        "is_print": dE > e_eps,
                        "layer": current_layer,
                        "is_support": support_mode,
                    }
                )
            else:
                if abs(dE) > e_eps:
                    ops.append({"type": "e_only", "de": dE, "f": F, "layer": current_layer, "is_support": support_mode})
            X, Y, Z = Xn, Yn, Zn
    return ops


def gcode_to_urscript(gcode_path: str, out_path: str, params: dict) -> bool:
    """
    params 字典需包含:
    sp_print, sp_travel, sp_support, line_width, layer_height, filament_d, flow_factor,
    acc, feature1, tool_rxyz, modbus_id, s_start, s_stop, use_tcp, tcp_params(list)
    """

    def mm_to_m(x: float) -> float:
        return float(x) * 0.001

    def speed_to_4xxx(speed_mm_s: float, vmax: float = 9.99) -> int:
        v = max(0.0, min(vmax, float(speed_mm_s)))
        return 4000 + int(round(v * 100.0))

    ops = parse_gcode(gcode_path)

    # 简单的分段逻辑
    segments: list[tuple[str, list[dict]]] = []
    buf: list[dict] = []
    mode: str | None = None
    for op in ops:
        if op["type"] == "e_only":
            continue  # 忽略原地挤出
        tag = "move_print" if op["is_print"] else "move_travel"
        if mode is None:
            mode = tag
            buf = [op]
            continue
        if tag == mode:
            buf.append(op)
        else:
            segments.append((mode, buf))
            buf = [op]
            mode = tag
    if buf:
        segments.append((mode or "move_travel", buf))

    # 参数提取
    feat = [float(x) for x in params["feature1"].split(",")]
    tool = [float(x) for x in params["tool_rxyz"].split(",")]
    rx, ry, rz = tool

    v_print = mm_to_m(params["sp_print"])
    v_travel = mm_to_m(params["sp_travel"])
    v_support = mm_to_m(params.get("sp_support", params["sp_print"]))
    acc = params["acc"]

    # 计算挤出速度
    def calc_ve(v_rob: float) -> float:
        area_bead = params["line_width"] * params["layer_height"]
        area_fil = math.pi * (params["filament_d"] * 0.5) ** 2
        return v_rob * (area_bead / area_fil) * params["flow_factor"]

    reg4_main = speed_to_4xxx(calc_ve(params["sp_print"]))
    reg4_sup = speed_to_4xxx(calc_ve(params.get("sp_support", params["sp_print"])))

    # 生成脚本
    lines: list[str] = []
    func_name = "job_" + re.sub(r"[^A-Za-z0-9_]", "_", Path(out_path).stem)
    lines.append(f"def {func_name}():")
    lines.append(f"  global feature1 = p[{feat[0]},{feat[1]},{feat[2]},{feat[3]},{feat[4]},{feat[5]}]")

    if params["use_tcp"]:
        tcp = params["tcp_params"]  # [x, y, z, rx, ry, rz]
        lines.append(f"  set_tcp(p[{mm_to_m(tcp[0])},{mm_to_m(tcp[1])},{mm_to_m(tcp[2])},{tcp[3]},{tcp[4]},{tcp[5]}])")

    lines.append(f"  global speed_g0 = {v_travel}")
    lines.append(f"  global speed_g2 = {v_print}")
    lines.append(f"  global speed_g2_sup = {v_support}")
    lines.append(f"  global acc = {acc}")
    lines.append(f"  _mb = \"{params['modbus_id']}\"")
    lines.append("")

    last_print_xyz: tuple[float, float, float] | None = None

    for kind, seg in segments:
        is_print = kind == "move_print"
        is_support = is_print and any(op.get("is_support", False) for op in seg)

        # 打印段前置操作
        if is_print:
            reg = reg4_sup if is_support else reg4_main
            lines.append(f"  modbus_set_output_register(_mb, {reg})")
            if params["s_start"] > 0:
                lines.append(f"  sleep({params['s_start']})")

            # 插入层注释
            if seg[0].get("layer") is not None:
                lines.append(f"  # LAYER {seg[0]['layer'] + 1} Z={seg[0]['z']}")

        # 移动
        for op in seg:
            x, y, z = mm_to_m(op["x"]), mm_to_m(op["y"]), mm_to_m(op["z"])
            v_var = "speed_g2_sup" if is_support else ("speed_g2" if is_print else "speed_g0")
            lines.append(
                f"  movep(pose_trans(feature1, p[{x:.6f},{y:.6f},{z:.6f},{rx:.5f},{ry:.5f},{rz:.5f}]), a=acc, v={v_var}, r=0)"
            )
            if is_print:
                last_print_xyz = (x, y, z)

        # 打印段后置操作
        if is_print:
            lines.append("  modbus_set_output_register(_mb, 3000)")
            if params["s_stop"] > 0:
                lines.append(f"  sleep({params['s_stop']})")

    # 结束抬升
    if last_print_xyz:
        lx, ly, lz = last_print_xyz
        lines.append(
            f"  movep(pose_trans(feature1, p[{lx:.6f},{ly:.6f},{lz+0.03:.6f},{rx:.5f},{ry:.5f},{rz:.5f}]), a=acc, v=speed_g0, r=0)"
        )

    lines.append("end")
    lines.append(f"{func_name}()")

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return True
