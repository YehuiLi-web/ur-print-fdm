"""
浅色主题定义
"""

from .tokens import ThemeTokens

# 浅色主题令牌
LIGHT: ThemeTokens = {
    # === Phase A 优化: 柔化背景色，降低刺眼感 ===
    "bg_main": "#f0f1f4",           # 主背景: 从灰白 #d8d8dd 调整为更柔和的浅灰
    "bg_secondary": "#fafbfc",      # 次要背景: 从纯白 #ffffff 调整为米白色
    "bg_tertiary": "#f5f6f8",       # 第三层背景: 微调
    "bg_panel": "#ffffff",          # 面板/卡片: 保留纯白作为浮层，拉开层次
    "bg_hover": "#e8eaef",          # 悬停背景: 略深
    "bg_hover_strong": "#dfe2e8",   # 强悬停背景: 更明显的反馈
    "border": "#c8cfd8",            # 边框: 略深，增强边界感
    "border_light": "#dfe2e8",      # 浅边框: 微调
    "text": "#1f2328",
    "text_muted": "#57606a",
    "text_dim": "#8c959f",
    "text_on_accent": "#ffffff",
    "icon": "#57606a",
    "accent": "#0969da",
    "accent_hover": "#0758b8",
    "accent_blue": "#0969da",
    "accent_link": "#0969da",
    "selection_bg": "#cfe8ff",
    # 文件树样式 - 专业软件风格
    "tree_selection_bg": "#0969da30",  # 蓝色半透明选中背景
    "tree_hover_bg": "rgba(0, 0, 0, 0.04)",  # 悬停时微弱黑色
    "primary_green": "#2da44e",
    "primary_green_hover": "#2c974b",
    "primary_green_pressed": "#238636",
    "danger": "#cf222e",
    "danger_hover": "#a40e26",
    "danger_pressed": "#82071e",
    "danger_checked": "#cf222e",
    "neutral": "#6e7781",
    "neutral_hover": "#5b646e",
    "neutral_pressed": "#48515a",
    "success": "#2da44e",
    "warning": "#bf8700",
    # Tooltips: keep dark for readability
    "tooltip_bg": "#1f2328",
    "tooltip_border": "#3d444d",
    "tooltip_text": "#f0f0f0",
    "radius": "4px",
    "radius_lg": "6px",
    "font_main": '"Segoe UI", "Microsoft YaHei", sans-serif',
    "font_mono": '"Consolas", "Courier New", monospace',
    "size_base": "10pt",
    "size_small": "9pt",
    "size_large": "11pt",
    "space_sm": "4px",
    "space_md": "8px",
    "space_lg": "12px",
    # Buttons (generic)
    "btn_bg": "#f6f8fa",
    "btn_bg_hover": "#eef2f6",
    "btn_bg_pressed": "#e7ebef",
    "btn_border": "#d0d7de",
    "btn_border_hover": "#b6bec8",
    "btn_text": "#1f2328",
    "btn_disabled_bg": "#f6f8fa",
    "btn_disabled_border": "#e6e8ee",
    "btn_disabled_text": "#8c959f",
    # Scrollbar handles
    "scroll_handle": "rgba(0, 0, 0, 0.18)",
    "scroll_handle_hover": "rgba(0, 0, 0, 0.28)",
    "scroll_handle_pressed": "rgba(0, 0, 0, 0.38)",
    # Tree branch icons (QSS cannot tint; pick per-theme assets)
    "tree_branch_closed_icon": "ur_print_fdm/ui/resources/icons/collapse_light.svg",
    "tree_branch_open_icon": "ur_print_fdm/ui/resources/icons/expand_light.svg",
    # Code editor syntax highlighting
    "syntax_operator": "#57606a",
    "syntax_comment": "#6a737d",
    "syntax_keyword": "#0550ae",
    "syntax_number": "#953800",
    "syntax_string": "#0a3069",
    "syntax_function": "#8250df",
    # URScript 特定语法高亮
    "syntax_type": "#0550ae",       # 类型关键字 (global, local, True, False)
    "syntax_motion": "#6f42c1",     # 运动指令 (movel, movej, movec)
    "syntax_io": "#a475f9",         # IO 指令 (set_digital_out, get_digital_in)
    "syntax_robot": "#0969da",      # 机器人指令 (get_actual_tcp_pose, set_tcp)
    "syntax_math": "#e36209",       # 数学函数 (sin, cos, sqrt) - 橙色
    "syntax_pose": "#22863a",       # 位姿函数 (pose_trans, pose_inv) - 绿色
    "syntax_force": "#cf222e",      # 力控指令 (force, zero_ftsensor)
}
