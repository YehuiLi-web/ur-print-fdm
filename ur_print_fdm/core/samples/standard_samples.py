from typing import List, Dict, Any
from ur_print_fdm.core.sample_library_manager import SampleBase, SampleParameter

class FlatPlateSample(SampleBase):
    @property
    def id(self) -> str:
        return "flat_plate"

    @property
    def title(self) -> str:
        return "平板样件"

    @property
    def description(self) -> str:
        return "生成标准平板样件，支持动态倾斜打印路径。"

    @property
    def instructions(self) -> str:
        return "1. 确保 Feature1 坐标系已正确对齐平板平面。\n2. 设置合适的层高和层数。"

    def get_parameters(self) -> List[SampleParameter]:
        return [
            SampleParameter("width", "宽度", 20.0, float, unit="mm"),
            SampleParameter("length", "长度", 100.0, float, unit="mm"),
            SampleParameter("layer_height", "层高", 0.5, float, unit="mm", decimals=3),
            SampleParameter("layers", "层数", 5, int),
            SampleParameter("speed", "速度", 16.0, float, unit="mm/s"),
            SampleParameter("tilt", "倾斜", 30.0, float, unit="deg"),
            SampleParameter("extrude", "启用挤出", True, bool),
            SampleParameter("feature", "Feature", "p[-0.49, 0.12, 0.15, -0.02, 0.0, -1.57]", str),
            SampleParameter("tcp", "TCP", "p[0.009, 0.011, 0.159, 0.0, 0.0, 0.0]", str),
        ]

    def generate_script(self, params: Dict[str, Any], context: Any = None) -> str:
        width_mm = params["width"]
        length_mm = params["length"]
        layer_h_mm = params["layer_height"]
        layers = params["layers"]
        speed_mm_s = params["speed"]
        tilt_deg = params["tilt"]
        feature_str = params["feature"]
        tcp_str = params["tcp"]

        ext_val = 0
        mb_ext = "MODBUS_1"
        if context:
            mb_ext = context.mb_ext
            if params.get("extrude", True):
                ext_val = context.calc_extruder_reg(speed_mm_s, 1.0, layer_h_mm)

        w_m = width_mm / 1000.0
        l_m = length_mm / 1000.0
        lh_m = layer_h_mm / 1000.0
        spd_m = speed_mm_s / 1000.0
        line_w_m = 0.001
        count_lines = int(w_m / line_w_m)

        script = f"""def job_generated_plate():
  # === 1. 基础设置 ===
  global feature1 = {feature_str}
  set_tcp({tcp_str})

  # === 2. 打印参数 ===
  local line_width = {line_w_m}
  local layer_h    = {lh_m}
  local p_len      = {l_m}

  local count_lines  = {count_lines}
  local count_layers = {layers}

  local v_print = {spd_m}
  local acc     = 0.3
  local corner_wait = 0.1

  # 挤出控制
  local ext_val = {ext_val}
  local mb_name = "{mb_ext}"

  # === 3. 姿态计算 (动态倾斜) ===
  local p_vert_ref = p[0, 0, 0, 2.221, -2.221, 0]
  local tilt_rad = d2r({tilt_deg})

  # 去程 (+角度)
  local rot_offset_fwd = p[0, 0, 0, 0, tilt_rad, 0]
  local p_pose_fwd = pose_trans(p_vert_ref, rot_offset_fwd)
  local rx_f = p_pose_fwd[3]; local ry_f = p_pose_fwd[4]; local rz_f = p_pose_fwd[5]

  # 回程 (-角度)
  local rot_offset_bwd = p[0, 0, 0, 0, -tilt_rad, 0]
  local p_pose_bwd = pose_trans(p_vert_ref, rot_offset_bwd)
  local rx_b = p_pose_bwd[3]; local ry_b = p_pose_bwd[4]; local rz_b = p_pose_bwd[5]

  # === 4. 计算偏移 ===
  local total_width = count_lines * line_width
  local x_start_offset = -(total_width / 2.0)
  local y_start_offset = -(p_len / 2.0)
  local y_end_offset   = (p_len / 2.0)

  # === 5. 执行循环 ===
  movej(pose_trans(feature1, p[0, 0, 0.02, rx_f, ry_f, rz_f]), a=1.0, v=0.05)

  local layer_idx = 0
  while (layer_idx < count_layers):
    local z_curr = (layer_idx + 1) * layer_h
    local line_idx = 0
    while (line_idx < count_lines):
      local x_curr = x_start_offset + (line_idx * line_width)
      if (ext_val > 0): modbus_set_output_register(mb_name, ext_val) end

      if (line_idx == 0):
        local p_s = pose_trans(feature1, p[x_curr, y_start_offset, z_curr, rx_f, ry_f, rz_f])
        local p_e = pose_trans(feature1, p[x_curr, y_end_offset, z_curr, rx_f, ry_f, rz_f])
        movel(p_s, a=acc, v=v_print)
        movel(p_e, a=acc, v=v_print)
      elif ((line_idx % 2) == 0):
        local p_shift_1 = pose_trans(feature1, p[x_curr, y_start_offset, z_curr+0.002, rx_f, ry_f, rz_f])
        local p_shift_2 = pose_trans(feature1, p[x_curr, y_start_offset, z_curr, rx_f, ry_f, rz_f])
        movel(p_shift_1, a=acc, v=v_print); movel(p_shift_2, a=acc, v=v_print)
        movel(pose_trans(feature1, p[x_curr, y_end_offset, z_curr, rx_f, ry_f, rz_f]), a=acc, v=v_print)
      else:
        local p_shift_1 = pose_trans(feature1, p[x_curr, y_end_offset, z_curr+0.002, rx_b, ry_b, rz_b])
        local p_shift_2 = pose_trans(feature1, p[x_curr, y_end_offset, z_curr, rx_b, ry_b, rz_b])
        movel(p_shift_1, a=acc, v=v_print); movel(p_shift_2, a=acc, v=v_print)
        movel(pose_trans(feature1, p[x_curr, y_start_offset, z_curr, rx_b, ry_b, rz_b]), a=acc, v=v_print)
      end
      if (ext_val > 0): modbus_set_output_register(mb_name, 0) end
      sleep(corner_wait)
      line_idx = line_idx + 1
    end
    layer_idx = layer_idx + 1
  end
  movel(pose_trans(feature1, p[0, 0, 0.1, rx_f, ry_f, rz_f]), a=0.5, v=0.05)
end
job_generated_plate()
"""
        return script

class CircularRingSample(SampleBase):
    @property
    def id(self) -> str:
        return "circular_ring"

    @property
    def title(self) -> str:
        return "⭕ 圆环样件"

    @property
    def description(self) -> str:
        return "生成圆形环状打印脚本。"

    def get_parameters(self) -> List[SampleParameter]:
        return [
            SampleParameter("diameter", "直径", 50.0, float, unit="mm"),
            SampleParameter("height", "高度", 20.0, float, unit="mm"),
            SampleParameter("layer_height", "层高", 0.5, float, unit="mm", decimals=3),
            SampleParameter("layers", "层数", 10, int),
            SampleParameter("speed", "速度", 10.0, float, unit="mm/s"),
            SampleParameter("extrude", "启用挤出", True, bool),
            SampleParameter("feature", "Feature", "p[-0.49, 0.12, 0.15, -0.02, 0.0, -1.57]", str),
            SampleParameter("tcp", "TCP", "p[0.009, 0.011, 0.159, 0.0, 0.0, 0.0]", str),
        ]

    def generate_script(self, params: Dict[str, Any], context: Any = None) -> str:
        dia_m = params["diameter"] / 1000.0
        h_m = params["height"] / 1000.0
        lh_m = params["layer_height"] / 1000.0
        layers = params["layers"]
        spd_m = params["speed"] / 1000.0
        radius_m = dia_m / 2.0
        feature_str = params["feature"]
        tcp_str = params["tcp"]

        ext_val = 0
        mb_ext = "MODBUS_1"
        if context:
            mb_ext = context.mb_ext
            if params.get("extrude", True):
                ext_val = context.calc_extruder_reg(params["speed"], 1.0, params["layer_height"])

        script = f"""def job_generated_ring():
  # === 1. 基础设置 ===
  global feature1 = {feature_str}
  set_tcp({tcp_str})

  # === 2. 打印参数 ===
  local radius = {radius_m}
  local height = {h_m}
  local layer_h = {lh_m}
  local count_layers = {layers}
  local v_print = {spd_m}
  local acc = 0.3
  local corner_wait = 0.1

  # 挤出控制
  local ext_val = {ext_val}
  local mb_name = "{mb_ext}"

  # === 3. 垂直参考姿态 ===
  local p_vert_ref = p[0, 0, 0, 2.221, -2.221, 0]

  # === 4. 执行循环 ===
  movej(pose_trans(feature1, p[0, 0, 0.02, p_vert_ref[3], p_vert_ref[4], p_vert_ref[5]]), a=1.0, v=0.05)

  local layer_idx = 0
  while (layer_idx < count_layers):
    local z_curr = (layer_idx + 1) * layer_h
    if (ext_val > 0): modbus_set_output_register(mb_name, ext_val) end

    local steps = 64
    local step_angle = 2 * 3.14159 / steps
    local angle = 0
    local i = 0
    while (i < steps):
      local x = radius * cos(angle)
      local y = radius * sin(angle)
      local p_curr = pose_trans(feature1, p[x, y, z_curr, p_vert_ref[3], p_vert_ref[4], p_vert_ref[5]])
      movel(p_curr, a=acc, v=v_print)
      angle = angle + step_angle
      i = i + 1
    end

    if (ext_val > 0): modbus_set_output_register(mb_name, 0) end
    sleep(corner_wait)
    layer_idx = layer_idx + 1
  end
  movel(pose_trans(feature1, p[0, 0, 0.1, p_vert_ref[3], p_vert_ref[4], p_vert_ref[5]]), a=0.5, v=0.05)
end
job_generated_ring()
"""
        return script
