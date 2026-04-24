"""测试主题切换功能"""
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from ur_print_fdm.ui.main_window import MainWindow
from ur_print_fdm.ui.theme_manager import get_theme_manager

def test_theme_switching():
    """测试主题切换"""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    theme_mgr = get_theme_manager()

    def switch_theme():
        current = theme_mgr.current_theme_id()
        new_theme = "light" if current == "dark" else "dark"
        print(f"切换主题: {current} -> {new_theme}")
        theme_mgr.set_theme(new_theme)

        # 3秒后再次切换
        QTimer.singleShot(3000, switch_theme)

    # 3秒后开始切换
    QTimer.singleShot(3000, switch_theme)

    sys.exit(app.exec())

if __name__ == "__main__":
    test_theme_switching()
