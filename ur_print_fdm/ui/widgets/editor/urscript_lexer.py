"""
URScript 自定义词法分析器
提供 URScript 语法高亮支持
"""

from PyQt6.QtGui import QColor, QFont

try:
    from PyQt6.Qsci import QsciLexerCustom, QsciScintilla
except ImportError:
    QsciLexerCustom = None
    QsciScintilla = None


# URScript 关键字分类
URSCRIPT_KEYWORDS = {
    # 控制流关键字
    "def", "end", "if", "elif", "else", "while", "for", "break", "continue",
    "return", "thread", "run", "kill", "join", "enter_critical", "exit_critical",
    "halt", "sync",
}

URSCRIPT_TYPES = {
    # 类型关键字
    "global", "local", "True", "False", "None",
}

URSCRIPT_MOTION_COMMANDS = {
    # 运动指令
    "movel", "movej", "movec", "movep", "servoj", "servoc",
    "speedl", "speedj", "stopj", "stopl",
    "teach_mode", "end_teach_mode", "force_mode", "end_force_mode",
    "freedrive_mode", "end_freedrive_mode",
}

URSCRIPT_IO_COMMANDS = {
    # IO 指令
    "set_standard_digital_out", "set_tool_digital_out", "set_configurable_digital_out",
    "set_standard_analog_out", "set_tool_analog_out",
    "get_standard_digital_in", "get_tool_digital_in", "get_configurable_digital_in",
    "get_standard_analog_in", "get_tool_analog_in",
    "set_digital_out", "get_digital_in",
    "set_analog_out", "get_analog_in",
    "set_flag", "get_flag",
    "modbus_set_output_register", "modbus_get_signal_status",
    "modbus_set_output_signal", "modbus_set_signal_update_frequency",
    "modbus_add_signal", "modbus_delete_signal",
    "socket_open", "socket_close", "socket_send_string", "socket_send_byte",
    "socket_send_int", "socket_send_line", "socket_read_byte_list",
    "socket_read_ascii_float", "socket_read_binary_integer", "socket_read_string",
    "socket_get_var",
}

URSCRIPT_ROBOT_COMMANDS = {
    # 机器人状态和配置指令
    "get_actual_tcp_pose", "get_actual_tcp_speed", "get_target_tcp_pose", "get_target_tcp_speed",
    "get_actual_joint_positions", "get_actual_joint_speeds", "get_target_joint_positions", "get_target_joint_speeds",
    "get_actual_joint_positions_history", "get_actual_joint_speeds_history",
    "get_joint_torques", "get_tcp_force", "get_tcp_offset",
    "set_tcp", "set_payload", "set_payload_cog", "set_payload_mass",
    "set_gravity", "set_target_payload",
    "get_inverse_kin", "get_forward_kin", "get_inverse_kin_has_solution",
    "is_within_safety_limits", "is_steady",
    "get_controller_temp", "get_joint_temp",
    "powerdown", "power_on", "power_off",
    "protective_stop", "unlock_protective_stop",
    "get_robot_mode", "get_safety_mode", "get_program_state",
    "popup", "textmsg", "sleep",
    "str_at", "str_cat", "str_empty", "str_find", "str_len", "str_sub", "to_str",
}

URSCRIPT_MATH_FUNCTIONS = {
    # 数学函数
    "sin", "cos", "tan", "asin", "acos", "atan", "atan2",
    "sqrt", "pow", "log", "exp", "abs", "ceil", "floor", "round",
    "norm", "normalize", "length", "point_dist",
    "d2r", "r2d",  # 角度转换
    "random", "binary_list_to_integer", "integer_to_binary_list",
}

URSCRIPT_POSE_FUNCTIONS = {
    # 位姿操作函数
    "pose_add", "pose_dist", "pose_inv", "pose_sub", "pose_trans",
    "interpolate_pose", "get_target_waypoint",
    "p", "rpy2rotvec", "rotvec2rpy",
}

URSCRIPT_CONVEYOR_COMMANDS = {
    # 传送带跟踪指令
    "conveyor_pulse_decode", "encoder_enable_pulse_decode", "encoder_get_tick_count",
    "encoder_set_tick_count", "encoder_unwind_delta_tick_count",
    "stop_conveyor_tracking", "conveyor_tracking",
}

URSCRIPT_FORCE_COMMANDS = {
    # 力控指令
    "force", "get_tcp_force", "zero_ftsensor",
    "tool_contact", "tool_contact_ex",
}

# 合并所有命令用于自动补全
ALL_URSCRIPT_COMMANDS = (
    URSCRIPT_KEYWORDS |
    URSCRIPT_TYPES |
    URSCRIPT_MOTION_COMMANDS |
    URSCRIPT_IO_COMMANDS |
    URSCRIPT_ROBOT_COMMANDS |
    URSCRIPT_MATH_FUNCTIONS |
    URSCRIPT_POSE_FUNCTIONS |
    URSCRIPT_CONVEYOR_COMMANDS |
    URSCRIPT_FORCE_COMMANDS
)


if QsciLexerCustom is not None:
    class URScriptLexer(QsciLexerCustom):
        """URScript 自定义词法分析器"""

        # 样式定义
        Default = 0
        Comment = 1
        Keyword = 2
        Type = 3
        MotionCommand = 4
        IOCommand = 5
        RobotCommand = 6
        MathFunction = 7
        PoseFunction = 8
        String = 9
        Number = 10
        Operator = 11
        Identifier = 12
        ForceCommand = 13

        def __init__(self, parent=None):
            super().__init__(parent)
            self._font = QFont("Consolas", 11)
            self._font.setFixedPitch(True)

            # 默认颜色（会被 apply_theme 覆盖）
            self._colors = {
                self.Default: QColor("#e0e0e0"),
                self.Comment: QColor("#6A9955"),
                self.Keyword: QColor("#569CD6"),
                self.Type: QColor("#4EC9B0"),
                self.MotionCommand: QColor("#DCDCAA"),
                self.IOCommand: QColor("#C586C0"),
                self.RobotCommand: QColor("#9CDCFE"),
                self.MathFunction: QColor("#B5CEA8"),
                self.PoseFunction: QColor("#CE9178"),
                self.String: QColor("#CE9178"),
                self.Number: QColor("#B5CEA8"),
                self.Operator: QColor("#858585"),
                self.Identifier: QColor("#e0e0e0"),
                self.ForceCommand: QColor("#FF8C00"),
            }

            self._paper = QColor("#1e1e1e")

        def language(self):
            return "URScript"

        def description(self, style):
            descriptions = {
                self.Default: "Default",
                self.Comment: "Comment",
                self.Keyword: "Keyword",
                self.Type: "Type",
                self.MotionCommand: "Motion Command",
                self.IOCommand: "IO Command",
                self.RobotCommand: "Robot Command",
                self.MathFunction: "Math Function",
                self.PoseFunction: "Pose Function",
                self.String: "String",
                self.Number: "Number",
                self.Operator: "Operator",
                self.Identifier: "Identifier",
                self.ForceCommand: "Force Command",
            }
            return descriptions.get(style, "")

        def defaultColor(self, style):
            return self._colors.get(style, self._colors[self.Default])

        def defaultPaper(self, style):
            return self._paper

        def defaultFont(self, style):
            return self._font

        def setColors(self, colors_dict):
            """设置颜色方案

            必须调用父类的 setColor() 方法才能真正更新 QScintilla 的颜色缓存
            """
            self._colors.update(colors_dict)
            # 关键：调用父类方法更新 QScintilla 内部颜色缓存
            for style, color in colors_dict.items():
                super().setColor(color, style)

        def setPaper(self, color, style=None):
            """设置背景色

            Args:
                color: 背景颜色
                style: 样式编号（可选，为兼容 QScintilla 接口）
            """
            self._paper = color
            # 关键：调用父类方法更新 QScintilla 内部背景色缓存
            # 为所有已定义的样式设置背景色
            for s in range(self.ForceCommand + 1):  # 0 到 13
                super().setPaper(color, s)

        def setFont(self, font):
            """设置字体"""
            self._font = font
            # 关键：调用父类方法更新 QScintilla 内部字体缓存
            for s in range(self.ForceCommand + 1):
                super().setFont(font, s)

        def styleText(self, start, end):
            """执行语法高亮

            注意：QScintilla 使用字节位置，而 Python 字符串使用字符位置。
            对于包含中文等多字节字符的文本，必须正确处理这种差异。
            """
            editor = self.editor()
            if not editor:
                return

            # 获取完整文本并转换为字节
            full_text = editor.text()
            if not full_text:
                return

            # 将完整文本编码为 UTF-8 字节
            text_bytes = full_text.encode('utf-8')

            # 确保 start 和 end 在有效范围内
            start = max(0, min(start, len(text_bytes)))
            end = max(start, min(end, len(text_bytes)))

            # 获取需要处理的字节范围，并解码为字符串
            portion_bytes = text_bytes[start:end]
            try:
                text = portion_bytes.decode('utf-8')
            except UnicodeDecodeError:
                # 如果解码失败，尝试从文档开头重新处理
                text = full_text
                start = 0

            if not text:
                return

            self.startStyling(start)

            # 状态机变量
            i = 0
            length = len(text)

            while i < length:
                ch = text[i]

                # 注释 (# 开头)
                if ch == '#':
                    # 找到行尾
                    j = i + 1
                    while j < length and text[j] != '\n':
                        j += 1
                    # 计算字节长度
                    byte_len = len(text[i:j].encode('utf-8'))
                    self.setStyling(byte_len, self.Comment)
                    i = j
                    continue

                # 字符串 (双引号)
                if ch == '"':
                    j = i + 1
                    while j < length:
                        if text[j] == '\\' and j + 1 < length:
                            j += 2
                            continue
                        if text[j] == '"':
                            j += 1
                            break
                        j += 1
                    byte_len = len(text[i:j].encode('utf-8'))
                    self.setStyling(byte_len, self.String)
                    i = j
                    continue

                # 数字
                # 只有在特定上下文中才将 - 视为负数的一部分
                is_negative_start = (ch == '-' and i + 1 < length and text[i + 1].isdigit() and
                                     (i == 0 or text[i - 1] in ' \t\n\r=([,<>!&|^~:+*/%'))
                if ch.isdigit() or is_negative_start:
                    j = i + 1 if ch == '-' else i
                    while j < length and (text[j].isdigit() or text[j] in '.eE+-'):
                        j += 1
                    byte_len = len(text[i:j].encode('utf-8'))
                    self.setStyling(byte_len, self.Number)
                    i = j
                    continue

                # 标识符和关键字
                if ch.isalpha() or ch == '_':
                    j = i + 1
                    while j < length and (text[j].isalnum() or text[j] == '_'):
                        j += 1
                    word = text[i:j]
                    byte_len = len(word.encode('utf-8'))

                    # 根据单词类型设置样式
                    if word in URSCRIPT_KEYWORDS:
                        self.setStyling(byte_len, self.Keyword)
                    elif word in URSCRIPT_TYPES:
                        self.setStyling(byte_len, self.Type)
                    elif word in URSCRIPT_MOTION_COMMANDS:
                        self.setStyling(byte_len, self.MotionCommand)
                    elif word in URSCRIPT_IO_COMMANDS:
                        self.setStyling(byte_len, self.IOCommand)
                    elif word in URSCRIPT_ROBOT_COMMANDS:
                        self.setStyling(byte_len, self.RobotCommand)
                    elif word in URSCRIPT_MATH_FUNCTIONS:
                        self.setStyling(byte_len, self.MathFunction)
                    elif word in URSCRIPT_POSE_FUNCTIONS:
                        self.setStyling(byte_len, self.PoseFunction)
                    elif word in URSCRIPT_FORCE_COMMANDS:
                        self.setStyling(byte_len, self.ForceCommand)
                    else:
                        self.setStyling(byte_len, self.Identifier)
                    i = j
                    continue

                # 运算符
                if ch in '+-*/%=<>!&|^~:,()[]{}':
                    self.setStyling(1, self.Operator)  # ASCII 字符始终是 1 字节
                    i += 1
                    continue

                # 其他字符（空白、中文等）
                byte_len = len(ch.encode('utf-8'))
                self.setStyling(byte_len, self.Default)
                i += 1

else:
    # 如果 QsciLexerCustom 不可用，提供一个空的占位类
    class URScriptLexer:
        """URScript Lexer 占位类（QScintilla 不可用时）"""
        def __init__(self, parent=None):
            pass


def get_urscript_completions():
    """获取 URScript 自动补全列表"""
    completions = []

    # 添加所有命令
    for cmd in sorted(ALL_URSCRIPT_COMMANDS):
        completions.append(cmd)

    # 添加常用代码片段
    snippets = [
        # 运动指令模板
        "movel(p[x, y, z, rx, ry, rz], a=1.2, v=0.25)",
        "movej([j0, j1, j2, j3, j4, j5], a=1.4, v=1.05)",
        "movec(via_pose, end_pose, a=1.2, v=0.25)",
        # 函数定义模板
        "def function_name():\n  # code here\nend",
        "thread thread_name():\n  # code here\nend",
        # 控制流模板
        "if condition:\n  # code\nelse:\n  # code\nend",
        "while condition:\n  # code\nend",
        "for i = 0 to 10:\n  # code\nend",
        # IO 模板
        "set_standard_digital_out(0, True)",
        "get_standard_digital_in(0)",
        # 位姿模板
        "p[0.0, 0.0, 0.0, 0.0, 0.0, 0.0]",
    ]

    completions.extend(snippets)
    return completions
