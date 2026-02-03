import math
import numpy as np  # <--- 必须添加 numpy
class URPrintLib:
    """
    UR机械臂 + 转盘协同打印核心计算库
    """
    def __init__(self, filament_dia=1.75, base_reg=4000, mb_ext="MODBUS_1", mb_pin="pin", mb_bu="bu"):
        """
        初始化硬件参数
        :param filament_dia: 耗材直径 (mm)
        :param base_reg: 挤出机停止基准值 (如 4000)
        :param mb_ext: 挤出机 Modbus 寄存器名
        :param mb_pin: 转盘方向/速度寄存器名
        :param mb_bu: 转盘步数寄存器名
        """
        self.filament_dia = filament_dia
        self.base_reg = base_reg
        self.mb_ext = mb_ext
        self.mb_pin = mb_pin
        self.mb_bu = mb_bu
        self.filament_area = math.pi * ((filament_dia / 2.0) ** 2)

    # ================= 工具函数 =================

    def parse_pose_string(self, p_str):
        """解析 UR p[...] 字符串为浮点数列表"""
        try:
            content = p_str.split('[')[1].split(']')[0]
            return [float(x) for x in content.split(',')]
        except IndexError:
            raise ValueError(f"坐标格式错误: {p_str}, 应为 p[x,y,z,rx,ry,rz]")

    def get_distance_mm(self, p1_str, p2_str):
        """计算两个位姿字符串之间的直线距离 (mm)"""
        p1 = self.parse_pose_string(p1_str)
        p2 = self.parse_pose_string(p2_str)
        # 欧几里得距离 (XYZ)
        dist_m = math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2 + (p2[2]-p1[2])**2)
        return dist_m * 1000.0

    # ================= 核心计算 =================

    def calc_extruder_reg(self, print_speed_mm_s, line_width, layer_height):
        """
        计算挤出机 Modbus 寄存器值
        :return: (int) 寄存器值
        """
        if self.filament_dia == 0: return self.base_reg
        
        # 流量 Q = V_print * W * H
        flow_rate = print_speed_mm_s * line_width * layer_height
        # E轴速度 = Q / Area
        e_speed = flow_rate / self.filament_area
        
        if e_speed > 9.99: e_speed = 9.99
        
        # 假设协议是 Base + Speed*100
        return int(self.base_reg + round(e_speed * 100))

    def calc_turntable_params(self, dist_mm, speed_mm_s, cylinder_dia, cw=True):
        """
        计算转盘协同打印参数 (Pin, Bu)
        :param dist_mm: 打印路径长度 (mm)
        :param speed_mm_s: 打印速度 (mm/s)
        :param cylinder_dia: 圆柱直径 (mm)
        :param cw: 是否顺时针
        :return: (int pin, int bu)
        """
        if speed_mm_s <= 0 or cylinder_dia <= 0: return 0, 0
        
        time_s = dist_mm / speed_mm_s
        circumference = math.pi * cylinder_dia
        
        # 假设逻辑：Z轴每走一个圆周长，转盘转一圈 (45度螺旋)
        turns = dist_mm / circumference
        
        # 计算步数 (16000步/圈)
        bu = int(round(turns * 16000))
        if bu < 1: bu = 1
        
        # 计算速度 (特定驱动器协议)
        spd_val = int(round((bu / 10.0) / time_s * 100))
        if spd_val > 9999: spd_val = 9999
        
        direction = 1 if cw else 2
        pin = direction * 10000 + spd_val
        
        return pin, bu

    def calc_index_params(self, line_width, cylinder_dia):
        """
        计算换行微调 (Index) 参数
        :return: (int pin, int bu)
        """
        # 转动角度比例 = 线宽 / 周长
        fraction = line_width / (math.pi * cylinder_dia)
        bu = int(round(fraction * 16000))
        if bu < 1: bu = 1
        
        # 设定为快速转动 (例如 0.5秒)
        # Speed = (Steps/10) / Time * 100
        # 这里简化：固定一个较快速度
        pin = 14912 # 默认一个中等速度正转
        
        return pin, bu

    # ================= 代码生成辅助 =================
    
    def gen_move_block(self, target_pose, speed_m_s, acc, ext_reg, turn_pin, turn_bu, comment=""):
        """
        生成一段标准的 URScript 打印代码块 (包含 Modbus 开关)
        """
        lines = []
        if comment: lines.append(f"    # {comment}")
        
        # 1. 设置转盘
        lines.append(f"    modbus_set_output_register(\"{self.mb_pin}\", {turn_pin})")
        lines.append(f"    sleep(0.05)")
        lines.append(f"    modbus_set_output_register(\"{self.mb_bu}\", {turn_bu})")
        
        # 2. 开启挤出
        lines.append(f"    modbus_set_output_register(\"{self.mb_ext}\", {ext_reg})")
        
        # 3. 移动
        lines.append(f"    movel({target_pose}, a={acc}, v={speed_m_s})")
        
        # 4. 停止挤出
        lines.append(f"    modbus_set_output_register(\"{self.mb_ext}\", 0)")
        
        # 5. 停止转盘
        lines.append(f"    sleep(0.05)")
        lines.append(f"    modbus_set_output_register(\"{self.mb_bu}\", 0)")
        lines.append(f"    sleep(0.05)")
        
        return "\n".join(lines)
    
    # ================= 平板样件生成逻辑 =================
    
    def gen_flat_plate_script(self, width_mm, length_mm, layer_h_mm, layers, 
                              speed_mm_s, tilt_deg, feature_str, tcp_str, 
                              modbus_val=0):
        """
        生成平板动态倾斜打印脚本 (基于 pingban.script 逻辑)
        :param modbus_val: 挤出速度寄存器值 (0表示不挤出)
        """
        
        # 将参数转换为 URScript 友好的字符串
        w_m = width_mm / 1000.0
        l_m = length_mm / 1000.0
        lh_m = layer_h_mm / 1000.0
        spd_m = speed_mm_s / 1000.0
        
        # 估算线数 (线宽假设 1mm，可由参数传入优化)
        # 这里为了保持脚本逻辑，我们假设线宽 1mm (0.001m)
        line_w_m = 0.001 
        count_lines = int(w_m / line_w_m)
        
        script = f"""def job_generated_plate():
  # === 1. 基础设置 ===
  global feature1 = {feature_str}
  set_tcp({tcp_str})
  
  # === 2. 打印参数 (Python 生成) ===
  local line_width = {line_w_m}
  local layer_h    = {lh_m}
  local p_len      = {l_m}
  
  local count_lines  = {count_lines}
  local count_layers = {layers}
  
  local v_print = {spd_m}
  local acc     = 0.3
  local corner_wait = 0.1
  
  # 挤出控制
  local ext_val = {modbus_val}
  local mb_name = "{self.mb_ext}"

  # === 3. 姿态计算 (动态倾斜) ===
  # 垂直参考姿态 (Z轴朝下)
  local p_vert_ref = p[0, 0, 0, 2.221, -2.221, 0] 
  
  # 倾斜角度 {tilt_deg} 度
  local tilt_rad = d2r({tilt_deg})
  
  # 去程 (+角度)
  local rot_offset_fwd = p[0, 0, 0, 0, tilt_rad, 0]
  local p_pose_fwd = pose_trans(p_vert_ref, rot_offset_fwd)
  local rx_f = p_pose_fwd[3]
  local ry_f = p_pose_fwd[4]
  local rz_f = p_pose_fwd[5]

  # 回程 (-角度)
  local rot_offset_bwd = p[0, 0, 0, 0, -tilt_rad, 0]
  local p_pose_bwd = pose_trans(p_vert_ref, rot_offset_bwd)
  local rx_b = p_pose_bwd[3]
  local ry_b = p_pose_bwd[4]
  local rz_b = p_pose_bwd[5]

  # === 4. 计算偏移 ===
  local total_width = count_lines * line_width
  local x_start_offset = -(total_width / 2.0)
  local y_start_offset = -(p_len / 2.0)
  local y_end_offset   = (p_len / 2.0)

  # === 5. 执行循环 ===
  # 移动到安全起点上方
  movej(pose_trans(feature1, p[0, 0, 0.02, rx_f, ry_f, rz_f]), a=1.0, v=0.05)

  local layer_idx = 0
  while (layer_idx < count_layers):
    local z_curr = (layer_idx + 1) * layer_h
    local line_idx = 0
    
    # 层起始注释
    # LAYER START
    
    while (line_idx < count_lines):
      local x_curr = x_start_offset + (line_idx * line_width)
      
      # 开启挤出 (如果设定了值)
      if (ext_val > 0):
        modbus_set_output_register(mb_name, ext_val)
      end
      
      if (line_idx == 0):
        # 第一条线 (去程 Fwd)
        local p_s = pose_trans(feature1, p[x_curr, y_start_offset, z_curr, rx_f, ry_f, rz_f])
        local p_e = pose_trans(feature1, p[x_curr, y_end_offset, z_curr, rx_f, ry_f, rz_f])
        movel(p_s, a=acc, v=v_print)
        movel(p_e, a=acc, v=v_print)
        
      elif ((line_idx % 2) == 0):
        # 偶数线 (去程 Fwd): 从 Start -> End
        # 变姿态过渡
        local p_shift_1 = pose_trans(feature1, p[x_curr, y_start_offset, z_curr+0.002, rx_f, ry_f, rz_f])
        local p_shift_2 = pose_trans(feature1, p[x_curr, y_start_offset, z_curr, rx_f, ry_f, rz_f])
        movel(p_shift_1, a=acc, v=v_print) # 抬刀变姿
        movel(p_shift_2, a=acc, v=v_print) # 下刀
        
        # 打印
        local p_fwd = pose_trans(feature1, p[x_curr, y_end_offset, z_curr, rx_f, ry_f, rz_f])
        movel(p_fwd, a=acc, v=v_print)
        
      else:
        # 奇数线 (回程 Bwd): 从 End -> Start
        # 变姿态过渡 (+30 -> -30)
        local p_shift_1 = pose_trans(feature1, p[x_curr, y_end_offset, z_curr+0.002, rx_b, ry_b, rz_b])
        local p_shift_2 = pose_trans(feature1, p[x_curr, y_end_offset, z_curr, rx_b, ry_b, rz_b])
        movel(p_shift_1, a=acc, v=v_print)
        movel(p_shift_2, a=acc, v=v_print)
        
        # 打印
        local p_bwd = pose_trans(feature1, p[x_curr, y_start_offset, z_curr, rx_b, ry_b, rz_b])
        movel(p_bwd, a=acc, v=v_print)
      end
      
      # 暂时关闭挤出 (转角)
      if (ext_val > 0):
        modbus_set_output_register(mb_name, 0)
      end
      sleep(corner_wait)
      
      line_idx = line_idx + 1
    end
    layer_idx = layer_idx + 1
  end
  
  # 结束抬升
  movel(pose_trans(feature1, p[0, 0, 0.1, rx_f, ry_f, rz_f]), a=0.5, v=0.05)
end
job_generated_plate()
"""
        return script
    
    # ================= 平面标定算法 (移植自 single_arm_calibration_plane.py) =================

    @staticmethod
    def fit_plane_feature(points_mm):
        """
        输入: 点列表 [[x,y,z], ...] (单位 mm)
        输出: (feature_str, log_str)
        """
        P = np.asarray(points_mm, dtype=float)
        if P.shape[0] < 3:
            return None, "错误: 点数少于 3 个，无法拟合。"

        # 1. 拟合平面 (SVD)
        centroid = P.mean(axis=0)
        Q = P - centroid
        U, S, Vt = np.linalg.svd(Q, full_matrices=False)
        normal = Vt[-1, :] # 法向量
        normal = normal / np.linalg.norm(normal)

        # 强制法向朝上 (+Z)
        if np.dot(normal, np.array([0.0, 0.0, 1.0])) < 0:
            normal = -normal

        # 计算残差
        residuals = (P - centroid) @ normal
        mean_err = float(np.mean(np.abs(residuals)))

        # 2. 构建坐标系 (O-X-Y)
        # 假设前三个点分别是 O, X, Y
        O = P[0]
        X = P[1]
        
        # z_axis = 平面法向
        z_axis = normal
        
        # x_axis = O->X 在平面上的投影
        vx = X - O
        vx = vx - np.dot(vx, z_axis) * z_axis
        if np.linalg.norm(vx) < 1e-6:
            return None, "错误: O 点和 X 点重合或垂直于平面，无法确定 X 轴。"
        x_axis = vx / np.linalg.norm(vx)
        
        # y_axis = z cross x
        y_axis = np.cross(z_axis, x_axis)
        y_axis = y_axis / np.linalg.norm(y_axis)

        # 3. 构建旋转矩阵 R
        R = np.column_stack((x_axis, y_axis, z_axis))
        
        # 转轴角 (rx, ry, rz)
        def rotmat_to_axis_angle(R):
            tr = np.trace(R)
            theta = np.arccos(np.clip((tr - 1.0) / 2.0, -1.0, 1.0))
            if abs(theta) < 1e-6: return 0.0, 0.0, 0.0
            
            k = 1.0 / (2.0 * np.sin(theta))
            rx = (R[2, 1] - R[1, 2]) * k
            ry = (R[0, 2] - R[2, 0]) * k
            rz = (R[1, 0] - R[0, 1]) * k
            
            vec = np.array([rx, ry, rz])
            vec = vec / np.linalg.norm(vec) * theta
            return vec[0], vec[1], vec[2]

        rx, ry, rz = rotmat_to_axis_angle(R)
        
        # 位置单位换算 mm -> m
        tx, ty, tz = O / 1000.0
        
        feat_str = f"p[{tx:.6f}, {ty:.6f}, {tz:.6f}, {rx:.6f}, {ry:.6f}, {rz:.6f}]"
        
        log_str = (f"拟合成功!\n"
                   f"点数: {len(P)}\n"
                   f"平均残差: {mean_err:.4f} mm\n"
                   f"Feature: {feat_str}")

        return feat_str, log_str

    def gen_circular_ring_script(self, diameter_mm, height_mm, layer_h_mm, layers,
                                speed_mm_s, feature_str, tcp_str, modbus_val=0):
        """
        生成圆形环状打印脚本
        :param diameter_mm: 圆环直径 (mm)
        :param height_mm: 圆环高度 (mm)
        :param layer_h_mm: 层高 (mm)
        :param layers: 层数
        :param speed_mm_s: 打印速度 (mm/s)
        :param feature_str: 特征坐标系字符串
        :param tcp_str: TCP偏移字符串
        :param modbus_val: 挤出速度寄存器值 (0表示不挤出)
        """
        dia_m = diameter_mm / 1000.0
        h_m = height_mm / 1000.0
        lh_m = layer_h_mm / 1000.0
        spd_m = speed_mm_s / 1000.0

        # 计算半径
        radius_m = dia_m / 2.0

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
  local ext_val = {modbus_val}
  local mb_name = "{self.mb_ext}"

  # === 3. 垂直参考姿态 ===
  local p_vert_ref = p[0, 0, 0, 2.221, -2.221, 0]

  # === 4. 执行循环 ===
  # 移动到安全起点上方
  movej(pose_trans(feature1, p[0, 0, 0.02, p_vert_ref[3], p_vert_ref[4], p_vert_ref[5]]), a=1.0, v=0.05)

  local layer_idx = 0
  while (layer_idx < count_layers):
    local z_curr = (layer_idx + 1) * layer_h

    # 开启挤出 (如果设定了值)
    if (ext_val > 0):
      modbus_set_output_register(mb_name, ext_val)
    end

    # 圆形路径 - 使用小步长近似圆
    local steps = 64  # 64步近似圆
    local step_angle = 2 * 3.14159 / steps
    local angle = 0

    local i = 0
    while (i < steps):
      local x = radius * cos(angle)
      local y = radius * sin(angle)
      local p_curr = pose_trans(feature1, p[x, y, z_curr, p_vert_ref[3], p_vert_ref[4], p_vert_ref[5]])

      if (i == 0):
        # 第一个点，移动到位
        movel(p_curr, a=acc, v=v_print)
      else:
        # 后续点，连续打印
        movel(p_curr, a=acc, v=v_print)
      end

      angle = angle + step_angle
      i = i + 1
    end

    # 关闭挤出
    if (ext_val > 0):
      modbus_set_output_register(mb_name, 0)
    end
    sleep(corner_wait)

    layer_idx = layer_idx + 1
  end

  # 结束抬升
  movel(pose_trans(feature1, p[0, 0, 0.1, p_vert_ref[3], p_vert_ref[4], p_vert_ref[5]]), a=0.5, v=0.05)
end
job_generated_ring()
"""
        return script