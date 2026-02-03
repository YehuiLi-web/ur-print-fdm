from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QGroupBox, QFormLayout, 
                             QLabel, QGridLayout, QPushButton, QListWidget, QTextEdit, 
                             QMessageBox, QApplication)
from PyQt6.QtGui import QFont
# ================= 独立的标定面板类 (保持不变) =================
class CalibrationWidget(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main = main_window 
        self.points = [] 
        self.o_idx = -1
        self.x_idx = -1
        self.y_idx = -1
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        
        # 左栏
        left_panel = QWidget(); left_vbox = QVBoxLayout(left_panel)
        grp_live = QGroupBox("实时 TCP (Base)")
        grp_live.setStyleSheet("QGroupBox { font-weight: bold; color: #4CAF50; }")
        live_layout = QFormLayout()
        self.lbl_tcp_pos = QLabel("Pos: 0, 0, 0")
        self.lbl_tcp_rot = QLabel("Rot: 0, 0, 0")
        live_layout.addRow(self.lbl_tcp_pos); live_layout.addRow(self.lbl_tcp_rot)
        grp_live.setLayout(live_layout); left_vbox.addWidget(grp_live)
        
        grp_keys = QGroupBox("关键点采集")
        grid = QGridLayout()
        btn_o = QPushButton("采集 原点 (O)"); btn_o.clicked.connect(lambda: self.capture_point('O'))
        btn_x = QPushButton("采集 X轴方向 (X)"); btn_x.clicked.connect(lambda: self.capture_point('X'))
        btn_y = QPushButton("采集 Y轴方向 (Y)"); btn_y.clicked.connect(lambda: self.capture_point('Y'))
        btn_add = QPushButton("采集 辅助点 (+)"); btn_add.clicked.connect(lambda: self.capture_point('Extra'))
        grid.addWidget(btn_o, 0, 0); grid.addWidget(btn_x, 0, 1)
        grid.addWidget(btn_y, 1, 0); grid.addWidget(btn_add, 1, 1)
        grp_keys.setLayout(grid); left_vbox.addWidget(grp_keys)
        
        grp_list = QGroupBox("采集记录")
        v_list = QVBoxLayout()
        self.pt_list_widget = QListWidget()
        btn_clear = QPushButton("清空所有点"); btn_clear.clicked.connect(self.clear_points)
        v_list.addWidget(self.pt_list_widget); v_list.addWidget(btn_clear)
        grp_list.setLayout(v_list); left_vbox.addWidget(grp_list)
        left_vbox.addStretch()
        layout.addWidget(left_panel, 1)
        
        # 右栏
        right_panel = QWidget(); right_vbox = QVBoxLayout(right_panel)
        grp_res = QGroupBox("计算结果")
        v_res = QVBoxLayout()
        btn_calc = QPushButton("拟合平面 & 计算 Feature")
        btn_calc.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 10px;")
        btn_calc.clicked.connect(self.do_calculate)
        self.txt_result = QTextEdit(); self.txt_result.setReadOnly(True)
        self.txt_result.setFont(QFont("Consolas", 10))
        self.txt_result.setPlaceholderText("采集至少3个点 (O, X, Y) 后点击计算...")
        v_res.addWidget(btn_calc); v_res.addWidget(self.txt_result)
        grp_res.setLayout(v_res); right_vbox.addWidget(grp_res)
        layout.addWidget(right_panel, 2)
        

    # === 修改为 ===
    # === 修改 1: 提高实时显示的精度 ===
    def update_live_tcp(self, tcp, joints):
        if tcp:
            # 原来是 .1f (0.1mm)，现在改为 .3f (0.001mm)
            self.lbl_tcp_pos.setText(f"Pos: {tcp[0]*1000:.3f}, {tcp[1]*1000:.3f}, {tcp[2]*1000:.3f} mm")
            self.lbl_tcp_rot.setText(f"Rot: {tcp[3]:.3f}, {tcp[4]:.3f}, {tcp[5]:.3f} rad")
        else:
            self.lbl_tcp_pos.setText("数据无效")

    def capture_point(self, p_type):
        if not self.main.driver.connected:
            QMessageBox.warning(self, "警告", "请先连接机器人！")
            return
        # 修改这行代码，适配新的 get_status() 返回值
        tcp, _, _,_ = self.main.driver.get_status()
        if not tcp: return
        p_mm = [tcp[0]*1000, tcp[1]*1000, tcp[2]*1000]
        idx = len(self.points); label = ""
        if p_type == 'O': self.o_idx = idx; label = "🔵 原点 (O)"
        elif p_type == 'X': self.x_idx = idx; label = "X轴向 (X)"
        elif p_type == 'Y': self.y_idx = idx; label = "Y轴向 (Y)"
        else: label = f"辅助点 {idx+1}"
        self.points.append(p_mm)
        self.pt_list_widget.addItem(f"{label}: {p_mm[0]:.3f}, {p_mm[1]:.3f}, {p_mm[2]:.3f}")

    def clear_points(self):
        self.points = []; self.pt_list_widget.clear(); self.txt_result.clear()
        self.o_idx = -1; self.x_idx = -1; self.y_idx = -1

    def do_calculate(self):
        if self.o_idx == -1 or self.x_idx == -1 or self.y_idx == -1:
            QMessageBox.warning(self, "数据不足", "必须至少采集 O, X, Y 三个关键点！")
            return
        ordered_points = [self.points[self.o_idx], self.points[self.x_idx], self.points[self.y_idx]]
        for i, p in enumerate(self.points):
            if i not in [self.o_idx, self.x_idx, self.y_idx]: ordered_points.append(p)
        feat_str, log = self.main.print_lib.fit_plane_feature(ordered_points)
        if feat_str:
            self.txt_result.setText("计算成功!\n\n" + log)
            self.txt_result.append("\n=== URScript 代码 ===")
            self.txt_result.append(f"global feature1 = {feat_str}")
            QApplication.clipboard().setText(feat_str)
            self.main.log("标定成功，Feature 字符串已复制到剪贴板。")
        else:
            self.txt_result.setText("计算失败\n" + log)

