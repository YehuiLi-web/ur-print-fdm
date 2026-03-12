"""
测试不同的 ComboBox 修复方案
"""
import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QWidget, QComboBox, QListView, QLabel
)
from PyQt6.QtCore import Qt

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ComboBox 修复测试")
        self.resize(400, 500)

        central = QWidget()
        layout = QVBoxLayout(central)
        self.setCentralWidget(central)

        # 测试1: 原始 ComboBox（有问题）
        layout.addWidget(QLabel("1. 原始 ComboBox (应该有覆盖问题):"))
        combo1 = QComboBox()
        combo1.addItems(["选项A", "选项B", "选项C"])
        layout.addWidget(combo1)

        # 测试2: 添加 setView(QListView())
        layout.addWidget(QLabel("\n2. 添加 setView(QListView()):"))
        combo2 = QComboBox()
        combo2.setView(QListView())
        combo2.addItems(["选项A", "选项B", "选项C"])
        layout.addWidget(combo2)

        # 测试3: 可编辑的 ComboBox
        layout.addWidget(QLabel("\n3. 可编辑的 ComboBox (像IP框):"))
        combo3 = QComboBox()
        combo3.setEditable(True)
        combo3.setView(QListView())
        combo3.addItems(["选项A", "选项B", "选项C"])
        layout.addWidget(combo3)

        # 测试4: 设置窗口标志
        layout.addWidget(QLabel("\n4. 设置窗口标志:"))
        combo4 = QComboBox()
        view4 = QListView()
        view4.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        combo4.setView(view4)
        combo4.addItems(["选项A", "选项B", "选项C"])
        layout.addWidget(combo4)

        # 测试5: 设置 InsertPolicy
        layout.addWidget(QLabel("\n5. 设置 InsertPolicy:"))
        combo5 = QComboBox()
        combo5.setView(QListView())
        combo5.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        combo5.addItems(["选项A", "选项B", "选项C"])
        layout.addWidget(combo5)

        # 测试6: 组合方案
        layout.addWidget(QLabel("\n6. 组合方案 (view + flags + policy):"))
        combo6 = QComboBox()
        view6 = QListView()
        view6.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        combo6.setView(view6)
        combo6.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        combo6.addItems(["选项A", "选项B", "选项C"])
        layout.addWidget(combo6)

        layout.addStretch()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())
