from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class URScriptParameter:
    name: str
    description: str
    default: str | None = None

    @property
    def display_name(self) -> str:
        if self.default is None:
            return self.name
        return f"{self.name} = {self.default}"


@dataclass(frozen=True)
class URScriptSymbol:
    name: str
    category: str
    summary: str
    signatures: tuple[str, ...] = ()
    parameters: tuple[URScriptParameter, ...] = ()
    example: str | None = None
    detail: str | None = None
    docs_section: str | None = None
    insert_text: str | None = None

    @property
    def completion_text(self) -> str:
        return self.insert_text or self.name


@dataclass(frozen=True)
class URScriptCallContext:
    name: str
    arg_index: int
    open_offset: int


def _param(name: str, description: str, default: str | None = None) -> URScriptParameter:
    return URScriptParameter(name=name, description=description, default=default)


def _symbol(
    name: str,
    category: str,
    summary: str,
    *,
    signatures: tuple[str, ...] = (),
    parameters: tuple[URScriptParameter, ...] = (),
    example: str | None = None,
    detail: str | None = None,
    docs_section: str | None = None,
    insert_text: str | None = None,
) -> URScriptSymbol:
    return URScriptSymbol(
        name=name,
        category=category,
        summary=summary,
        signatures=signatures,
        parameters=parameters,
        example=example,
        detail=detail,
        docs_section=docs_section,
        insert_text=insert_text,
    )


URSCRIPT_SYMBOLS: tuple[URScriptSymbol, ...] = (
    _symbol(
        "def",
        "keyword",
        "定义函数块，块体必须以 end 显式闭合。",
        example="def main():\n  textmsg(\"start\")\nend",
        docs_section="语法基础",
    ),
    _symbol(
        "thread",
        "keyword",
        "定义线程块，线程不能带参数，返回值会被忽略。",
        example="thread watchdog():\n  sync()\nend",
        detail="线程循环里通常要配合 sync() 或 sleep() 主动让出控制周期。",
        docs_section="作用域与线程",
    ),
    _symbol(
        "sec",
        "keyword",
        "定义 secondary program，适合轻量 I/O 辅助逻辑。",
        example="sec io_helper():\n  set_digital_out(0, True)\nend",
        detail="sec 中不应使用 move、sleep、线程或阻塞式 RPC/socket 逻辑。",
        docs_section="作用域与线程",
    ),
    _symbol("end", "keyword", "结束当前块。", docs_section="语法基础"),
    _symbol("if", "keyword", "条件分支入口。", docs_section="语法基础"),
    _symbol("elif", "keyword", "追加条件分支。", docs_section="语法基础"),
    _symbol("else", "keyword", "条件分支兜底路径。", docs_section="语法基础"),
    _symbol("while", "keyword", "条件循环，常与 sync()/sleep() 配合使用。", docs_section="语法基础"),
    _symbol("for", "keyword", "范围循环。", docs_section="语法基础"),
    _symbol("break", "keyword", "提前跳出当前循环。", docs_section="语法基础"),
    _symbol("continue", "keyword", "跳过本轮循环剩余逻辑。", docs_section="语法基础"),
    _symbol("return", "keyword", "从函数返回结果；无结果时常显式返回 None。", docs_section="语法基础"),
    _symbol("run", "keyword", "启动线程并返回线程句柄。", example="th = run watchdog()", docs_section="作用域与线程"),
    _symbol("join", "keyword", "等待指定线程结束。", example="join th", docs_section="作用域与线程"),
    _symbol("kill", "keyword", "终止指定线程及其子线程。", example="kill th", docs_section="作用域与线程"),
    _symbol("enter_critical", "keyword", "进入临界区保护共享状态。", docs_section="作用域与线程"),
    _symbol("exit_critical", "keyword", "离开临界区。", docs_section="作用域与线程"),
    _symbol("halt", "keyword", "立即停止程序执行；机器人运动中使用风险较高。", docs_section="语法基础"),
    _symbol("pause", "keyword", "暂停程序执行。", docs_section="语法基础"),
    _symbol("and", "keyword", "布尔与运算。", docs_section="语法基础"),
    _symbol("or", "keyword", "布尔或运算。", docs_section="语法基础"),
    _symbol("not", "keyword", "布尔非运算。", docs_section="语法基础"),
    _symbol("xor", "keyword", "布尔异或运算。", docs_section="语法基础"),
    _symbol("global", "type", "显式定义或绑定全局变量。", docs_section="作用域与线程"),
    _symbol("local", "type", "显式定义局部变量。", docs_section="作用域与线程"),
    _symbol("True", "type", "布尔真值。", docs_section="语法基础"),
    _symbol("False", "type", "布尔假值。", docs_section="语法基础"),
    _symbol("None", "type", "空值/无返回值占位。", docs_section="语法基础"),
    _symbol(
        "movej",
        "motion",
        "关节空间运动，适合大姿态切换、快速到位和避障过渡。",
        signatures=("movej(q, a = 1.4, v = 1.05, t = 0, r = 0)",),
        parameters=(
            _param("q", "目标关节角列表，也可以是控制器可求解 IK 的 pose。"),
            _param("a", "关节加速度。", "1.4"),
            _param("v", "关节速度。", "1.05"),
            _param("t", "指定动作时长；非 0 时会覆盖速度规划。", "0"),
            _param("r", "blend 半径，用于路径拼接。", "0"),
        ),
        example="movej([0, -1.57, 1.57, -1.57, -1.57, 0], a = 1.0, v = 1.0)",
        docs_section="运动指令",
    ),
    _symbol(
        "movel",
        "motion",
        "TCP 直线运动，打印、点胶和轨迹跟随最常用。",
        signatures=("movel(pose, a = 1.2, v = 0.25, t = 0, r = 0)",),
        parameters=(
            _param("pose", "目标 TCP pose。"),
            _param("a", "笛卡尔加速度。", "1.2"),
            _param("v", "TCP 线速度。", "0.25"),
            _param("t", "指定动作时长。", "0"),
            _param("r", "blend 半径。", "0"),
        ),
        example="movel(p[0.30, 0.10, 0.25, 0, 3.14159, 0], a = 0.5, v = 0.05)",
        docs_section="运动指令",
    ),
    _symbol(
        "movep",
        "motion",
        "平滑路径运动，适合速度连续性要求更高的工艺段。",
        signatures=("movep(pose, a = 1.2, v = 0.25, r = 0)",),
        parameters=(
            _param("pose", "目标 TCP pose。"),
            _param("a", "笛卡尔加速度。", "1.2"),
            _param("v", "TCP 线速度。", "0.25"),
            _param("r", "blend 半径。", "0"),
        ),
        docs_section="运动指令",
    ),
    _symbol(
        "movec",
        "motion",
        "圆弧运动，使用经过点和终点共同定义轨迹。",
        signatures=("movec(pose_via, pose_to, a = 1.2, v = 0.25, r = 0, mode = 0)",),
        parameters=(
            _param("pose_via", "圆弧经过点。"),
            _param("pose_to", "圆弧终点。"),
            _param("a", "笛卡尔加速度。", "1.2"),
            _param("v", "TCP 线速度。", "0.25"),
            _param("r", "blend 半径。", "0"),
            _param("mode", "圆弧模式参数。", "0"),
        ),
        detail="离线回放时不要把 movec 简化成两段直线。",
        docs_section="运动指令",
    ),
    _symbol(
        "servoj",
        "motion",
        "高频关节伺服，常用于外部实时控制。",
        signatures=("servoj(q, a, v, t = 0.002, lookahead_time = 0.1, gain = 300)",),
        parameters=(
            _param("q", "目标关节角列表。"),
            _param("a", "关节加速度。"),
            _param("v", "关节速度。"),
            _param("t", "控制步长。", "0.002"),
            _param("lookahead_time", "前瞻时间。", "0.1"),
            _param("gain", "伺服增益。", "300"),
        ),
        docs_section="运动指令",
    ),
    _symbol(
        "servoc",
        "motion",
        "对笛卡尔目标进行伺服式控制。",
        signatures=("servoc(pose, a = 1.2, v = 0.25, r = 0)",),
        parameters=(
            _param("pose", "目标 TCP pose。"),
            _param("a", "笛卡尔加速度。", "1.2"),
            _param("v", "TCP 线速度。", "0.25"),
            _param("r", "blend 半径。", "0"),
        ),
        docs_section="运动指令",
    ),
    _symbol(
        "speedj",
        "motion",
        "直接给关节速度向量，按持续时间展开执行。",
        signatures=("speedj(qd, a, t)",),
        parameters=(
            _param("qd", "关节速度向量。"),
            _param("a", "关节加速度。"),
            _param("t", "速度维持时间。"),
        ),
        docs_section="运动指令",
    ),
    _symbol(
        "speedl",
        "motion",
        "直接给 TCP 速度向量，适合短时速度控制。",
        signatures=("speedl(xd, a, t, aRot = a)",),
        parameters=(
            _param("xd", "[vx, vy, vz, wx, wy, wz] 形式的 TCP 速度向量。"),
            _param("a", "平移加速度。"),
            _param("t", "速度维持时间。"),
            _param("aRot", "旋转方向相关参数。", "a"),
        ),
        detail="speedl/speedj 是速度命令，不是瞬间跳到终点的位姿命令。",
        docs_section="运动指令",
    ),
    _symbol(
        "stopj",
        "motion",
        "让关节速度控制或伺服动作平稳停止。",
        signatures=("stopj(a)",),
        parameters=(_param("a", "关节减速度。"),),
        docs_section="运动指令",
    ),
    _symbol(
        "stopl",
        "motion",
        "让笛卡尔速度控制或伺服动作平稳停止。",
        signatures=("stopl(a, aRot = a)",),
        parameters=(
            _param("a", "平移减速度。"),
            _param("aRot", "旋转方向相关参数。", "a"),
        ),
        docs_section="运动指令",
    ),
    _symbol("teach_mode", "motion", "进入示教模式。"),
    _symbol("end_teach_mode", "motion", "退出示教模式。"),
    _symbol("force_mode", "force", "进入力控模式。"),
    _symbol("end_force_mode", "force", "退出力控模式。"),
    _symbol("freedrive_mode", "motion", "进入自由驱动/拖动示教模式。"),
    _symbol("end_freedrive_mode", "motion", "退出自由驱动模式。"),
    _symbol(
        "set_tcp",
        "robot",
        "设置 TCP 偏置，对打印、点胶、焊接和探针测量都很关键。",
        signatures=(
            "set_tcp(p[0, 0, 0.12, 0, 0, 0])",
            "set_tcp(p[0, 0, 0.12, 0, 0, 0], tcp_name = \"nozzle\")",
        ),
        parameters=(
            _param("tcp", "TCP pose 偏置。"),
            _param("tcp_name", "可选 TCP 名称。", "\"nozzle\""),
        ),
        example="set_tcp(p[0, 0, 0.12, 0, 0, 0])",
        docs_section="系统、I/O 与 RPC",
    ),
    _symbol(
        "set_payload",
        "robot",
        "设置工具负载，可选同时指定重心。",
        signatures=("set_payload(mass, cog)",),
        parameters=(
            _param("mass", "负载质量。"),
            _param("cog", "重心位置 pose/list。"),
        ),
    ),
    _symbol("set_payload_mass", "robot", "单独设置工具负载质量。", signatures=("set_payload_mass(mass)",)),
    _symbol("set_payload_cog", "robot", "单独设置工具负载重心。", signatures=("set_payload_cog(cog)",)),
    _symbol("set_gravity", "robot", "设置重力方向向量。", signatures=("set_gravity(d)",)),
    _symbol("set_target_payload", "robot", "设置目标负载参数。"),
    _symbol(
        "get_actual_tcp_pose",
        "robot",
        "读取当前实际 TCP pose。",
        signatures=("get_actual_tcp_pose()",),
        docs_section="系统、I/O 与 RPC",
    ),
    _symbol(
        "get_actual_tool_flange_pose",
        "robot",
        "读取当前法兰 pose，可用于区分法兰与 TCP 坐标。",
        signatures=("get_actual_tool_flange_pose()",),
        docs_section="系统、I/O 与 RPC",
    ),
    _symbol(
        "get_target_tcp_pose",
        "robot",
        "读取当前规划目标 TCP pose。",
        signatures=("get_target_tcp_pose()",),
    ),
    _symbol("get_actual_tcp_speed", "robot", "读取当前实际 TCP 速度。", signatures=("get_actual_tcp_speed()",)),
    _symbol("get_target_tcp_speed", "robot", "读取当前规划目标 TCP 速度。", signatures=("get_target_tcp_speed()",)),
    _symbol(
        "get_actual_joint_positions",
        "robot",
        "读取当前实际关节角。",
        signatures=("get_actual_joint_positions()",),
        docs_section="系统、I/O 与 RPC",
    ),
    _symbol(
        "get_target_joint_positions",
        "robot",
        "读取当前规划目标关节角。",
        signatures=("get_target_joint_positions()",),
        docs_section="系统、I/O 与 RPC",
    ),
    _symbol("get_actual_joint_speeds", "robot", "读取当前实际关节速度。", signatures=("get_actual_joint_speeds()",)),
    _symbol("get_target_joint_speeds", "robot", "读取当前规划目标关节速度。", signatures=("get_target_joint_speeds()",)),
    _symbol("get_actual_joint_positions_history", "robot", "读取历史关节位置记录。"),
    _symbol("get_actual_joint_speeds_history", "robot", "读取历史关节速度记录。"),
    _symbol("get_joint_torques", "robot", "读取关节力矩。", signatures=("get_joint_torques()",)),
    _symbol("get_tcp_offset", "robot", "读取当前 TCP 偏置。", signatures=("get_tcp_offset()",)),
    _symbol("get_controller_temp", "robot", "读取控制器温度。"),
    _symbol("get_joint_temp", "robot", "读取关节温度。"),
    _symbol("get_robot_mode", "robot", "读取机器人模式。"),
    _symbol("get_safety_mode", "robot", "读取安全模式。"),
    _symbol("get_program_state", "robot", "读取程序执行状态。"),
    _symbol("power_on", "robot", "上电机器人。"),
    _symbol("power_off", "robot", "下电机器人。"),
    _symbol("powerdown", "robot", "关闭控制器。"),
    _symbol("protective_stop", "robot", "触发保护停机。"),
    _symbol("unlock_protective_stop", "robot", "解除保护停机。"),
    _symbol("is_within_safety_limits", "robot", "判断目标是否处于安全限制范围内。"),
    _symbol("is_steady", "robot", "判断机器人是否处于静稳状态。"),
    _symbol(
        "pose_trans",
        "pose",
        "做位姿复合，最适合在 feature 坐标系下生成目标点。",
        signatures=("pose_trans(p_from, p_from_to)",),
        parameters=(
            _param("p_from", "基准 pose。"),
            _param("p_from_to", "相对于基准 pose 的增量 pose。"),
        ),
        example="target = pose_trans(feature, local_target)",
        docs_section="位姿与数学",
    ),
    _symbol(
        "pose_add",
        "pose",
        "做简化位姿叠加。",
        signatures=("pose_add(p1, p2)",),
        parameters=(
            _param("p1", "第一个 pose。"),
            _param("p2", "第二个 pose。"),
        ),
        detail="pose_add 不等同于严格的 SE(3) 乘法语义。",
        docs_section="位姿与数学",
    ),
    _symbol(
        "pose_sub",
        "pose",
        "求两个位姿之间的差。",
        signatures=("pose_sub(p_to, p_from)",),
        parameters=(
            _param("p_to", "目标 pose。"),
            _param("p_from", "起始 pose。"),
        ),
        docs_section="位姿与数学",
    ),
    _symbol(
        "pose_inv",
        "pose",
        "求位姿逆变换。",
        signatures=("pose_inv(p)",),
        parameters=(_param("p", "待求逆的 pose。"),),
        docs_section="位姿与数学",
    ),
    _symbol(
        "pose_dist",
        "pose",
        "计算两个 pose 之间的位姿距离。",
        signatures=("pose_dist(p1, p2)",),
        parameters=(
            _param("p1", "第一个 pose。"),
            _param("p2", "第二个 pose。"),
        ),
        docs_section="位姿与数学",
    ),
    _symbol(
        "point_dist",
        "math",
        "计算两个 pose/点的位置距离。",
        signatures=("point_dist(p1, p2)",),
        parameters=(
            _param("p1", "第一个点或 pose。"),
            _param("p2", "第二个点或 pose。"),
        ),
        docs_section="位姿与数学",
    ),
    _symbol(
        "interpolate_pose",
        "pose",
        "在两个 pose 之间按比例插值。",
        signatures=("interpolate_pose(p_from, p_to, alpha)",),
        parameters=(
            _param("p_from", "起始 pose。"),
            _param("p_to", "目标 pose。"),
            _param("alpha", "插值比例，通常在 0 到 1 之间。"),
        ),
        docs_section="位姿与数学",
    ),
    _symbol(
        "get_forward_kin",
        "pose",
        "读取正运动学结果，可用于和自写 FK 做误差对比。",
        signatures=("get_forward_kin()", "get_forward_kin(q)"),
        parameters=(_param("q", "可选关节角列表；不传时使用当前关节状态。"),),
        docs_section="位姿与数学",
    ),
    _symbol(
        "get_inverse_kin",
        "pose",
        "求目标 pose 的逆运动学解。",
        signatures=("get_inverse_kin(pose)",),
        parameters=(_param("pose", "目标 TCP pose。"),),
        docs_section="位姿与数学",
    ),
    _symbol(
        "get_inverse_kin_has_solution",
        "pose",
        "判断某个位姿是否存在 IK 解。",
        signatures=("get_inverse_kin_has_solution(pose)",),
        parameters=(_param("pose", "目标 TCP pose。"),),
        docs_section="位姿与数学",
    ),
    _symbol(
        "p",
        "pose",
        "pose 字面量前缀，写法为 p[x, y, z, ax, ay, az]。",
        signatures=("p[x, y, z, ax, ay, az]",),
        detail="后三项是轴角旋转向量，不是欧拉角。",
        docs_section="位姿与数学",
    ),
    _symbol("rpy2rotvec", "pose", "将 RPY 角转换为轴角旋转向量。"),
    _symbol("rotvec2rpy", "pose", "将轴角旋转向量转换为 RPY。"),
    _symbol("sin", "math", "正弦函数。", signatures=("sin(x)",)),
    _symbol("cos", "math", "余弦函数。", signatures=("cos(x)",)),
    _symbol("tan", "math", "正切函数。", signatures=("tan(x)",)),
    _symbol("asin", "math", "反正弦函数。", signatures=("asin(x)",)),
    _symbol("acos", "math", "反余弦函数。", signatures=("acos(x)",)),
    _symbol("atan", "math", "反正切函数。", signatures=("atan(x)",)),
    _symbol("atan2", "math", "双参数反正切，常用于平面方向计算。", signatures=("atan2(y, x)",)),
    _symbol("sqrt", "math", "平方根。", signatures=("sqrt(x)",)),
    _symbol("pow", "math", "幂运算。", signatures=("pow(x, y)",)),
    _symbol("log", "math", "对数函数。", signatures=("log(x)",)),
    _symbol("exp", "math", "指数函数。", signatures=("exp(x)",)),
    _symbol("abs", "math", "绝对值。", signatures=("abs(x)",)),
    _symbol("ceil", "math", "向上取整。", signatures=("ceil(x)",)),
    _symbol("floor", "math", "向下取整。", signatures=("floor(x)",)),
    _symbol("round", "math", "四舍五入。", signatures=("round(x)",)),
    _symbol("norm", "math", "计算向量范数。", signatures=("norm(v)",)),
    _symbol("normalize", "math", "归一化向量。", signatures=("normalize(v)",)),
    _symbol(
        "length",
        "math",
        "获取向量长度；在容器方法上下文中也常表示 list.length()。",
        signatures=("length(v)",),
        docs_section="位姿与数学",
    ),
    _symbol("d2r", "math", "角度转弧度。", signatures=("d2r(d)",)),
    _symbol("r2d", "math", "弧度转角度。", signatures=("r2d(r)",)),
    _symbol("random", "math", "生成随机数。"),
    _symbol("binary_list_to_integer", "math", "将二进制列表转换为整数。"),
    _symbol("integer_to_binary_list", "math", "将整数转换为二进制列表。"),
    _symbol(
        "sleep",
        "runtime",
        "按秒休眠，是线程循环里最常见的让步方式之一。",
        signatures=("sleep(t)",),
        parameters=(_param("t", "休眠秒数。"),),
        example="sleep(0.1)",
        docs_section="系统、I/O 与 RPC",
    ),
    _symbol(
        "sync",
        "runtime",
        "同步到控制器周期，让当前线程把时间片还给实时循环。",
        signatures=("sync()",),
        detail="纯计算死循环里建议显式加 sync() 或 sleep()，避免实时超时。",
        docs_section="系统、I/O 与 RPC",
    ),
    _symbol(
        "textmsg",
        "runtime",
        "输出调试文本到控制器日志。",
        signatures=("textmsg(value_1, value_2, ...)",),
        example="textmsg(\"state\", value)",
        docs_section="系统、I/O 与 RPC",
    ),
    _symbol(
        "popup",
        "runtime",
        "弹出现场提示信息，适合人工干预节点。",
        signatures=("popup(message, title = \"warning\")",),
        parameters=(
            _param("message", "弹窗正文。"),
            _param("title", "弹窗标题。", "\"warning\""),
        ),
        example="popup(\"Check nozzle\", title = \"warning\")",
        docs_section="系统、I/O 与 RPC",
    ),
    _symbol(
        "rpc_factory",
        "runtime",
        "创建 RPC 客户端句柄，常用于视觉、外部规划或数据库查询。",
        signatures=("rpc_factory(\"xmlrpc\", \"http://127.0.0.1/RPC2\")",),
        parameters=(
            _param("protocol", "RPC 协议类型，例如 xmlrpc。"),
            _param("url", "远端 RPC 服务地址。"),
        ),
        example="camera = rpc_factory(\"xmlrpc\", \"http://127.0.0.1/RPC2\")",
        detail="阻塞式 RPC 不要放进 sec，也不要在高频线程里无节制调用。",
        docs_section="系统、I/O 与 RPC",
    ),
    _symbol("str_at", "runtime", "读取字符串指定位置的字节。"),
    _symbol("str_cat", "runtime", "拼接字符串。"),
    _symbol("str_empty", "runtime", "判断字符串是否为空。"),
    _symbol("str_find", "runtime", "查找字符串片段。"),
    _symbol("str_len", "runtime", "按字节长度获取字符串长度。"),
    _symbol("str_sub", "runtime", "截取字符串片段。"),
    _symbol("to_str", "runtime", "将值转换为字符串。"),
    _symbol(
        "set_digital_out",
        "io",
        "设置数字量输出。",
        signatures=("set_digital_out(output_id, value)",),
        parameters=(
            _param("output_id", "输出通道编号。"),
            _param("value", "True/False 输出值。"),
        ),
        example="set_digital_out(0, True)",
        docs_section="系统、I/O 与 RPC",
    ),
    _symbol(
        "get_digital_in",
        "io",
        "读取数字量输入。",
        signatures=("get_digital_in(input_id)",),
        parameters=(_param("input_id", "输入通道编号。"),),
        docs_section="系统、I/O 与 RPC",
    ),
    _symbol(
        "set_analog_out",
        "io",
        "设置模拟量输出。",
        signatures=("set_analog_out(output_id, value)",),
        parameters=(
            _param("output_id", "输出通道编号。"),
            _param("value", "模拟量输出值。"),
        ),
        docs_section="系统、I/O 与 RPC",
    ),
    _symbol(
        "get_analog_in",
        "io",
        "读取模拟量输入。",
        signatures=("get_analog_in(input_id)",),
        parameters=(_param("input_id", "输入通道编号。"),),
        docs_section="系统、I/O 与 RPC",
    ),
    _symbol("set_standard_digital_out", "io", "设置标准数字量输出。", signatures=("set_standard_digital_out(output_id, value)",)),
    _symbol("set_tool_digital_out", "io", "设置工具端数字量输出。", signatures=("set_tool_digital_out(output_id, value)",)),
    _symbol("set_configurable_digital_out", "io", "设置可配置数字量输出。", signatures=("set_configurable_digital_out(output_id, value)",)),
    _symbol("get_standard_digital_in", "io", "读取标准数字量输入。", signatures=("get_standard_digital_in(input_id)",)),
    _symbol("get_tool_digital_in", "io", "读取工具端数字量输入。", signatures=("get_tool_digital_in(input_id)",)),
    _symbol("get_configurable_digital_in", "io", "读取可配置数字量输入。", signatures=("get_configurable_digital_in(input_id)",)),
    _symbol("set_standard_analog_out", "io", "设置标准模拟量输出。", signatures=("set_standard_analog_out(output_id, value)",)),
    _symbol("set_tool_analog_out", "io", "设置工具端模拟量输出。", signatures=("set_tool_analog_out(output_id, value)",)),
    _symbol("get_standard_analog_in", "io", "读取标准模拟量输入。", signatures=("get_standard_analog_in(input_id)",)),
    _symbol("get_tool_analog_in", "io", "读取工具端模拟量输入。", signatures=("get_tool_analog_in(input_id)",)),
    _symbol("set_flag", "io", "设置标志位。"),
    _symbol("get_flag", "io", "读取标志位。"),
    _symbol(
        "modbus_set_output_register",
        "io",
        "写入 Modbus 输出寄存器。",
        signatures=("modbus_set_output_register(signal_name, value)",),
        parameters=(
            _param("signal_name", "Modbus 信号名或寄存器标识。"),
            _param("value", "要写入的值。"),
        ),
    ),
    _symbol("modbus_get_signal_status", "io", "读取 Modbus 信号状态。", signatures=("modbus_get_signal_status(signal_name)",)),
    _symbol("modbus_set_output_signal", "io", "写入 Modbus 输出信号。"),
    _symbol("modbus_set_signal_update_frequency", "io", "设置 Modbus 信号刷新频率。"),
    _symbol("modbus_add_signal", "io", "注册 Modbus 信号。"),
    _symbol("modbus_delete_signal", "io", "删除 Modbus 信号。"),
    _symbol(
        "socket_open",
        "io",
        "打开 socket 连接。",
        signatures=("socket_open(host, port, socket_name)",),
        parameters=(
            _param("host", "目标主机地址。"),
            _param("port", "目标端口。"),
            _param("socket_name", "连接名称。"),
        ),
    ),
    _symbol("socket_close", "io", "关闭 socket 连接。", signatures=("socket_close(socket_name)",)),
    _symbol("socket_send_string", "io", "通过 socket 发送字符串。", signatures=("socket_send_string(value, socket_name)",)),
    _symbol("socket_send_byte", "io", "通过 socket 发送单字节。"),
    _symbol("socket_send_int", "io", "通过 socket 发送整数。"),
    _symbol("socket_send_line", "io", "通过 socket 发送带换行的一行文本。", signatures=("socket_send_line(value, socket_name)",)),
    _symbol("socket_read_byte_list", "io", "通过 socket 读取字节列表。"),
    _symbol("socket_read_ascii_float", "io", "通过 socket 读取 ASCII 浮点数。"),
    _symbol("socket_read_binary_integer", "io", "通过 socket 读取二进制整数。"),
    _symbol("socket_read_string", "io", "通过 socket 读取字符串。"),
    _symbol("socket_get_var", "io", "读取 socket 侧变量值。"),
    _symbol(
        "struct",
        "container",
        "创建 struct 容器，成员名来自命名参数。",
        signatures=("struct(field = value, ...)",),
        example="part = struct(id = 1, name = \"bolt\", ok = True)",
        docs_section="语法基础",
    ),
    _symbol(
        "make_list",
        "container",
        "创建可变长度 list，同时指定当前长度和容量。",
        signatures=("make_list(length, initial_value, capacity)",),
        parameters=(
            _param("length", "当前长度。"),
            _param("initial_value", "初始填充值。"),
            _param("capacity", "最大容量。"),
        ),
        example="b = make_list(length = 7, initial_value = 11, capacity = 20)",
        docs_section="语法基础",
    ),
    _symbol("append", "container", "向 list 末尾追加元素。", signatures=("append(element)",)),
    _symbol("extend", "container", "用另一个 list 扩展当前 list。", signatures=("extend(list)",)),
    _symbol("insert", "container", "在指定位置插入元素。", signatures=("insert(index, element)",)),
    _symbol("pop", "container", "弹出末尾元素。", signatures=("pop()",)),
    _symbol("remove", "container", "删除指定位置元素。", signatures=("remove(index)",)),
    _symbol("clear", "container", "清空容器。", signatures=("clear()",)),
    _symbol("capacity", "container", "返回 list 容量上限。", signatures=("capacity()",)),
    _symbol("excess_capacity", "container", "返回容器剩余容量。", signatures=("excess_capacity()",)),
    _symbol("slice", "container", "截取容器片段。", signatures=("slice(begin, end)",)),
    _symbol("to_string", "container", "把容器格式化为字符串。", signatures=("to_string()",)),
    _symbol("get_row", "container", "读取矩阵指定行。", signatures=("get_row(index)",)),
    _symbol("get_column", "container", "读取矩阵指定列。", signatures=("get_column(index)",)),
    _symbol("shape", "container", "读取矩阵形状。", signatures=("shape()",)),
    _symbol("conveyor_pulse_decode", "runtime", "配置传送带脉冲解码。"),
    _symbol("encoder_enable_pulse_decode", "runtime", "启用编码器脉冲解码。"),
    _symbol("encoder_get_tick_count", "runtime", "读取编码器 tick 计数。"),
    _symbol("encoder_set_tick_count", "runtime", "设置编码器 tick 计数。"),
    _symbol("encoder_unwind_delta_tick_count", "runtime", "回卷编码器 tick 增量。"),
    _symbol("stop_conveyor_tracking", "runtime", "停止传送带跟踪。"),
    _symbol("conveyor_tracking", "runtime", "启用传送带跟踪。"),
    _symbol("force", "force", "读取或构造力/力矩向量。"),
    _symbol("get_tcp_force", "force", "读取当前 TCP 受力。", signatures=("get_tcp_force()",)),
    _symbol("zero_ftsensor", "force", "将力传感器清零。"),
    _symbol("tool_contact", "force", "检测工具接触。"),
    _symbol("tool_contact_ex", "force", "扩展版工具接触检测。"),
)

URSCRIPT_CATEGORY_SETS: dict[str, frozenset[str]] = {}
for _symbol_item in URSCRIPT_SYMBOLS:
    URSCRIPT_CATEGORY_SETS.setdefault(_symbol_item.category, set()).add(_symbol_item.name)
URSCRIPT_CATEGORY_SETS = {
    category: frozenset(sorted(names))
    for category, names in URSCRIPT_CATEGORY_SETS.items()
}

URSCRIPT_KEYWORDS = URSCRIPT_CATEGORY_SETS.get("keyword", frozenset())
URSCRIPT_TYPES = URSCRIPT_CATEGORY_SETS.get("type", frozenset())
URSCRIPT_MOTION_COMMANDS = URSCRIPT_CATEGORY_SETS.get("motion", frozenset())
URSCRIPT_IO_COMMANDS = URSCRIPT_CATEGORY_SETS.get("io", frozenset())
URSCRIPT_ROBOT_COMMANDS = URSCRIPT_CATEGORY_SETS.get("robot", frozenset())
URSCRIPT_MATH_FUNCTIONS = URSCRIPT_CATEGORY_SETS.get("math", frozenset())
URSCRIPT_POSE_FUNCTIONS = URSCRIPT_CATEGORY_SETS.get("pose", frozenset())
URSCRIPT_FORCE_COMMANDS = URSCRIPT_CATEGORY_SETS.get("force", frozenset())
URSCRIPT_RUNTIME_COMMANDS = URSCRIPT_CATEGORY_SETS.get("runtime", frozenset())
URSCRIPT_CONTAINER_FUNCTIONS = URSCRIPT_CATEGORY_SETS.get("container", frozenset())

URSCRIPT_SYMBOL_INDEX = {symbol.name: symbol for symbol in URSCRIPT_SYMBOLS}
ALL_URSCRIPT_COMMANDS = frozenset(URSCRIPT_SYMBOL_INDEX)

URSCRIPT_SNIPPETS: tuple[str, ...] = (
    "def main():\n  textmsg(\"start\")\nend",
    "thread watchdog():\n  while True:\n    sync()\n  end\nend",
    "sec io_helper():\n  set_digital_out(0, True)\nend",
    "if condition:\n  # code\nend",
    "while condition:\n  sync()\nend",
    "movej([j0, j1, j2, j3, j4, j5], a = 1.4, v = 1.05)",
    "movel(p[x, y, z, rx, ry, rz], a = 1.2, v = 0.25)",
    "camera = rpc_factory(\"xmlrpc\", \"http://127.0.0.1/RPC2\")",
    "target = pose_trans(feature, local_target)",
    "b = make_list(length = 7, initial_value = 0, capacity = 20)",
)

DECLARATION_KEYWORDS = frozenset({"def", "thread", "sec"})


def get_urscript_symbol(name: str) -> URScriptSymbol | None:
    return URSCRIPT_SYMBOL_INDEX.get(name)


def get_urscript_completions() -> list[str]:
    seen: set[str] = set()
    completions: list[str] = []
    for item in sorted(ALL_URSCRIPT_COMMANDS):
        if item not in seen:
            completions.append(item)
            seen.add(item)
    for snippet in URSCRIPT_SNIPPETS:
        if snippet not in seen:
            completions.append(snippet)
            seen.add(snippet)
    return completions


def format_symbol_help(name: str) -> str:
    symbol = get_urscript_symbol(name)
    if symbol is None:
        return ""

    lines: list[str] = []
    if symbol.signatures:
        lines.extend(symbol.signatures[:2])
    else:
        lines.append(symbol.name)

    lines.append(f"用途: {symbol.summary}")
    if symbol.detail:
        lines.append(symbol.detail)

    if symbol.parameters:
        lines.append("参数:")
        for parameter in symbol.parameters:
            lines.append(f"- {parameter.display_name}: {parameter.description}")

    if symbol.example:
        lines.append(f"写法: {symbol.example}")
    if symbol.docs_section:
        lines.append(f"专题: {symbol.docs_section}")
    return "\n".join(lines)


def format_call_tip(name: str, arg_index: int) -> str:
    symbol = get_urscript_symbol(name)
    if symbol is None or not symbol.signatures:
        return ""

    lines = list(symbol.signatures[:2])
    lines.append(f"用途: {symbol.summary}")

    if symbol.parameters:
        if 0 <= arg_index < len(symbol.parameters):
            parameter = symbol.parameters[arg_index]
            lines.append(
                f"当前参数 {arg_index + 1}/{len(symbol.parameters)}: "
                f"{parameter.display_name} - {parameter.description}"
            )
        else:
            lines.append(
                f"当前参数 {arg_index + 1}: 已超出常用位置参数范围，请检查是否在使用命名参数。"
            )

    return "\n".join(lines)


def line_index_to_offset(text: str, line: int, index: int) -> int:
    if line <= 0:
        return max(0, index)

    offset = 0
    current_line = 0
    text_length = len(text)
    while offset < text_length and current_line < line:
        if text[offset] == "\n":
            current_line += 1
        offset += 1
    return min(text_length, offset + max(0, index))


def identifier_at_offset(text: str, offset: int) -> str | None:
    if not text:
        return None

    candidate = None
    if 0 <= offset < len(text) and _is_identifier_char(text[offset]):
        candidate = offset
    elif 0 < offset <= len(text) and _is_identifier_char(text[offset - 1]):
        candidate = offset - 1

    if candidate is None:
        return None

    start = candidate
    while start > 0 and _is_identifier_char(text[start - 1]):
        start -= 1

    end = candidate + 1
    while end < len(text) and _is_identifier_char(text[end]):
        end += 1

    word = text[start:end]
    if not word or word[0].isdigit():
        return None
    return word


def find_call_context(text: str, cursor_offset: int) -> URScriptCallContext | None:
    cursor_offset = max(0, min(len(text), cursor_offset))
    stack: list[tuple[str, URScriptCallContext | None]] = []
    in_string = False
    escaped = False
    in_comment = False

    for index in range(cursor_offset):
        ch = text[index]

        if in_comment:
            if ch == "\n":
                in_comment = False
            continue

        if in_string:
            if escaped:
                escaped = False
                continue
            if ch == "\\":
                escaped = True
                continue
            if ch == '"':
                in_string = False
            continue

        if ch == "#":
            in_comment = True
            continue

        if ch == '"':
            in_string = True
            continue

        if ch == "(":
            name = _callable_name_before(text, index)
            if name is None:
                stack.append(("paren", None))
            else:
                stack.append(("paren", URScriptCallContext(name=name, arg_index=0, open_offset=index)))
            continue

        if ch == "[":
            stack.append(("bracket", None))
            continue

        if ch == "{":
            stack.append(("brace", None))
            continue

        if ch == "," and stack:
            scope_type, current = stack[-1]
            if scope_type == "paren" and current is not None:
                stack[-1] = ("paren", URScriptCallContext(
                    name=current.name,
                    arg_index=current.arg_index + 1,
                    open_offset=current.open_offset,
                ))
            continue

        if ch == ")" and stack:
            while stack:
                scope_type, _context = stack.pop()
                if scope_type == "paren":
                    break
            continue

        if ch == "]" and stack:
            while stack:
                scope_type, _context = stack.pop()
                if scope_type == "bracket":
                    break
            continue

        if ch == "}" and stack:
            while stack:
                scope_type, _context = stack.pop()
                if scope_type == "brace":
                    break
            continue

    for scope_type, context in reversed(stack):
        if scope_type == "paren" and context is not None:
            return context
    return None


def _callable_name_before(text: str, open_index: int) -> str | None:
    cursor = open_index - 1
    while cursor >= 0 and text[cursor].isspace():
        cursor -= 1

    if cursor < 0 or not _is_identifier_char(text[cursor]):
        return None

    end = cursor + 1
    while cursor >= 0 and (_is_identifier_char(text[cursor]) or text[cursor] == "."):
        cursor -= 1

    expression = text[cursor + 1:end]
    if not expression:
        return None

    name = expression.split(".")[-1]
    if not name or name[0].isdigit():
        return None

    previous = _previous_identifier(text, cursor)
    if previous in DECLARATION_KEYWORDS:
        return None

    return name


def _previous_identifier(text: str, cursor: int) -> str | None:
    while cursor >= 0 and text[cursor].isspace():
        cursor -= 1
    if cursor < 0 or not _is_identifier_char(text[cursor]):
        return None

    end = cursor + 1
    while cursor >= 0 and _is_identifier_char(text[cursor]):
        cursor -= 1
    word = text[cursor + 1:end]
    if not word or word[0].isdigit():
        return None
    return word


def _is_identifier_char(ch: str) -> bool:
    return ch.isalnum() or ch == "_"
