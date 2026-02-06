from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QListWidget,
                              QStackedWidget, QTextBrowser, QDialogButtonBox, QFrame)
from PyQt6.QtCore import Qt
from ur_print_fdm.ui import theme

class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("UR5 Fiber Printer Studio - 技术说明文档中心")
        # Phase D 优化: 使用相对尺寸，基于父窗口大小自适应
        if parent:
            parent_size = parent.size()
            self.resize(int(parent_size.width() * 0.75), int(parent_size.height() * 0.8))
        else:
            self.resize(900, 650)
        self.setMinimumSize(700, 500)  # 设置合理的最小尺寸
        self._browsers = []
        self._page_html_getters = [
            self._get_user_guide_html,
            self._get_process_script_html,
            self._get_hardware_protocol_html,
            self._get_developer_api_html,
        ]
        self._init_ui()
        self.apply_theme()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)

        # 水平布局：左侧导航 + 右侧内容
        content_layout = QHBoxLayout()

        # 左侧导航栏
        self.nav_list = QListWidget()
        self.nav_list.setFixedWidth(220)
        self.nav_list.addItems([
            "1. 快速入门与操作手册",
            "2. 打印工艺与脚本编写",
            "3. 下位机硬件与协议",
            "4. 软件架构与开发参考"
        ])
        self.nav_list.setObjectName("nav_list")

        # 右侧内容堆叠区
        self.stack = QStackedWidget()
        self._create_pages()

        # 连接信号
        self.nav_list.currentRowChanged.connect(self.stack.setCurrentIndex)

        content_layout.addWidget(self.nav_list)
        content_layout.addWidget(self.stack)

        main_layout.addLayout(content_layout)

        # 底部按钮
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)
        main_layout.addWidget(buttons)

    def _create_pages(self):
        # 模块 A: 快速入门
        page1 = self._create_browser_page(self._get_user_guide_html())
        self.stack.addWidget(page1)

        # 模块 B: 打印工艺
        page2 = self._create_browser_page(self._get_process_script_html())
        self.stack.addWidget(page2)

        # 模块 C: 硬件协议
        page3 = self._create_browser_page(self._get_hardware_protocol_html())
        self.stack.addWidget(page3)

        # 模块 D: 开发参考
        page4 = self._create_browser_page(self._get_developer_api_html())
        self.stack.addWidget(page4)

    def _create_browser_page(self, html_content):
        browser = QTextBrowser()
        browser.setReadOnly(True)
        browser.setOpenExternalLinks(True)
        browser.setHtml(self._get_common_style() + html_content)
        self._browsers.append(browser)
        return browser

    def _get_common_style(self):
        t = theme.current_tokens()
        # Phase C 优化: 使用 bg_panel (纯白) 作为文档背景，与外层 bg_main 形成层次
        return f"""
        <style>
            body {{
                font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
                line-height: 1.7;
                color: {t["text"]};
                background-color: {t["bg_panel"]};
                padding: 5px 15px;
            }}
            h1 {{
                color: {t["accent_link"]};
                border-bottom: 2px solid {t["accent_link"]};
                padding-bottom: 10px;
                margin-top: 10px;
            }}
            h2 {{
                color: {t["accent_blue"]};
                margin-top: 25px;
                border-bottom: 1px solid {t["border_light"]};
                padding-bottom: 6px;
            }}
            h3 {{
                color: {t["text"]};
                margin-top: 15px;
            }}
            a {{ color: {t["accent_link"]}; }}
            code {{
                background-color: {t["bg_tertiary"]};
                color: {t["accent_link"]};
                padding: 2px 6px;
                border-radius: 4px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 0.95em;
            }}
            pre {{
                background-color: {t["bg_tertiary"]};
                padding: 15px;
                border-left: 4px solid {t["accent_link"]};
                border-radius: 4px;
                font-family: 'Consolas', 'Courier New', monospace;
                overflow-x: auto;
            }}
            .tip {{
                background-color: {t["bg_tertiary"]};
                border-left: 4px solid {t["success"]};
                padding: 12px 15px;
                margin: 15px 0;
                border-radius: 0 4px 4px 0;
            }}
            .warning {{
                background-color: {t["bg_tertiary"]};
                border-left: 4px solid {t["danger"]};
                padding: 12px 15px;
                margin: 15px 0;
                border-radius: 0 4px 4px 0;
            }}
            table {{ border-collapse: collapse; width: 100%; margin: 15px 0; }}
            th, td {{ border: 1px solid {t["border"]}; padding: 10px 12px; text-align: left; }}
            th {{ background-color: {t["bg_tertiary"]}; font-weight: 600; }}
            tr:hover {{ background-color: {t["bg_hover"]}; }}
            ul, ol {{ padding-left: 25px; }}
            li {{ margin: 6px 0; }}
        </style>
        """

    def apply_theme(self) -> None:
        """Re-apply themed HTML to all pages on theme change."""
        try:
            common = self._get_common_style()
            getters = list(self._page_html_getters or [])
            for idx, browser in enumerate(self._browsers):
                html = ""
                if idx < len(getters):
                    try:
                        html = str(getters[idx]() or "")
                    except Exception:
                        html = ""
                browser.setHtml(common + html)
        except Exception:
            pass

    def _get_user_guide_html(self):
        return """
        <h1>1. 快速入门与操作手册</h1>
        <p>本手册旨在指导实验室新手快速搭建环境并完成首次 3D 打印任务。</p>

        <h2>1.1 环境搭建</h2>
        <ul>
            <li><b>Python 环境</b>: 建议使用 Python 3.9+。</li>
            <li><b>核心库</b>: 必须安装 <code>ur_rtde</code> (用于机器人通信) 和 <code>PyQt6</code> (用于界面)。</li>
            <pre>pip install ur_rtde PyQt6</pre>
        </ul>

        <h2>1.2 硬件连接步骤</h2>
        <ol>
            <li><b>物理连接</b>: 将电脑、UR 机器人控制箱、Arduino 挤出机通过交换机连接在同一局域网。</li>
            <li><b>IP 配置</b>:
                <ul>
                    <li>机器人默认 IP: <code>192.168.137.120</code></li>
                    <li>电脑 IP 需设为同网段（如 <code>192.168.137.1</code>）。</li>
                </ul>
            </li>
            <li><b>上电顺序</b>: 先启动机器人并进入遥控模式，再运行本 IDE 软件。</li>
        </ol>

        <h2>1.3 标准操作流程</h2>
        <div class="tip">
            <b>第一步：</b> 在左侧资源管理器打开或导入 G-code 文件。<br>
            <b>第二步：</b> 使用“脚本生成”工具将其转换为 URScript。<br>
            <b>第三步：</b> 在工具栏输入 IP，点击“连接”。观察状态栏变为绿色连接状态。<br>
            <b>第四步：</b> 点击“发送脚本”，观察机器人开始运动。
        </div>
        """

    # 核心更新片段预览 (已写入文件)
    def _get_process_script_html(self):
        return """
        <h1>2. 打印工艺与脚本编写深度指南</h1>
        <p>本模块将 PolyScope 界面节点映射为底层 URScript 语法，助你实现精密打印控制。</p>

        <h2>2.1 运动模式对比 (Move Nodes)</h2>
        <table>
            <tr><th>指令</th><th>图形界面映射</th><th>工艺用途</th><th>核心参数</th></tr>
            <tr><td><code>movej</code></td><td>移动 (关节)</td><td>起始点复位、快速空移</td><td>a(加速度), v(速度)</td></tr>
            <tr><td><code>movel</code></td><td>移动 (直线)</td><td>层间跳跃、短距离直线</td><td>确保末端轨迹为直线</td></tr>
            <tr><td><code>movep</code></td><td>向导 (工艺)</td><td><b>主打印路径</b></td><td>r(混合半径): 决定拐角平滑度</td></tr>
        </table>

        <h2>2.3 逻辑与并发控制 (Advanced Nodes)</h2>
        <h3>线程 (Thread) 的妙用</h3>
        <p>在 FDM 打印中，可以使用独立线程实现<b>实时看门狗</b>：</p>
        <pre>
        thread ExtruderWatchdog():
            while True:
                if get_actual_tcp_speed() < 0.001:
                    write_port(502, 3000) # 速度过低自动关停挤出机
                sync()
        run ExtruderWatchdog()
        </pre>

        <h2>2.4 关键数学函数 (Math)</h2>
        <ul>
            <li><code>pose_trans(p_from, p_to)</code>: 坐标系转换。用于将打印路径相对于 Feature 平面进行偏移。</li>
            <li><code>pose_inv(p)</code>: 求逆位姿。用于计算相对移动矢量。</li>
            <li><code>d2r(deg)</code>: 角度转弧度。URScript 内部所有旋转参数均使用弧度制。</li>
        </ul>

        <h2>2.5 向导功能 (Wizards)</h2>
        <p>映射截图中的“向导”选项卡：</p>
        <ul>
            <li><b>托盘 (Pallet)</b>：可用于批量打印小型零件的阵列排布。</li>
            <li><b>力 (Force)</b>：结合力控传感器，可实现喷头对不平整打印平台的自适应贴合（接触力探测）。</li>
            <li><b>探寻 (Seek)</b>：通过碰撞传感器或 I/O 信号，自动寻找打印起始高度 Z0。</li>
        </ul>
        """

    def _get_hardware_protocol_html(self):
        return """
        <h1>3. 下位机硬件与协议手册</h1>
        <p>详细解析 Arduino 挤出机与转台的底层控制逻辑。</p>

        <h2>3.1 Modbus TCP 寄存器定义</h2>
        <table>
            <tr><th>寄存器</th><th>功能描述</th><th>数值范围/含义</th></tr>
            <tr><td>Holding Register 0</td><td>电机 2 (Motor 2) 控制</td><td>1xxx(使能), 2xxx(方向), 4xxx(速度)</td></tr>
            <tr><td>Holding Register 1</td><td>电机 1 (Motor 1) 控制</td><td>同上</td></tr>
        </table>

        <h2>3.2 挤出机逻辑 (ext_modbus.ino)</h2>
        <h3>速度同步公式</h3>
        <p>当发送 <code>4133</code> 时，控制器解析 <code>133</code> 为速度基准值。该值与步进驱动器的细分设置共同决定了最终出料速率。</p>
        <div class="warning">
            <b>安全保护：</b> 软件内置了 3000ms 的自动切断逻辑。如果长时间未接收到更新的速度指令，挤出机会自动停止（防止堆料）。
        </div>

        <h2>3.3 转台同步控制 (rot5.9.ino)</h2>
        <p>通过 <code>HR[0]</code> 传递速度编码，<code>HR[1]</code> 传递目标步数（Circles）。控制器使用硬件定时器产生脉冲，确保旋转角度与机器人 TCP 移动精确匹配。</p>
        """

    def _get_developer_api_html(self):
        return """
        <h1>4. 软件架构与开发参考</h1>
        <p>针对需要二次开发 IDE 或核心算法的研究员。</p>

        <h2>4.1 核心类库：print_lib.py</h2>
        <ul>
            <li><b>平面拟合</b>: 基于 SVD (奇异值分解) 的最小二乘法，用于通过离散采样点计算最优打印平面。</li>
            <li><b>路径转换引擎</b>: 负责将 <code>G1 X.. Y.. Z.. E..</code> 解析为 URScript 姿态数组。</li>
        </ul>

        <h2>4.2 多线程模型</h2>
        <ul>
            <li><b>MonitorThread</b>: 周期性获取机器人 RTDE 数据（关节角、TCP 坐标）。</li>
            <li><b>ScriptSendThread</b>: 负责将生成的脚本分块发送至 30002 端口。</li>
            <li><b>Watchdog</b>: 监控机器人运行状态，若发生碰撞或急停，立即下发 Modbus <code>3000</code> 指令关停挤出机。</li>
        </ul>

        <h2>4.3 通信端口参考</h2>
        <ul>
            <li><b>30002</b>: 机器人主接口（用于发送大型脚本）。</li>
            <li><b>30004</b>: RTDE 接口（用于高速数据监控）。</li>
            <li><b>502</b>: Modbus TCP 端口（用于 Arduino 通信）。</li>
        </ul>
        """
