import re
import math
import os
import socket
from pathlib import Path

# =============================================================================
# 工具 1: G-code 转 URScript (Planar)
# =============================================================================
from ur_print_fdm.processes.gcode_planar import gcode_to_urscript, parse_gcode

# =============================================================================
# 工具 2: 脚本分割 (Splitter)
# =============================================================================

def split_urscript(in_path, out_dir, max_lines=100000, extra_heights=[]):
    """
    分割 URScript，支持按行数和指定层高强制分割。
    返回生成的片段数量。
    """
    def is_layer_comment(line):
        s = line.strip().lower()
        return (s.startswith("#") or s.startswith("//")) and ("layer" in s or "seg" in s)

    def parse_z(line):
        m = re.search(r"z\s*=\s*([-+]?\d*\.?\d+)", line, re.IGNORECASE)
        return float(m.group(1)) if m else None

    path = Path(in_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    try: text = path.read_text(encoding='utf-8')
    except: text = path.read_text(encoding='latin-1')
    
    lines = text.splitlines(keepends=True)
    
    # 找 header / footer
    header_end = 0
    for i, line in enumerate(lines):
        if is_layer_comment(line): header_end = i; break
    
    footer_start = len(lines)
    for i in range(len(lines)-1, -1, -1):
        if lines[i].strip().startswith("end"): footer_start = i; break
        
    header = lines[:header_end]
    body = lines[header_end:footer_start]
    footer = lines[footer_start:]
    
    # 扫描 body 切割点
    splits = [] # (index_in_body, z_val)
    curr_z = None
    
    for i in range(len(body)):
        if is_layer_comment(body[i]):
            z = parse_z(body[i])
            if z is not None: curr_z = z
            
        if "modbus_set_output_register" in body[i] and "3000" in body[i]:
            # 检查下一行是否 sleep，如果是，这就是一个安全的切割点
            if i+1 < len(body) and "sleep" in body[i+1]:
                splits.append( (i+1, curr_z) )

    if not splits: return 0
    
    # 计算实际切割点索引
    force_indices = []
    # 映射额外层高到切割点
    for h in extra_heights:
        # 找最接近 h 的 z
        best_diff = float('inf')
        candidates = []
        for idx, z in splits:
            if z is None: continue
            diff = abs(z - h)
            if diff < best_diff: best_diff = diff; candidates = [idx]
            elif diff == best_diff: candidates.append(idx)
        
        if candidates and best_diff < 0.5: # 容差 0.5mm
            force_indices.append(max(candidates)) # 取该层最后一个切点

    # 生成分段
    final_segments = []
    start = 0
    limit = max_lines - len(header) - len(footer)
    
    while start < len(body):
        end_target = start + limit
        # 找下一个强制点
        next_force = None
        for f in sorted(force_indices):
            if f > start: next_force = f; break
            
        real_limit = min(end_target, next_force) if next_force else end_target
        if real_limit >= len(body): real_limit = len(body) - 1

        # 在范围内找最大的 split 点
        cut_point = None
        for idx, _ in splits:
            if idx > start and idx <= real_limit:
                cut_point = idx
            if idx > real_limit: break
            
        if cut_point:
            final_segments.append((start, cut_point + 1))
            start = cut_point + 1
        else:
            # 没找到切点，强行切完剩余（或报错）
            final_segments.append((start, len(body)))
            break

    # 写文件
    for i, (s, e) in enumerate(final_segments):
        part_name = f"{path.stem}_part{i+1:02d}.script"
        (out_dir / part_name).write_text("".join(header + body[s:e] + footer), encoding='utf-8')
        
    return len(final_segments)

# =============================================================================
# 工具 3: 插入完成标志 (Flag Inserter)
# =============================================================================

def insert_flag(filepath, do_index=7):
    """
    在 def 开头插 DO=False，end 前插 DO=True
    """
    MARK_RESET = "# === AUTO_RESET ==="
    MARK_DONE = "# === AUTO_DONE ==="
    
    path = Path(filepath)
    try: text = path.read_text(encoding='utf-8')
    except: return False
    
    if MARK_DONE in text: return True # 已存在
    
    lines = text.splitlines()
    
    def_idx = -1
    end_idx = -1
    
    for i, line in enumerate(lines):
        if line.lstrip().startswith("def "): def_idx = i; break
        
    for i in range(len(lines)-1, -1, -1):
        if lines[i].strip() == "end": end_idx = i; break
        
    if def_idx != -1 and end_idx != -1:
        # 插入 Reset
        indent = "  "
        lines.insert(def_idx+1, f"{indent}{MARK_RESET}")
        lines.insert(def_idx+2, f"{indent}set_standard_digital_out({do_index}, False)")
        
        # 插入 Done (因为上面插入了2行，end_idx要+2)
        end_idx += 2
        lines.insert(end_idx, f"{indent}set_standard_digital_out({do_index}, True)")
        lines.insert(end_idx, f"{indent}{MARK_DONE}")
        
        path.write_text("\n".join(lines), encoding='utf-8')
        return True
    return False
