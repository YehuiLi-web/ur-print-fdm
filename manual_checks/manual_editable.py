"""
测试可编辑属性对弹出框的影响
"""
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QComboBox, QLabel

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("测试可编辑属性")
        self.resize(400, 300)

        # 应用 Fusion 样式
        app = QApplication.instance()
        app.setStyle("Fusion")

        central = QWidget()
        layout = QVBoxLayout(central)
        self.setCentralWidget(central)

        # 测试1: 不可编辑
        layout.addWidget(QLabel("1. 不可编辑 ComboBox:"))
        combo1 = QComboBox()
        combo1.addItems(["选项A", "选项B", "选项C"])
        layout.addWidget(combo1)

        # 测试2: 可编辑
        layout.addWidget(QLabel("\n2. 可编辑 ComboBox:"))
        combo2 = QComboBox()
        combo2.setEditable(True)
        combo2.addItems(["选项A", "选项B", "选项C"])
        layout.addWidget(combo2)

        # 测试3: 可编辑 + InsertPolicy
        layout.addWidget(QLabel("\n3. 可编辑 + NoInsert:"))
        combo3 = QComboBox()
        combo3.setEditable(True)
        combo3.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        combo3.addItems(["选项A", "选项B", "选项C"])
        layout.addWidget(combo3)

        layout.addStretch()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())
