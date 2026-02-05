"""测试UI启动"""
import sys
from PyQt6.QtWidgets import QApplication

print("1. 导入QApplication成功")

try:
    from ur_print_fdm.ui.theme_manager import get_theme_manager
    print("2. 导入theme_manager成功")
except Exception as e:
    print(f"2. 导入theme_manager失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    app = QApplication(sys.argv)
    print("3. 创建QApplication成功")
except Exception as e:
    print(f"3. 创建QApplication失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    theme_mgr = get_theme_manager()
    print("4. 获取ThemeManager成功")
except Exception as e:
    print(f"4. 获取ThemeManager失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    theme_mgr.set_theme("dark")
    print("5. 设置主题成功")
except Exception as e:
    print(f"5. 设置主题失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    from ur_print_fdm.ui.main_window import URPrintIDE
    print("6. 导入URPrintIDE成功")
except Exception as e:
    print(f"6. 导入URPrintIDE失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    win = URPrintIDE()
    print("7. 创建URPrintIDE实例成功")
    win.show()
    print("8. 显示窗口成功")
    print("9. 程序启动成功！窗口应该已经显示。")
except Exception as e:
    print(f"7-8. 创建/显示窗口失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 不执行事件循环，只测试启动
print("测试完成，退出。")
