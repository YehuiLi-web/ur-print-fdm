"""
测试 QComboBox 下拉框问题
运行此脚本查看带图标和不带图标的 ComboBox 区别
"""
import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QToolBar, QComboBox, QLabel, QWidget, QVBoxLayout
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import QSize

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ComboBox 测试")
        self.resize(600, 200)

        toolbar = QToolBar("测试工具栏")
        toolbar.setIconSize(QSize(20, 20))
        self.addToolBar(toolbar)

        # ComboBox 1: 不带图标（类似 ip_combo）
        toolbar.addWidget(QLabel("无图标:"))
        combo1 = QComboBox()
        combo1.setEditable(True)
        combo1.addItems(["选项A", "选项B", "选项C"])
        combo1.setMinimumWidth(100)
        toolbar.addWidget(combo1)

        toolbar.addSeparator()

        # ComboBox 2: 带图标（类似 run_mode_combo）
        toolbar.addWidget(QLabel("带图标:"))
        combo2 = QComboBox()
        # 使用系统标准图标
        icon1 = self.style().standardIcon(self.style().StandardPixmap.SP_MediaPlay)
        icon2 = self.style().standardIcon(self.style().StandardPixmap.SP_MediaStop)
        combo2.addItem(icon1, "生产模式", "production")
        combo2.addItem(icon2, "直连模式", "direct")
        combo2.setMinimumWidth(100)
        toolbar.addWidget(combo2)

        toolbar.addSeparator()

        # ComboBox 3: 带图标但不可编辑，设置 view
        toolbar.addWidget(QLabel("带图标+修复:"))
        combo3 = QComboBox()
        combo3.addItem(icon1, "生产模式", "production")
        combo3.addItem(icon2, "直连模式", "direct")
        combo3.setMinimumWidth(100)
        # 尝试修复：设置 frame 为 false
        combo3.view().window().setWindowFlags(
            combo3.view().window().windowFlags() |
            combo3.view().window().windowFlags()
        )
        toolbar.addWidget(combo3)

        # 中央 widget
        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addWidget(QLabel("点击上方的下拉框测试"))
        layout.addWidget(QLabel("观察：带图标的下拉框是否有不同的行为"))
        self.setCentralWidget(central)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())
