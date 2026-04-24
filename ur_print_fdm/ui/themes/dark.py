"""
深色主题定义
"""

from .tokens import ThemeTokens

# 深色主题令牌
DARK: ThemeTokens = {
    "bg_main": "#2b2b2b",
    "bg_secondary": "#1e1e1e",
    "bg_tertiary": "#252526",
    "bg_panel": "#2d2d2d",
    "bg_hover": "#2a2a2a",
    "bg_hover_strong": "#383838",
    "border": "#3a3a3e",
    "border_light": "#46464a",
    "text": "#e0e0e0",
    "text_muted": "#8a8a8a",
    "text_dim": "#6a6a6a",
    "text_on_accent": "#ffffff",
    "icon": "#d4d4d4",
    "accent": "#094771",
    "accent_hover": "#0e639c",
    "accent_blue": "#2196F3",
    "accent_link": "#569CD6",
    "selection_bg": "#264f78",
    # 文件树样式 - 专业软件风格
    "tree_selection_bg": "#094771",  # 蓝色选中背景（VS Code 风格）
    "tree_hover_bg": "rgba(255, 255, 255, 0.05)",  # 悬停时微弱白色
    "primary_green": "#388E3C",
    "primary_green_hover": "#43A047",
    "primary_green_pressed": "#2E7D32",
    "danger": "#D32F2F",
    "danger_hover": "#E53935",
    "danger_pressed": "#B71C1C",
    "danger_checked": "#c62828",
    "neutral": "#455A64",
    "neutral_hover": "#546E7A",
    "neutral_pressed": "#37474F",
    "success": "#4CAF50",
    "warning": "#FFA726",
    "tooltip_bg": "#353535",
    "tooltip_border": "#4a4a4a",
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
    "btn_bg": "#3c3c3c",
    "btn_bg_hover": "#4a4a4a",
    "btn_bg_pressed": "#2a2a2a",
    "btn_border": "#505050",
    "btn_border_hover": "#606060",
    "btn_text": "#ffffff",
    "btn_disabled_bg": "#323232",
    "btn_disabled_border": "#404040",
    "btn_disabled_text": "#6a6a6a",
    # Scrollbar handles
    "scroll_handle": "rgba(121, 121, 121, 0.2)",
    "scroll_handle_hover": "rgba(121, 121, 121, 0.5)",
    "scroll_handle_pressed": "rgba(121, 121, 121, 0.7)",
    # Tree branch icons (QSS cannot tint; pick per-theme assets)
    "tree_branch_closed_icon": "ur_print_fdm/ui/resources/icons/collapse.svg",
    "tree_branch_open_icon": "ur_print_fdm/ui/resources/icons/expand.svg",
    # Code editor syntax highlighting
    "syntax_operator": "#858585",
    "syntax_comment": "#6A9955",
    "syntax_keyword": "#569CD6",
    "syntax_number": "#B5CEA8",
    "syntax_string": "#CE9178",
    "syntax_function": "#DCDCAA",
    # URScript 特定语法高亮
    "syntax_type": "#4EC9B0",       # 类型关键字 (global, local, True, False)
    "syntax_motion": "#DCDCAA",     # 运动指令 (movel, movej, movec)
    "syntax_io": "#C586C0",         # IO 指令 (set_digital_out, get_digital_in)
    "syntax_robot": "#9CDCFE",      # 机器人指令 (get_actual_tcp_pose, set_tcp)
    "syntax_math": "#D7BA7D",       # 数学函数 (sin, cos, sqrt) - 金色
    "syntax_pose": "#4FC1FF",       # 位姿函数 (pose_trans, pose_inv) - 亮青色
    "syntax_force": "#FF8C00",      # 力控指令 (force, zero_ftsensor)
}
