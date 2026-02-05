"""
测试 Fusion 样式 + QSS 对 ComboBox 的影响
"""
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QComboBox, QListView, QLabel
from PyQt6.QtCore import Qt

# 模拟项目的 QSS（简化版）
SIMPLE_QSS = """
QComboBox {
    background-color: #2b2b2b;
    border: 1px solid #3c3c3c;
    border-radius: 4px;
    padding: 5px 8px;
    color: #e0e0e0;
    min-height: 22px;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 22px;
    border-left: 1px solid #3c3c3c;
}

QComboBox QAbstractItemView {
    background-color: #1e1e1e;
    border: 1px solid #3c3c3c;
    color: #e0e0e0;
    selection-background-color: #0d7377;
    selection-color: #ffffff;
    outline: none;
    padding: 4px 0;
    min-width: 100%;
}

QComboBox QAbstractItemView::item {
    padding: 6px 8px;
    margin: 1px 0;
    border-radius: 3px;
    min-height: 20px;
}
"""

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("测试 Fusion + QSS 影响")
        self.resize(400, 300)

        central = QWidget()
        layout = QVBoxLayout(central)
        self.setCentralWidget(central)

        layout.addWidget(QLabel("测试1: 普通 ComboBox"))
        combo1 = QComboBox()
        combo1.addItems(["选项A", "选项B", "选项C"])
        layout.addWidget(combo1)

        layout.addWidget(QLabel("\n测试2: setView(QListView())"))
        combo2 = QComboBox()
        combo2.setView(QListView())
        combo2.addItems(["选项A", "选项B", "选项C"])
        layout.addWidget(combo2)

        layout.addWidget(QLabel("\n测试3: setView + WindowFlags"))
        combo3 = QComboBox()
        view3 = QListView()
        view3.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        combo3.setView(view3)
        combo3.addItems(["选项A", "选项B", "选项C"])
        layout.addWidget(combo3)

        layout.addStretch()

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 模拟项目设置
    app.setStyle("Fusion")
    app.setStyleSheet(SIMPLE_QSS)

    window = TestWindow()
    window.show()
    sys.exit(app.exec())
